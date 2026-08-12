"""Tests for diagnosis-reference parsing/matching and page assembly."""

import numpy as np
import pytest

from beamreport import Plate, Provenance, Quality, Results, Sidecar, build
from beamreport.finding import Finding
from beamreport.reference import Entry, ReferenceError, apply, coverage, parse
from beamreport.render import Page, RenderError, render

GOOD = """
## Detector centre offset
symptom: trend.amplitude_constant
coord: azimuth

**Test.** Compare the amplitude across bins of radius. Constant in absolute units
means a rigid centre shift; growing with radius means something else.

**Cause.** A rigid detector-centre offset.

**Lever.** Recalibrate against a standard and re-index.

## A common offset in any channel
symptom: systematic.common_offset

**Test.** Compare the mean of the per-object medians against their spread.

**Lever.** Refine the shared parameter, not the per-object ones.
"""


def test_parses_entries_and_sections():
    e = parse(GOOD)
    assert len(e) == 2
    assert e[0].symptom == "trend.amplitude_constant"
    assert e[0].coord == "azimuth"
    assert "rigid centre shift" in e[0].test
    assert e[0].lever.startswith("Recalibrate")
    assert e[1].cause is None


def test_entry_without_test_is_refused():
    with pytest.raises(ReferenceError, match="Test"):
        parse("## X\nsymptom: systematic.common_offset\n\n**Lever.** Do a thing.\n")


def test_entry_without_symptom_is_refused():
    with pytest.raises(ReferenceError, match="symptom"):
        parse("## X\n\n**Test.** Something.\n")


def test_unknown_symptom_is_refused_and_lists_valid_ones():
    with pytest.raises(ReferenceError, match="Either use a generic symptom"):
        parse("## X\nsymptom: trend.wobbly\n\n**Test.** Something.\n")


# --- technique-local symptoms (DOCS_SPEC §5b) ---------------------------------

LOCAL = """
## Local symptoms

| symptom | emitted by |
|---|---|
| `pedestal_dilution` | moment reduction, Notebook 1a |

## Amplitude far too small
symptom: pedestal_dilution

**Test.** Recompute on subtracted frames; if it moves < 10% the pedestal is not the cause.

**Lever.** Subtract the background before the moment.
"""


def test_declared_local_symptom_is_accepted():
    e = parse(LOCAL)
    assert len(e) == 1 and e[0].symptom == "pedestal_dilution"


def test_local_declaration_table_is_not_parsed_as_an_entry():
    assert all(x.title != "Local symptoms" for x in parse(LOCAL))


def test_undeclared_local_symptom_still_refused():
    with pytest.raises(ReferenceError):
        parse(LOCAL.replace("| `pedestal_dilution` | moment reduction, Notebook 1a |", ""))


def test_local_symptoms_maps_name_to_emitter():
    from beamreport.reference import local_symptoms
    assert local_symptoms(LOCAL)["pedestal_dilution"].startswith("moment reduction")


def test_most_specific_entry_wins():
    entries = parse(GOOD)
    scoped = Finding(symptom="trend.amplitude_constant", level="systematic",
                     title="t", statement="s", coord="azimuth")
    apply([scoped], entries)
    assert scoped.cause == "A rigid detector-centre offset."


def test_scoped_entry_does_not_match_a_different_coord():
    entries = parse(GOOD)
    other = Finding(symptom="trend.amplitude_constant", level="systematic",
                    title="t", statement="s", coord="delay")
    apply([other], entries)
    assert other.lever is None


def test_coverage_names_the_unexplained():
    entries = parse(GOOD)
    fs = [
        Finding(symptom="systematic.common_offset", level="systematic", title="a", statement="b"),
        Finding(symptom="split.bimodal", level="caution", title="c", statement="d"),
    ]
    apply(fs, entries)
    cov = coverage(fs, entries)
    assert cov["n_symptoms"] == 2 and cov["n_explained"] == 1
    assert cov["unexplained"] == ["split.bimodal"]


