"""Framework-independent request handling: bytes in, (status, body) out.

Everything here is a pure function of its arguments. The HTTP layer
(``app.py``) only moves bytes; all behavior that matters is testable
without a server.

Invariants:
- the engine's result is serialized faithfully via the core's canonical
  structure; the API never recomputes, rounds, ranks or reinterprets it;
- ``certified=false`` is exposed as ``outcome.certified == false`` with a
  null ``status`` (also nulled inside ``result``): "could not certify" is
  never presented as "proven unaffordable";
- error bodies never echo request content.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from pydantic import ValidationError

from finguard_api import API_VERSION
from finguard_api.errors import ApiError
from finguard_api.schemas import AnalysisRequest
from finguard_core import analyze, forecast
from finguard_core.canonical import canonical_dict
from finguard_core.contracts import (
    ENGINE_VERSION,
    AffordabilityStatus,
    CandidateType,
    DataQualityLevel,
)
from finguard_core.engine import validate_input
from finguard_core.reason_codes import ReasonCode, severity_of
from finguard_core.validation import InputValidationError

# Resource guards (ADR 0011). These are transport/DoS limits of the API,
# NOT affordability rules, and are advertised by GET /v1/meta.
MAX_WINDOW_DAYS_CAP = 3660
MAX_FLEXIBLE_TARGETS = 40


@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    body: dict[str, Any]


def encode(body: dict[str, Any]) -> bytes:
    """Deterministic response bytes: sorted keys, no whitespace, ASCII."""

    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def parse_request(raw: bytes) -> AnalysisRequest:
    try:
        return AnalysisRequest.model_validate_json(raw)
    except ValidationError as exc:
        errors = exc.errors(include_input=False, include_url=False, include_context=False)
        if any(e["type"] == "json_invalid" for e in errors):
            raise ApiError(400, "invalid_json") from None
        violations = tuple(sorted({f"{'.'.join(str(p) for p in e['loc'])}:{e['type']}" for e in errors}))
        raise ApiError(422, "invalid_request", violations) from None


def _limit_violations(request: AnalysisRequest) -> tuple[str, ...]:
    out: list[str] = []
    if request.config is not None:
        for name in ("horizon_days", "max_window_days", "variable_spend_lookback_days"):
            value = getattr(request.config, name)
            if value is not None and value > MAX_WINDOW_DAYS_CAP:
                out.append(f"limit_exceeded:config.{name}")
    targets = {
        (e.recurrence_group_id if e.recurrence_group_id is not None else e.event_id)
        for e in request.events
        if e.is_stoppable or e.is_reducible
    }
    if len(targets) > MAX_FLEXIBLE_TARGETS:
        out.append("limit_exceeded:flexible_targets")
    return tuple(sorted(out))


def _prepare(raw: bytes) -> Any:
    request = parse_request(raw)
    limits = _limit_violations(request)
    if limits:
        raise ApiError(422, "limit_exceeded", limits)
    return request.to_core()


def _hash(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(text.encode("utf-8")).hexdigest()


def handle_analyze(raw: bytes) -> ApiResponse:
    core_input = _prepare(raw)
    try:
        result = analyze(core_input)
    except InputValidationError as exc:
        raise ApiError(422, "invalid_input", exc.violations) from None
    exposed = canonical_dict(result)
    if not result.certified:
        exposed["status"] = None
    return ApiResponse(
        200,
        {
            "api_version": API_VERSION,
            "engine_version": ENGINE_VERSION,
            "input_hash": result.input_hash,
            "result_hash": _hash(exposed),
            "outcome": {
                "certified": result.certified,
                "status": result.status.value if result.certified else None,
            },
            "result": exposed,
        },
    )


def handle_forecast(raw: bytes) -> ApiResponse:
    core_input = _prepare(raw)
    try:
        result = forecast(core_input)
    except InputValidationError as exc:
        raise ApiError(422, "invalid_input", exc.violations) from None
    exposed = canonical_dict(result)
    return ApiResponse(
        200,
        {
            "api_version": API_VERSION,
            "engine_version": ENGINE_VERSION,
            "input_hash": result.input_hash,
            "result_hash": _hash(exposed),
            "result": exposed,
        },
    )


def handle_validate(raw: bytes) -> ApiResponse:
    core_input = _prepare(raw)
    try:
        validate_input(core_input)
    except InputValidationError as exc:
        return ApiResponse(200, {"api_version": API_VERSION, "valid": False, "violations": list(exc.violations)})
    return ApiResponse(200, {"api_version": API_VERSION, "valid": True, "violations": []})


def handle_meta() -> ApiResponse:
    return ApiResponse(
        200,
        {
            "api_version": API_VERSION,
            "engine_version": ENGINE_VERSION,
            "statuses": sorted(s.value for s in AffordabilityStatus),
            "candidate_types": sorted(c.value for c in CandidateType),
            "data_quality_levels": sorted(q.value for q in DataQualityLevel),
            "certification": {
                "uncertified_status": None,
                "note_code": ReasonCode.UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION.value,
            },
            "reason_codes": [
                {"code": c.value, "severity": severity_of(c).value} for c in sorted(ReasonCode, key=lambda c: c.value)
            ],
            "limits": {
                "max_window_days": MAX_WINDOW_DAYS_CAP,
                "max_flexible_targets": MAX_FLEXIBLE_TARGETS,
            },
        },
    )


def handle_request_schema() -> ApiResponse:
    return ApiResponse(200, AnalysisRequest.model_json_schema())
