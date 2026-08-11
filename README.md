# beamreport

**Turn a finished measurement into a self-contained, diagnostic, publishable account.**

You hand it a result table, a quality scalar, provenance, and — the part that matters —
per-observation residuals with the coordinates they were measured at. It gives you back one
page that says what the data supports, which systematics are present, how each was
discriminated from its plausible alternative, and what to change.

It draws no technique-specific figure and invents no interpretation. Your figures and your
diagnosis reference stay in your repository.

> **Status: pre-release.** The contract is written and enforced; the report builder is not
> written yet. See [Roadmap](#roadmap). The contract is stable enough to write an adapter
> against today, which is the point of releasing it first.

---

## Why this exists

The same reporting pattern was built twice at APS, independently, in two repositories, for two
different techniques. Both converged on the same layers and the same document split. This
package is the part of that convergence that is not technique-specific.

The design rests on one observation: **most pipelines compute a per-observation misfit during
the fit and then discard it**, keeping only fitted parameters and a chi-squared. That single
habit is what makes automated reporting impossible downstream, and reversing it is usually a
dozen lines.

## Two products

| You supply | You get |
|---|---|
| results + quality + provenance | a **descriptive** report: what was measured, what came out, how it distributes |
| ...plus per-observation residuals and a diagnosis reference | a **diagnostic** report: which systematics are present, and what to change |

The second is the one people want. It needs the sidecar.

## What generalises, and what does not

**Detection generalises.** "Fit the residual against each coordinate axis, then compare the
mean of the per-object offsets against their scatter" separates a global systematic from
genuine per-object spread. It does not care whether the axis is an azimuth, a delay time, or a
detector region.

**Interpretation does not.** Which lever to pull is your knowledge. `beamreport` gives you the
format to write it in and applies it; it cannot supply it.

## Quick look

```python
from beamreport import Results, Quality, Provenance, Sidecar, validate

sidecar = Sidecar(
    table   = obs,                       # (N, K), one row per OBSERVATION
    columns = ["object_id", "q",    "delay", "d_amplitude"],
    units   = ["",          "1/nm", "s",     "counts"],
    roles   = ["id",        "coord", "coord", "residual"],
)

warnings = validate(results, provenance, quality=quality, sidecar=sidecar)
```

`validate` refuses input that cannot produce an honest report and reports every violation at
once rather than one at a time. Run it against your adapter before you have a builder — it is
the cheapest way to find out whether your pipeline retains what a diagnostic report needs.

## Refusals

The conventions are enforced, not merely documented. `beamreport` refuses a column with no
declared unit, a submission with no provenance, an unknown role, a sidecar with no residual or
no coordinate, and observation ids that do not match the result table. It warns on residuals
that appear squared, a single coordinate axis, and quantities with no registered null.

Full list and rationale in [SPEC.md](SPEC.md) §8. A silent degradation in a report generator is
worse than a crash, because the page still looks authoritative.

## Documentation

| Document | Read it when |
|---|---|
| [SPEC.md](SPEC.md) | You want to know what the contract is and why each rule exists. Start here. |
| [ADAPTER.md](ADAPTER.md) | You have a pipeline and want reports out of it. ~50-100 lines, one afternoon. |
| [DOCS_SPEC.md](DOCS_SPEC.md) | You are writing the documents around a technique, not just the report. SPEC §7's three-document table, expanded into a contract with a linter. |
| [REGISTRY.md](REGISTRY.md) | You want to read a live doc set before writing your own. |
| [DATA_REQUEST.md](DATA_REQUEST.md) | You are asking another group for data to try this on. |

The doc set and the report are the same idea at two scales: a diagnosis reference is what
turns a descriptive page into a diagnostic one, and it is also the file a person reaches
for when a plot looks wrong. `beamreport-doc-lint` checks that it exists, parses, and is
keyed to symptoms the sidecar can actually emit.

## Roadmap

Gates, not dates. Each gate can kill or reshape the design, which is the point of having them.

| Phase | Content | Gate |
|---|---|---|
| 0 ✅ | Contract, spec, adapter guide | — |
| 1 | Assembly kernel + technique-independent diagnostics | **G1** — port an existing bespoke report generator onto it. It must get materially shorter. If it does not, the abstraction is wrong; stop. |
| 2 | First external adapter, on a good and a problematic dataset | **G2** — does the problematic dataset's report surface the defect its owners already know about, using generic diagnostics alone? |
| 3 | Co-author that group's diagnosis reference | **G3** — one of their scientists reads a generated report and agrees with its findings without editing them. |
| 4 | v0.1 to PyPI | two internal callers and one external, ported cleanly |

Explicitly deferred until a second caller asks: multi-lane export (LaTeX, pptx, print), the
null harness as an enforced API, live during-acquisition reporting, any figure library or
plugin system.

## Installing

```bash
pip install -e ".[dev]"
pytest
```

## License

See [LICENSE](LICENSE). Produced at the Advanced Photon Source, Argonne National Laboratory.
