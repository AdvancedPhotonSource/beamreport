"""Tests for the contract refusals.

Each test names the SPEC rule it guards. A refusal that stops firing is a silent
degradation in a report generator, which is worse than a crash because the page still
looks authoritative.
"""

import numpy as np
import pytest

from beamreport import ContractError, Provenance, Quality, Results, Sidecar, validate
from beamreport.contract import check_consistency


def make_results(n=4):
    return Results(
        object_id=np.arange(n),
        columns={"position_x": (np.linspace(0, 1, n), "um")},
    )


def make_provenance(tmp_path):
    p = tmp_path / "params.txt"
    p.write_text("threshold = 3\n")
    return Provenance(inputs=[p], command="run.py --in params.txt", code_version="abc1234")


def make_sidecar(n_obs=20, n_obj=4, resid=None):
    rng = np.random.default_rng(0)
    ids = rng.integers(0, n_obj, n_obs).astype(float)
    coord_a = rng.uniform(0, 360, n_obs)
    coord_b = rng.uniform(0, 1, n_obs)
    if resid is None:
        resid = rng.normal(0, 1, n_obs)
    return Sidecar(
        table=np.column_stack([ids, coord_a, coord_b, resid]),
        columns=["object_id", "azimuth", "delay", "d_amplitude"],
        units=["", "deg", "s", "counts"],
        roles=["id", "coord", "coord", "residual"],
    )


# --- SPEC 8.1: a column with no declared unit is refused ---------------------


def test_results_column_without_unit_is_refused(tmp_path):
    r = Results(object_id=np.arange(3), columns={"radius": (np.ones(3), "")})
    with pytest.raises(ContractError) as e:
        validate(r, make_provenance(tmp_path))
    assert any(p.code == "R005" for p in e.value.problems)


def test_sidecar_coord_without_unit_is_refused(tmp_path):
    s = make_sidecar()
    s.units = ["", "", "s", "counts"]  # azimuth lost its unit
    with pytest.raises(ContractError) as e:
        validate(make_results(), make_provenance(tmp_path), sidecar=s)
    assert any(p.code == "S008" for p in e.value.problems)


def test_dimensionless_marker_is_accepted(tmp_path):
    r = Results(object_id=np.arange(3), columns={"ratio": (np.ones(3), "1")})
    validate(r, make_provenance(tmp_path))  # must not raise


# --- SPEC 8.2: a number with no provenance does not go on the page -----------


def test_provenance_without_inputs_is_refused():
    with pytest.raises(ContractError) as e:
        validate(make_results(), Provenance(inputs=[], command="x"))
    assert any(p.code == "P001" for p in e.value.problems)


def test_provenance_without_command_is_refused(tmp_path):
    p = tmp_path / "params.txt"
    p.write_text("x")
    with pytest.raises(ContractError) as e:
        validate(make_results(), Provenance(inputs=[p], command="   "))
    assert any(p.code == "P002" for p in e.value.problems)


def test_missing_path_warns_but_does_not_refuse():
    warns = validate(
        make_results(), Provenance(inputs=["/nowhere/at/all"], command="run.py", code_version="v1")
    )
    assert any(p.code == "P003" for p in warns)


# --- Sidecar role declaration ------------------------------------------------


def test_sidecar_without_residual_is_refused(tmp_path):
    s = make_sidecar()
    s.roles = ["id", "coord", "coord", "aux"]
    with pytest.raises(ContractError) as e:
        validate(make_results(), make_provenance(tmp_path), sidecar=s)
    assert any(p.code == "S005" for p in e.value.problems)


def test_sidecar_without_coord_is_refused(tmp_path):
    s = make_sidecar()
    s.roles = ["id", "aux", "aux", "residual"]
    s.units = ["", "", "", "counts"]
    with pytest.raises(ContractError) as e:
        validate(make_results(), make_provenance(tmp_path), sidecar=s)
    assert any(p.code == "S006" for p in e.value.problems)


def test_single_coordinate_warns(tmp_path):
    s = make_sidecar()
    s.roles = ["id", "coord", "aux", "residual"]
    s.units = ["", "deg", "", "counts"]
    warns = validate(make_results(), make_provenance(tmp_path), sidecar=s)
    assert any(p.code == "S007" for p in warns)


def test_unknown_role_is_refused(tmp_path):
    s = make_sidecar()
    s.roles = ["id", "coord", "coordinate", "residual"]
    with pytest.raises(ContractError) as e:
        validate(make_results(), make_provenance(tmp_path), sidecar=s)
    assert any(p.code == "S003" for p in e.value.problems)


def test_mismatched_column_lengths_are_refused(tmp_path):
    s = make_sidecar()
    s.columns = ["object_id", "azimuth", "delay"]
    with pytest.raises(ContractError) as e:
        validate(make_results(), make_provenance(tmp_path), sidecar=s)
    assert any(p.code == "S002" for p in e.value.problems)


# --- The sign rule: squared residuals destroy the information we need --------


def test_squared_residual_warns(tmp_path):
    rng = np.random.default_rng(1)
    squared = rng.normal(0, 1, 20) ** 2
    s = make_sidecar(resid=squared)
    warns = validate(make_results(), make_provenance(tmp_path), sidecar=s)
    assert any(p.code == "S009" for p in warns)


def test_signed_residual_does_not_warn(tmp_path):
    warns = validate(make_results(), make_provenance(tmp_path), sidecar=make_sidecar())
    assert not any(p.code == "S009" for p in warns)


# --- id consistency: silently-wrong aggregation is the worst failure ---------


def test_orphan_observation_ids_are_refused():
    r = make_results(n=3)
    s = make_sidecar(n_obj=9)  # ids up to 8, results only know 0-2
    problems = check_consistency(r, s)
    assert any(p.code == "X001" and p.level == "error" for p in problems)


def test_unobserved_object_warns():
    r = make_results(n=40)
    s = make_sidecar(n_obj=3)
    problems = check_consistency(r, s)
    assert any(p.code == "X002" and p.level == "warning" for p in problems)


# --- general ----------------------------------------------------------------


def test_clean_submission_passes(tmp_path):
    warns = validate(
        make_results(),
        make_provenance(tmp_path),
        quality=Quality(values=np.linspace(0.2, 0.9, 4), name="explained variance", threshold=0.5),
        sidecar=make_sidecar(),
    )
    assert not [p for p in warns if p.level == "error"]


def test_strict_promotes_warnings_to_errors(tmp_path):
    with pytest.raises(ContractError):
        validate(
            make_results(),
            make_provenance(tmp_path),
            quality=Quality(values=np.linspace(0.2, 0.9, 4), name="q"),  # no threshold -> Q004
            sidecar=make_sidecar(),
            strict=True,
        )


def test_all_errors_reported_at_once(tmp_path):
    r = Results(object_id=np.array([1, 1, 2]), columns={"x": (np.ones(3), "")})
    with pytest.raises(ContractError) as e:
        validate(r, Provenance(inputs=[], command=""))
    codes = {p.code for p in e.value.problems}
    assert {"R002", "R005", "P001", "P002"} <= codes
