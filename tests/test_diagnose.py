"""Tests for the technique-independent diagnostics.

Every detector is tested in BOTH directions: it must fire on data with the effect
injected, and must NOT fire on matched data without it. A detector tested only on
positive cases is indistinguishable from one that always fires, and a report generator
that always finds something is worse than none.
"""

import numpy as np
import pytest

from beamreport.contract import Results, Sidecar
from beamreport.diagnose import (
    amplitude_across,
    bimodality,
    bound_pileup,
    clears_null,
    diagnose,
    fit_trend,
    param_residual_correlation,
    systematic_vs_scatter,
)

RNG = lambda s=0: np.random.default_rng(s)  # noqa: E731


# ------------------------------------------------------------------ trend fitting


def test_flat_residual_reads_as_constant():
    r = RNG(1).normal(0, 1, 400)
    c = np.linspace(0, 360, 400)
    assert fit_trend(c, r, "deg")["model"] == "constant"


def test_periodic_residual_is_found_with_right_amplitude():
    c = np.linspace(0, 360, 600)
    r = 5.0 * np.cos(np.radians(c)) + RNG(2).normal(0, 0.5, 600)
    f = fit_trend(c, r, "deg")
    assert f["model"] == "periodic"
    assert f["amplitude"] == pytest.approx(5.0, rel=0.1)


def test_linear_residual_is_found():
    c = np.linspace(0, 10, 400)
    r = 2.0 * c + RNG(3).normal(0, 0.5, 400)
    assert fit_trend(c, r, "s")["model"] == "linear"


def test_periodic_not_fitted_to_a_non_angular_axis():
    """A 0-360 delay axis in seconds must not be wrapped as if it were an angle."""
    c = np.linspace(0, 360, 400)
    r = 5.0 * np.cos(np.radians(c)) + RNG(4).normal(0, 0.5, 400)
    assert fit_trend(c, r, "s")["model"] != "periodic"


def test_amplitude_constant_versus_growing():
    rng = RNG(5)
    c = rng.uniform(0, 360, 3000)
    other = rng.uniform(1, 5, 3000)

    flat = 4.0 * np.cos(np.radians(c)) + rng.normal(0, 0.3, 3000)
    assert amplitude_across(c, flat, other, "deg")["verdict"] == "constant"

    grow = other * np.cos(np.radians(c)) + rng.normal(0, 0.3, 3000)
    assert amplitude_across(c, grow, other, "deg")["verdict"] == "growing"


# --------------------------------------------------- systematic versus scatter


def test_common_offset_is_detected():
    rng = RNG(6)
    ids = np.repeat(np.arange(60), 20)
    r = 3.0 + rng.normal(0, 1.0, ids.size)  # every object shares +3
    v = systematic_vs_scatter(ids, r)
    assert v["verdict"] == "common_offset"
    assert v["mean"] == pytest.approx(3.0, abs=0.2)


def test_per_object_spread_is_not_called_a_common_offset():
    rng = RNG(7)
    ids = np.repeat(np.arange(60), 20)
    per_obj = rng.normal(0, 3.0, 60)  # each object its own offset, mean zero
    r = per_obj[ids] + rng.normal(0, 0.5, ids.size)
    assert systematic_vs_scatter(ids, r)["verdict"] == "no_common_offset"


def test_small_but_significant_mean_is_mixed_not_common():
    """Mean clearly nonzero (t=6) yet dwarfed by per-object spread (ratio=0.3)."""
    rng = RNG(8)
    ids = np.repeat(np.arange(400), 12)
    per_obj = rng.normal(1.5, 5.0, 400)
    r = per_obj[ids] + rng.normal(0, 0.3, ids.size)
    v = systematic_vs_scatter(ids, r)
    assert v["verdict"] == "mixed"
    assert v["t"] > 3 and v["ratio"] < 1


def test_tiny_mean_is_not_reported_at_all():
    """An insignificant mean must not be dressed up as a systematic."""
    rng = RNG(18)
    ids = np.repeat(np.arange(400), 12)
    per_obj = rng.normal(0.5, 5.0, 400)  # t = 2.0
    r = per_obj[ids] + rng.normal(0, 0.3, ids.size)
    assert systematic_vs_scatter(ids, r)["verdict"] == "no_common_offset"


