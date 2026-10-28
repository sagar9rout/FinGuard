"""Documented routes, exact response schemas, and fidelity to the engine (docs/api/v1.md)."""

from __future__ import annotations

import json

import pytest

from app.schemas.responses import (
    AnalyzeResponse,
    ErrorResponse,
    ForecastResponse,
    HealthResponse,
    MetaResponse,
    ValidateResponse,
)
from tests.conftest import JSON_HEADERS, client_fixture, minimal_request

DOCUMENTED_ROUTES = {
    ("GET", "/health"),
    ("GET", "/v1/meta"),
    ("GET", "/v1/schema/analysis-request"),
    ("POST", "/v1/validate"),
    ("POST", "/v1/forecast"),
    ("POST", "/v1/analyze"),
}


def post(client, path, payload):
    return client.post(path, content=json.dumps(payload), headers=JSON_HEADERS)


def test_health_is_exactly_the_documented_body(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    HealthResponse.model_validate(r.json())
    assert r.headers["cache-control"] == "no-store" and r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["content-type"] == "application/json"


def test_meta_matches_the_documented_schema_and_engine(client):
    r = client.get("/v1/meta")
    assert r.status_code == 200
    meta = MetaResponse.model_validate(r.json())
    assert meta.api_version == "v1"
    assert sorted(meta.statuses) == ["affordable_later", "affordable_now", "affordable_with_plan", "not_affordable"]
    assert meta.certification.uncertified_status is None
    assert meta.certification.note_code == "UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION"
    assert meta.limits.max_window_days == 3660 and meta.limits.max_flexible_targets == 40
    assert len(meta.reason_codes) > 20


def test_request_schema_is_served(client):
    r = client.get("/v1/schema/analysis-request")
    assert r.status_code == 200
    schema = r.json()
    assert schema["type"] == "object" and "as_of" in schema["properties"]
    assert schema["additionalProperties"] is False
    assert {"as_of", "profile", "purchase", "preferences"} <= set(schema["required"])


def test_validate_valid_and_invalid(client):
    ok = post(client, "/v1/validate", minimal_request())
    assert ok.status_code == 200 and ValidateResponse.model_validate(ok.json()).valid is True
    assert ok.json()["violations"] == []
    bad = minimal_request()
    bad["purchase"]["amount"] = "0"
    r = post(client, "/v1/validate", bad)
    body = ValidateResponse.model_validate(r.json())
    assert r.status_code == 200 and body.valid is False and body.violations


def test_analyze_returns_the_documented_envelope(client):
    r = post(client, "/v1/analyze", minimal_request())
    assert r.status_code == 200
    body = AnalyzeResponse.model_validate(r.json())
    assert body.outcome.certified is True and body.outcome.status in {
        "affordable_now",
        "affordable_with_plan",
        "affordable_later",
        "not_affordable",
    }
    assert body.result["status"] == body.outcome.status and body.result["certified"] is True
    assert len(body.input_hash) == 64 and len(body.result_hash) == 64


def test_forecast_returns_a_baseline_series_without_a_decision(client):
    r = post(client, "/v1/forecast", minimal_request())
    assert r.status_code == 200
    body = ForecastResponse.model_validate(r.json())
    series = body.result["baseline_series"]
    assert series and set(series[0]) == {"close", "day", "low"}
    assert "status" not in body.result and "outcome" not in r.json()


def test_money_is_canonical_decimal_text_never_a_number(client):
    body = post(client, "/v1/forecast", minimal_request()).json()
    for day in body["result"]["baseline_series"]:
        assert isinstance(day["low"], str) and isinstance(day["close"], str)
    assert isinstance(body["result"]["baseline_summary"]["max_shortfall"], str)


def test_responses_are_deterministic_bytes(client):
    a = client.post("/v1/analyze", content=json.dumps(minimal_request()), headers=JSON_HEADERS).content
    b = client.post("/v1/analyze", content=json.dumps(minimal_request()), headers=JSON_HEADERS).content
    assert a == b and a == json.dumps(json.loads(a), sort_keys=True, separators=(",", ":")).encode()


def test_only_documented_routes_exist(client):
    from app.core.config import Settings  # noqa: PLC0415
    from app.main import create_app  # noqa: PLC0415

    paths = {(m, r.path) for r in create_app(Settings()).routes for m in r.methods if m != "HEAD"}  # type: ignore[attr-defined]
    assert paths == DOCUMENTED_ROUTES


@pytest.mark.parametrize("path", ["/", "/v2/analyze", "/docs", "/openapi.json", "/v1/persist", "/v1/chat"])
def test_undocumented_paths_are_not_found_with_the_standard_error(client, path):
    r = client.get(path)
    assert r.status_code == 404 and ErrorResponse.model_validate(r.json()).error.code == "not_found"


def test_wrong_method_is_405_with_the_standard_error(client):
    r = client.get("/v1/analyze")
    assert r.status_code == 405 and r.json() == {"error": {"code": "method_not_allowed"}}
    assert client.post("/health", content=b"{}", headers=JSON_HEADERS).status_code == 405


@pytest.mark.parametrize(
    ("request_name", "response_name"),
    [
        ("affordableNowRequest", "affordableNowResponse"),
        ("affordableWithPlanRequest", "affordableWithPlanResponse"),
        ("affordableLaterRequest", "affordableLaterResponse"),
        ("notAffordableRequest", "notAffordableResponse"),
        ("uncertifiedRequest", "uncertifiedResponse"),
    ],
)
def test_server_reproduces_the_frontends_committed_samples_exactly(client, request_name, response_name):
    """The frontend's mock responses were captured from the engine; the real server must return identical bytes of
    meaning. Skipped (and reported as skipped) if the client fixtures file is absent."""
    r = post(client, "/v1/analyze", client_fixture(request_name))
    assert r.status_code == 200
    assert r.json() == client_fixture(response_name)


def test_server_reproduces_the_frontends_dashboard_forecast(client):
    r = post(client, "/v1/forecast", client_fixture("dashboardRequest"))
    assert r.status_code == 200 and r.json() == client_fixture("dashboardForecast")
