# <TECHNIQUE> — <one line: what this takes in, what it produces>

**Use this doc to start a fresh session on a dataset this pipeline has never seen.**
Paste it in together with `LAB_NOTEBOOK.md`, then give:

```
Data folder:   <ABSOLUTE PATH>
<other input>: <...>
```

**Scope.** <The exact configuration every recipe here was measured on: instrument,
detector, file format, dimensionality.> If your data differs in <the axes that matter>,
**stop and ask** rather than adapting a recipe — the field maps and geometry below assume
this configuration throughout.

<!-- The scope gate is not boilerplate. Most silent failures are a recipe applied one
     step outside where it was measured. Name the axes, not just the instrument. -->

## The doc set — what to read when

| File | Holds | Read it |
|---|---|---|
| **`README.md`** (this) | scope gate, install gate, the order, hard rules, halt conditions | always |
| `phase-0-*.md` … | the numbered procedure | when you reach that phase |
| `DIAGNOSIS.md` | symptom → test → cause → lever | **when something looks wrong** |
| `RUNBOOK.md` | where it runs, what healthy looks like, pick-up point | on resume |
| `LAB_NOTEBOOK.md` | evidence, ledger, **retracted claims** | before re-investigating |

## STOP — read this before touching anything

### When to stop and come back with a question

**"Get back to me if you get stuck" does not fire here.** <Name two or three failures in
THIS technique that finish and look right.> The run completes and the output is plausible.

So the trigger is not confusion. **Halt on these named conditions, whether or not anything
seems wrong:**

| Condition | Why you cannot decide it yourself |
|---|---|
| <a checkable condition> | <why judgement will not settle it> |

When you halt, say which row fired, what you measured, and what you would need to proceed.
Finish everything not blocked by it first.

### Hard rules

<!-- The invariants that make a result silently WRONG, not merely worse. Each should name
     the symptom you would NOT see. Rules about your own run ("suspect success", "debug
     your config before the physics") belong here too -- they are the ones a
     context-free session skips. -->

1. **<Rule>.** <What breaks, and why it is invisible afterwards.>

### Traps that silently corrupt results

| Trap | Symptom if missed | Where |
|---|---|---|
| <trap> | <what you see, which looks fine> | <§> |

## 0. Verify the install

<!-- Whatever proves the code is the code this document describes. Prefer a command whose
     output can be pasted over a table of version numbers that goes stale. -->

## 0a. THE ORDER

| # | Step | Where | Why it is here and not later |
|---|---|---|---|
| 0 | Verify the install | §0 | invalidates everything downstream if skipped |
| 1 | <step> | <file> | <the input it produces for the next one> |
