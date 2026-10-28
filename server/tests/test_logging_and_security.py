"""Safe logging (no request data) and the security behaviour implemented in this phase."""

from __future__ import annotations

import json
import logging

from starlette.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.engine_gateway import EngineGateway
from tests.conftest import JSON_HEADERS, make_client, minimal_request

SECRET_TEXT = "SECRET-MARKER-9917"
SECRET_AMOUNT = "987654.32"


def all_log_text(records: list[logging.LogRecord]) -> str:
    return "\n".join(r.getMessage() + " " + str(r.exc_info) + str(r.args) for r in records)


def sensitive_request() -> dict:
    payload = minimal_request()
    payload["events"][0]["description"] = SECRET_TEXT
    payload["events"][0]["amount"] = SECRET_AMOUNT
    return payload


def test_successful_requests_log_only_method_path_status_duration(client, log_records):
    client.post("/v1/analyze", content=json.dumps(sensitive_request()), headers=JSON_HEADERS)
    text = all_log_text(log_records)
    assert "method=POST" in text and "path=/v1/analyze" in text and "status=200" in text and "duration_ms=" in text
    assert SECRET_TEXT not in text and SECRET_AMOUNT not in text and "150000" not in text


def test_rejected_requests_do_not_log_request_values(client, log_records):
    bad = sensitive_request()
    bad["profile"]["surprise"] = SECRET_TEXT
    client.post("/v1/analyze", content=json.dumps(bad), headers=JSON_HEADERS)
    client.post("/v1/analyze", content=b"{" + SECRET_TEXT.encode(), headers=JSON_HEADERS)
    client.post("/v1/analyze", content=json.dumps(bad), headers={"content-type": "text/plain"})
    text = all_log_text(log_records)
    assert "status=422" in text and "status=400" in text and "status=415" in text
    assert SECRET_TEXT not in text


def test_query_strings_and_unknown_paths_never_reach_the_log(client, log_records):
    client.get(f"/v1/meta?token={SECRET_TEXT}")
    client.get(f"/{SECRET_TEXT}/anything")
    text = all_log_text(log_records)
    assert SECRET_TEXT not in text and "path=<unmatched>" in text and "path=/v1/meta" in text


def test_unhandled_errors_log_the_exception_type_only(log_records):
    class Boom(EngineGateway):
        def analyze(self, raw: bytes):  # type: ignore[no-untyped-def]
            raise RuntimeError(f"{SECRET_TEXT} {SECRET_AMOUNT}")

    c = make_client(gateway=Boom(Settings().backend_path))
    c.post("/v1/analyze", content=json.dumps(sensitive_request()), headers=JSON_HEADERS)
    text = all_log_text(log_records)
    assert "type=RuntimeError" in text
    assert SECRET_TEXT not in text and SECRET_AMOUNT not in text
    assert all(r.exc_info is None for r in log_records)


def test_every_response_carries_a_server_generated_request_id(client):
    a = client.get("/health").headers["x-request-id"]
    b = client.get("/health", headers={"x-request-id": "attacker-chosen"}).headers["x-request-id"]
    assert len(a) == 32 and len(b) == 32 and a != b and b != "attacker-chosen"


# ---- host guard -------------------------------------------------------------------------------------------------
def test_non_loopback_host_headers_are_rejected(client):
    for host in ["evil.example", "192.168.1.5:8000", "localhost.evil.example", "0.0.0.0:8000"]:
        r = client.get("/health", headers={"host": host})
        assert r.status_code == 400 and r.json() == {"error": {"code": "invalid_host"}}, host


def test_loopback_host_headers_are_accepted(client):
    for host in ["localhost", "localhost:8000", "127.0.0.1:8000", "[::1]:8000"]:
        assert client.get("/health", headers={"host": host}).status_code == 200, host


# ---- CORS -------------------------------------------------------------------------------------------------------
def cors_client(*origins: str) -> TestClient:
    return make_client(Settings(cors_origins=tuple(origins)))


def test_cors_is_off_by_default(client):
    r = client.get("/health", headers={"origin": "http://localhost:5173"})
    assert "access-control-allow-origin" not in r.headers
    pre = client.options(
        "/v1/analyze",
        headers={"origin": "http://localhost:5173", "access-control-request-method": "POST", "access-control-request-headers": "content-type"},
    )
    assert "access-control-allow-origin" not in pre.headers


def test_configured_origin_is_allowed_exactly_and_without_credentials():
    c = cors_client("http://localhost:5173")
    r = c.get("/health", headers={"origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-credentials" not in r.headers


def test_other_origins_get_no_cors_headers():
    c = cors_client("http://localhost:5173")
    for origin in ["http://localhost:5174", "http://127.0.0.1:5173", "https://evil.example", "null"]:
        r = c.get("/health", headers={"origin": origin})
        assert "access-control-allow-origin" not in r.headers, origin


def test_preflight_allows_only_post_get_and_content_type():
    c = cors_client("http://localhost:5173")
    ok = c.options(
        "/v1/analyze",
        headers={"origin": "http://localhost:5173", "access-control-request-method": "POST", "access-control-request-headers": "content-type"},
    )
    assert ok.status_code == 200 and ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert set(ok.headers["access-control-allow-methods"].replace(" ", "").split(",")) == {"GET", "POST"}
    bad_method = c.options("/v1/analyze", headers={"origin": "http://localhost:5173", "access-control-request-method": "DELETE"})
    assert bad_method.status_code == 400
    bad_header = c.options(
        "/v1/analyze",
        headers={"origin": "http://localhost:5173", "access-control-request-method": "POST", "access-control-request-headers": "authorization"},
    )
    assert bad_header.status_code == 400


def test_default_application_binds_nothing_public():
    s = Settings()
    assert s.host == "127.0.0.1" and create_app(s) is not None