# ------------------------------------------------- parameter/residual coupling


def test_parameter_absorbing_misfit_is_detected():
    rng = RNG(9)
    p = rng.normal(0, 1, 200)
    assert param_residual_correlation(p, -0.8 * p + rng.normal(0, 0.3, 200))["verdict"] == "correlated"


def test_supported_parameter_is_not_flagged():
    rng = RNG(10)
    p = rng.normal(0, 1, 200)
    assert param_residual_correlation(p, rng.normal(0, 0.3, 200))["verdict"] == "supported"


# ----------------------------------------------------------- population splits


def test_two_separated_populations_are_found():
    rng = RNG(11)
    x = np.concatenate([rng.normal(-4, 1, 200), rng.normal(4, 1, 200)])
    assert bimodality(x)["verdict"] == "two"


def test_unimodal_is_not_called_bimodal():
    assert bimodality(RNG(12).normal(0, 1, 400))["verdict"] == "one"


def test_skewed_unimodal_is_not_called_bimodal():
    """BIC alone prefers two components here; the separation guard must stop it."""
    assert bimodality(RNG(13).lognormal(0, 0.6, 500))["verdict"] == "one"


# ---------------------------------------------------------------------- bounds


def test_pileup_at_bound_is_detected():
    rng = RNG(14)
    x = np.concatenate([rng.uniform(-1, 1, 200), np.full(40, 0.999)])
    assert bound_pileup(x, -1, 1)["verdict"] == "pileup"


def test_no_pileup_when_bound_is_not_reached():
    assert bound_pileup(RNG(15).normal(0, 0.2, 400), -1, 1)["verdict"] == "no_pileup"


# ----------------------------------------------------------------------- nulls


def test_value_clearing_its_null():
    assert clears_null(10.0, RNG(16).normal(0, 1, 200))["verdict"] == "cleared"


def test_value_inside_its_null_is_not_quotable():
    assert clears_null(0.4, RNG(17).normal(0, 1, 200))["verdict"] == "not_cleared"


# --------------------------------------------------------------- orchestration


def _submission(with_offset: bool, seed: int = 20):
    rng = RNG(seed)
    n_obj, n_per = 50, 30
    ids = np.repeat(np.arange(n_obj), n_per).astype(float)
    az = rng.uniform(0, 360, ids.size)
    delay = rng.uniform(0, 1, ids.size)
    r = rng.normal(0, 1.0, ids.size)
    if with_offset:
        r = r + 4.0 * np.cos(np.radians(az)) + 2.5
    results = Results(
        object_id=np.arange(n_obj),
        columns={"position_x": (rng.normal(0, 1, n_obj), "um")},
    )
    sidecar = Sidecar(
        table=np.column_stack([ids, az, delay, r]),
        columns=["object_id", "azimuth", "delay", "d_signal"],
        units=["", "deg", "s", "counts"],
        roles=["id", "coord", "coord", "residual"],
    )
    return results, sidecar


def test_diagnose_finds_injected_systematics():
    findings = diagnose(*_submission(with_offset=True))
    syms = {f.symptom for f in findings}
    assert "systematic.common_offset" in syms
    assert any(s.startswith("trend.") for s in syms)


def test_diagnose_stays_quiet_on_clean_data():
    findings = diagnose(*_submission(with_offset=False))
    syms = {f.symptom for f in findings if f.symptom}
    assert not syms, f"false positives on clean data: {syms}"


def test_clean_data_still_reports_a_solid_finding():
    """Silence and 'nothing wrong' must be distinguishable on the page."""
    findings = diagnose(*_submission(with_offset=False))
    assert any(f.level == "solid" for f in findings)


def test_findings_are_ordered_systematic_first():
    findings = diagnose(*_submission(with_offset=True))
    levels = [f.level for f in findings]
    assert levels.index("systematic") < max(
        (i for i, l in enumerate(levels) if l == "solid"), default=len(levels)
    )
