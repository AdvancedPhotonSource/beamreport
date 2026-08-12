"""The three detectors the DFXM doc set exposed as missing.

Each is tested in both directions. The first one matters most: it is the class of error
a residual-based diagnostic cannot see at all, so a test that only checks it fires would
not distinguish it from a detector that always fires.
"""

import numpy as np
import pytest

from beamreport import Finding, Provenance, Results, Sidecar, build, envelope
from beamreport.diagnose import (
    at_floor,
    diagnose,
    scale_against_expectation,
    uncertainty_calibration,
)

RNG = np.random.default_rng


# --- scale against an independent expectation --------------------------------


def test_suppressed_magnitude_is_detected():
    r = scale_against_expectation(measured=1.5, expected=100.0)
    assert r["verdict"] == "suppressed"
    assert r["ratio"] == pytest.approx(0.015)


def test_inflated_magnitude_is_detected():
    assert scale_against_expectation(measured=300.0, expected=100.0)["verdict"] == "inflated"


def test_consistent_magnitude_is_not_flagged():
    assert scale_against_expectation(measured=105.0, expected=100.0)["verdict"] == "consistent"


def test_scale_error_is_invisible_in_the_residual():
    """The reason this detector has to exist.

    Scale the data by 1/67 and refit a free amplitude: the residual is statistically
    indistinguishable from the unscaled case, so no residual-based test can see it.
    This is the DFXM pedestal-dilution failure in miniature.
    """
    rng = RNG(0)
    x = np.linspace(0, 1, 500)
    truth = 100.0 * np.sin(2 * np.pi * x)
    noise = rng.normal(0, 1.0, x.size)

    def refit_residual(scale):
        y = scale * truth + scale * noise
        amp = float(np.dot(y, truth) / np.dot(truth, truth))   # free amplitude
        return y - amp * truth

    full = np.std(refit_residual(1.0)) / 1.0
    diluted = np.std(refit_residual(1 / 67)) / (1 / 67)
    assert full == pytest.approx(diluted, rel=1e-6)            # identical, in units of scale


def test_diagnose_reports_a_suppressed_scale():
    results = Results(object_id=np.arange(5), columns={"a": (np.ones(5), "um")})
    f = diagnose(results, expectations={"mosaicity amplitude": (1.5, 100.0)})
    assert any(x.symptom == "scale.suppressed" for x in f)
    assert any("free amplitude" in x.statement for x in f)


def test_diagnose_says_nothing_without_an_expectation():
    """The expectation must come from outside the fit; it is never inferred."""
    results = Results(object_id=np.arange(5), columns={"a": (np.ones(5), "um")})
    assert not [x for x in diagnose(results) if x.symptom.startswith("scale.")]


# --- uncertainty calibration --------------------------------------------------


def test_underestimated_errors_are_detected():
    rng = RNG(1)
    r = rng.normal(0, 3.0, 500)
    assert uncertainty_calibration(r, np.full(500, 1.0))["verdict"] == "underestimated"


def test_overestimated_errors_are_detected():
    rng = RNG(2)
    r = rng.normal(0, 1.0, 500)
    assert uncertainty_calibration(r, np.full(500, 4.0))["verdict"] == "overestimated"


def test_calibrated_errors_are_not_flagged():
    rng = RNG(3)
    r = rng.normal(0, 1.0, 500)
    out = uncertainty_calibration(r, np.full(500, 1.0))
    assert out["verdict"] == "calibrated"
    assert out["chi2_per_dof"] == pytest.approx(1.0, abs=0.15)


def _sidecar_with_weight(resid_sigma, declared_sigma, w_unit="um"):
    rng = RNG(4)
    n_obj, n_per = 30, 20
    ids = np.repeat(np.arange(n_obj), n_per).astype(float)
    az = rng.uniform(0, 360, ids.size)
    r = rng.normal(0, resid_sigma, ids.size)
    w = np.full(ids.size, declared_sigma)
    return Sidecar(
        table=np.column_stack([ids, az, r, w]),
        columns=["object_id", "azimuth", "d_signal", "sigma"],
        units=["", "deg", "um", w_unit],
        roles=["id", "coord", "residual", "weight"],
    )


def test_miscalibration_fires_through_diagnose():
    results = Results(object_id=np.arange(30), columns={"x": (np.ones(30), "um")})
    f = diagnose(results, sidecar=_sidecar_with_weight(3.0, 1.0))
    assert any(x.symptom == "uncertainty.miscalibrated" for x in f)


def test_weight_in_other_units_is_not_guessed_at():
    """A weight could be 1/sigma^2. Guessing would be wrong by orders of magnitude,
    so a unit mismatch means the check is skipped, not approximated."""
    results = Results(object_id=np.arange(30), columns={"x": (np.ones(30), "um")})
    f = diagnose(results, sidecar=_sidecar_with_weight(3.0, 1.0, w_unit="1/um^2"))
    assert not any(x.symptom == "uncertainty.miscalibrated" for x in f)


# --- floor limited ------------------------------------------------------------


def test_values_piled_at_the_floor_are_detected():
    x = np.concatenate([np.full(60, 0.01), np.linspace(0.05, 1.0, 140)])
    assert at_floor(x, floor=0.01)["verdict"] == "at_floor"


def test_values_above_the_floor_are_not_flagged():
    assert at_floor(np.linspace(0.5, 1.0, 200), floor=0.01)["verdict"] == "above_floor"


