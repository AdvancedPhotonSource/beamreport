# The technique doc set — specification

SPEC §7 says a technique needs **three documents, never one**. This file is that table
expanded into a contract a technique can be checked against, plus the fourth artifact §7
did not name because it was already covered elsewhere: the **diagnosis reference**.

`beamreport` supplies the contract and the linter. It does **not** supply the content —
same boundary as ADAPTER.md §5. Your procedure cites your code, so it lives in your
repository where a citation can be checked and a release can invalidate it.

---

## 1. Why a doc *set* and not a document

A handbook that grows past roughly a thousand lines stops being loadable. An agent, or a
person in a hurry, then does one of two things: takes the whole file and spends its
context on sections it will never reach, or skips to the step it thinks it needs. The
second is the dangerous one, because the rules that prevent a silently wrong result are
concentrated at the top and are exactly what gets skipped.

Splitting fixes that only if the split is on the right axis. **Split by when it is read,
not by subject.** A file per step sounds tidy and is wrong: the hard rules apply across
all steps, and a symptom is almost never diagnosed in the step that caused it.

## 2. The four artifacts

| Artifact | Contains | Read when | Volatile? |
|---|---|---|---|
| **Spine** (`README.md`) | scope gate, install gate, order of operations, hard rules, halt conditions, an index of the rest | **always** — the only part that stays loaded | slowly |
| **Phase files** | the numbered procedure, one file per phase of the work | when you reach that phase | slowly |
| **Diagnosis reference** (`DIAGNOSIS.md`) | symptom → discriminating test → cause → lever | when something looks wrong | grows |
| **Lab notebook** | evidence, measurement ledger, **retracted claims and open questions** | before re-investigating anything | only grows |
| **Runbook** | where it runs, what healthy looks like *with conditions*, current pick-up point | on resume | **every session** |

Rules that decide where something goes:

- A new **procedure** → spine or a phase file.
- A new **finding or refutation** → notebook.
- A number quoted in the procedure has its **provenance in the notebook ledger**.
- Anything that is true *today* and may not be next month → runbook.

Write one notebook **per campaign, not per dataset, and start it on day one.** The
retractions decay fastest and backfilling them does not work.

## 3. The spine

The spine is the handover document: the thing you paste to start a session that has never
seen this technique. It must be small enough that pasting it is not a decision.

It carries, in this order:

1. **What to hand it.** The two or three lines of input the reader must supply.
2. **A scope gate.** What configuration this doc set describes, and an instruction to stop
   rather than adapt outside it. Most silent failures come from a recipe applied one step
   outside where it was measured.
3. **An install gate.** Whatever check proves the code is the code the document describes.
4. **Halt conditions.** See §4.
5. **Hard rules** and the trap table — the invariants that make a result silently wrong.
6. **The order**, with a column saying why each step is where it is.
7. **An index** of the rest of the set.

## 4. Halt conditions, and why "ask if you get stuck" fails

The instruction people give is *"get back to me if you get stuck."* It does not fire,
because the failures that matter do not feel like being stuck. A mirrored reconstruction
produces a clean result. A wrong assignment converges. A solver that returns its input
reports success. The run finishes and looks right.

So the spine carries a table of **named conditions**, each with why the reader cannot
decide it alone, and the instruction is to halt on those **whether or not anything seems
wrong**. Every halt is a condition someone can check without judgement.

Finish everything not blocked by the halt before reporting it.

## 5. The diagnosis reference

Format and semantics are SPEC §6; `beamreport.reference` parses it and `doclint` checks
it. Two properties are non-negotiable:

- **Every entry declares a `symptom:` that the sidecar can actually emit.** An entry keyed
  to a symptom nothing produces is dead text that will never fire, and it reads as
  coverage.
- **Every entry's test can come back the other way.** An entry that cannot exonerate the
  cause it names turns the report into a machine for confirming what its author already
  believed.

It grows one entry at a time, the day someone works out what a strange plot meant.

## 6. The runbook, and why there is no single healthy number

The runbook is the only volatile document, and the one most likely to be missing —
handbook and notebook are natural to write, "what is true right now" is not.

**Publish ranges with their conditions, never a single threshold.** One number produces
false alarms on the heavy measurements and silence on the broken ones. A row that cannot
state the conditions it was measured under is not ready to be a row.

It ends with a **current pick-up point** that every session updates before it finishes. A
stale pick-up point is worse than none: the next session re-derives what was already
known and trusts the rest of the file less.

## 7. Checking it

```bash
beamreport-doc-lint path/to/doc-set/          # check
beamreport-doc-lint --init path/to/doc-set/   # scaffold from templates/technique-docs/
```

The linter checks the contract, not the content. It cannot tell you a claim is true, only
that the set has the parts, that the diagnosis entries are well-formed and keyed to real
symptoms, and that the spine carries a scope gate, an install gate and halt conditions.

**Citations are checked in your repository, not here** — they point at your code. Whatever
enforces that belongs in the tree that contains the code, and should run in your
pre-commit hook.

## 8. Known instances

See [REGISTRY.md](REGISTRY.md). Reading a live, maintained one beats reading a template.
