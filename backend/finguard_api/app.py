"""The ASGI application (Starlette; see ADR 0011 for why not FastAPI yet).

Stateless: no database, no sessions, no authentication, no AI. It MUST
NOT be exposed publicly until the authentication phase lands.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from finguard_api import service
from finguard_api.errors import ApiError

log = logging.getLogger("finguard_api")

DEFAULT_MAX_BODY_BYTES = 1_048_576

_HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}


def _respond(status_code: int, body: dict[str, Any]) -> Response:
    return Response(
        content=service.encode(body), status_code=status_code, media_type="application/json", headers=_HEADERS
    )


def _error(error: ApiError) -> Response:
    return _respond(error.status_code, error.body())


async def _read_body(request: Request, limit: int) -> bytes:
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > limit:
        raise ApiError(413, "payload_too_large")
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise ApiError(413, "payload_too_large")
        chunks.append(chunk)
    return b"".join(chunks)


def _post_route(path: str, handler: Callable[[bytes], service.ApiResponse], limit: int) -> Route:
    async def endpoint(request: Request) -> Response:
        try:
            media = request.headers.get("content-type", "").split(";")[0].strip().lower()
            if media != "application/json":
                raise ApiError(415, "unsupported_media_type")
            raw = await _read_body(request, limit)
            result = await run_in_threadpool(handler, raw)
            return _respond(result.status_code, result.body)
        except ApiError as error:
            return _error(error)

    return Route(path, endpoint, methods=["POST"])


def _get_route(path: str, handler: Callable[[], service.ApiResponse]) -> Route:
    async def endpoint(request: Request) -> Response:
        result = handler()
        return _respond(result.status_code, result.body)

    return Route(path, endpoint, methods=["GET"])


async def _on_http_exception(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, HTTPException)
    codes = {404: "not_found", 405: "method_not_allowed"}
    return _error(ApiError(exc.status_code, codes.get(exc.status_code, "http_error")))


async def _on_unhandled(request: Request, exc: Exception) -> Response:
    # Log the exception type only: never the message or the request body,
    # either of which may contain financial data.
    log.error("unhandled error: %s", type(exc).__name__)
    return _error(ApiError(500, "internal_error"))


def create_app(max_body_bytes: int = DEFAULT_MAX_BODY_BYTES) -> Starlette:
    routes = [
        _get_route("/health", lambda: service.ApiResponse(200, {"status": "ok"})),
        _get_route("/v1/meta", service.handle_meta),
        _get_route("/v1/schema/analysis-request", service.handle_request_schema),
        _post_route("/v1/validate", service.handle_validate, max_body_bytes),
        _post_route("/v1/forecast", service.handle_forecast, max_body_bytes),
        _post_route("/v1/analyze", service.handle_analyze, max_body_bytes),
    ]
    return Starlette(
        routes=routes,
        exception_handlers={HTTPException: _on_http_exception, Exception: _on_unhandled},
    )
