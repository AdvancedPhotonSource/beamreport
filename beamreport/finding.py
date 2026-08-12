"""Findings: what a diagnostic concluded, and the vocabulary it concludes in.

A Finding is produced by arithmetic (see diagnose.py) and carries its own numbers. It
does NOT carry an interpretation. The cause and the lever are filled in later from the
caller's diagnosis reference (see reference.py), matched on `symptom`.

That split is the whole design: detection generalises across techniques, interpretation
does not.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# The symptom vocabulary. A diagnosis-reference entry declares which of these it
# explains; anything a reference cannot explain still appears on the page, labelled as
# an unexplained symptom, which is more useful than silence.
SYMPTOMS: dict[str, str] = {
    "trend.periodic": "a residual varies periodically with an angular coordinate",
    "trend.linear": "a residual trends linearly with a coordinate",
    "trend.amplitude_constant": "a trend's amplitude is constant across bins of another coordinate",
    "trend.amplitude_growing": "a trend's amplitude grows with another coordinate",
    "trend.amplitude_shrinking": "a trend's amplitude falls with another coordinate",
    "systematic.common_offset": "per-object offsets share a mean that dominates their scatter",
    "systematic.per_object": "per-object offsets are nonzero on average but scatter dominates",
    "split.bimodal": "a per-object aggregate splits into two populations",
    "param.residual_correlated": "a fitted parameter correlates with its own residual",
    "bound.pileup": "objects pile up against a declared parameter bound",
    "quality.low_fraction": "a substantial fraction of objects fall below the quality threshold",
    "null.not_cleared": "a quoted quantity does not clear its null",
    # --- added after the DFXM doc set exposed the gap -------------------------
    # A residual-based diagnostic is structurally BLIND to a multiplicative error
    # when the model carries a free amplitude: the scale is absorbed and the
    # residual stays flat. Catching it needs an expectation from outside the fit.
    # DFXM's pedestal dilution is the model case -- a perfectly smooth orientation
    # map, 67x too small, with nothing wrong in the residual.
    "scale.suppressed": "a recovered magnitude is far below an independent expectation",
    "scale.inflated": "a recovered magnitude is far above an independent expectation",
    "uncertainty.miscalibrated": "the declared uncertainties do not match the observed scatter",
    "floor.limited": "recovered values pile up at the pipeline's own resolution floor",
}

# Levels, in the order a report presents them.
#   solid       - something the data supports; state it plainly
#   systematic  - a structured deviation with a plausible lever; the actionable class
#   caution     - present, but the evidence does not support a confident reading
LEVELS = ("solid", "systematic", "caution")


@dataclass
class Finding:
    """One conclusion, its numbers, and (once matched) what to do about it."""

    symptom: str
    level: str
    title: str
    statement: str
    numbers: dict = field(default_factory=dict)
    channel: str | None = None
    coord: str | None = None

    # Filled from the diagnosis reference. Absent means the reference has no entry for
    # this symptom yet, which the report says out loud rather than hiding.
    cause: str | None = None
    test: str | None = None
    lever: str | None = None

    # Set when the technique's envelope declares this symptom fixed or intrinsic. The
    # observation still stands; the lever stops being advice.
    governed: dict | None = None

    @property
    def explained(self) -> bool:
        return self.lever is not None

    @property
    def key(self) -> tuple:
        """Identity used to match a reference entry: symptom, plus optional scoping."""
        return (self.symptom, self.channel, self.coord)

    def __str__(self) -> str:
        tail = "" if self.explained else "  [no reference entry]"
        return f"<{self.level}/{self.symptom}> {self.title}{tail}"


def fmt(x: float, sig: int = 3) -> str:
    """Format a number for a statement without lying about precision."""
    if x is None or not _finite(x):
        return "n/a"
    ax = abs(x)
    if ax == 0:
        return "0"
    if ax >= 1e5 or ax < 1e-3:
        return f"{x:.{sig - 1}e}"
    from math import floor, log10

    dec = max(0, sig - 1 - int(floor(log10(ax))))
    return f"{x:.{dec}f}"


def _finite(x) -> bool:
    try:
        return x == x and abs(x) != float("inf")
    except Exception:
        return False
