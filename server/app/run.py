"""``python -m app.run``: start the server on the configured loopback address with access logging disabled
(uvicorn's access log records request paths and query strings, which this project keeps out of logs)."""

from __future__ import annotations

import os
import sys

import uvicorn

from app.core.config import ConfigError, settings_from_environ
from app.main import create_app


def main() -> None:
    try:
        settings = settings_from_environ(os.environ)
    except ConfigError as exc:
        sys.stderr.write(f"configuration error: {exc}\n")
        raise SystemExit(2) from None
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        access_log=False,
        server_header=False,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
