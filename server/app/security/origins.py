"""CORS origin validation. Only exact, loopback http(s) origins are accepted in this phase.

The documented development origin of the Vite client is ``http://localhost:5173`` (client/vite.config.ts binds the dev
server to ``localhost``; 5173 is Vite's default port). Wildcards, ``null``, paths and non-loopback hosts are rejected.
"""

from __future__ import annotations

import re

from app.security.hosts import is_loopback_host

_ORIGIN = re.compile(r"^(?P<scheme>https?)://(?P<host>\[[0-9A-Fa-f:]+\]|[A-Za-z0-9.-]+)(?::(?P<port>\d{1,5}))?$")


def validate_origin(origin: str) -> str:
    # Local import keeps the module free of a config dependency cycle.
    from app.core.config import ConfigError

    match = _ORIGIN.match(origin)
    if match is None:
        raise ConfigError("FINGUARD_CORS_ORIGINS entries must look like http://localhost:5173 (no wildcard or path)")
    if not is_loopback_host(match["host"]):
        raise ConfigError("FINGUARD_CORS_ORIGINS may only list loopback origins in this phase")
    port = match["port"]
    if port is not None and not 1 <= int(port) <= 65535:
        raise ConfigError("FINGUARD_CORS_ORIGINS contains an invalid port")
    return origin
