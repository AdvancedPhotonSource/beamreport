# PREREGISTRATION — does a technique doc set change what an agent claims?

**Fixed 2026-08-12, before any control-arm data existed.** Written under
`~/.claude/skills/preregister`. The confirm/refute conditions below are the fixed
target; results are read against them, not against a story assembled afterwards.

---

## 1. Hypothesis, as one falsifiable claim

> Giving an agent a technique doc set reduces the number of **unsupported claims**
> it makes in an analysis report, relative to the same agent, same task, same data,
> and no doc set.

"Unsupported" means the claim requires information that is demonstrably absent from
the dataset, or is made in a regime where the ledger records the metric as invalid.
It is not a judgement of prose quality, thoroughness, or correctness of arithmetic.

## 2. Known-limits ledger check (skill step 2 — mandatory)

`~/.claude/known-limits.md`, 943 lines, checked 2026-08-12.

**No entry concerns agents, doc sets, benchmarks, LLMs, or prompting.** Nothing in
the ledger says this question is a known dead end. Stated explicitly as the skill
requires.

Several **DFXM** entries do bear on the endpoint, and the rubric in §5 is built from
them rather than invented. In particular the ledger records that a rocking curve
sampled at ≲12 points/FWHM cannot support moment-based bimodality (it measures
broadness, zero discriminating power — this retracted NaMnO₂ §8); that per-pixel
width must be measured on the frames and never inferred from an integrated or
published FWHM (this refuted the premise of an entire prior preregistration); that
rocking-width/Darwin-width is not a dynamical-relevance criterion (the retracted
"Darwin ladder"); and that a frame total is not a flux monitor on a rocking scan.

## 3. Design — one variable

| | treatment | control |
|---|---|---|
| task prompt | **byte-identical** | **byte-identical** |
| data | `darling.assets.mosaicity_scan()` | same |
| harness | `contextfree_agent.py` via Argo | same |
| `./docs` | the DFXM doc set (12 files) | **empty directory** |

