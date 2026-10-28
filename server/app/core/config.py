"""Explicit configuration from environment variables. Nothing here is a secret, and no default is permissive.

``FINGUARD_SERVER_HOST``     bind address; must be a loopback address (default 127.0.0.1)
``FINGUARD_SERVER_PORT``     port 1024-65535 (default 8000)
``FINGUARD_CORS_ORIGINS``    comma-separated exact origins allowed to call the API from a browser (default: none)
``FINGUARD_MAX_BODY_BYTES``  request body limit, 1 KiB to 1 MiB (default 1 MiB, the documented ADR 0011 limit)
``FINGUARD_LOG_LEVEL``       DEBUG, INFO, WARNING or ERROR (default INFO)
``FINGUARD_BACKEND_PATH``    directory containing ``finguard_api`` and ``finguard_core`` (default ../backend)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from app.security.hosts import is_loopback_host
from app.security.origins import validate_origin

DEFAULT_BACKEND_PATH = Path(__file__).resolve().parents[3] / "backend"
MAX_BODY_LIMIT = 1_048_576
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


class ConfigError(ValueError):
    """Invalid configuration. The message names the setting, never a value that could be sensitive."""


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: tuple[str, ...] = ()
    max_body_bytes: int = MAX_BODY_LIMIT
    log_level: str = "INFO"
    backend_path: Path = DEFAULT_BACKEND_PATH

    def __post_init__(self) -> None:
        if not is_loopback_host(self.host):
            raise ConfigError("FINGUARD_SERVER_HOST must be a loopback address (127.0.0.1, ::1 or localhost)")
        if not 1024 <= self.port <= 65535:
            raise ConfigError("FINGUARD_SERVER_PORT must be between 1024 and 65535")
        if not 1024 <= self.max_body_bytes <= MAX_BODY_LIMIT:
            raise ConfigError("FINGUARD_MAX_BODY_BYTES must be between 1024 and 1048576")
        if self.log_level not in LOG_LEVELS:
            raise ConfigError("FINGUARD_LOG_LEVEL must be one of DEBUG, INFO, WARNING, ERROR")
        for origin in self.cors_origins:
            validate_origin(origin)


def _int(environ: Mapping[str, str], name: str, default: int) -> int:
    raw = environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError:
        raise ConfigError(f"{name} must be a whole number") from None


def settings_from_environ(environ: Mapping[str, str]) -> Settings:
    origins = tuple(o.strip() for o in environ.get("FINGUARD_CORS_ORIGINS", "").split(",") if o.strip())
    backend = environ.get("FINGUARD_BACKEND_PATH", "").strip()
    return Settings(
        host=environ.get("FINGUARD_SERVER_HOST", "127.0.0.1").strip(),
        port=_int(environ, "FINGUARD_SERVER_PORT", 8000),
        cors_origins=origins,
        max_body_bytes=_int(environ, "FINGUARD_MAX_BODY_BYTES", MAX_BODY_LIMIT),
        log_level=environ.get("FINGUARD_LOG_LEVEL", "INFO").strip().upper(),
        backend_path=Path(backend).expanduser().resolve() if backend else DEFAULT_BACKEND_PATH,
    )
