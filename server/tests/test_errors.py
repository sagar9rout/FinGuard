"""Rejection of malformed or inconsistent requests, and the exact error schema (ADR 0011 points 7 and 8)."""

from __future__ import annotations

import json

import pytest

from app.core.config import Settings
from app.schemas.responses import ErrorResponse
from tests.conftest import JSON_HEADERS, make_client, minimal_request

SECRET = "SECRET-MARKER-4242"
ENGINE_POSTS = ["/v1/validate", "/v1/forecast", "/v1/analyze"]


def assert_error(r, status, code):
    assert r.status_code == status
    body = ErrorResponse.model_validate(r.json())
    assert body.error.code == code
    return body


@pytest.mark.parametrize("path", ENGINE_POSTS)
def test_malformed_json_is_400(client, path):
    r = client.post(path, content=b"{not json", headers=JSON_HEADERS)
    assert r.json() == {"error": {"code": "invalid_json"}} and r.status_code == 400


@pytest.mark.parametrize("path", ENGINE_POSTS)
def test_wrong_or_missing_media_type_is_415(client, path):
    body = json.dumps(minimal_request())
    assert_error(client.post(path, content=body, headers={"content-type": "text/plain"}), 415, "unsupported_media_type")
    assert_error(client.post(path, content=body), 415, "unsupported_media_type")


def test_media_type_parameters_are_accepted(client):
    r = client.post("/v1/analyze", content=json.dumps(minimal_request()), headers={"content-type": "application/json; charset=utf-8"})
    assert r.status_code == 200


def test_unknown_fields_are_rejected_not_ignored(client):
    payload = minimal_request()
    payload["profile"]["surprise"] = SECRET
    payload["extra_top_level"] = 1
    r = client.post("/v1/analyze", content=json.dumps(payload), headers=JSON_HEADERS)
    err = assert_error(r, 422, "invalid_request")
    assert err.error.violations is not None
    assert "profile.surprise:extra_forbidden" in err.error.violations
    assert "extra_top_level:extra_forbidden" in err.error.violations
    assert SECRET not in r.text


@pytest.mark.parametrize("bad", [1000.5, True, None, [], {}, "not-a-number", "NaN", "Infinity"])
def test_money_must_be_a_finite_decimal_string_or_integer(client, bad):
    payload = minimal_request()
    payload["purchase"]["amount"] = bad
    r = client.post("/v1/analyze", content=json.dumps(payload), headers=JSON_HEADERS)
    assert_error(r, 422, "invalid_request")


def test_missing_required_fields_are_listed_by_location(client):
    payload = minimal_request()
    del payload["purchase"]
    err = assert_error(client.post("/v1/analyze", content=json.dumps(payload), headers=JSON_HEADERS), 422, "invalid_request")
    assert err.error.violations and any(v.startswith("purchase") for v in err.error.violations)


def test_inconsistent_but_well_formed_input_is_422_invalid_input(client):
    payload = minimal_request()
    payload["purchase"]["amount"] = "0"
    err = assert_error(client.post("/v1/analyze", content=json.dumps(payload), headers=JSON_HEADERS), 422, "invalid_input")
    assert err.error.violations


def test_limit_exceeded_is_422(client):
    payload = minimal_request()
    payload["config"] = {"horizon_days": 99999}
    err = assert_error(client.post("/v1/analyze", content=json.dumps(payload), headers=JSON_HEADERS), 422, "limit_exceeded")
    assert err.error.violations == ["limit_exceeded:config.horizon_days"]


def test_declared_oversize_body_is_413():
    c = make_client(Settings(max_body_bytes=1024))
    r = c.post("/v1/analyze", content=b"x" * 2048, headers=JSON_HEADERS)
    assert_error(r, 413, "payload_too_large")


def test_streamed_oversize_body_is_413_without_a_declared_length():
    c = make_client(Settings(max_body_bytes=1024))

    def chunks():
        for _ in range(4):
            yield b"x" * 512

    r = c.post("/v1/analyze", content=chunks(), headers=JSON_HEADERS)
    assert_error(r, 413, "payload_too_large")


def test_error_bodies_have_no_traces_or_internal_paths(client):
    r = client.post("/v1/analyze", content=b"{", headers=JSON_HEADERS)
    for needle in ("Traceback", "File \"", ".py", "backend", "/home/"):
        assert needle not in r.text
