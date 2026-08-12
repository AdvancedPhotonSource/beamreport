"""Check a technique doc set against the contract in DOCS_SPEC.md.

Checks the contract, never the content. It cannot tell you a claim is true; it
tells you the set has its parts, that the diagnosis entries are well-formed and
keyed to symptoms something can actually emit, and that the spine carries the
three things a context-free reader needs before it can do damage.

Citations (``path:line`` into source) are deliberately NOT checked here. They
point at the technique's own code, so whatever checks them has to run in the
repository that contains that code -- see DOCS_SPEC §8.

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
from .reference import ReferenceError, local_symptoms, parse as parse_reference

SPINE = "README.md"
DIAGNOSIS = "DIAGNOSIS.md"
ENVELOPE = "ENVELOPE.md"
RUNBOOK = "RUNBOOK.md"

# The three tiers of DOCS_SPEC §6. Matched on the tier word alone: what matters is
# that limits were SORTED, because the tier is what decides whether a report may
# suggest changing something or must state it as unobtainable.
ENVELOPE_TIERS = (
    ("fixed", re.compile(r"(?im)^#{1,3}.*\bfixed\b|^\s*\|?\s*\*{0,2}fixed\b")),
    ("configured", re.compile(r"(?im)^#{1,3}.*\bconfigur|^\s*\|?\s*\*{0,2}configur")),
    ("intrinsic", re.compile(r"(?im)^#{1,3}.*\bintrinsic\b|^\s*\|?\s*\*{0,2}intrinsic\b")),
)
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
    # Bidirectional and wide on purpose. The first version demanded the gating verb
    # AFTER the word "scope" within 120 chars, and false-flagged a doc set whose scope
    # gate is a row in its halt table ("...confirm first (scope)"). A checker that
    # fails a doc for the shape of its prose teaches people to write for the checker.
    ("scope gate",
     re.compile(r"\bscope\b.{0,200}?(stop|halt|confirm|only|assumes|covers|gate|ask)"
                r"|(stop|halt|confirm|only|assumes|covers|gate|ask).{0,200}?\bscope\b"
                r"|stop and ask", _IS)),
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


_EMPTY_CELL = {"", "-", "--", "—", "n/a", "na", "tbd", "?"}


def _bounds_are_sourced(env: str) -> bool | None:
    """Does the configured tier say what imposes each bound?

    Checks the *column*, not a phrase. Searching for wording would make this a style
    checker that renaming a heading routes around, and would pass a file whose rows
    are all empty -- which is the "reads as coverage" failure the check exists for.

    Returns None when there is no table to judge, so a doc set that states its bounds
    in prose is not failed for the shape of its markup.
    """
    lines = env.splitlines()
    for i, ln in enumerate(lines):
        if "|" not in ln:
            continue
        head = [c.strip().lower() for c in ln.strip().strip("|").split("|")]
        col = next((k for k, c in enumerate(head)
                    if re.search(r"limited by|imposed by|bounded by|source", c)), None)
        if col is None:
            continue
        cells = []
        for row in lines[i + 2:]:                     # +2 skips the |---| separator
            if "|" not in row:
                break
            parts = [c.strip() for c in row.strip().strip("|").split("|")]
            if len(parts) > col:
                cells.append(parts[col])
        if cells:
            filled = [c for c in cells if c.lower().strip("* ") not in _EMPTY_CELL]
            # Half is deliberate: an envelope is allowed to declare some bounds
            # unknown (that is what suppresses their counterfactuals), but a table
            # that is mostly blank is a template, not an envelope.
            return len(filled) * 2 >= len(cells)
    return None


def check_set(root: Path) -> list[Problem]:
    out: list[Problem] = []
    if not root.is_dir():
        return [Problem(f"{root}: not a directory")]

    files = {p.name: p for p in root.glob("*.md")}

    # 1. The artifacts exist.
    for want, why in ((SPINE, "the spine is what a fresh session is handed"),
                      (DIAGNOSIS, "without it a report has no findings, only figures"),
                      (ENVELOPE, "without it 'what could be observed differently' is guesswork"),
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

    # 2b. The spine indexes the phase files that exist beside it.
    #
    # The Laue spine named "Phase 0".."Phase 6" five times and linked none of the seven
    # files. A session that took the spine at its word -- "the one file you keep loaded"
    # -- read the invariants and the worked example and never learned the procedure was
    # in separate files; it found them only by listing the directory. Nothing else in
    # this contract can see that, because every artifact was present and well-formed.
    phases = sorted(p.name for p in root.glob("phase-*.md"))
    if phases and spine:
        linked = set(re.findall(r"phase-[0-9][\w.-]*\.md", spine))
        missing = [p for p in phases if p not in linked]
        if missing:
            out.append(Problem(
                f"SPINE      {SPINE} does not link {len(missing)} of {len(phases)} phase "
                f"file(s): {', '.join(missing[:4])}{'...' if len(missing) > 4 else ''} -- "
                f"a spine that names its phases without linking them leaves them "
                f"undiscoverable to a reader who trusts it"))

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
        # A technique may declare its own symptoms (DOCS_SPEC §5b) for detectors
        # beamreport does not have. The control that stops that being an escape hatch
        # is that every one must name what emits it.
        local = local_symptoms(_read(files[DIAGNOSIS]))
        for name, emitter in sorted(local.items()):
            if not emitter or emitter.strip("*_` ").lower() in ("", "-", "tbd", "?"):
                out.append(Problem(
                    f"DIAGNOSIS  local symptom {name!r} names nothing that emits it -- "
                    f"an entry nothing produces is dead text that reads as coverage"))
        for e in entries:
            if e.symptom not in SYMPTOMS and e.symptom not in local:
                out.append(Problem(
                    f"DIAGNOSIS  entry {e.title!r} keyed to unknown symptom "
                    f"{e.symptom!r}"))
            if not getattr(e, "test", None):
                out.append(Problem(
                    f"DIAGNOSIS  entry {e.title!r} has no Test -- an entry that cannot "
                    f"come back the other way only confirms its author"))

    # 3b. The envelope sorted its limits, and is not stale.
    env = _read(files.get(ENVELOPE, root / ENVELOPE))
    if env:
        missing = [name for name, pat in ENVELOPE_TIERS if not pat.search(env)]
        if missing:
            out.append(Problem(
                f"ENVELOPE   {ENVELOPE} does not sort limits into {', '.join(missing)} -- "
                f"the tier is what decides whether a report may suggest a change or must "
                f"call the quantity unobtainable"))
        if not re.search(r"\b20\d\d-\d\d-\d\d\b", env):
            out.append(Problem(
                f"ENVELOPE   {ENVELOPE} carries no date; a stale envelope recommends what "
                f"the beamline stopped being able to do"))
        if not re.search(r"(?i)\bowner\b|\bmaintain(er|ed by)\b", env):
            out.append(Problem(
                f"ENVELOPE   {ENVELOPE} names no owner -- nobody re-checks a spec-sheet "
                f"number that is nobody's"))
        # A bound with no source is the row that produces confident bad advice, so the
        # tier that carries counterfactuals has to say what imposes each limit.
        if _bounds_are_sourced(env) is False:
            out.append(Problem(
                f"ENVELOPE   {ENVELOPE} lists changeable parameters without saying what "
                f"limits them -- an unsourced bound is worse than a missing one"))

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
