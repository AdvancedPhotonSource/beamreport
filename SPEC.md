# beamreport — specification

**What it is.** A contract plus a report builder. You hand it a finished measurement in a
declared shape; it produces a self-contained, publishable account of that measurement,
including diagnostics that separate what the data supports from what is a fixable systematic.

**What it is not.** It is not a plotting library, and it does not know your technique. It draws
no technique-specific figure and invents no interpretation. The parts that make a report worth
reading — your figures, and your diagnosis reference — stay in your repository.

This document is written for a person or an agent to follow directly. Sections 1–3 are the
contract (what you must supply). Sections 4–7 are the conventions (what makes the output
honest). Section 8 lists the refusals, which are how the conventions are enforced rather than
merely recommended.

---

## 1. The contract, in one paragraph

You supply five objects. Three of them almost certainly already exist in your pipeline. The
fourth — the diagnostics sidecar — usually does not, because most fitting code computes
per-observation residuals and then discards them. The fifth is the diagnosis reference, which
is written prose and is the part that takes real time.

| # | Object | Usually exists? | Without it you lose |
|---|--------|-----------------|---------------------|
| 1 | Result table | yes | everything |
| 2 | Quality scalar | usually | filtering, colouring, most stat tiles |
| 3 | Parameters + provenance | yes | the ability to re-derive any number |
| 4 | **Diagnostics sidecar** | **usually not** | **every diagnostic; the report becomes descriptive only** |
| 5 | Diagnosis reference | no | the findings; the page is typeset and says nothing |

A report built from 1–3 alone is a **descriptive report**: what was measured, what came out,
how the results distribute. That is a real deliverable and `beamreport` will produce it.

A report built from 1–5 is a **diagnostic report**: it also says which systematics are present,
how they were discriminated from the alternatives, and what to change. That is the product
people actually want.

---

## 2. Objects 1–3: results, quality, provenance

### 1. Result table

One row per recovered object. An "object" is whatever your analysis recovers as a unit: a
grain, a domain, a fitted mode, a region, a time bin.

```
object_id     int      stable within this run
<params...>   float    the recovered quantities
```

**Units are declared, never assumed.** `beamreport` imposes no unit system. It requires each
column to carry a unit string, and refuses to render a column that has none (§8). A column
named `radius` with no unit is a bug report, not data.

### 2. Quality scalar

One float per object saying how well the model explains that object. Higher is better. Any
monotone measure works — a completeness fraction, an explained-variance, a normalised
likelihood. Everything on the page can be filtered, sorted and coloured by this, so it is worth
supplying even if imperfect.

Declare the threshold below which you would not quote an object. `beamreport` shows both
populations and never silently drops rows.

### 3. Parameters and provenance

The configuration the analysis ran with, plus enough to re-derive any number on the page:
input paths, the parameter file, the command line, code version. This is printed on the report
as a provenance strip.

The rule that makes this worth enforcing: **a number that cannot be re-derived does not go on
the page.** Not "is flagged". Does not go on.

---

## 3. Object 4: the diagnostics sidecar

This is the object that decides which product you get, and the one change most groups have to
make. If your fit computes a per-observation misfit and keeps only fitted parameters and a
chi-squared, that information is being thrown away roughly at the moment it becomes useful.

### Shape

```
observations/table        (N, K) float array — ONE ROW PER OBSERVATION, not per object
observations/columns      list[str]  — column names
observations/units        list[str]  — one per column
observations/roles        list[str]  — one per column: "id" | "coord" | "residual" | "weight" | "aux"

rollups/<coord>/...       optional pre-binned medians and spreads along each coordinate
overall/...               optional scalars: median and robust spread per residual channel
```

The only thing you must decide is **which columns are coordinates and which are residuals**.
That declaration is the entire adapter job, and it is what lets generic diagnostics run on a
technique they have never seen.

- **`id`** — links the observation back to a row of the result table.
- **`coord`** — where the observation was taken. Any axis along which a systematic could
  organise itself: an angle, a detector region, a delay time, a wavevector, a frame index, a
  temperature. Supply every axis you can; unused ones cost nothing.
