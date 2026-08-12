"""Check a technique doc set against the contract in DOCS_SPEC.md.

Checks the contract, never the content. It cannot tell you a claim is true; it
tells you the set has its parts, that the diagnosis entries are well-formed and
keyed to symptoms something can actually emit, and that the spine carries the
three things a context-free reader needs before it can do damage.

Citations (``path:line`` into source) are deliberately NOT checked here. They
point at the technique's own code, so whatever checks them has to run in the
repository that contains that code -- see DOCS_SPEC §7.

    beamreport-doc-lint path/to/doc-set/
    beamreport-doc-lint --init path/to/doc-set/
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

from .finding import SYMPTOMS
from .reference import ReferenceError, parse as parse_reference

SPINE = "README.md"
DIAGNOSIS = "DIAGNOSIS.md"
RUNBOOK = "RUNBOOK.md"
# A glob, not a filename: DOCS_SPEC §2 says one notebook PER CAMPAIGN, so a
# technique with three campaigns has three, named for them. Requiring one exact
# name would push a project into merging campaign records, which is the opposite
# of what the rule is for.
NOTEBOOK_GLOB = ("*LAB_NOTEBOOK*.md", "*Lab_Notebook*.md", "*NOTEBOOK*.md")

# What the spine must demonstrably carry. Matched loosely on purpose: this is a
# contract about substance, and pinning exact wording would make it a style
# checker that people route around by renaming a heading.
_IS = re.I | re.S
SPINE_REQUIRED = [
    ("scope gate",
     re.compile(r"\bscope\b.{0,120}(stop|only|assumes|covers)|stop and ask", _IS)),
    ("install gate",
     re.compile(r"(install|version|floor|environment).{0,160}(gate|check|verify)", _IS)),
    # `\bhalt\b` and not "stop and ask": the scope gate says "stop and ask" too, and
    # accepting that let a doc set pass the halt check on its scope sentence alone.
    # They are different things -- scope says which data this describes, the halt list
    # says when to stop on data it DOES describe.
    ("halt conditions", re.compile(r"\bhalt\b", _IS)),
    ("order of operations",
     re.compile(r"\border\b.{0,80}(not optional|sequence|in this order)|the order", _IS)),
]


class Problem(str):
    """A contract violation, rendered as one line."""


def _read(p: Path) -> str:
    return p.read_text(errors="replace") if p.is_file() else ""


def check_set(root: Path) -> list[Problem]:
    out: list[Problem] = []
    if not root.is_dir():
        return [Problem(f"{root}: not a directory")]

    files = {p.name: p for p in root.glob("*.md")}

    # 1. The artifacts exist.
    for want, why in ((SPINE, "the spine is what a fresh session is handed"),
                      (DIAGNOSIS, "without it a report has no findings, only figures"),
                      (RUNBOOK, "'what is true right now' is the document that goes missing")):
        if want not in files:
            out.append(Problem(f"MISSING    {want} -- {why}"))
    # `any(list(...))`, not `any(root.glob(...))`: a generator object is always
    # truthy, so the unlisted form made this check silently never fire.
    if not any(list(root.glob(g)) for g in NOTEBOOK_GLOB):
        out.append(Problem(
            "MISSING    a lab notebook (*LAB_NOTEBOOK*.md) -- the evidence and the "
            "retractions; without it a refuted idea comes back"))

    # 2. The spine carries what a context-free reader needs.
    spine = _read(files.get(SPINE, root / SPINE))
    if spine:
        for label, pat in SPINE_REQUIRED:
            if not pat.search(spine):
                out.append(Problem(f"SPINE      {SPINE} has no discernible {label}"))
        if len(spine.split("\n")) > 450:
            out.append(Problem(
                f"SPINE      {SPINE} is {len(spine.splitlines())} lines -- the spine is "
                f"the part that stays loaded; move detail into phase files"))

    # 3. The diagnosis reference parses, and its symptoms are real.
    if DIAGNOSIS in files:
        try:
            entries = parse_reference(_read(files[DIAGNOSIS]), source=DIAGNOSIS)
        except ReferenceError as e:
            out.append(Problem(f"DIAGNOSIS  {e}"))
            entries = []
        if not entries:
            out.append(Problem(
                f"DIAGNOSIS  {DIAGNOSIS} has no entries -- three is a working start"))
        for e in entries:
            if e.symptom not in SYMPTOMS:          # parse() already refuses, belt-and-braces
                out.append(Problem(
                    f"DIAGNOSIS  entry {e.title!r} keyed to unknown symptom "
                    f"{e.symptom!r}"))
            if not getattr(e, "test", None):
                out.append(Problem(
                    f"DIAGNOSIS  entry {e.title!r} has no Test -- an entry that cannot "
                    f"come back the other way only confirms its author"))

    # 4. The runbook is dated and has a pick-up point.
    rb = _read(files.get(RUNBOOK, root / RUNBOOK))
    if rb:
        if not re.search(r"(?i)pick[- ]up point|current state|where .{0,20}stopped", rb):
            out.append(Problem(
                f"RUNBOOK    {RUNBOOK} has no current pick-up point -- the next session "
                f"re-derives what you already knew"))
        if not re.search(r"\b20\d\d-\d\d-\d\d\b", rb):
            out.append(Problem(
                f"RUNBOOK    {RUNBOOK} carries no date; a runbook with no date cannot "
                f"be judged stale"))
        if re.search(r"(?i)healthy", rb) and not re.search(r"(?i)condition", rb):
            out.append(Problem(
                f"RUNBOOK    {RUNBOOK} says what is healthy without stating conditions -- "
                f"one threshold false-alarms on heavy runs and goes silent on broken ones"))
    return out


def init(root: Path) -> int:
    src = Path(__file__).resolve().parent.parent / "templates" / "technique-docs"
    if not src.is_dir():
        print(f"template not found at {src}", file=sys.stderr)
        return 2
    root.mkdir(parents=True, exist_ok=True)
    made = []
    for f in sorted(src.glob("*.md")):
        dst = root / f.name
        if dst.exists():
            print(f"  skip (exists): {dst.name}")
            continue
        shutil.copy2(f, dst)
        made.append(dst.name)
    print(f"scaffolded into {root}: {', '.join(made) or 'nothing (all present)'}")
    print("\nFill them in beside your code. Read DOCS_SPEC.md, and a live instance from "
          "REGISTRY.md\nbefore the template -- a real one shows what the sections are for.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", type=Path, help="the doc-set directory")
    ap.add_argument("--init", action="store_true",
                    help="scaffold a doc set from the bundled template")
    a = ap.parse_args(argv)

    if a.init:
        return init(a.path)

    problems = check_set(a.path)
    print(f"beamreport-doc-lint: {a.path}")
    if not problems:
        print("doc set satisfies the contract "
              "(DOCS_SPEC.md) -- this says nothing about whether its claims are true")
        return 0
    print(f"\nFAILED -- {len(problems)}:\n")
    for p in problems:
        print("  " + p)
    return 1


if __name__ == "__main__":
    sys.exit(main())
