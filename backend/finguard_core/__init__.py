"""finguard_core — the pure deterministic FinGuard financial engine.

This package is the single source of truth for affordability decisions.
It is a pure function of its input: no filesystem, network, database,
wall-clock, or LLM access (see docs/adr/0001-core-purity-and-contracts.md).

Public entry points:
    analyze(AnalysisInput) -> AnalysisResult
    forecast(AnalysisInput) -> ForecastResult
    validate_input(AnalysisInput) -> tuple[ReasonEntry, ...]

Everything else in this package is an implementation detail and may
change without notice; only the names re-exported here, plus the
contract types in ``finguard_core.contracts``, are the stable interface.
"""

from finguard_core.contracts import AnalysisInput, AnalysisResult
from finguard_core.engine import analyze, forecast, validate_input

__all__ = [
    "AnalysisInput",
    "AnalysisResult",
    "analyze",
    "forecast",
    "validate_input",
]
