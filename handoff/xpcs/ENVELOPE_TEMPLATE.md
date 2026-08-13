# XPCS measurement envelope — skeleton for 8-ID-I

> **This file is deliberately unfinished, and the blanks are the point.**
>
> An envelope declares what a report-generating agent may and may not recommend
> changing. It only works if the values come from the people who run the instrument.
> If we filled these in from the literature we would be inventing the very thing the
> envelope exists to prevent — a confident recommendation with no basis — and the
> first time it told someone to change a fixed quantity, the whole mechanism would
> have earned its distrust.
>
> Every `<...>` below is a question for the instrument owners. A blank left blank is
> a correct outcome; a blank filled in by us is not.

**Instrument:** APS 8-ID-I · **Owner:** <name> · **Date:** <YYYY-MM-DD>

---

## Why an envelope, in one paragraph

A diagnosis reference maps a symptom to a *lever* — "residual X looks like Y, so
change Z." That advice is worthless or harmful when Z cannot be changed on this
instrument. The envelope declares, per quantity, which of three tiers it sits in, and
**the envelope outranks the diagnosis reference**: where they disagree, the lever is
withheld and the finding is reported as a characterisation of the measurement rather
than as a defect to correct.

| tier | meaning | may the agent propose changing it? |
|---|---|---|
| **fixed** | set by the instrument or the facility; not adjustable by a user in a normal experiment | **no** — report the consequence, withhold the lever |
| **configured** | chosen per experiment, adjustable next time | **yes** — this is the only tier that earns a counterfactual |
| **intrinsic** | a property of the sample or the physics, not of the setup | **no** — it is the thing being measured |

Worked example from a live set, for the shape: in `manuals/ff-hedm/ENVELOPE.md` the
beam-shape row is declared **fixed**, so when the generator fired
`trend.amplitude_growing` on real data it printed the reference's lever *and then
withheld it*, saying the envelope declares the quantity unchangeable. That is the
behaviour to aim for.

---

## 1. Beam and coherence

| quantity | tier | value / range | notes |
|---|---|---|---|
| photon energy | <fixed / configured> | <keV, and the set of values actually selectable> | if only discrete energies are practical, say which |
| transverse coherence length | <fixed> | <µm, H × V> | after APS-U; state the date, it changed |
| longitudinal coherence length | <fixed> | <µm> | sets the usable q·Δλ/λ range |
| coherent flux | <fixed> | <ph/s> | the number that sets achievable statistics |
| beam size at sample | <configured?> | <µm × µm, and the selectable set> | slits vs focusing optics — which is realistically changeable mid-run? |

## 2. Detector and geometry

| quantity | tier | value / range | notes |
|---|---|---|---|
| detector(s) available | <fixed> | <model(s)> | |
| pixel size | <fixed> | <µm> | |
| **frame rate — maximum and practical** | <fixed> | <Hz> | **the ceiling on the shortest measurable delay.** If an agent recommends "sample faster", this row is what makes that advice legal or illegal |
| sample–detector distance | <configured> | <m, and the selectable set> | if it takes a shutdown to change, it is fixed, not configured |
| accessible q-range | <derived> | <Å⁻¹> | derived from the two rows above; state it so the agent need not re-derive it |
| detector gaps / beamstop / masked regions | <fixed> | <description or mask file> | |

## 3. Acquisition

| quantity | tier | value / range | notes |
|---|---|---|---|
| shortest delay time | <fixed, derived> | <s> | = 1 / max frame rate |
| longest delay time | <configured> | <s> | set by series length; state the practical limit |
| number of frames per series | <configured> | <range> | |
| **flux / transmission monitor present?** | <fixed> | <yes → channel name / no> | if **no**, every cross-run intensity comparison is unsupported and the agent must be told so |
| attenuation / dose control | <configured> | <what is adjustable> | the lever for beam-damage findings |

## 4. Sample environment

| quantity | tier | value / range | notes |
|---|---|---|---|
| temperature control | <configured / none> | <range, stability> | |
| sample cell / geometry | <configured> | <options> | |
| **is the sample changing during acquisition?** | <intrinsic> | — | ageing, damage and equilibration are the measurement, not a defect |

## 5. Declared-fixed symptoms — the rows that actually do work

For each symptom the diagnosis reference can emit, name the quantity it would tell
someone to change, and whether that is legal here. **Only rows whose quantity is
`configured` may produce a lever.**

| symptom | reference would say | quantity | tier | lever? |
|---|---|---|---|---|
| decay faster than the shortest delay | "sample faster" | max frame rate | <fixed> | **withhold** — report that the dynamics are faster than the instrument resolves |
| decay slower than the longest delay | "measure longer" | series length | <configured> | allow |
| statistics too poor at high q | "increase flux" | coherent flux | <fixed> | **withhold** — report the q above which the measurement is not statistics-limited but flux-limited |
| intensity drift across runs | "normalise by monitor" | monitor channel | <fixed: present or absent> | allow **only if a monitor exists**; otherwise withhold and report the comparison as unsupported |
| <add rows as the reference grows> | | | | |

---

## How to finish this

1. Fill in the tiers first, values second. The tier is the load-bearing part; a value
   with the wrong tier is worse than a blank.
2. For anything you hesitate over, ask: *if the report told a user to change this,
   could they actually do it before their beamtime ends?* If no, it is fixed.
3. Sourced bounds only — every value should be traceable to a measurement, a
   commissioning record or a specification, not to recollection. The linter
   (`beamreport-doc-lint`) checks that bounds carry a source.
4. Send it back unfinished if that is where it gets to. A half-filled envelope with
   honest blanks is usable; a complete one containing guesses is not.
