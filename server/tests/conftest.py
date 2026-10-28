from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.engine_gateway import EngineGateway

HERE = Path(__file__).resolve().parent
JSON_HEADERS = {"content-type": "application/json"}
CLIENT_FIXTURES = HERE.parents[1] / "client" / "src" / "fixtures" / "engineSamples.ts"


def minimal_request() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((HERE / "fixtures" / "minimal_request.json").read_text(encoding="utf-8"))
    return data


def make_client(settings: Settings | None = None, gateway: EngineGateway | None = None) -> TestClient:
    cfg = settings if settings is not None else Settings()
    return TestClient(create_app(cfg, gateway), base_url="http://localhost:8000", raise_server_exceptions=False)


@pytest.fixture
def client() -> TestClient:
    return make_client()


@pytest.fixture
def log_records() -> Iterator[list[logging.LogRecord]]:
    """Every record emitted by the server logger, captured without relying on propagation."""
    records: list[logging.LogRecord] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = Capture(level=logging.DEBUG)
    logger = logging.getLogger("finguard_server")
    logger.addHandler(handler)
    try:
        yield records
    finally:
        logger.removeHandler(handler)


def client_fixture(name: str) -> Any:
    """A committed synthetic sample from the frontend's fixtures file (JSON-shaped TypeScript), or skip if absent."""
    if not CLIENT_FIXTURES.is_file():
        pytest.skip("client/src/fixtures/engineSamples.ts not present")
    text = CLIENT_FIXTURES.read_text(encoding="utf-8")
    match = re.search(rf"export const {name}\b[^=]*= (\{{.*?\n\}});", text, re.S)
    assert match is not None, f"fixture {name} not found"
    return json.loads(match.group(1))
