"""Request logging as a pure ASGI middleware: one safe line per request, a server-generated request id."""

from __future__ import annotations

import time
import uuid

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import get_logger

_METHODS = frozenset({"GET", "POST", "OPTIONS", "HEAD", "PUT", "PATCH", "DELETE"})


class RequestLogMiddleware:
    """Logs method, matched route path, status and duration. Never the body, query string, headers or any value from
    the request: unknown paths are logged as ``<unmatched>`` so attacker-chosen text cannot enter the log."""

    def __init__(self, app: ASGIApp, known_paths: frozenset[str]) -> None:
        self.app = app
        self._known = known_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid.uuid4().hex
        started = time.perf_counter()
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = int(message["status"])
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            path = scope["path"] if scope["path"] in self._known else "<unmatched>"
            get_logger().info(
                "request id=%s method=%s path=%s status=%d duration_ms=%d",
                request_id,
                scope["method"] if scope["method"] in _METHODS else "<other>",
                path,
                status,
                int((time.perf_counter() - started) * 1000),
            )
