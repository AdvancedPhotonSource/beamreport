# Known technique doc sets

Instances of the contract in [DOCS_SPEC.md](DOCS_SPEC.md). **Read a live one before the
template** — a real set shows what each section is *for*, which a skeleton cannot.

This is a registry of pointers, not a home for content. Each set lives beside the code it
cites, so its citations can be checked and its release cadence is its own. Adding a
technique means adding a row here and writing the set in your own repository — not a pull
request into this one.

| Technique | Doc set | Repository | Status |
|---|---|---|---|
| FF-HEDM (far-field 3DXRD) | `manuals/ff-hedm/` | [MIDAS](https://github.com/marinerhemant/MIDAS) | complete — spine, 5 phases, diagnosis, runbook, notebook |
| NF-HEDM (near-field) | `manuals/NF_HEDM_Handbook.md` | MIDAS | **not split** — handbook + notebook only; no diagnosis reference, no runbook |
| Laue microdiffraction | `scripts/pipeline/Laue_Handbook.md` | LaueMatching (private) | **not split** — handbook + 2 notebooks + a runbook; phase-structured already |

## What "complete" means

`beamreport-doc-lint <path>` exits 0. That checks the contract, not the content: the set
has its parts, the diagnosis entries are well-formed and keyed to symptoms something can
emit, and the spine carries a scope gate, an install gate, halt conditions and an order.

It says nothing about whether the claims are true. Nothing can.

## Adding one

```bash
beamreport-doc-lint --init docs/techniques/<name>/
```

Then fill it in beside your code, wire the lint into your pre-commit hook alongside
whatever checks your citations, and add a row above.

## A note on what the FF set cost

It came out of an existing 1378-line handbook, and the split itself was mechanical — every
source line assigned to exactly one output file, verified. The parts that took real work
were the two that did not exist before: the **runbook** (nobody writes "what is true right
now" unprompted) and the **diagnosis reference** (which only gets written the day someone
works out what a strange plot meant, and only if they write it down that day).

Budget accordingly. The split is an afternoon; the runbook is a conversation with whoever
runs the instrument.
