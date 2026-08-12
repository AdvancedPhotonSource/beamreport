"""build() — the one call an adapter makes.

Validate the contract, run the technique-independent diagnostics, attach the caller's
diagnosis reference, assemble one self-contained page. Every step refuses rather than
degrades: a silent degradation in a report generator is worse than a crash, because the
page still looks authoritative.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from . import envelope as _envelope
from . import reference as _ref
from .contract import Provenance, Quality, Results, Sidecar, validate
from .diagnose import diagnose
from .finding import Finding, fmt
from .render import Page, Plate, Tile, write


def build(
    *,
    results: Results,
    provenance: Provenance,
    title: str,
    out: str | Path,
    quality: Quality | None = None,
    sidecar: Sidecar | None = None,
    figures: list[Plate] | None = None,
    diagnosis_reference: str | Path | None = None,
    bounds: dict | None = None,
    nulls: dict | None = None,
    expectations: dict | None = None,
    floors: dict | str | Path | None = None,
    subtitle: str = "",
    tiles: list[Tile] | None = None,
    methods: str = "",
    extra_findings: list[Finding] | None = None,
    strict: bool = False,
) -> Path:
    """Produce one report. Returns the path written.

    `sidecar=None` produces a descriptive report and says so on the page. With a
    sidecar and no `diagnosis_reference`, symptoms are detected and reported as
    unexplained, which is the honest state of a pipeline whose reference is not written
    yet.
    """
    warnings = validate(results, provenance, quality=quality, sidecar=sidecar, strict=strict)

    # A path means an ENVELOPE.md: the floors come from the technique's declared
    # limits, never from the data being judged, which would be circular.
    if isinstance(floors, (str, Path)):
        floors = _envelope.floors(floors)
    findings = diagnose(results, sidecar=sidecar, quality=quality, bounds=bounds,
                        nulls=nulls, expectations=expectations, floors=floors)
    findings += list(extra_findings or [])

    entries: list = []
    if diagnosis_reference is not None:
        entries = _ref.load(diagnosis_reference)
        _ref.apply(findings, entries)
    cov = _ref.coverage(findings, entries)

    if sidecar is None:
        findings.insert(0, Finding(
            symptom="", level="caution", title="Descriptive report only",
            statement=(
                "No diagnostics sidecar was supplied, so no residual-based diagnostic could "
                "run. This page describes what was measured and how it distributes; it makes "
                "no claim about which systematics are present."
            ),
        ))

    page = Page(
        title=title,
        subtitle=subtitle,
        tiles=tiles if tiles is not None else default_tiles(results, quality, sidecar),
        plates=list(figures or []),
        findings=findings,
        provenance=_prov_dict(provenance),
        coverage=cov,
        warnings=[str(w) for w in warnings],
        methods=methods,
    )
    return write(page, out)


def build_overview(
    *,
    title: str,
    provenance: Provenance,
    children: list[tuple],
    out: str | Path,
    subtitle: str = "",
    findings: list[Finding] | None = None,
    tiles: list[Tile] | None = None,
    figures: list[Plate] | None = None,
    methods: str = "",
) -> Path:
    """The campaign overview: the stable URL, linking out to one page per measurement.

    Children are `(title, url, blurb)`. URLs must already be resolved — publish the
    children first, collect their URLs, then build this. A page that grows with a
    campaign instead of linking out becomes a chronology of the analysis, and the
    experimenter cannot find their own measurement in it.
    """
    page = Page(
        title=title,
        subtitle=subtitle,
        tiles=list(tiles or []),
        plates=list(figures or []),
        findings=list(findings or []),
        provenance=_prov_dict(provenance),
        children=list(children),
        methods=methods,
    )
    return write(page, out)


def default_tiles(results, quality, sidecar) -> list[Tile]:
    """A summary row derived from the contract alone, so every page has one."""
    t = [Tile(f"{len(results.object_id):,}", "objects")]
    if quality is not None:
        q = np.asarray(quality.values, dtype=float)
        q = q[np.isfinite(q)]
        if q.size:
            t.append(Tile(fmt(float(np.median(q))), f"median {quality.name}"))
        if quality.threshold is not None and q.size:
            t.append(Tile(f"{100 * np.mean(q >= quality.threshold):.0f}%", "above threshold"))
    if sidecar is not None:
        t.append(Tile(f"{sidecar.table.shape[0]:,}", "observations"))
        t.append(Tile(str(len(sidecar.names("coord"))), "coordinate axes"))
        t.append(Tile(str(len(sidecar.names("residual"))), "residual channels"))
    return t


def _prov_dict(p: Provenance) -> dict:
    d = {
        "inputs": ", ".join(str(Path(x).name) for x in p.inputs),
        "command": p.command,
    }
    if p.parameters:
        d["parameters"] = str(Path(p.parameters).name)
    if p.code_version:
        d["version"] = p.code_version
    return d
