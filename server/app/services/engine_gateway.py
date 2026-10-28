"""The only place the server touches the engine, and only through the existing backend API handlers.

``backend/finguard_api/service.py`` validates the request, calls ``finguard_core`` and serialises its result faithfully
(ADR 0011). This gateway forwards raw request bytes to those handlers and returns their status and body unchanged.
If the backend packages cannot be imported, every engine route answers ``engine_unavailable`` (503): this layer never
fabricates, estimates or mocks a result.
"""

from __future__ import annotations

import importlib
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from app.core.errors import ENGINE_UNAVAILABLE, ServerError


@dataclass(frozen=True)
class GatewayResponse:
    status_code: int
    body: dict[str, Any]


Loader = Callable[[], tuple[ModuleType, type[Exception]]]


class EngineGateway:
    def __init__(self, backend_path: Path, loader: Loader | None = None) -> None:
        self._backend_path = backend_path
        self._loader = loader if loader is not None else self._default_loader
        self._lock = threading.Lock()
        self._loaded: tuple[ModuleType, type[Exception]] | None = None

    def _default_loader(self) -> tuple[ModuleType, type[Exception]]:
        path = str(self._backend_path)
        if self._backend_path.is_dir() and path not in sys.path:
            sys.path.insert(0, path)
        service = importlib.import_module("finguard_api.service")
        errors = importlib.import_module("finguard_api.errors")
        api_error: type[Exception] = errors.ApiError
        return service, api_error

    def _service(self) -> tuple[ModuleType, type[Exception]]:
        with self._lock:
            if self._loaded is None:
                try:
                    self._loaded = self._loader()
                except Exception:  # any import-time failure means the engine is not usable
                    raise ENGINE_UNAVAILABLE from None
            return self._loaded

    def is_available(self) -> bool:
        try:
            self._service()
        except ServerError:
            return False
        return True

    def _call(self, name: str, *args: bytes) -> GatewayResponse:
        service, api_error = self._service()
        try:
            result: Any = getattr(service, name)(*args)
        except Exception as exc:
            if isinstance(exc, api_error):
                violations = tuple(str(v) for v in getattr(exc, "violations", ()))
                raise ServerError(int(exc.status_code), str(exc.code), violations) from None  # type: ignore[attr-defined]
            raise
        return GatewayResponse(int(result.status_code), dict(result.body))

    def meta(self) -> GatewayResponse:
        return self._call("handle_meta")

    def request_schema(self) -> GatewayResponse:
        return self._call("handle_request_schema")

    def validate(self, raw: bytes) -> GatewayResponse:
        return self._call("handle_validate", raw)

    def forecast(self, raw: bytes) -> GatewayResponse:
        return self._call("handle_forecast", raw)

    def analyze(self, raw: bytes) -> GatewayResponse:
        return self._call("handle_analyze", raw)