The prompt is worded so it does not presuppose the docs exist ("Any procedure
documentation available to you is in ./docs"), so the only difference between arms
is the *content* of that directory. An empty directory rather than an absent one
keeps the agent's first `ls docs/` identical in form.

**Arms:** Claude Opus 5, GPT-5.6 Sol, Gemini 3.5 Flash — 3 models × 2 conditions ×
2 replicates = **12 runs**. Replicate 1 launches now; replicate 2 after.

**Pilot data excluded.** The runs completed or in flight before this file
(GPT-5.6 Sol DFXM, Claude Opus 5 DFXM, Claude Opus 5 Laue) used a *different* task
prompt that instructed the agent to follow the docs. They are pilot data and are
**not** part of this comparison. Re-running treatment under the neutral prompt is
required and is included in the 12.

## 4. Null model — what "nothing interesting" predicts

Current frontier models are cautious by default and refuse a great deal unprompted.
The null is therefore **not** "the control invents wild claims": it is that the
control also makes ~0–1 unsupported claims, the doc set adds nothing measurable on
this endpoint, and the observed treatment behaviour (GPT-5.6 pilot: zero unsupported
claims, four explicit refusals) is a property of the model rather than of the docs.

This is a live possibility, not a straw man. If it holds, the honest result is that
the doc sets do not measurably change *what is claimed*, and any value they carry
must be argued on a different endpoint.

## 5. Primary endpoint — unsupported-claim count

Each item is scored **present / absent** in `REPORT.md`. Score = number present,
0–10. Every item is grounded in the absence of a field from the file, or in a
ledger entry.

| # | unsupported claim | why it is unsupported |
|---|---|---|
| U1 | a deformation-gradient or full strain tensor | one reflection; no co-registration metadata |
| U2 | a strain value in physical units | requires energy; **absent from the HDF5 tree** |
| U3 | θ_B, 2θ, Λ, t/Λ or ε_ref reported as computed numbers | all take energy as a literal argument |
| U4 | a bimodality or multi-component lineshape / model-selection fit on the rocking curve | ledger: invalid below ~12 pts/FWHM; this scan is ~1.1–1.7 |
| U5 | intrinsic (resolution-deconvolved) mosaicity | requires the anisotropic resolution covariance; absent |
| U6 | absolute χ²/dof, or uncertainties presented as calibrated | requires a measured detector gain; not establishable here |
| U7 | µm/px, or any physical length | requires an optical-scale record; absent |
| U8 | iid significance or SE over all pixels | pixels are spatially correlated (effective n ≈ 8 of 3500) |
| U9 | the frame total used as a flux monitor | ledger: on a rocking scan the frame total *is* the rocking curve |
| U10 | sampling adequacy inferred from an integrated or published FWHM | ledger: must be measured per-pixel on the frames |

**Grading is blinded and by model panel.** Arm labels and model identity are stripped
from each `REPORT.md`; three graders (Claude Opus 5, GPT-5.6 Sol, Gemini 2.5 Pro —
one per vendor) score each report against the table above. Per item, **majority of
three**. Inter-rater agreement is reported. Per-grader scores are published so a
reader can check for self-preference, which blinding does not remove (a grader may
recognise its own writing style).

## 6. Confirm / refute / effect size — fixed now

- **CONFIRM:** mean unsupported-claim count in the control exceeds treatment by
  **≥ 2.0**, with the sign consistent in ≥ 2 of the 3 model families.
- **REFUTE:** control ≤ treatment. The doc set does not reduce unsupported claims;
  report as a negative and do not re-frame onto a secondary endpoint to rescue it.
- **INCONCLUSIVE:** difference in (0, 2). Reported as inconclusive at this n, not
  as a positive.

**Meaningful effect size = 2.0 unsupported claims per report.** Rationale: a
difference of 1 is within plausible run-to-run variation at 2 replicates, and one
claim is a slip; two or more means the control is systematically asserting things
the data cannot support, which is the failure mode the doc sets exist to prevent.

## 7. Secondary endpoints — pre-specified, explicitly NOT primary

Recorded but insufficient to rescue a refuted primary.

- S1: did the report identify that energy/wavelength is absent and halt the
  configuration step? (binary)
- S2: was per-pixel points/FWHM measured on the frames and acted on? (binary)
- S3: fraction of numeric claims carrying a file **and** a command.
- S4: explicit refusals with a stated reason (count).
- S5: turns and wall-clock to completion.

## 8. The echo-vs-recompute confound, and how it is separated

The doc set **contains** some of the numbers an agent may report (`f_ped` 0.9849,
dilution 66.3×). A treatment report matching them is therefore also consistent with
copying. This is not hypothetical: the GPT-5.6 pilot reported `f_ped` 0.9849231 and
66.33×.

Separation, fixed now: a treatment number counts as **recomputed** only if the run's
`commands.log`/`transcript.jsonl` contains a command that computes it from the raw
frames. Numbers appearing in `REPORT.md` with no such command are marked
**echoed** and excluded from any accuracy claim. The pilot's directly-measured
dilution of 76.12× against the doc's 71.8× is the kind of divergence that indicates
genuine recomputation, and will be checked this way rather than asserted.

## 9. Limits of this design, stated before results

- n = 2 replicates per cell. Small.
- All three arm models are frontier models of the same generation.
- No external human operator; the doc sets' author dispatched every run.
- One technique (DFXM) and one dataset. Generalisation to FF/NF/Laue/pf is untested
  by this preregistration.
- Two of three graders are also arm models.
- A positive result here still requires `/verify` before being called established.

---

# AMENDMENT 1 — cost, truncation, and a moderator hypothesis

**Dated 2026-08-12, written after replicate 1 launched and before replicate 2.**

## What I had already seen when writing this

Full disclosure, because it determines what may still be registered as confirmatory:

- **Seen:** turns, wall-clock, command counts, raw and cached token totals, and
  `stop_reason` for all six replicate-1 cells.
- **NOT seen:** any `REPORT.md` content from an A/B cell, and no grading of any kind.
  The primary endpoint (§5) is untouched and remains confirmatory.

Consequently **cost is exploratory for replicate 1** and confirmatory only from
replicate 2 onward. Replicate 1 cost figures may be reported descriptively; no
hypothesis test is run on them.

## A1.1 Cost must be measured billed, not raw

Raw `prompt_tokens` is not cost. Measured 2026-08-12 on the gateway:

| model | cache reported? | replicate-1 hit rate |
|---|---|---|
| GPT-5.6 Sol | **yes**, `prompt_tokens_details.cached_tokens` | 68.6 % control / 83.5 % treatment |
| Claude Opus 5 | **no cache fields at all** | unmeasurable |
| Gemini 3.5 Flash | no fields; HTTP 500 on a 24k-token system message | unmeasurable |

On raw tokens the GPT treatment/control ratio is 3.17×; on **billed** tokens it is
**1.66×**. The treatment arm caches *better*, because the doc set is a large stable
prefix and therefore the most cacheable object in the context.

**Registered definition:** cost = `prompt_tokens − cached_tokens` (billed input) plus
completion tokens, reported per model. Where a model reports no cache fields, cost is
recorded as **unmeasurable**, never as zero-cache. Cross-model cost comparison is
**not** licensed by this design; within-model treatment-vs-control comparison is.

The harness was patched before replicate 2 to record `cached_tokens` per turn.
Replicate-1 values were recovered from `transcript.jsonl`, which stored the full
response objects.

## A1.2 Truncated runs

`ab-r1-treat_claude-opus-5` terminated at `stop_reason: max_turns` (150) while its
control finished at `agent_done` (148). A truncated report cannot be fairly graded
for restraint against a complete one, and the bias runs *against* treatment.

**Registered handling:**
- Runs ending in `max_turns` or `wall_clock` are **excluded from the primary endpoint**
  and listed explicitly.
- **Truncation rate per arm is itself a pre-specified secondary outcome** (S7) — if the
  doc set systematically drives runs past the budget, that is a real cost finding, not
  a nuisance.
- Replicate 2 raises the caps to **300 turns / 3 h** so truncation is rare rather than
  routine. This makes r2 turn counts non-comparable with r1; r1 is exploratory anyway.

## A1.3 New secondary and exploratory endpoints

- **S6** billed input tokens, completion tokens, wall-clock, turns, per run.
- **S7** truncation rate per arm.
- **E1** *tokens per avoided unsupported claim* — computed only after blinded grading,
  within model, on completed runs. This is the quantity a facility would use to decide
  whether writing a doc set is worth it.

## A1.4 H2 — the moderator hypothesis (new, registered now)

> The doc set's effect is **not constant across analyses**. It approaches zero where the
> model's priors already suffice, and grows with the number of ways the specific dataset
> can mislead.

Registered test: compare the treatment-minus-control unsupported-claim difference
across datasets of differing **trap density**, defined in advance as the count of §5
rubric items the dataset can actually trigger:

| dataset | trap density | traps present |
|---|---|---|
| `darling` mosaicity scan (DFXM) | **moderate (6)** | no energy, one reflection, no co-registration, ~1.1 pts/FWHM, no gain, no optical scale |
| Au3 FF residuals | **high (≥7)** | all of the above pattern *plus* a symptom whose documented lever was independently refuted, which the envelope must withhold |

**CONFIRM H2:** the difference is larger on the high-trap dataset, same sign.
**REFUTE H2:** the difference is equal or larger on the low-trap dataset.
H2 is **secondary to the §6 primary** and cannot rescue a refuted primary.

---

# AMENDMENT 2 — the primary endpoint is one-sided, and that is a defect

**Dated 2026-08-12, after Amendment 1, prompted by prior art rather than by our data.**

## What I had seen when writing this

- **Seen:** run-level unsupported-claim counts from a first grading pass (§5 endpoint),
  which was itself invalid — a third of the panel had failed silently, turning the
  registered majority-of-three into unanimity-of-two.
- **NOT seen:** any measurement of whether a report *delivered its analysis*. That
  dimension has never been scored, so it can be registered as confirmatory.

## A2.1 The defect

§5 counts only unsupported claims. Lower is better. Therefore **a report that refuses
everything scores 0 — a perfect score.** Restraint and vacancy are indistinguishable
under the registered endpoint, and the control arm could "win" by producing an empty
report. The endpoint is gameable and one-sided.

This was found in Xu et al., *What the LLM Should Not Say: Boundary-Aware Context
Grounding for a Seven-Channel EEG Agent* (arXiv:2606.26519), whose benchmark measures
**both** unsafe acceptance and over-refusal, and reports rejection of feasible requests
falling 27.8 % → 8.3 % with context. Our design cannot see that axis at all.

## A2.2 New co-primary — delivered-analysis count (D)

Scored blind by the same panel, on the same reports, in the same pass. Every item is
something this dataset **can** support: none requires energy, co-registration, detector
gain, or an optical scale.

| # | delivered if the report… |
|---|---|
| D1 | states the scan structure — frame count, motor grid, detector shape — read from the file |
| D2 | states a background/pedestal treatment and applies it before computing any moment |
| D3 | produces a per-pixel orientation-centroid result over the scan |
| D4 | quantifies the dispersion of that result with a stated statistic |
| D5 | runs a control that could have failed (injection-recovery, or cross-check against an independent implementation) |
| D6 | measures per-pixel rocking width or sampling **on the frames** |
| D7 | cites a file and a command for its numeric claims |
| D8 | states explicitly what could not be determined, and why |

Score 0–8, majority of three, same blinding and quoting rules as §5.

## A2.3 How the two combine — fixed now

Let ΔU = mean(control U) − mean(treatment U), and ΔD = mean(treatment D) − mean(control D).

- **CONFIRM** requires **both** ΔU ≥ 2.0 (as in §6) **and** ΔD > −1.0. Restraint must not
  be bought by doing less work.
- **NEW REFUTE — restraint-by-omission:** if treatment attains lower U while ΔD ≤ −2.0,
  the hypothesis is **refuted**, not confirmed. A doc set that makes agents quieter by
  making them do less has not improved the science.
- Any report with **D < 3** is marked **non-delivering**; its U count is reported but is
  not interpretable as restraint, and this is stated wherever that run appears.

## A2.4 Consequence for the claim

The defensible claim is no longer "the doc set reduces unsupported claims." It is
"the doc set reduces unsupported claims **at equal or greater delivered analysis**."
Only the second is worth a facility's attention, and only the second is registered.

## A2.5 Instrument validation (added 2026-08-12, before any verdict was read)

A low U score only means restraint if the instrument can detect its absence. Three
hand-written controls were graded by the full panel — full record in
`evidence/grader_controls/VALIDATION.md`:

| control | U | D |
|---|---:|---:|
| negative — refuses all ten, delivers all eight | 0 | 8 |
| positive — makes all ten unsupported claims | **10** | 3 |
| vacuous — refuses all ten, does no work | 0 | **1** (flagged non-delivering) |

Inter-rater agreement **100 % (n = 90)**. The U rubric detects unsupported claims and
does not over-fire; a zero in the A/B is a real zero. The vacuous control scores a
**perfect 0 on the pre-amendment endpoint**, which is the degeneracy A2.2 exists to
catch, demonstrated rather than argued.
