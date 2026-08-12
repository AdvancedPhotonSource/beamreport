"""beamreport — a contract and a report builder for measurement analyses.

You hand it a finished measurement in a declared shape; it produces a self-contained,
publishable account of that measurement, including diagnostics that separate what the
data supports from what is a fixable systematic.

It draws no technique-specific figure and invents no interpretation. Your figures and
your diagnosis reference stay in your repository. See SPEC.md.

Status: pre-release. Contract, technique-independent diagnostics, diagnosis-reference
matching and page assembly are implemented. See the roadmap in README.md.
"""

from .build import build, build_overview
from .contract import (
    ContractError,
    Problem,
    Provenance,
    Quality,
    Results,
    Sidecar,
    check_consistency,
    validate,
)
from . import envelope
from .diagnose import diagnose
from .finding import SYMPTOMS, Finding
from .reference import ReferenceError
from .render import Page, Plate, RenderError, Tile, render

__version__ = "0.0.1"

__all__ = [
    "build",
    "build_overview",
    "diagnose",
    "envelope",
    "Finding",
    "SYMPTOMS",
    "Plate",
    "Tile",
    "Page",
    "render",
    "RenderError",
    "ReferenceError",
    "Results",
    "Quality",
    "Provenance",
    "Sidecar",
    "Problem",
    "ContractError",
    "validate",
    "check_consistency",
    "__version__",
]
