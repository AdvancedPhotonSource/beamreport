"""Tests for the doc-set contract.

Each test names the DOCS_SPEC rule it guards. The linter's failure mode is
silence: a check that stops firing turns into "the doc set is fine", which is
what an incomplete set looks like anyway.
"""
import pytest

from beamreport.doclint import check_set

SPINE_OK = """
# T — a technique

**Scope.** Only 1-ID, one panel. Outside that, stop and ask.

## 0. Verify the install — before anything else
Run the version check and read its output.

## STOP
Halt on these named conditions, whether or not anything seems wrong:

| Condition | Why |
|---|---|
| a is not b | never established |

## 0a. THE ORDER — not optional
| # | Step |
|---|---|
| 0 | verify |
"""

DIAG_OK = """
# T diagnosis reference

## Centre offset
symptom: trend.amplitude_constant

**Test.** Amplitude constant across radius bins means centre; growing means distance,
which is the other entry.

**Cause.** The centre used differs from the true one.

**Lever.** Recalibrate and re-index.
"""

RUNBOOK_OK = """
# T runbook
## R1. Where it runs
## R2. What healthy looks like
Ranges with the conditions attached; there is no single number.
| q | v | conditions |
|---|---|---|
| a | 1 | on dataset X |
## R3. Current pick-up point
**Last updated: 2026-08-11.**
"""


def _write(d, **files):
    for name, text in files.items():
        (d / name.replace("__", ".")).write_text(text)
    return d


def _full(tmp_path):
    return _write(tmp_path, README__md=SPINE_OK, DIAGNOSIS__md=DIAG_OK,
                  RUNBOOK__md=RUNBOOK_OK, LAB_NOTEBOOK__md="# notes\n")


def test_complete_set_passes(tmp_path):
    assert check_set(_full(tmp_path)) == []


@pytest.mark.parametrize("missing", ["DIAGNOSIS.md", "RUNBOOK.md", "LAB_NOTEBOOK.md"])
def test_missing_artifact_is_named(tmp_path, missing):
    """DOCS_SPEC §2: four artifacts, and the linter names which is absent."""
    _full(tmp_path)
    (tmp_path / missing).unlink()
    problems = check_set(tmp_path)
    assert any(missing.split(".")[0] in p for p in problems), problems


@pytest.mark.parametrize("drop,label", [
    ("**Scope.** Only 1-ID, one panel. Outside that, stop and ask.", "scope gate"),
    ("Halt on these named conditions, whether or not anything seems wrong:",
     "halt conditions"),
])
def test_spine_must_carry_its_gates(tmp_path, drop, label):
    """DOCS_SPEC §3: the spine is the handover document; these are what make it one."""
    _full(tmp_path)
    (tmp_path / "README.md").write_text(SPINE_OK.replace(drop, ""))
    assert any(label in p for p in check_set(tmp_path))


def test_diagnosis_entry_needs_a_real_symptom(tmp_path):
    """DOCS_SPEC §5: an entry keyed to a symptom nothing emits never fires."""
    _full(tmp_path)
    (tmp_path / "DIAGNOSIS.md").write_text(
        DIAG_OK.replace("trend.amplitude_constant", "trend.invented"))
    assert any("DIAGNOSIS" in p for p in check_set(tmp_path))


def test_empty_diagnosis_is_reported(tmp_path):
    """An empty reference yields a correct page with no findings -- say so."""
    _full(tmp_path)
    (tmp_path / "DIAGNOSIS.md").write_text("# T diagnosis reference\n")
    assert any("no entries" in p for p in check_set(tmp_path))


def test_runbook_without_pickup_point_is_reported(tmp_path):
    """DOCS_SPEC §6: the pick-up point is what stops the next session re-deriving."""
    _full(tmp_path)
    (tmp_path / "RUNBOOK.md").write_text(
        RUNBOOK_OK.replace("## R3. Current pick-up point", "## R3. Notes"))
    assert any("pick-up point" in p for p in check_set(tmp_path))


def test_runbook_healthy_without_conditions_is_reported(tmp_path):
    """DOCS_SPEC §6: one threshold false-alarms on heavy runs, silences broken ones."""
    _full(tmp_path)
    (tmp_path / "RUNBOOK.md").write_text(
        RUNBOOK_OK.replace("Ranges with the conditions attached; there is no single number.",
                           "Healthy is above 0.9.").replace("| q | v | conditions |",
                                                            "| q | v | x |"))
    assert any("conditions" in p for p in check_set(tmp_path))


def test_oversized_spine_is_reported(tmp_path):
    """DOCS_SPEC §3: the spine is the part that stays loaded."""
    _full(tmp_path)
    (tmp_path / "README.md").write_text(SPINE_OK + "\nfiller\n" * 500)
    assert any("stays loaded" in p for p in check_set(tmp_path))
