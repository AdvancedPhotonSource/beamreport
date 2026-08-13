# Echo/recompute checker — fixture validation

**Built and validated 2026-08-12 while the beamline hosts were unreachable.**
Implements `PREREGISTER_docset_effect.md` §8.

## What it decides

A treatment report matching a documented number is equally consistent with having
**computed** it and with having **copied** it. §8 fixes the rule: a number counts as
RECOMPUTED only if the run's transcript contains a **tool output** carrying it — the
agent actually saw it come back from a command.

| verdict | meaning | use |
|---|---|---|
| RECOMPUTED | appears in a tool result | usable as evidence |
| ECHOED | in the doc set, in no tool result | **excluded from accuracy claims** |
| UNTRACEABLE | in neither | excluded; an asserted number, worth inspecting |

Biased against the flattering answer: RECOMPUTED is the verdict that would license an
accuracy claim, so it requires a strict digit-string match and every verdict prints
the surrounding context for audit.

## Fixture

A synthetic run with ground truth fixed by construction — a report, a doc set, and a
transcript whose tool outputs are known.

| value | placed in | expected | result |
|---|---|---|---|
| `0.98492` | tool output only | RECOMPUTED | ✓ |
| `76.12` | tool output only | RECOMPUTED | ✓ |
| `66.3` | doc set only | ECHOED | ✓ |
| `71.8` | doc set only | ECHOED | ✓ |
| `0.999858` | both | RECOMPUTED (tool wins) | ✓ |
| `42.4242` | neither | UNTRACEABLE | ✓ |

## The bug the fixture caught

The first implementation used a trailing `(?![\w.])` in the number regex, which
**rejects any number followed by a letter**. In scientific text that is most of them —
`66.3x`, `95.0 keV`, `1.21385 deg`, `12%`. Both ECHOED cases were silently
misclassified as UNTRACEABLE, and on real reports the checker would have missed the
majority of claims while appearing to work. Fixed to `(?![\d.])`, with explicit
exponent handling so `1.5e-3` is not split.

Worth recording because the failure was *invisible without a fixture*: the tool ran,
produced a plausible table, and was wrong.

## Known conservatism, stated

Precision is part of the match. A doc set carrying `0.9849` and a tool output carrying
`0.98492` are different digit strings, so a report quoting the rounded `0.9849` is
classified **ECHOED** even if it was in fact computed and rounded for presentation.
This biases against claiming recomputation, which is the intended direction, but it
means the ECHOED count is an upper bound rather than an exact one.

Numeric tokens that are really identifiers — dates like `20260812`, run indices — are
counted and will land in UNTRACEABLE. They are noise, not claims; read the context
column before treating an UNTRACEABLE count as a finding.

## Ready to run

```bash
python echo_recompute_check.py \
  --run-dir <chiltepin>/runs/ab-r2-treat_gpt-5-6-sol_<stamp> \
  --docs    <chiltepin>/docset_dfxm \
  --out     echo_gpt_treat.json
```

The first question it answers: in the GPT treatment report, were `f_ped = 0.9849231`
and the `66.33x` predicted dilution computed from the frames, or copied from
`SURVEY_TEMPLATE.md`? The pilot's directly-measured `76.12x` — which *differs* from
the documented `71.8x` — is already weak evidence for recomputation, and this settles
it per-number.
