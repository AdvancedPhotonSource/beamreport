"""The diagnosis reference: your written symptom -> test -> cause -> lever table.

This module parses that file and attaches its entries to Findings. It supplies no
content of its own. An empty reference produces a correct, well-typeset page with no
levers, and the page says so out loud rather than looking complete.

Format: a markdown file, one `##` heading per entry, with key: value lines before the
prose body. Keys are `symptom` (required), and optionally `channel` / `coord` to scope
an entry to one residual channel or one coordinate.

    ## Detector centre offset
    symptom: trend.amplitude_constant
    coord: azimuth

    **Test.** Compare the amplitude across bins of ring radius...

    **Cause.** A rigid detector-centre shift.

    **Lever.** Recalibrate against a standard and re-index.

`Test`, `Cause` and `Lever` are pulled from `**Bold.**` run-in headings in the body.
The Test is required: an entry without a falsifiable test is refused, because an entry
that cannot come back the other way turns the report into a machine for confirming
whatever its author already believed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .finding import SYMPTOMS, Finding

_ENTRY = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.M)
_KEY = re.compile(r"^(?P<key>[a-z_]+):\s*(?P<val>.+?)\s*$", re.M)
_SECTION = re.compile(r"\*\*(?P<name>Test|Cause|Lever)\.?\*\*\s*(?P<body>.*?)(?=\n\s*\n\*\*|\Z)", re.S)


class ReferenceError(ValueError):
    pass


@dataclass
class Entry:
    title: str
    symptom: str
    test: str
    cause: str | None = None
    lever: str | None = None
    channel: str | None = None
    coord: str | None = None

    def matches(self, f: Finding) -> int:
        """Match score, or -1 for no match. Higher scores win, so the most specific
        entry is used when several could apply."""
        if f.symptom != self.symptom:
            return -1
        score = 0
        for mine, theirs in ((self.channel, f.channel), (self.coord, f.coord)):
            if mine is not None:
                if theirs != mine:
                    return -1
                score += 1
        return score


def parse(text: str, source: str = "<string>") -> list[Entry]:
    entries: list[Entry] = []
    marks = list(_ENTRY.finditer(text))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        block = text[m.end():end]
        keys = {k.group("key"): k.group("val") for k in _KEY.finditer(block)}
        title = m.group("title")

        symptom = keys.get("symptom")
        if not symptom:
            raise ReferenceError(f"{source}: entry {title!r} has no `symptom:` key")
        if symptom not in SYMPTOMS:
            raise ReferenceError(
                f"{source}: entry {title!r} declares unknown symptom {symptom!r}.\n"
                f"Known symptoms:\n  " + "\n  ".join(sorted(SYMPTOMS))
            )

        sections = {s.group("name").lower(): s.group("body").strip() for s in _SECTION.finditer(block)}
        if not sections.get("test"):
            raise ReferenceError(
                f"{source}: entry {title!r} has no **Test.** section. Every entry needs a "
                f"discriminating test that could come back the other way; without one the "
                f"entry cannot exonerate the cause it names."
            )
        entries.append(Entry(
            title=title, symptom=symptom,
            test=sections["test"], cause=sections.get("cause"), lever=sections.get("lever"),
            channel=keys.get("channel"), coord=keys.get("coord"),
        ))
    return entries


def load(path: str | Path) -> list[Entry]:
    p = Path(path)
    if not p.exists():
        raise ReferenceError(f"diagnosis reference not found: {p}")
    return parse(p.read_text(), str(p))


def apply(findings: list[Finding], entries: list[Entry]) -> list[Finding]:
    """Attach the best-matching reference entry to each finding, in place."""
    for f in findings:
        best, best_score = None, -1
        for e in entries:
            s = e.matches(f)
            if s > best_score:
                best, best_score = e, s
        if best is not None and best_score >= 0:
            f.test, f.cause, f.lever = best.test, best.cause, best.lever
    return findings


def coverage(findings: list[Finding], entries: list[Entry]) -> dict:
    """How much of what was detected can the reference actually explain?

    Reported on every page. A high symptom count with low coverage is the honest
    signal that the reference, not the data, is the thing limiting the report.
    """
    symptomatic = [f for f in findings if f.symptom]
    explained = [f for f in symptomatic if f.explained]
    return {
        "n_symptoms": len(symptomatic),
        "n_explained": len(explained),
        "n_entries": len(entries),
        "unexplained": sorted({f.symptom for f in symptomatic if not f.explained}),
        "fraction": len(explained) / len(symptomatic) if symptomatic else 1.0,
    }
