"""The beamreport contract: the five objects a caller supplies, and their validation.

This module is deliberately dependency-light (numpy only) and knows nothing about any
measurement technique. It defines what a caller must hand over and refuses input that
cannot produce an honest report.

See SPEC.md sections 1-3 for the contract and section 8 for the refusal list. Every
refusal implemented here cites its SPEC code so a failure message can be traced back
to the rule that produced it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

VALID_ROLES = ("id", "coord", "residual", "weight", "aux")

# Roles whose columns carry a physical quantity and therefore must declare a unit.
# `id` and `aux` are exempt: an identifier has no unit, and `aux` is carried through
# without interpretation.
UNIT_REQUIRED_ROLES = ("coord", "residual", "weight")


class ContractError(ValueError):
    """Raised when supplied objects cannot produce an honest report.

    Carries every problem found, not just the first, so a caller fixes their adapter
    in one pass rather than one error at a time.
    """

    def __init__(self, problems: Sequence["Problem"]):
        self.problems = list(problems)
        body = "\n".join(f"  [{p.code}] {p.where}: {p.message}" for p in self.problems)
        super().__init__(f"{len(self.problems)} contract violation(s):\n{body}")


@dataclass(frozen=True)
class Problem:
    """One validation finding. `level` is 'error' (refusal) or 'warning' (rendered, flagged)."""

    level: str
    code: str
    where: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.where}: {self.message}"


def _as_array(x, name: str) -> np.ndarray:
    a = np.asarray(x)
    if a.ndim != 1:
        raise ContractError([Problem("error", "C001", name, f"expected 1-D, got shape {a.shape}")])
    return a


@dataclass
class Results:
    """One row per recovered object.

    `columns` maps a column name to `(values, unit)`. The unit is required: a column
    with no declared unit is refused rather than rendered with a guess (SPEC 8.1),
    which is what lets this package stay technique-neutral instead of quietly
    assuming one field's conventions.
    """

    object_id: np.ndarray
    columns: Mapping[str, tuple]

    def __post_init__(self):
        self.object_id = _as_array(self.object_id, "Results.object_id")

    def validate(self) -> list[Problem]:
        out: list[Problem] = []
        n = len(self.object_id)

        if n == 0:
            out.append(Problem("error", "R001", "Results.object_id", "no objects"))
        if len(np.unique(self.object_id)) != n:
            out.append(
                Problem("error", "R002", "Results.object_id", "object_id values are not unique")
            )

        if not self.columns:
            out.append(Problem("error", "R003", "Results.columns", "no result columns supplied"))

        for name, spec in self.columns.items():
            where = f"Results.columns[{name!r}]"
            if not (isinstance(spec, tuple) and len(spec) == 2):
                out.append(
                    Problem("error", "R004", where, "expected a (values, unit) tuple")
                )
                continue
            values, unit = spec
            values = np.asarray(values)
            if not isinstance(unit, str) or not unit.strip():
                out.append(
                    Problem(
                        "error",
                        "R005",
                        where,
                        "no declared unit; a column with no unit is refused (SPEC 8.1). "
                        "Use a dimensionless marker such as '1' if it genuinely has none.",
                    )
                )
            if values.shape[0] != n:
                out.append(
                    Problem(
                        "error",
                        "R006",
                        where,
                        f"has {values.shape[0]} rows, but object_id has {n}",
                    )
                )
        return out


@dataclass
class Quality:
    """One float per object saying how well the model explains it.

    Any monotone measure works. `threshold` is the value below which the caller would
    not quote an object; both populations are always shown and nothing is silently
    dropped.
    """

    values: np.ndarray
    name: str
    threshold: float | None = None
    higher_is_better: bool = True

    def __post_init__(self):
        self.values = _as_array(self.values, "Quality.values")

    def validate(self, n_objects: int | None = None) -> list[Problem]:
        out: list[Problem] = []
        if not self.name.strip():
            out.append(Problem("error", "Q001", "Quality.name", "must be named"))
        if n_objects is not None and len(self.values) != n_objects:
            out.append(
                Problem(
                    "error",
                    "Q002",
                    "Quality.values",
                    f"has {len(self.values)} entries, but there are {n_objects} objects",
                )
            )
        if np.all(~np.isfinite(self.values)):
            out.append(Problem("error", "Q003", "Quality.values", "no finite values"))
        if self.threshold is None:
            out.append(
                Problem(
                    "warning",
                    "Q004",
                    "Quality.threshold",
                    "no threshold declared; the report cannot separate quotable objects "
                    "from the rest",
                )
            )
        return out


@dataclass
class Provenance:
    """Enough to re-derive any number on the page.

    The rule this enforces: a number that cannot be re-derived does not go on the
    page. Not 'is flagged'. Does not go on.
    """

    inputs: Sequence[str | Path]
    command: str
    parameters: str | Path | None = None
    code_version: str | None = None

    def validate(self) -> list[Problem]:
        out: list[Problem] = []
        if not self.inputs:
            out.append(
                Problem("error", "P001", "Provenance.inputs", "no input paths (SPEC 8.2)")
            )
        if not self.command.strip():
            out.append(
                Problem(
                    "error",
                    "P002",
                    "Provenance.command",
                    "no command recorded; the page could not be reproduced from it",
                )
            )
        # Missing paths are a warning, not a refusal: a report is sometimes built on a
        # different machine from the one that produced the run.
        for p in list(self.inputs) + ([self.parameters] if self.parameters else []):
            if p is not None and not Path(p).exists():
                out.append(
                    Problem("warning", "P003", str(p), "path does not exist on this machine")
                )
        if not self.code_version:
            out.append(
                Problem("warning", "P004", "Provenance.code_version", "no code version recorded")
            )
        return out


@dataclass
class Sidecar:
    """Per-observation residuals, with the coordinates they were measured at.

    One row per OBSERVATION, not per object. This is the object most pipelines do not
    have, because they compute a per-observation misfit and keep only a chi-squared.
    The role declaration below is the entire adapter job, and it is what lets
    technique-independent diagnostics run on a technique they have never seen.
    """

    table: np.ndarray
    columns: Sequence[str]
    units: Sequence[str]
    roles: Sequence[str]
    rollups: Mapping[str, np.ndarray] = field(default_factory=dict)

    def __post_init__(self):
        self.table = np.asarray(self.table)

    def _idx(self, role: str) -> list[int]:
        return [i for i, r in enumerate(self.roles) if r == role]

    def column(self, name: str) -> np.ndarray:
        return self.table[:, list(self.columns).index(name)]

    def names(self, role: str) -> list[str]:
        return [self.columns[i] for i in self._idx(role)]

    def validate(self) -> list[Problem]:
        out: list[Problem] = []

        if self.table.ndim != 2:
            return [
                Problem("error", "S001", "Sidecar.table", f"expected 2-D, got {self.table.shape}")
            ]

        k = self.table.shape[1]
        for label, seq in (("columns", self.columns), ("units", self.units), ("roles", self.roles)):
            if len(seq) != k:
                out.append(
                    Problem(
                        "error",
                        "S002",
                        f"Sidecar.{label}",
                        f"has {len(seq)} entries, but the table has {k} columns",
                    )
                )
        if out:
            return out  # nothing below is meaningful with mismatched lengths

        bad = sorted({r for r in self.roles if r not in VALID_ROLES})
        if bad:
            out.append(
                Problem(
                    "error",
                    "S003",
                    "Sidecar.roles",
                    f"unknown role(s) {bad}; valid roles are {list(VALID_ROLES)}",
                )
            )

        n_id = len(self._idx("id"))
        if n_id != 1:
            out.append(
                Problem(
                    "error",
                    "S004",
                    "Sidecar.roles",
                    f"expected exactly one 'id' column, found {n_id}; without it "
                    "observations cannot be aggregated per object",
                )
            )

        resid = self._idx("residual")
        if not resid:
            out.append(
                Problem(
                    "error",
                    "S005",
                    "Sidecar.roles",
                    "no 'residual' column; a sidecar with no residuals cannot produce "
                    "any diagnostic. Supply objects 1-3 only for a descriptive report.",
                )
            )

        coord = self._idx("coord")
        if not coord:
            out.append(
                Problem(
                    "error",
                    "S006",
                    "Sidecar.roles",
                    "no 'coord' column; every diagnostic asks whether a residual "
                    "organises itself along some axis, which needs at least one axis",
                )
            )
        elif len(coord) == 1:
            out.append(
                Problem(
                    "warning",
                    "S007",
                    "Sidecar.roles",
                    "only one coordinate axis declared; systematics along any other axis "
                    "cannot be seen. Declaring an extra axis costs one panel.",
                )
            )

        for i, (name, unit, role) in enumerate(zip(self.columns, self.units, self.roles)):
            if role in UNIT_REQUIRED_ROLES and not (isinstance(unit, str) and unit.strip()):
                out.append(
                    Problem(
                        "error",
                        "S008",
                        f"Sidecar.columns[{name!r}]",
                        f"role {role!r} requires a declared unit (SPEC 8.1)",
                    )
                )

        # Residuals must be signed. An all-non-negative channel is almost always a
        # squared or absolute value, which has already destroyed the information that
        # separates a common offset from symmetric scatter.
        for i in resid:
            col = self.table[:, i]
            finite = col[np.isfinite(col)]
            if finite.size and finite.min() >= 0 and np.median(finite) > 0:
                out.append(
                    Problem(
                        "warning",
                        "S009",
                        f"Sidecar.columns[{self.columns[i]!r}]",
                        "residual channel is entirely non-negative, which usually means it "
                        "was squared or absolute-valued. The sign is what distinguishes a "
                        "common offset from symmetric scatter; supply it signed.",
                    )
                )
        return out


def check_consistency(results: Results, sidecar: Sidecar) -> list[Problem]:
    """Cross-check that sidecar observations refer to objects that exist.

    An id mismatch produces per-object aggregates that are silently wrong rather than
    obviously wrong, which is the worst failure mode available, so it is an error.
    """
    idx = sidecar._idx("id")
    if not idx:
        return []
    obs_ids = np.unique(sidecar.table[:, idx[0]])
    known = np.unique(results.object_id)
    orphan = np.setdiff1d(obs_ids, known)
    out: list[Problem] = []
    if orphan.size:
        out.append(
            Problem(
                "error",
                "X001",
                "Sidecar id column",
                f"{orphan.size} observation id(s) not present in Results.object_id "
                f"(e.g. {orphan[:5].tolist()}); per-object aggregation would be wrong",
            )
        )
    unobserved = np.setdiff1d(known, obs_ids)
    if unobserved.size:
        out.append(
            Problem(
                "warning",
                "X002",
                "Results.object_id",
                f"{unobserved.size} object(s) have no observations in the sidecar",
            )
        )
    return out


def validate(
    results: Results,
    provenance: Provenance,
    quality: Quality | None = None,
    sidecar: Sidecar | None = None,
    *,
    strict: bool = False,
) -> list[Problem]:
    """Validate a full submission. Raises ContractError on any error-level problem.

    Returns the warning-level problems so a caller can print or attach them. With
    `strict=True` warnings are promoted to errors, which is the right setting for CI
    on an adapter that is meant to stay clean.
    """
    problems: list[Problem] = []
    problems += results.validate()
    problems += provenance.validate()
    if quality is not None:
        problems += quality.validate(len(results.object_id))
    if sidecar is not None:
        problems += sidecar.validate()
        if not any(p.level == "error" for p in problems):
            problems += check_consistency(results, sidecar)

    errors = [p for p in problems if p.level == "error" or (strict and p.level == "warning")]
    if errors:
        raise ContractError(errors)
    return [p for p in problems if p.level == "warning"]