- **`residual`** — the model misfit. One column per independent channel. Signed, in physical
  units, not squared and not summed.
- **`weight`** — optional per-observation weight or uncertainty.
- **`aux`** — carried through, plotted on request, never interpreted.

### Why per-observation, and why signed

Summary statistics cannot answer the question the diagnostics ask, which is always *does this
misfit organise itself along some axis, or is it noise*. A chi-squared has already destroyed
that information. Squared residuals destroy the sign, and the sign is what distinguishes a
common offset from symmetric scatter.

### Size

Sidecars are large — hundreds of MB is normal. Write them next to the run, build the report
where the data lives, and ship only the report. Never write either to `/tmp`.

---

## 4. What beamreport computes for you

These tests are technique-independent. They know nothing about your physics; they only require
the `coord` / `residual` declaration above.

- **Trend against each coordinate.** For every residual channel against every coordinate axis:
  fit constant, linear and periodic trends, and report which is supported. A structured
  residual is a systematic; a flat one is not.
- **Systematic versus scatter.** Aggregate the residual per object, then compare the mean of
  those aggregates against their spread. `mean >> spread` means a common offset shared by every
  object, which is an instrument or model property and is usually fixable. `mean ~ 0` with large
  spread is genuine per-object variation and is not a bug. This single test resolves more
  arguments than any other.
- **Constant-versus-growing amplitude.** When a trend exists on more than one coordinate bin,
  report whether its amplitude is constant in absolute units or grows with the coordinate. The
  two point at different causes, and the discrimination is arithmetic, not judgement.
- **Per-bin rollups** along each coordinate, with robust spread.
- **Population splits.** Detect multimodality in per-object aggregates, and test whether the
  split is spatial, parametric, or neither. A bimodal quality distribution that splits
  spatially is usually illumination or coverage; one that does not is usually a solver branch.
- **Null comparison** for any quantity that has a registered null (§5).
- **Quality distributions**, bounded populations, and objects at a parameter bound.

**Detection generalises. Interpretation does not.** `beamreport` tells you a trend is there,
what shape it has, and whether it is common or per-object. Which lever to pull is your
diagnosis reference.

---

## 5. The null rule

**Every quantity you intend to quote gets a null**: what the same analysis returns on data that
cannot contain the effect. Shuffled labels, an unloaded reference, a region known to be empty,
a synthetic sample with the effect absent.

Quote only **doubly-supported** quantities: above the measured null *and* recurring across
independent measurements. A quantity that clears the null once, at one position, is a pipeline
intermediate.

This matters more, not less, once reports are automatic. When a page takes seconds to build,
the bottleneck stops being production and becomes discrimination. A fast builder with no null
layer produces confident nonsense at scale, and it produces it faster than anyone can check it.

Register nulls alongside the quantity they guard. In v0.1 an unnulled quantity renders with a
visible warning; the intent is that it becomes an error.

---

## 6. The diagnosis reference

The written table that turns a diagnostic into an action. It is the highest-value object in
this whole design and it cannot be generated, borrowed, or inferred from data.

### Entry format

Every entry has four parts, in this order:

1. **Symptom** — what is visible in a diagnostic figure, stated so a reader can match it.
2. **Discriminating test** — the arithmetic that separates this cause from the most plausible
   competing cause. **This test must be able to come back the other way.**
3. **Cause** — what it means when the test comes back this way.
4. **Lever** — the specific change that fixes it.

### Why part 2 is non-negotiable

An entry without a falsifiable test turns the report into a machine for confirming whatever
the author already believed, and automation makes that failure fast and voluminous. If you
cannot write a test that could exonerate the suspected cause, you do not yet understand the
symptom well enough to write the entry.

### Worked entry, technique-neutral

> **Symptom** — fitted positions show a sharp core plus a broad tail.
>
> **Discriminating test** — do not assume the tail is physical, and do not assume it is the
> optimiser hitting a bound. Test both. If the outermost shell holds near zero percent of
> objects, the bound is not being reached and divergence-to-bound is refuted. Then correlate
> each fitted position against its own residual. Near-zero correlation means the data supports
> those positions. Strong negative correlation, with tail objects carrying residuals pointing
> back toward the core, means the observations contradict the fit.
>
> **Cause** — the tail is a fitting artifact, not structure.
>
> **Lever** — set the illumination extent to the true per-measurement value rather than the
> whole-sample envelope, then re-check that the residual stays flat.

