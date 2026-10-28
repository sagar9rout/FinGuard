"""Typed response schemas for the documented ``/v1`` contract (docs/api/v1.md, backend/finguard_api/service.py).

These models are strict (unknown fields forbidden) and exist so the exact wire shape is asserted in tests. The request
schema is the backend's own ``AnalysisRequest`` (served at ``GET /v1/schema/analysis-request``) and is not duplicated.
Money in ``result`` is canonical decimal text and is never converted to a number here; ``result`` is the engine's
canonical structure passed through untouched.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class HealthResponse(_Strict):
    status: Literal["ok"]


class ErrorBody(_Strict):
    code: str
    violations: list[str] | None = None


class ErrorResponse(_Strict):
    error: ErrorBody


class ReasonCodeInfo(_Strict):
    code: str
    severity: str


class Certification(_Strict):
    uncertified_status: None
    note_code: str


class Limits(_Strict):
    max_window_days: int
    max_flexible_targets: int


class MetaResponse(_Strict):
    api_version: str
    engine_version: str
    statuses: list[str]
    candidate_types: list[str]
    data_quality_levels: list[str]
    certification: Certification
    reason_codes: list[ReasonCodeInfo]
    limits: Limits


class ValidateResponse(_Strict):
    api_version: str
    valid: bool
    violations: list[str]


class Outcome(_Strict):
    certified: bool
    status: str | None


class AnalyzeResponse(_Strict):
    api_version: str
    engine_version: str
    input_hash: str
    result_hash: str
    outcome: Outcome
    result: dict[str, Any]


class ForecastResponse(_Strict):
    api_version: str
    engine_version: str
    input_hash: str
    result_hash: str
    result: dict[str, Any]
