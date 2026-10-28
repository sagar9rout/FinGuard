"""HTTP behavior of the ``/v1`` API (stateless; no auth/DB/AI in PR-2)."""

from __future__ import annotations

import json
import random

import pytest
from starlette.testclient import TestClient

from finguard_api import API_VERSION, service
from finguard_api.app import create_app
from finguard_core import analyze, forecast
from finguard_core.canonical import canonical_dict, canonical_json, result_hash
from finguard_core.contracts import ENGINE_VERSION
from tests.support.api import to_body, to_wire
from tests.support.builders import make_input_with_unconvertible_debit, make_minimal_input
from tests.support.scenarios import rich_scenario, shuffled

JSON = {"content-type": "application/json"}


@pytest.fixture
def client():
    return TestClient(create_app(), raise_server_exceptions=False)


def post(client, path, body, headers=JSON):
    return client.post(path, content=body, headers=headers)


# --- read-only endpoints ---------------------------------------------------


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_meta_publishes_engine_version_statuses_codes_and_limits(client):
    body = client.get("/v1/meta").json()
    assert body["api_version"] == API_VERSION and body["engine_version"] == ENGINE_VERSION
    assert body["statuses"] == ["affordable_later", "affordable_now", "affordable_with_plan", "not_affordable"]
    assert body["certification"]["uncertified_status"] is None
    codes = {c["code"] for c in body["reason_codes"]}
    assert {"PURCHASE_UNRELATED_TO_BREACH", "UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION"} <= codes
    assert body["limits"]["max_flexible_targets"] == service.MAX_FLEXIBLE_TARGETS


def test_request_schema_is_served(client):
    schema = client.get("/v1/schema/analysis-request").json()
    assert "properties" in schema and "as_of" in schema["properties"]


# --- analyze / forecast / validate ----------------------------------------


def test_analyze_returns_exactly_the_core_result(client):
    inp = rich_scenario()
    r = post(client, "/v1/analyze", to_body(inp))
    assert r.status_code == 200
    body = r.json()
    core = analyze(inp)
    assert body["result"] == canonical_dict(core)
    assert body["result_hash"] == result_hash(core)
    assert body["input_hash"] == core.input_hash
    assert body["engine_version"] == ENGINE_VERSION
    assert body["outcome"] == {"certified": True, "status": core.status.value}


def test_forecast_returns_exactly_the_core_forecast(client):
    inp = rich_scenario()
    body = post(client, "/v1/forecast", to_body(inp)).json()
    assert body["result"] == canonical_dict(forecast(inp))
    assert "outcome" not in body


def test_validate_reports_valid_and_invalid_inputs_without_erroring(client):
    ok = post(client, "/v1/validate", to_body(make_minimal_input())).json()
    assert ok == {"api_version": "v1", "valid": True, "violations": []}
    wire = to_wire(make_minimal_input())
    wire["events"] = [
        {**_event("dup"), "event_id": "dup"},
        {**_event("dup"), "event_id": "dup"},
    ]
    r = post(client, "/v1/validate", json.dumps(wire))
    assert r.status_code == 200
    assert r.json()["valid"] is False and "event_id_duplicate:dup" in r.json()["violations"]


def _event(event_id):
    return {
        "event_id": event_id,
        "event_date": "2026-01-05",
        "amount": "10",
        "currency": "INR",
        "direction": "debit",
        "status": "scheduled",
        "category": "other",
    }


def test_analyze_and_forecast_reject_structurally_invalid_input_with_422(client):
    wire = to_wire(make_minimal_input())
    wire["purchase"]["amount"] = "-5"
    for path in ("/v1/analyze", "/v1/forecast"):
        r = post(client, path, json.dumps(wire))
        assert r.status_code == 422
        assert r.json() == {"error": {"code": "invalid_input", "violations": ["purchase_amount_not_positive:purchase"]}}


# --- certified=false is preserved through the API -------------------------


def test_uncertifiable_is_not_reported_as_unaffordable(client):
    r = post(client, "/v1/analyze", to_body(make_input_with_unconvertible_debit()))
    body = r.json()
    assert r.status_code == 200
    assert body["outcome"] == {"certified": False, "status": None}
    assert body["result"]["certified"] is False
    assert body["result"]["status"] is None
    assert body["result"]["reasons"][0]["code"] == "UNCONVERTIBLE_DEBIT_BLOCKS_CERTIFICATION"
    assert body["result"]["chosen"] is None
    assert "not_affordable" not in r.text


def test_certified_results_are_untouched_and_hash_matches_core(client):
    core = analyze(make_minimal_input())
    body = post(client, "/v1/analyze", to_body(make_minimal_input())).json()
    assert body["result"]["status"] == core.status.value
    assert body["result_hash"] == result_hash(core)


# --- determinism -------------------------------------------------------------


def test_response_bytes_are_identical_across_repeats_and_input_orderings(client):
    base = rich_scenario()
    first = post(client, "/v1/analyze", to_body(base)).content
    assert first == post(client, "/v1/analyze", to_body(base)).content
    for seed in range(8):
        wire = to_wire(shuffled(base, random.Random(seed)))
        assert post(client, "/v1/analyze", json.dumps(wire)).content == first


def test_response_body_is_canonical_json(client):
    r = post(client, "/v1/analyze", to_body(make_minimal_input()))
    assert r.content == service.encode(json.loads(r.content))
    assert canonical_json(analyze(make_minimal_input())) == json.dumps(
        canonical_dict(analyze(make_minimal_input())), sort_keys=True, separators=(",", ":")
    )


def test_responses_are_not_cacheable(client):
    for r in (client.get("/health"), post(client, "/v1/analyze", to_body(make_minimal_input()))):
        assert r.headers["cache-control"] == "no-store"
        assert r.headers["x-content-type-options"] == "nosniff"
