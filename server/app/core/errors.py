"""The single error-body shape (docs/adr/0011-backend-api-boundary.md point 7): ``{"error": {"code", "violations"?}}``.

Error bodies never echo request content and never carry exception text or stack traces.
``engine_unavailable`` (503) is the one code this layer adds: it is returned when the deterministic engine cannot be
loaded, so the server never answers an engine route with anything but the real engine's output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ServerError(Exception):
    status_code: int
    code: str
    violations: tuple[str, ...] = ()

    def body(self) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code}
        if self.violations:
            error["violations"] = list(self.violations)
        return {"error": error}


ENGINE_UNAVAILABLE = ServerError(503, "engine_unavailable")
