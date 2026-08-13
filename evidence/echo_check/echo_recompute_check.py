#!/usr/bin/env python3
"""PREREGISTER §8 — separate RECOMPUTED numbers from ECHOED ones.

The problem it solves: the doc set contains some of the numbers an agent may report
(f_ped 0.9849, dilution 66.3x). A treatment report matching them is equally
consistent with having copied them. Accuracy claims built on echoed numbers are
circular.

§8 fixes the rule: a number counts as RECOMPUTED only if the run's transcript
contains a tool OUTPUT carrying it -- i.e. the agent actually saw it come back from
a command. A number that appears in the doc set but in no tool output is ECHOED and
is excluded from any accuracy claim.

Classification per numeric claim in REPORT.md:

  RECOMPUTED   appears in a tool result  -> usable as evidence
  ECHOED       in the doc set, in no tool result -> EXCLUDED from accuracy claims
  UNTRACEABLE  in neither -> excluded, and worth looking at: an asserted number

Deliberately biased AGAINST the flattering answer: "recomputed" is the conclusion
that would let us claim accuracy, so the match required for it is strict (>= MIN_SIG
significant digits, exact digit-string containment), and every verdict carries the
snippet it matched so a human can audit it.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

MIN_SIG = 3          # numbers with fewer significant digits are not diagnostic
CONTEXT = 60         # chars of context to show around a claim

# A number must not be preceded or followed by another DIGIT or a dot -- but a
# trailing letter is fine, because in scientific text a unit almost always follows:
# 66.3x, 95.0keV, 1.21385deg, 12%. An earlier version used (?![\w.]) here, which
# rejected exactly those and made the checker blind to most real claims; the fixture
# caught it. Exponent notation is matched explicitly so 1.5e-3 is not split.
NUM_RE = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)(?![\d.])")


def sig_digits(tok: str) -> str:
    """Canonical digit string: strip sign, point, and leading zeros. 0.9849 -> 9849."""
    d = tok.replace(".", "").lstrip("0")
    return d.rstrip("0") if "." in tok else d


def numbers_with_context(text: str):
    out = []
    for m in NUM_RE.finditer(text):
        tok = m.group(1)
        sd = sig_digits(tok)
        if len(sd) < MIN_SIG:
            continue
        a, b = max(0, m.start() - CONTEXT), min(len(text), m.end() + CONTEXT)
        out.append((tok, sd, " ".join(text[a:b].split())))
    return out


def tool_outputs_from_transcript(path: str) -> str:
    """Every tool RESULT the agent saw. Each transcript record holds the full message
    history for that turn, so the last record carries them all; earlier records are
    folded in anyway to survive a truncated final line."""
    chunks = []
    try:
        for line in open(path, encoding="utf8", errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            for msg in (rec.get("request") or {}).get("messages", []):
                if msg.get("role") == "tool":
                    c = msg.get("content")
                    if isinstance(c, str):
                        chunks.append(c)
    except FileNotFoundError:
        return ""
    return "\n".join(chunks)


def load_docset(doc_dir: str) -> str:
    if not doc_dir or not os.path.isdir(doc_dir):
        return ""
    out = []
    for p in sorted(glob.glob(os.path.join(doc_dir, "**", "*.md"), recursive=True)):
        try:
            out.append(open(p, encoding="utf8", errors="replace").read())
        except Exception:  # noqa: BLE001
            pass
    return "\n".join(out)


def classify(report: str, tool_text: str, doc_text: str):
    tool_digits = {sig_digits(m.group(1)) for m in NUM_RE.finditer(tool_text)}
    doc_digits = {sig_digits(m.group(1)) for m in NUM_RE.finditer(doc_text)}
    rows = []
    for tok, sd, ctx in numbers_with_context(report):
        in_tool = sd in tool_digits
        in_doc = sd in doc_digits
        if in_tool:
            verdict = "RECOMPUTED"
        elif in_doc:
            verdict = "ECHOED"
        else:
            verdict = "UNTRACEABLE"
        rows.append({"value": tok, "sig": sd, "verdict": verdict,
                     "in_tool_output": in_tool, "in_doc_set": in_doc,
                     "context": ctx})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True,
                    help="a run directory containing transcript.jsonl and workdir/REPORT.md")
    ap.add_argument("--docs", default="", help="doc set directory (treatment runs)")
    ap.add_argument("--out", default="")
    ap.add_argument("--show", default="ECHOED,UNTRACEABLE",
                    help="comma-separated verdicts to list individually")
    a = ap.parse_args()

    rp = os.path.join(a.run_dir, "workdir", "REPORT.md")
    if not os.path.exists(rp):
        print(f"no REPORT.md under {a.run_dir}", file=sys.stderr)
        return 1
    report = open(rp, encoding="utf8", errors="replace").read()
    tool_text = tool_outputs_from_transcript(os.path.join(a.run_dir, "transcript.jsonl"))
    doc_text = load_docset(a.docs)

    rows = classify(report, tool_text, doc_text)
    tally = {}
    for r in rows:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1

    print(f"run       : {os.path.basename(a.run_dir.rstrip('/'))}")
    print(f"report    : {len(report)} chars, {len(rows)} numeric claims (>= {MIN_SIG} sig digits)")
    print(f"tool text : {len(tool_text)} chars of tool output")
    print(f"doc set   : {len(doc_text)} chars" + ("" if doc_text else "  (control arm / none given)"))
    print()
    for k in ("RECOMPUTED", "ECHOED", "UNTRACEABLE"):
        n = tally.get(k, 0)
        pct = (100.0 * n / len(rows)) if rows else 0.0
        print(f"  {k:12s} {n:4d}  ({pct:.0f}%)")

    wanted = {s.strip() for s in a.show.split(",") if s.strip()}
    for k in ("ECHOED", "UNTRACEABLE", "RECOMPUTED"):
        if k not in wanted:
            continue
        sel = [r for r in rows if r["verdict"] == k]
        if not sel:
            continue
        print(f"\n--- {k} ({len(sel)}) ---")
        for r in sel[:40]:
            print(f"  {r['value']:>14s}  …{r['context']}…")

    if a.out:
        json.dump({"run": a.run_dir, "tally": tally, "claims": rows},
                  open(a.out, "w"), indent=2)
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
