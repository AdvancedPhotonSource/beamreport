"""Read the machine-usable parts of a technique's ENVELOPE.md.

The envelope (DOCS_SPEC §6) is prose, because most of it is prose: the consequence of
a fixed geometry, the substitute for something unobtainable. But its §4 "Derived limits"
table carries numbers a report should compute against rather than restate, and a floor
that lives only in prose is a floor no diagnostic can enforce.

The convention is light on purpose. A §4 row whose quantity cell contains a backticked
identifier is treated as a machine-readable limit on that column; every other row stays
free text and is ignored. Adding the backticks is the entire opt-in.

    | Fastest resolvable timescale (`tau`) | 0.01 s | frame time |

This is the seam where the envelope and the diagnosis reference finally meet: a value
sitting at a floor declared here fires `floor.limited`, which the reference then explains.
"""

from __future__ import annotations

import re
from pathlib import Path

_SEC4 = re.compile(r"^##+\s*\d*\.?\s*derived limits.*$", re.I | re.M)
_IDENT = re.compile(r"`([A-Za-z_][\w]*)`")
_IDENT_DOTTED = re.compile(r"`([A-Za-z_][\w.]*)`")
# The WHOLE limit cell must be a bare quantity: a number and an optional unit.
#
# An earlier version searched for any number anywhere in the cell and pulled "1.0" out
# of the prose "phase-dependent, often < 1 ... do not assume 1.0", inventing a floor of
# 1.0 for a quantity that has a cap and no floor at all. A limit stated in prose is the
# envelope declining to give a number, and the parser must read that as a decline.
_BARE = re.compile(r"^\**\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*[\w/^%·µ°]*\s*\**$")


def floors(path: str | Path) -> dict[str, tuple[float, str]]:
    """Parse §4 into {column: (limit, provenance)}.

    Returns only rows that named a column and carried a number. A row whose limit is
    "phase-dependent" or "not a fixed number" is deliberately unparseable: that is the
    envelope declining to give a floor, and an undeclared limit produces no
    counterfactual (DOCS_SPEC §6).
    """
    p = Path(path)
    if not p.is_file():
        return {}
    text = p.read_text(errors="replace")
    m = _SEC4.search(text)
    if not m:
        return {}
    block = text[m.end():]
    nxt = re.search(r"^##+\s", block, re.M)
    if nxt:
        block = block[: nxt.start()]

    out: dict[str, tuple[float, str]] = {}
    for line in block.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        ident = _IDENT.search(cells[0])
        if not ident:
            continue
        num = _BARE.match(cells[1])
        if not num:
            continue                       # the envelope declined to give a number
        prov = cells[2] if len(cells) > 2 else ""
        out[ident.group(1)] = (float(num.group(1)), prov)
    return out


_SEC_FIXED = re.compile(r"^##+\s*\d*\.?\s*fixed\b.*$", re.I | re.M)
_SEC_INTRINSIC = re.compile(r"^##+\s*\d*\.?\s*intrinsic\b.*$", re.I | re.M)


def _section(text: str, head: re.Pattern) -> str:
    m = head.search(text)
    if not m:
        return ""
    block = text[m.end():]
    nxt = re.search(r"^##+\s", block, re.M)
    return block[: nxt.start()] if nxt else block


def governed(path: str | Path, known: set[str] | None = None) -> dict[str, dict]:
    """Symptoms the envelope declares are fixed or intrinsic: {symptom: {...}}.

    A diagnosis entry can name a lever for something the instrument cannot change. On
    Au3 the report fired `trend.amplitude_growing`, matched an entry proposing an Lsd
    recalibration, and printed it as advice -- while the same doc set's envelope said
    that residual is a fixed property of an extended beam and must NOT be "fixed". Both
    documents were right; nothing connected them, so the page recommended the one thing
    the technique already knew was wrong.

    A row in the Fixed or Intrinsic tier opts in by naming the symptom in backticks,
    the same convention section 4 uses for floors. Adding the backticks is the whole
    mechanism.
    """
    p = Path(path)
    if not p.is_file():
        return {}
    text = p.read_text(errors="replace")
    out: dict[str, dict] = {}
    for tier, head in (("fixed", _SEC_FIXED), ("intrinsic", _SEC_INTRINSIC)):
        block = _section(text, head)
        for line in block.splitlines():
            if "|" not in line:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 2 or set("".join(cells)) <= set("-: "):
                continue
            for name in _IDENT_DOTTED.findall(line):
                if known is not None and name not in known:
                    continue
                out[name] = {
                    "tier": tier,
                    # The consequence column carries the "why", which is what a reader
                    # needs; fall back to the whole row when the shape is unexpected.
                    "text": cells[3] if len(cells) > 3 else " | ".join(cells),
                    "property": cells[0],
                    "substitute": cells[4] if len(cells) > 4 else "",
                }
    return out


def floor_columns(path: str | Path) -> dict[str, str]:
    """Parse §4 into {column: what sets its floor}, whether or not a number is given.

    Most floors turn out to be **per-run, not per-technique**: a grid step, a frame
    time, a threshold measured from the data. The envelope's job for those is to say
    *which quantities have a floor and what sets it*; the value comes from that run's
    parameters and the adapter supplies it.

    So this is the function an adapter uses to find out what it must look up, and
    `floors()` is the narrower one returning the few floors that are genuinely static.
    A column here with no entry in `floors()` is the envelope saying "this has a floor,
    go and measure it", which is different from saying there is none.
    """
    p = Path(path)
    if not p.is_file():
        return {}
    text = p.read_text(errors="replace")
    m = _SEC4.search(text)
    if not m:
        return {}
    block = text[m.end():]
    nxt = re.search(r"^##+\s", block, re.M)
    if nxt:
        block = block[: nxt.start()]

    out: dict[str, str] = {}
    for line in block.splitlines():
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        ident = _IDENT.search(cells[0])
        if ident:
            out[ident.group(1)] = (cells[2] if len(cells) > 2 else "").strip()
    return out
