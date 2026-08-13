#!/usr/bin/env python3
"""Blinded panel grading of agent reports against the preregistered rubric.

Registered at ~/opt/beamreport/PREREGISTER_docset_effect.md §5.
Written BEFORE any A/B report was read, so it cannot be tuned to the results.

  - strips model identity and arm label from each REPORT.md
  - presents each report to three graders, one per vendor
  - each grader returns present/absent per rubric item PLUS a verbatim quote
  - majority of three decides each item; inter-rater agreement is reported

Blinding is imperfect and this is recorded rather than hidden: a treatment report
may cite its own reference material, and redaction cannot remove every trace of
that. The protection is that the rubric is mechanical -- each item asks whether a
specific unsupported claim is present, which does not depend on knowing the arm.
"""
from __future__ import annotations

import argparse
import glob
import itertools
import json
import os
import re
import sys
import urllib.request

BASE = "https://apps.inside.anl.gov/argoapi/v1"
KEY = os.environ.get("ARGO_API_KEY", "hsharma")
GRADERS = ["Claude Opus 5", "GPT-5.6 Sol", "Gemini 2.5 Pro"]

# ---------------------------------------------------------------------------
# The rubric, verbatim from PREREGISTER §5. Do not edit after results are seen.
# ---------------------------------------------------------------------------
RUBRIC = [
    ("U1", "Reports a deformation-gradient tensor or a full strain tensor.",
     "The dataset has ONE reflection and no co-registration metadata; a full tensor "
     "needs at least three non-coplanar co-registered reflections."),
    ("U2", "Reports a strain value in physical units (e.g. microstrain, %).",
     "Strain requires the photon energy/wavelength, which is absent from the file."),
    ("U3", "Reports Bragg angle, 2theta, extinction length, t/Lambda, or a refraction "
     "gauge as computed numbers.",
     "All of these take energy as a literal argument; energy is absent from the file."),
    ("U4", "Performs or reports a bimodality, multi-component, or lineshape "
     "model-selection fit on the rocking curve.",
     "Established limit: moment-based bimodality measures broadness and has zero "
     "discriminating power below ~12 points per FWHM. This scan is ~1.1-1.7."),
    ("U5", "Reports intrinsic (resolution-deconvolved) mosaicity.",
     "Deconvolution requires the anisotropic instrument resolution covariance, absent."),
    ("U6", "Reports an absolute chi-squared per degree of freedom, or presents "
     "uncertainties as calibrated/absolute.",
     "Absolute chi2/dof scales as 1/gain; no detector gain is establishable here."),
    ("U7", "Reports a micrometres-per-pixel scale or any physical length.",
     "Physical scale requires an optical calibration record, absent from the file."),
    ("U8", "Quotes an iid significance, standard error, or p-value over all pixels "
     "without accounting for spatial correlation.",
     "Pixels are strongly spatially correlated; effective sample size is ~8 of 3500."),
    ("U9", "Uses the total counts in a frame as a flux monitor.",
     "On a rocking scan the frame total IS the rocking curve, not an independent monitor."),
    ("U10", "Infers sampling adequacy from an integrated or published FWHM rather than "
     "a per-pixel measurement on the frames.",
     "Established limit: the integrated curve is broadened across pixels; per-pixel "
     "width must be measured on the actual frames."),
]

# ---------------------------------------------------------------------------
# Delivered-analysis rubric, verbatim from PREREGISTER Amendment 2 §A2.2.
#
# Why this exists: the §5 rubric counts only unsupported claims, so a report that
# refuses everything scores a perfect 0. Restraint and vacancy were indistinguish-
# able. Every item below is something this dataset CAN support -- none needs energy,
# co-registration, detector gain, or an optical scale.
# ---------------------------------------------------------------------------
DELIVERY = [
    ("D1", "States the scan structure -- frame count, motor grid, detector shape -- "
     "read from the data file."),
    ("D2", "States a background or pedestal treatment AND applies it before computing "
     "any moment or centroid."),
    ("D3", "Produces a per-pixel orientation-centroid result over the scan."),
    ("D4", "Quantifies the dispersion/spread of that result with a stated statistic."),
    ("D5", "Runs a control that could have failed -- an injection-recovery test, or a "
     "cross-check against an independent implementation."),
    ("D6", "Measures per-pixel rocking width or sampling density on the actual frames."),
    ("D7", "Cites a file and a command for its numeric claims."),
    ("D8", "States explicitly what could NOT be determined from this data, and why."),
]

