"""Loopback-only guard: the bind address and the Host header must both be loopback (DNS-rebinding defence)."""

from __future__ import annotations

import ipaddress
import json
from typing import Any

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

ALLOWED_HOST_NAMES = frozenset({"localhost", "127.0.0.1", "::1"})


def is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def _host_name(header: str) -> str:
    value = header.strip().lower()
    if value.startswith("["):
        end = value.find("]")
        return value[1:end] if end != -1 else value
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


class HostGuardMiddleware:
    """Rejects any request whose Host header is not loopback with the standard JSON error body."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        if _host_name(Headers(scope=scope).get("host", "")) in ALLOWED_HOST_NAMES:
            await self.app(scope, receive, send)
            return
        if scope["type"] == "http":
            body: dict[str, Any] = {"error": {"code": "invalid_host"}}
            payload = json.dumps(body, separators=(",", ":")).encode("ascii")
            await send(
                {
                    "type": "http.response.start",
                    "status": 400,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(payload)).encode("ascii")),
                        (b"cache-control", b"no-store"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": payload})
        else:
            await send({"type": "websocket.close", "code": 1008})