def test_floor_finding_says_it_measures_the_pipeline():
    vals = np.concatenate([np.full(60, 0.01), np.linspace(0.05, 1.0, 140)])
    results = Results(object_id=np.arange(vals.size), columns={"tau": (vals, "s")})
    f = diagnose(results, floors={"tau": (0.01, "frame time")})
    hit = [x for x in f if x.symptom == "floor.limited"]
    assert hit and "measure the pipeline, not the" in hit[0].statement
    assert "frame time" in hit[0].statement


# --- envelope wiring ----------------------------------------------------------

ENV = """
# T envelope
**Last checked: 2026-08-12** - Owner: A
## 1. Fixed
## 2. Configured
## 4. Derived limits
| Quantity | Limit | From |
|---|---|---|
| Fastest resolvable timescale (`tau`) | 0.01 s | frame time |
| Smallest separable feature (`step`) | not a fixed number | per-run grid step |
| Confidence that means real | not a fixed number | phase cap |
## 5. Did not
"""


def test_envelope_yields_static_floors_only(tmp_path):
    p = tmp_path / "ENVELOPE.md"
    p.write_text(ENV)
    assert envelope.floors(p) == {"tau": (0.01, "frame time")}


def test_envelope_declining_a_number_is_not_a_missing_floor(tmp_path):
    """`step` has a floor set per run. The envelope says so without giving a value,
    which is different from saying there is no floor."""
    p = tmp_path / "ENVELOPE.md"
    p.write_text(ENV)
    cols = envelope.floor_columns(p)
    assert set(cols) == {"tau", "step"}
    assert cols["step"] == "per-run grid step"
    assert "step" not in envelope.floors(p)


def test_build_reads_floors_from_an_envelope_path(tmp_path):
    (tmp_path / "ENVELOPE.md").write_text(ENV)
    par = tmp_path / "p.txt"
    par.write_text("x")
    vals = np.concatenate([np.full(60, 0.01), np.linspace(0.05, 1.0, 140)])
    out = build(
        results=Results(object_id=np.arange(vals.size), columns={"tau": (vals, "s")}),
        provenance=Provenance(inputs=[par], command="run.py", code_version="v1"),
        floors=tmp_path / "ENVELOPE.md",
        title="floor wiring",
        out=tmp_path / "r.html",
    )
    assert "measure the pipeline" in out.read_text()


# --- what the Au3 adversarial pass found (2026-08-12) -------------------------

ENV_GOV = """
# T envelope
**Last checked: 2026-08-12** - Owner: A
## 1. Fixed
| Property | Value | Provenance | What it makes unobtainable | Substitute |
|---|---|---|---|---|
| Beam shape (`trend.amplitude_growing`) | line | station | Position along the beam is weakly constrained; not a defect. | Report orientation instead. |
## 2. Configured
| p | used | range | limited by | buys |
|---|---|---|---|---|
| frame time | 10 ms | 5-100 | limited by readout | speed |
## 3. Intrinsic
## 4. Derived limits
"""


def test_envelope_governance_is_parsed():
    import tempfile, pathlib
    from beamreport import envelope
    from beamreport.finding import SYMPTOMS
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "ENVELOPE.md"
        p.write_text(ENV_GOV)
        g = envelope.governed(p, known=set(SYMPTOMS))
    assert g["trend.amplitude_growing"]["tier"] == "fixed"
    assert "not a defect" in g["trend.amplitude_growing"]["text"]


def test_governed_finding_withholds_its_lever(tmp_path):
    """The envelope outranks the reference. On Au3 the report recommended an Lsd
    recalibration for a residual the same doc set calls a fixed property."""
    from beamreport.render import Page, render
    f = Finding(symptom="trend.amplitude_growing", level="systematic",
                title="amplitude grows", statement="s",
                lever="Refine Lsd against a calibrant.",
                governed={"tier": "fixed", "text": "not a defect", "property": "Beam shape",
                          "substitute": ""})
    html = render(Page(title="t", provenance={"a": "b"}, findings=[f]))
    assert "Lever, withheld" in html
    assert "envelope says this is fixed" in html
    assert '<p class="f-l">' not in html          # never rendered as advice


def test_ungoverned_finding_still_gives_its_lever():
    from beamreport.render import Page, render
    f = Finding(symptom="trend.amplitude_growing", level="systematic",
                title="t", statement="s", lever="Recalibrate.")
    html = render(Page(title="t", provenance={"a": "b"}, findings=[f]))
    assert '<p class="f-l">' in html and "withheld" not in html


def test_narrow_azimuthal_coverage_is_refused_not_fitted():
    """A sliver of the circle gave amplitude 1310 um against a ~150 um real scale."""
    from beamreport.diagnose import fit_trend
    rng = RNG(11)
    eta = np.concatenate([rng.uniform(-96, -94, 20), rng.uniform(94, 96, 20)])
    r = 150.0 * np.cos(np.radians(eta)) + rng.normal(0, 10, eta.size)
    f = fit_trend(eta, r, "deg")
    assert f.get("periodic_refused")
    assert f["model"] != "periodic"


def test_shrinking_amplitude_is_not_called_growing():
    """abs(growth) > 0.5 labelled a large shrink as 'growing'."""
    from beamreport.diagnose import amplitude_across
    rng = RNG(12)
    eta = rng.uniform(0, 360, 4000)
    other = rng.choice([1., 2., 3., 4., 5.], 4000)
    r = (6.0 - other) * 40.0 * np.cos(np.radians(eta)) + rng.normal(0, 3, eta.size)
    out = amplitude_across(eta, r, other, "deg")
    assert out["verdict"] == "shrinking"
    assert out["growth_fraction"] < 0
