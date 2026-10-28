"""When the engine cannot be loaded the server must say so, and must never invent a result."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import Settings
from app.schemas.responses import ErrorResponse
from app.services.engine_gateway import EngineGateway
from tests.conftest import JSON_HEADERS, make_client, minimal_request


def _missing_loader():
    raise ImportError("finguard_api is not installed")


def unavailable_client():
    return make_client(gateway=EngineGateway(Path("/nonexistent"), loader=_missing_loader))


def test_engine_routes_answer_503_engine_unavailable():
    c = unavailable_client()
    for method, path in [("GET", "/v1/meta"), ("GET", "/v1/schema/analysis-request")]:
        r = c.request(method, path)
        assert r.status_code == 503 and ErrorResponse.model_validate(r.json()).error.code == "engine_unavailable"
    for path in ["/v1/validate", "/v1/forecast", "/v1/analyze"]:
        r = c.post(path, content=json.dumps(minimal_request()), headers=JSON_HEADERS)
        assert r.status_code == 503 and r.json() == {"error": {"code": "engine_unavailable"}}


def test_no_decision_or_result_fields_appear_when_the_engine_is_unavailable():
    r = unavailable_client().post("/v1/analyze", content=json.dumps(minimal_request()), headers=JSON_HEADERS)
    assert not ({"outcome", "result", "status", "result_hash"} & set(r.json()))


def test_health_stays_a_pure_liveness_check_without_the_engine():
    assert unavailable_client().get("/health").json() == {"status": "ok"}


def test_a_missing_backend_directory_is_unavailable_not_a_crash(tmp_path):
    import sys  # noqa: PLC0415

    # A directory that exists but holds no packages, and finguard_api forced to be unimportable.
    saved = {k: sys.modules.pop(k) for k in list(sys.modules) if k.startswith("finguard_")}
    sys.modules["finguard_api"] = None  # type: ignore[assignment]
    try:
        gateway = EngineGateway(tmp_path)
        assert gateway.is_available() is False
        c = make_client(gateway=gateway)
        assert c.post("/v1/analyze", content=b"{}", headers=JSON_HEADERS).status_code == 503
    finally:
        sys.modules.pop("finguard_api", None)
        sys.modules.update(saved)


def test_unexpected_engine_exceptions_become_a_generic_500():
    class Boom(EngineGateway):
        def analyze(self, raw: bytes):  # type: ignore[no-untyped-def]
            raise RuntimeError("secret internal detail 123456.78")

    c = make_client(gateway=Boom(Settings().backend_path))
    r = c.post("/v1/analyze", content=json.dumps(minimal_request()), headers=JSON_HEADERS)
    assert r.status_code == 500 and r.json() == {"error": {"code": "internal_error"}}
    assert "secret" not in r.text and "123456.78" not in r.text
