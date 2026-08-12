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
| NF-HEDM (near-field) | `manuals/nf-hedm/` | MIDAS | complete — spine, 6 phases, parameter reference, diagnosis, runbook, notebook |
| Laue microdiffraction | `scripts/pipeline/laue/` | [LaueMatching](https://github.com/AdvancedPhotonSource/LaueMatching) | complete — spine, 7 phases, diagnosis, runbook, **two** campaign notebooks |

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

## What the three cost, and where the time went

All three passed `beamreport-doc-lint` on the same day. The splits were mechanical — every
source line assigned to exactly one output file, verified — and took a fraction of the
effort. What actually cost time was the two artifacts that did not exist anywhere:

- **The runbook.** Nobody writes "what is true right now" unprompted, and it cannot be
  derived from the handbook. It is a conversation with whoever runs the instrument.
- **The diagnosis reference.** It only gets written the day someone works out what a
  strange plot meant, and only if they write it down that day. FF had one already; NF and
  Laue did not, and theirs had to be reconstructed from campaign notebooks.

The linter also refused two of the three spines for things their authors had not noticed
were missing: NF's scope paragraph said to re-derive a convention "rather than inheriting
it" and never said to **stop**; the Laue spine had no scope gate, no install gate and no
halt list at all, despite being the best-structured document of the three. Both were real
gaps, not regex pedantry.
