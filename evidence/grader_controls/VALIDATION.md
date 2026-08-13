# Grader validation — positive, negative and vacuous controls

**Run 2026-08-12, from the Mac against the Argo gateway, while the beamline hosts
were unreachable.** Registered rubrics: `PREREGISTER_docset_effect.md` §5 (U,
unsupported claims) and Amendment 2 §A2.2 (D, delivered analysis).

## Why this had to be done

Every A/B report graded so far scored U between 0 and 3. A low score is only
evidence of restraint if the instrument can detect the absence of restraint. Without
a positive control, "GPT ΔU = 0" is indistinguishable from a grader that returns
zero on everything, and the whole comparison is uninterpretable.

## Controls

Three reports were written by hand, none produced by an agent:

| control | construction | expectation |
|---|---|---|
| `control_positive.md` | contains all ten §5 unsupported claims, written to read like a plausible report rather than a caricature | U ≈ 10 |
| `control_negative.md` | makes none of the ten, and delivers all eight A2.2 items with provenance | U ≈ 0, D ≈ 8 |
| `control_vacuous.md` | makes none of the ten and does no work at all | U ≈ 0, **D ≈ 0** |

## Result

| control | U | D | flag |
|---|---:|---:|---|
| negative | **0** | **8** | — |
| positive | **10** | 3 | — |
| vacuous | **0** | **1** | NON-DELIVERING (D<3) |

**Inter-rater agreement: 100.0 % (n = 90 item-judgments)** across Claude Opus 5,
GPT-5.6 Sol and Gemini 2.5 Pro. Every grader agreed on every item of every control.

## What it establishes

1. **The U rubric detects unsupported claims.** 10/10 on the positive control,
   unanimously. A zero in the A/B is therefore a real zero.
2. **It does not over-fire.** 0/10 on a report that discusses all the same physics
   while refusing to claim any of it — so the rubric distinguishes *explaining why a
   quantity is unavailable* from *asserting it*.
3. **Amendment 2 works, and was necessary.** The vacuous report scores a **perfect 0
   on the original endpoint** — pre-amendment it would have ranked as the best report
   in the study. The delivery rubric separates it (D = 1) and flags it automatically.

## What it does not establish

- Agreement is not accuracy. All three graders could share a blind spot, and a
  hand-written control cannot rule that out.
- The controls were written by the same author as the rubric. They test whether the
  instrument reads what the rubric says, not whether the rubric captures everything a
  domain expert would call unsupported.
- Three controls is a floor check, not a calibration curve. Nothing here estimates
  the rubric's behaviour on reports scoring in the middle of the range, which is
  where real reports mostly land.
