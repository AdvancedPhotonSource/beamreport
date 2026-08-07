"""beamreport — a contract and a report builder for measurement analyses.

You hand it a finished measurement in a declared shape; it produces a self-contained,
publishable account of that measurement, including diagnostics that separate what the
data supports from what is a fixable systematic.

It draws no technique-specific figure and invents no interpretation. Your figures and
your diagnosis reference stay in your repository. See SPEC.md.

Status: pre-release. The contract (this module) is stable enough to write an adapter
against; the builder is not written yet. See ROADMAP in README.md.
"""

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

__version__ = "0.0.1"

__all__ = [
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