### How the reference grows

Not by a writing project. Every time somebody spends an afternoon working out what a strange
plot meant, that afternoon becomes one entry, written the same day. Three entries is enough to
start; the reference compounds because the work was going to happen anyway.

---

## 7. Report architecture and the documents

### One overview, linking out to one page per measurement

A single page that grows with a campaign becomes a chronology of the analysis rather than a
description of the samples, and the experimenter cannot find their own sample in it. **Split at
the second dataset, not when it hurts.**

```
OVERVIEW                          the URL you share first; keep it stable, re-publish in place
  ├── what the campaign is, one table of measurements with links
  ├── findings that SPAN measurements
  └── what is still open
        ├──> per-measurement page        ├──> per-measurement page
        └──> per-measurement page        └──> per-measurement page
```

- **One page per measurement, not per specimen**, when measurements differ in conditions. Two
  measurements of one specimen get two pages and are compared *in the overview*, never silently
  averaged.
- **Combine only what the reader treats as one question** — a sample and its own control belong
  together because they are read against each other.
- **Each page is self-contained.** It repeats its method and caveats. Readers arrive from a
  link; a page that assumes the overview was read will be misread.
- **Every page carries the same handful of diagnostics**, because those are what make two pages
  comparable at all. Include the effective sample size beside the nominal count.
- **Export the numbers next to the pictures.** A CSV per measurement alongside the figures.
  "We extracted the parameters" usually means the reader wants the table, not only the map.
- **Publish children first, collect their URLs, then build the overview**, and re-publish the
  overview whenever a child changes.
- **Every spatial map is drawn to true scale.** A stretched map misrepresents exactly the shape
  the reader is examining.

### Three documents, never one

| Document | Contains | For |
|---|---|---|
| **Handbook** | Hard rules, the trap table, the numbered procedure, the invariants that make a result silently wrong if violated. | Someone with no prior context who must take a measurement through to an answer today. |
| **Lab notebook** | The evidence. What the campaign established with a status column, defects fixed, method findings, scientific findings, **retracted claims and open questions**, and a measurement ledger putting every verified number beside its provenance. | Anyone about to re-investigate something, so they learn it was already investigated and how it came out. |
| **Runbook** | Operational state. Access, how to launch, **what healthy looks like for this instrument with conditions attached**, and one volatile section holding the current pick-up point that every session updates before it ends. | The next session, human or agent. |

Rules: a new *procedure* goes in the handbook; a new *finding or refutation* goes in the
notebook; any number quoted in the handbook has its provenance in the notebook ledger. Write
one notebook **per campaign, not per dataset, and start it on day one** — the retractions decay
fastest, and backfilling them does not work.

There is no single number for "healthy". A runbook that publishes one threshold will produce
false alarms on the heavy measurements and silence on the broken ones. Publish a table of
measured ranges with the conditions attached.

---

## 8. Refusals

These are how the conventions are enforced rather than merely documented. `beamreport` will
refuse to render:

1. A column with no declared unit.
2. A number with no provenance path.
3. A page with no provenance strip.
4. A spatial map with a non-equal aspect ratio.
5. An overview whose child links have not been resolved to URLs.

And will render with a visible warning:

6. A quoted quantity with no registered null.
7. An objects-at-bound fraction above zero that the caller has not acknowledged.

Refusals are loud and name the offending field. A silent degradation in a report generator is
worse than a crash, because the page still looks authoritative.

---

## 9. Deferred, explicitly

Not in v0.1, and not to be designed for until there is a second caller asking:

- Multi-lane export (LaTeX, pptx, print). Today these lanes share numbers and figures but not a
  source. Decide which lane is canonical before unifying them.
- The null harness as an enforced API rather than a warning.
- Live, during-acquisition reporting.
- Any figure library, plugin system, or config schema.

The sidecar contract (§3) is the seam that makes each of these cheap later. Building to it now
is not throwaway work.
