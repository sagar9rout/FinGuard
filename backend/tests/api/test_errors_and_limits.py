"""Error handling, transport limits and information-leak guarantees."""

from __future__ import annotations

import json

import pytest
from starlette.testclient import TestClient

from finguard_api import service
from finguard_api.app import create_app
from tests.support.api import to_body, to_wire
from tests.support.builders import make_minimal_input

JSON = {"content-type": "application/json"}
SECRET = "SECRET-MARKER-4242"


@pytest.fixture
def client():
    return TestClient(create_app(), raise_server_exceptions=False)


def post(client, body, path="/v1/analyze", headers=JSON):
    return client.post(path, content=body, headers=headers)


def test_malformed_json_is_400(client):
    r = post(client, b"{not json")
    assert r.status_code == 400 and r.json() == {"error": {"code": "invalid_json"}}


def test_wrong_media_type_is_415(client):
    r = post(client, to_body(make_minimal_input()), headers={"content-type": "text/plain"})
    assert r.status_code == 415 and r.json()["error"]["code"] == "unsupported_media_type"
    assert post(client, b"{}", headers={}).status_code == 415


def test_media_type_parameters_are_accepted(client):
    r = post(client, to_body(make_minimal_input()), headers={"content-type": "application/json; charset=utf-8"})
    assert r.status_code == 200


def test_schema_violations_are_422_with_locations_and_never_echo_values(client):
    wire = to_wire(make_minimal_input())
    wire["purchase"]["amount"] = SECRET
    wire["profile"]["surprise"] = SECRET
    r = post(client, json.dumps(wire))
    assert r.status_code == 422
    error = r.json()["error"]
    assert error["code"] == "invalid_request"
    assert "purchase.amount:value_error" in error["violations"]
    assert "profile.surprise:extra_forbidden" in error["violations"]
    assert SECRET not in r.text


def test_float_money_is_rejected_not_rounded(client):
    wire = to_wire(make_minimal_input())
    wire["purchase"]["amount"] = 1000.5
    r = post(client, json.dumps(wire))
    assert r.status_code == 422 and "purchase.amount:value_error" in r.json()["error"]["violations"]


def test_oversized_bodies_are_413(client):
    small = TestClient(create_app(max_body_bytes=200), raise_server_exceptions=False)
    r = small.post("/v1/analyze", content=to_body(make_minimal_input()), headers=JSON)
    assert r.status_code == 413 and r.json() == {"error": {"code": "payload_too_large"}}


def test_oversized_chunked_bodies_are_413_without_content_length():
    small = TestClient(create_app(max_body_bytes=200), raise_server_exceptions=False)

    def chunks():
        for _ in range(10):
            yield b"x" * 100

    r = small.post("/v1/analyze", content=chunks(), headers=JSON)
    assert r.status_code == 413


def test_resource_guard_on_window_config(client):
    wire = to_wire(make_minimal_input())
    wire["config"]["max_window_days"] = service.MAX_WINDOW_DAYS_CAP + 1
    r = post(client, json.dumps(wire))
    assert r.status_code == 422
    assert r.json()["error"] == {"code": "limit_exceeded", "violations": ["limit_exceeded:config.max_window_days"]}
    wire["config"]["max_window_days"] = service.MAX_WINDOW_DAYS_CAP
    assert post(client, json.dumps(wire)).status_code == 200


def test_resource_guard_on_flexible_targets(client):
    wire = to_wire(make_minimal_input())
    wire["events"] = [{**_event(f"e{i}"), "is_stoppable": True} for i in range(service.MAX_FLEXIBLE_TARGETS + 1)]
    r = post(client, json.dumps(wire))
    assert r.status_code == 422 and r.json()["error"]["violations"] == ["limit_exceeded:flexible_targets"]
    # one recurrence group is ONE target however many occurrences it has
    wire["events"] = [
        {**_event(f"e{i}"), "is_stoppable": True, "recurrence_group_id": "g"}
        for i in range(service.MAX_FLEXIBLE_TARGETS * 3)
    ]
    assert post(client, json.dumps(wire)).status_code == 200


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


def test_unknown_routes_and_methods_use_the_error_shape(client):
    assert client.get("/nope").json() == {"error": {"code": "not_found"}}
    r = client.get("/v1/analyze")
    assert r.status_code == 405 and r.json() == {"error": {"code": "method_not_allowed"}}
    assert client.post("/health", content=b"", headers=JSON).status_code == 405


def test_unexpected_failures_are_500_with_no_internal_detail(client, monkeypatch, caplog):
    def boom(_core_input):
        raise RuntimeError(f"internal {SECRET}")

    monkeypatch.setattr(service, "analyze", boom)
    with caplog.at_level("ERROR", logger="finguard_api"):
        r = post(client, to_body(make_minimal_input()))
    assert r.status_code == 500 and r.json() == {"error": {"code": "internal_error"}}
    assert SECRET not in r.text
    assert SECRET not in caplog.text  # exception message and request body are never logged
    assert "RuntimeError" in caplog.text