# ------------------------------------------------------------------- rendering


def _prov(tmp_path):
    p = tmp_path / "params.txt"
    p.write_text("x")
    return Provenance(inputs=[p], command="run.py", code_version="v1")


def test_page_without_provenance_is_refused():
    with pytest.raises(RenderError, match="provenance"):
        render(Page(title="t"))


def test_stretched_spatial_plate_is_refused(tmp_path):
    img = tmp_path / "f.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    page = Page(title="t", provenance={"a": "b"},
                plates=[Plate(img, "map", spatial=True, aspect_equal=False)])
    with pytest.raises(RenderError, match="aspect"):
        render(page)


def test_overview_child_without_url_is_refused():
    page = Page(title="t", provenance={"a": "b"}, children=[("G31", "", "blurb")])
    with pytest.raises(RenderError, match="URL"):
        render(page)


def test_unexplained_symptom_is_stated_on_the_page():
    f = Finding(symptom="split.bimodal", level="caution", title="split", statement="two groups")
    html = render(Page(title="t", provenance={"a": "b"}, findings=[f]))
    assert "No diagnosis-reference entry" in html and "split.bimodal" in html


def test_no_findings_says_so_rather_than_rendering_empty():
    html = render(Page(title="t", provenance={"a": "b"}))
    assert "No findings" in html


def test_page_is_theme_aware_both_directions():
    html = render(Page(title="t", provenance={"a": "b"}))
    assert "prefers-color-scheme:dark" in html
    assert "[data-theme=dark]" in html and "[data-theme=light]" in html


def test_page_has_no_external_requests(tmp_path):
    img = tmp_path / "f.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    html = render(Page(title="t", provenance={"a": "b"}, plates=[Plate(img, "fig")]))
    assert "data:image/png;base64," in html
    assert "http://" not in html and "https://" not in html


def test_title_is_escaped():
    html = render(Page(title="<script>x</script>", provenance={"a": "b"}))
    assert "<script>x</script>" not in html


# ----------------------------------------------------------------- end to end


def test_build_end_to_end_writes_a_page(tmp_path):
    rng = np.random.default_rng(0)
    n_obj, n_per = 40, 25
    ids = np.repeat(np.arange(n_obj), n_per).astype(float)
    az = rng.uniform(0, 360, ids.size)
    rad = rng.uniform(1, 4, ids.size)
    resid = 3.0 * np.cos(np.radians(az)) + 2.0 + rng.normal(0, 0.6, ids.size)

    ref = tmp_path / "ref.md"
    ref.write_text(GOOD)

    out = build(
        results=Results(object_id=np.arange(n_obj),
                        columns={"position_x": (rng.normal(0, 1, n_obj), "um")}),
        quality=Quality(values=rng.uniform(0.3, 1.0, n_obj), name="completeness", threshold=0.5),
        provenance=_prov(tmp_path),
        sidecar=Sidecar(
            table=np.column_stack([ids, az, rad, resid]),
            columns=["object_id", "azimuth", "radius", "d_signal"],
            units=["", "deg", "mm", "um"],
            roles=["id", "coord", "coord", "residual"],
        ),
        diagnosis_reference=ref,
        title="End to end",
        out=tmp_path / "report.html",
    )
    html = out.read_text()
    assert out.exists() and len(html) > 3000
    assert "Diagnosis reference explains" in html
    assert "Refine the shared parameter" in html  # a lever came from the reference


def test_build_without_sidecar_says_descriptive_only(tmp_path):
    rng = np.random.default_rng(1)
    out = build(
        results=Results(object_id=np.arange(20), columns={"x": (rng.normal(0, 1, 20), "um")}),
        provenance=_prov(tmp_path),
        title="Descriptive",
        out=tmp_path / "d.html",
    )
    assert "Descriptive report only" in out.read_text()
