# <TECHNIQUE> — measurement envelope

**Instrument / beamline:** <where this applies>
**Last checked:** <YYYY-MM-DD> · **Owner:** <name>

What this measurement can and cannot determine, and which of those is changeable. Read it
before promising an answer, and before suggesting a different measurement. See
`DOCS_SPEC.md` §6 for why the tiers matter.

> This is **not** the scope gate. Scope says whether the doc set applies to your data.
> This says whether the measurement can answer the question at all. A dataset can be
> squarely in scope and still unable to support what is being asked of it.

---

## 1. Fixed — cannot change this cycle

No counterfactual belongs here. State the consequence and the substitute, not a suggestion.

| Property | Value | Provenance | What it makes unobtainable | Substitute |
|---|---|---|---|---|
| <e.g. beam/detector angle> | <value + unit> | <measured / spec sheet + date / person> | <the quantity that is now not directly measurable> | <the external input that stands in, or "none"> |

## 2. Configured — set per run, changeable next time

**The only tier where "what could be observed differently" has an answer.** Every row needs
a current value *and* a bound, or the report will decline to reason about that axis.

| Parameter | Used | Achievable range | Limited by | What changing it would buy |
|---|---|---|---|---|
| <e.g. frame time> | <value + unit> | <min–max + unit> | <detector / dose / stage / source> | <the quantity it would make accessible> |

Bounds with no declared source are the dangerous rows. A precise number nobody re-checked
is worse than a missing one, because a missing one produces silence and a stale one
produces confident advice.

## 3. Intrinsic — the sample or the physics forbids it

No configuration helps. Say so plainly and stop.

| Question | Why it is not answerable | Distinguish from |
|---|---|---|
| <the thing people will ask for> | <the physical reason> | <the nearby thing that IS answerable, so the two do not get conflated> |

## 4. Derived limits

What follows arithmetically from §1–2. These are the numbers a report may quote directly.

| Quantity | Limit | From |
|---|---|---|
| <e.g. fastest resolvable timescale> | <value + unit> | <which rows above, and the relation> |

## 5. Did not versus cannot

Things that were *not* done on this run but are perfectly possible. They read identically
to hard limits in a parameter file and mean the opposite to anyone deciding whether to
come back.

- <what was skipped, and what it would have cost>

---

**Checklist before this file is trusted**

- [ ] Every row has a unit
- [ ] Every bound in §2 names what imposes it
- [ ] Every spec-sheet number carries the date it was taken from the sheet
- [ ] Nothing in §1 or §3 is phrased as a suggestion
- [ ] `Last checked` is within the current run cycle
