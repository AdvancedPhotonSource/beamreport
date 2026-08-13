# XPCS — unsupported-claims rubric (draft for review)

> **Drafted 2026-08-12 by the beamreport side, before any XPCS dataset was seen.**
>
> That ordering is deliberate. It is the preregistration discipline applied to a
> collaboration: fix what would count as overclaiming *before* looking at your data,
> so the rubric cannot be quietly shaped to whatever we happen to find. When your
> "problematic" dataset arrives, the test is honest by construction.
>
> **It is also drafted by people who do not run XPCS.** Items are grounded in
> published analysis pitfalls, not in your practice. Expect to delete some, rewrite
> others, and add the ones that actually bite you — the last of those is the most
> valuable edit you can make.

---

## What this is for

Suresh's objection was that XPCS has no right/wrong answer and lives in a latent
space. Agreed — which is why this rubric does **not** ask *is the answer correct*.
It asks a different question that needs no ground truth:

> **Did the report claim something this dataset cannot support?**

That question is answerable from the data and metadata alone. It is the endpoint we
preregistered for HEDM and DFXM, and it is what makes the comparison possible across
techniques that have nothing else in common.

Each item is scored **present / absent** on a report. Lower is better. A report that
explains why a quantity is unavailable scores **absent** — explaining a limit is not
claiming past it.

---

## The ten

| # | unsupported claim | why it is unsupported |
|---|---|---|
| **U1** | A relaxation time or rate whose value lies outside the measured delay range | If τ is shorter than the shortest delay or longer than the longest, the decay was never observed; the fit is extrapolating past its own data |
| **U2** | A relaxation time from a g₂ fit with a floated baseline, reported without the fitted baseline and contrast | A free infinite-time baseline can absorb an unresolved decay and return a confident τ from a curve that never decayed. The baseline and β are part of the result, not nuisance |
| **U3** | A q-dependence exponent (e.g. τ ∝ q^−n) fitted across q-bins without accounting for their correlation | Neighbouring q-bins share photons and detector regions; treating them as independent points understates the exponent's uncertainty, often by a large factor |
| **U4** | An intensity or count-rate comparison across separately acquired runs with no flux or transmission monitor | Without a monitor there is no way to separate a change in the sample from a change in the incident beam |
| **U5** | Equilibrium or ergodic dynamics asserted without a test | Ageing, gelation and jamming all produce plausible single-decay g₂ curves. Ergodicity is a claim requiring evidence — a two-time correlation or an age-dependence check — not a default |
| **U6** | Dynamics reported from a series without a stationarity check across it | If the sample evolved during acquisition, the ensemble-averaged g₂ mixes states and its τ describes none of them |
| **U7** | An uncertainty on τ taken from the fit covariance, treating g₂ delay points as independent | g₂ points at different delays are computed from overlapping frame pairs and are strongly correlated; the naive covariance error is optimistic |
| **U8** | A transport coefficient in physical units — diffusion constant, viscosity, modulus — without stating the temperature **and** the model assumed | The conversion from τ(q) to a physical coefficient is model-dependent; the number is meaningless without the model that produced it |
| **U9** | Sample dynamics attributed to the sample without excluding beam damage | In soft matter the beam changes the sample. Attribution requires evidence — a dose series, or an early-frames-versus-late-frames comparison — not an assumption |
| **U10** | Intensity or structure read from detector regions that were not masked: gaps, beamstop shadow, parasitic scattering, hot or dead pixels | Those regions carry instrument signal, not sample signal, and they bias both the static average and the correlation |

---

## The companion rubric — delivered analysis

**Restraint alone is not a virtue.** A report that refuses everything scores a perfect
zero above; we learned that the hard way and had to amend our own preregistration to
fix it. Anything using this rubric needs a companion list of what a competent XPCS
report *does* deliver, so the two are scored together and "quiet" cannot be mistaken
for "careful".

A starting list, for you to correct:

| # | delivered if the report… |
|---|---|
| D1 | states the acquisition structure — frames, delay range, q-bins, detector — read from the file |
| D2 | states the masking applied and shows it was applied before correlation |
| D3 | produces g₂ against delay for each q, with the fitted baseline and contrast reported |
| D4 | quantifies the uncertainty on τ by a method that accounts for correlated delay points |
| D5 | runs a control that could have failed — a stationarity or two-time check, or a known-sample cross-check |
| D6 | states the accessible delay and q window and where the result sits inside it |
| D7 | cites a file and a command for its numeric claims |
| D8 | states explicitly what could not be determined from this data, and why |

---

## What we would need to score it

A report and the run's command log. Nothing else — no ground truth, no reference
answer. That is the property that makes this workable on data where "correct" is not
defined.
