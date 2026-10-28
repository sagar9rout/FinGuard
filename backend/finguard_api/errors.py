"""API error type and the single error-body shape.

Error bodies never echo request content (financial data is sensitive) and
never contain exception text or stack traces.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiError(Exception):
    status_code: int
    code: str
    violations: tuple[str, ...] = ()

    def body(self) -> dict[str, object]:
        error: dict[str, object] = {"code": self.code}
        if self.violations:
            error["violations"] = list(self.violations)
        return {"error": error}
