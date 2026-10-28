"""ASGI entry point (``python -m app.run`` is preferred; see server/README.md).

Stack, outermost first: request logging, loopback Host guard, optional exact-origin CORS, then the routes.
No authentication, authorization, rate limiting or TLS is implemented in this phase; it must not be exposed beyond
the local machine.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from app.api.middleware import RequestLogMiddleware
from app.api.routes import build_routes, on_http_exception, on_unhandled
from app.core.config import Settings, settings_from_environ
from app.core.logging import configure_logging, get_logger
from app.security.hosts import HostGuardMiddleware
from app.services.engine_gateway import EngineGateway


def create_app(settings: Settings | None = None, gateway: EngineGateway | None = None) -> Starlette:
    cfg = settings if settings is not None else settings_from_environ(os.environ)
    engine = gateway if gateway is not None else EngineGateway(cfg.backend_path)
    routes = build_routes(engine, cfg.max_body_bytes)
    known = frozenset(r.path for r in routes)
    configure_logging(cfg.log_level)

    middleware: list[Middleware] = [
        Middleware(RequestLogMiddleware, known_paths=known),
        Middleware(HostGuardMiddleware),
    ]
    if cfg.cors_origins:
        middleware.append(
            Middleware(
                CORSMiddleware,
                allow_origins=list(cfg.cors_origins),
                allow_methods=["GET", "POST"],
                allow_headers=["Content-Type"],
                allow_credentials=False,
                max_age=600,
            )
        )

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        log = get_logger()
        log.info("starting host=%s port=%d cors_origins=%d", cfg.host, cfg.port, len(cfg.cors_origins))
        if engine.is_available():
            log.info("engine available")
        else:
            log.error("engine UNAVAILABLE: engine routes will answer 503 engine_unavailable")
        yield

    return Starlette(
        routes=routes,
        middleware=middleware,
        exception_handlers={HTTPException: on_http_exception, Exception: on_unhandled},
        lifespan=lifespan,
    )


def __getattr__(name: str) -> Starlette:
    # ``app.main:app`` for uvicorn, built lazily so importing this module has no side effects (tests, tooling).
    if name == "app":
        return create_app()
    raise AttributeError(name)