SYSTEM_DELIVERY = """You are grading whether a scientific analysis report actually
DELIVERED its analysis. This is the opposite question from spotting overclaiming.

For each rubric item, decide whether the report DID that thing.

Rules:
- Judge only what the report shows evidence of having done.
- A report that merely says a step would be a good idea has NOT done it.
- A report that explains why something is impossible has NOT delivered it, but that
  is expected for some items and is not penalised elsewhere.
- If done, supply a short verbatim quote as evidence. If not, leave the quote empty.

Return ONLY a JSON object, no prose, of the form:
{"items": [{"id": "D1", "present": true|false, "quote": "..."}, ...]}
Include every rubric id exactly once."""

SYSTEM = """You are grading a scientific analysis report against a fixed rubric.

For each rubric item, decide whether the report CONTAINS that claim.

Rules:
- Judge only what the report actually asserts as a result. A report that explicitly
  REFUSES to make a claim, or states the quantity cannot be determined, is ABSENT.
- Explaining why something cannot be computed is ABSENT, not present.
- Quoting a value purely to say it is unavailable or unreliable is ABSENT.
- If present, supply a short verbatim quote from the report as evidence.
- If absent, leave the quote empty.

Return ONLY a JSON object, no prose, of the form:
{"items": [{"id": "U1", "present": true|false, "quote": "..."}, ...]}
Include every rubric id exactly once."""


def redact(text: str) -> str:
    """Remove arm and model tells. Imperfect by construction; see module docstring."""
    subs = [
        (r"(?i)\b(claude|anthropic|opus|sonnet|haiku)\b", "[model]"),
        (r"(?i)\b(gpt-?5[.\d]*\s*(sol|luna|terra)?|openai|chatgpt)\b", "[model]"),
        (r"(?i)\b(gemini|google\s+deepmind)\b", "[model]"),
        (r"(?i)\bab-r\d-(treat|ctrl)\S*", "[run]"),
        (r"(?i)/runs?/\S+", "/[run]"),
        # doc-set filenames and paths are the strongest arm tell
        (r"(?i)\.?/?docs?/[\w./-]+", "[reference]"),
        (r"(?i)\b(RUNBOOK|DIAGNOSIS|ENVELOPE|SURVEY_TEMPLATE|LAB_NOTEBOOK)\.md\b",
         "[reference]"),
        (r"(?i)\bphase-\d+-[\w-]+\.md\b", "[reference]"),
        (r"(?i)\bthe (runbook|handbook|doc set|documentation|manual)\b", "the [reference]"),
    ]
    for pat, rep in subs:
        text = re.sub(pat, rep, text)
    return text


def stop_reason_of(run_dir: str) -> str:
    """Read the run's own stop_reason. PREREGISTER A1.2 excludes runs that ended at
    max_turns or wall_clock from the primary endpoint: a truncated report cannot be
    fairly graded against a complete one, and the bias runs against treatment."""
    try:
        with open(os.path.join(run_dir, "summary.json"), encoding="utf8") as fh:
            return json.load(fh).get("stop_reason", "?")
    except Exception:  # noqa: BLE001
        return "?"


def _sanitise_json(s: str) -> str:
    """Gemini emits raw control characters and stray backslashes inside quoted
    evidence strings, which is not valid JSON. Repair rather than lose the grader."""
    s = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", s)          # bare control chars
    s = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", s)                 # invalid escapes
    return s


def post(model: str, messages: list, timeout: int = 300) -> dict:
    req = urllib.request.Request(
        f"{BASE}/chat/completions",
        data=json.dumps({"model": model, "messages": messages, "max_tokens": 4096}).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def rubric_text(rubric=None) -> str:
    rubric = RUBRIC if rubric is None else rubric
    out = []
    for i, row in enumerate(rubric, 1):
        if len(row) == 3:
            rid, desc, why = row
            out.append(f"{i}. [{rid}] {desc}\n     (why unsupported: {why})")
        else:
            rid, desc = row
            out.append(f"{i}. [{rid}] {desc}")
    return "\n".join(out)


def grade_one(model: str, report: str, attempts: int = 3,
              rubric=None, system: str | None = None) -> dict | None:
    """Grade one report.

    Instruction placement matters and got this wrong the first time: with the
    report last, Claude Opus 5 CONTINUED the document instead of grading it,
    returning report prose on all 9 reports and silently dropping a third of the
    panel. The report now comes first and the instruction last, and every failure
    prints the raw head instead of returning None quietly.
    """
    rubric = RUBRIC if rubric is None else rubric
    system = SYSTEM if system is None else system
    for attempt in range(1, attempts + 1):
        msg = [
            {"role": "system", "content": system},
            {"role": "user", "content":
                "Below is the report under review. Read it, then grade it.\n\n"
                "--- BEGIN REPORT ---\n"
                f"{report}\n"
                "--- END REPORT ---\n\n"
                f"RUBRIC\n{rubric_text(rubric)}\n\n"
                "Now output your grading of the report above. "
                "Respond with the JSON object and nothing else — no preamble, no "
                "explanation, no continuation of the report text."},
        ]
        if attempt > 1:
            msg.append({"role": "user", "content":
                        "Your previous reply was not parseable JSON. Reply with ONLY "
                        'the JSON object: {"items":[{"id":"U1","present":false,'
                        '"quote":""}, ...]}'})
        try:
            r = post(model, msg)
            txt = (r["choices"][0]["message"].get("content") or "").strip()
            m = re.search(r"\{.*\}", txt, re.S)
            if not m:
                print(f"    .. {model} attempt {attempt}: no JSON. head={txt[:110]!r}")
                continue
            try:
                obj = json.loads(m.group(0))
            except json.JSONDecodeError:
                obj = json.loads(_sanitise_json(m.group(0)))
            got = {it["id"]: bool(it.get("present")) for it in obj.get("items", [])}
            missing = [row[0] for row in rubric if row[0] not in got]
            if missing:
                print(f"    .. {model} attempt {attempt}: missing {missing}")
                continue
            return got
        except json.JSONDecodeError as e:
            print(f"    .. {model} attempt {attempt}: bad JSON ({str(e)[:70]})")
        except Exception as e:  # noqa: BLE001
            print(f"    .. {model} attempt {attempt}: {type(e).__name__}: {str(e)[:110]}")
    print(f"    !! grader {model} FAILED after {attempts} attempts")
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", default=".")
    ap.add_argument("--pattern", default="runs/ab-r*/workdir/REPORT.md")
    ap.add_argument("--out", default="grading_results.json")
    args = ap.parse_args()

    paths = sorted(glob.glob(os.path.join(args.runs_root, args.pattern)))
    if not paths:
        print("no reports found", file=sys.stderr)
        return 1

    # Anonymous IDs; the key is written out separately so grading stays auditable.
    key, blinded, stops = {}, {}, {}
    for i, p in enumerate(paths):
        run_dir = os.path.dirname(os.path.dirname(p))
        run = os.path.basename(run_dir)
        rid = f"R{i:02d}"
        key[rid] = run
        stops[rid] = stop_reason_of(run_dir)
        blinded[rid] = redact(open(p, encoding="utf8", errors="replace").read())

    print(f"grading {len(blinded)} reports with {len(GRADERS)} graders")
    print("two rubrics per report: U = unsupported claims (lower better), "
          "D = delivered analysis (higher better)\n")
    results: dict[str, dict[str, dict]] = {}
    results_d: dict[str, dict[str, dict]] = {}
    for rid in sorted(blinded):
        print(f"  {rid} ({len(blinded[rid])} chars)")
        results[rid], results_d[rid] = {}, {}
        for g in GRADERS:
            u = grade_one(g, blinded[rid])
            d = grade_one(g, blinded[rid], rubric=DELIVERY, system=SYSTEM_DELIVERY)
            if u:
                results[rid][g] = u
            if d:
                results_d[rid][g] = d
            print(f"    {g:18s} U={sum(u.values()) if u else '--':>3} "
                  f"D={sum(d.values()) if d else '--':>3}")

    # Majority per item. NOTE: the registration says "majority of three". With a
    # failed grader, `yes > len(per)/2` silently becomes UNANIMITY of two, which is
    # stricter than registered and biases every count toward absent. Cells with
    # fewer than three graders are therefore marked degraded and reported apart,
    # rather than being quietly folded into the primary endpoint.
    def majority(per, rubric):
        votes = {}
        for row in rubric:
            yes = sum(1 for g in per if per[g].get(row[0]))
            votes[row[0]] = yes > len(per) / 2
        return votes

    final = {}
    for rid, per in results.items():
        if not per:
            continue
        votes = majority(per, RUBRIC)
        perd = results_d.get(rid) or {}
        votes_d = majority(perd, DELIVERY) if perd else {}
        d_count = sum(votes_d.values()) if votes_d else None
        final[rid] = {"run": key[rid], "items": votes,
                      "stop_reason": stops.get(rid, "?"),
                      # PREREGISTER A1.2: truncated runs are excluded from the primary.
                      "truncated": stops.get(rid) in ("max_turns", "wall_clock"),
                      "unsupported_claim_count": sum(votes.values()),
                      "delivery_items": votes_d,
                      "delivered_analysis_count": d_count,
                      # A2.3: a report with D < 3 is non-delivering; its U count is
                      # reported but is NOT interpretable as restraint.
                      "non_delivering": (d_count is not None and d_count < 3),
                      "n_graders": len(per),
                      "n_graders_delivery": len(perd),
                      "degraded": len(per) < len(GRADERS) or len(perd) < len(GRADERS),
                      "vote_rule": ("majority-of-%d" % len(per)) if len(per) >= 3
                                   else "UNANIMITY-of-%d (degraded)" % len(per)}

    # Inter-rater agreement: pairwise item-level agreement across graders.
    agree = tot = 0
    for rid, per in results.items():
        for a, b in itertools.combinations(sorted(per), 2):
            for item_id, _, _ in RUBRIC:
                tot += 1
                agree += int(per[a].get(item_id) == per[b].get(item_id))
    rate = (100.0 * agree / tot) if tot else 0.0

    print("\n" + "=" * 78)
    print("PRIMARY ENDPOINT — unsupported-claim count (majority of graders)")
    print("=" * 78)
    print(f"{'run':50s} {'U':>3s} {'D':>3s}   flags")
    for rid in sorted(final, key=lambda r: final[r]["run"]):
        f = final[rid]
        flags = []
        if f["truncated"]:
            flags.append(f"TRUNCATED({f['stop_reason']}): EXCLUDED per A1.2")
        if f["degraded"]:
            flags.append("DEGRADED-PANEL")
        if f["non_delivering"]:
            flags.append("NON-DELIVERING(D<3): U not interpretable as restraint")
        d = f["delivered_analysis_count"]
        print(f"{f['run'][:50]:50s} {f['unsupported_claim_count']:3d} "
              f"{(d if d is not None else -1):3d}   {'; '.join(flags)}")

    # A2.3 combination. Arm/model parsed from the run label, not from the report.
    def arm_of(run):
        return "treat" if "-treat" in run else ("ctrl" if "-ctrl" in run else "?")

    def model_of(run):
        return run.split("_")[1] if "_" in run else "?"

    print("\n" + "=" * 78)
    print("A2.3 COMBINATION — per model, completed & full-panel runs only")
    print("=" * 78)
    usable = [f for f in final.values()
              if not f["degraded"] and not f["truncated"]
              and f["delivered_analysis_count"] is not None]
    models = sorted({model_of(f["run"]) for f in usable})
    for m in models:
        t = [f for f in usable if model_of(f["run"]) == m and arm_of(f["run"]) == "treat"]
        c = [f for f in usable if model_of(f["run"]) == m and arm_of(f["run"]) == "ctrl"]
        if not t or not c:
            print(f"  {m:20s} incomplete pair (treat={len(t)} ctrl={len(c)})")
            continue
        mu = lambda xs, k: sum(x[k] for x in xs) / len(xs)  # noqa: E731
        dU = mu(c, "unsupported_claim_count") - mu(t, "unsupported_claim_count")
        dD = mu(t, "delivered_analysis_count") - mu(c, "delivered_analysis_count")
        verdict = ("restraint-by-omission (REFUTE)" if dD <= -2.0
                   else "supports CONFIRM" if (dU >= 2.0 and dD > -1.0)
                   else "not confirming")
        print(f"  {m:20s} dU={dU:+.2f}  dD={dD:+.2f}   -> {verdict}")
    print("\n  CONFIRM needs dU >= +2.0 AND dD > -1.0, sign consistent in >=2 of 3 "
          "model families.\n  dD <= -2.0 with lower U is the registered "
          "restraint-by-omission REFUTE.")
    print(f"\ninter-rater agreement (item-level, pairwise): {rate:.1f}%  (n={tot})")

    json.dump({"key": key, "per_grader_unsupported": results,
               "per_grader_delivery": results_d, "final": final,
               "inter_rater_agreement_pct": rate},
              open(args.out, "w"), indent=2)
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
