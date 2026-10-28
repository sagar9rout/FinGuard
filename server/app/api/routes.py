"""The documented routes, and only those: GET /health, GET /v1/meta, GET /v1/schema/analysis-request, and
POST /v1/validate, /v1/forecast, /v1/analyze (docs/api/v1.md). Bodies are forwarded to the engine gateway untouched."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from app.core.errors import ServerError
from app.core.logging import get_logger
from app.services.engine_gateway import EngineGateway, GatewayResponse

HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}


def encode(body: dict[str, Any]) -> bytes:
    """Deterministic response bytes, identical to the backend's encoding: sorted keys, no whitespace, ASCII."""
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def respond(status_code: int, body: dict[str, Any]) -> Response:
    return Response(encode(body), status_code=status_code, media_type="application/json", headers=HEADERS)


def error_response(error: ServerError) -> Response:
    return respond(error.status_code, error.body())


async def _read_body(request: Request, limit: int) -> bytes:
    declared = request.headers.get("content-length")
    if declared is not None and declared.isdigit() and int(declared) > limit:
        raise ServerError(413, "payload_too_large")
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise ServerError(413, "payload_too_large")
        chunks.append(chunk)
    return b"".join(chunks)


def build_routes(gateway: EngineGateway, max_body_bytes: int) -> list[Route]:
    def post_route(path: str, handler: Callable[[bytes], GatewayResponse]) -> Route:
        async def endpoint(request: Request) -> Response:
            try:
                media = request.headers.get("content-type", "").split(";")[0].strip().lower()
                if media != "application/json":
                    raise ServerError(415, "unsupported_media_type")
                raw = await _read_body(request, max_body_bytes)
                result = await run_in_threadpool(handler, raw)
                return respond(result.status_code, result.body)
            except ServerError as error:
                return error_response(error)
            except Exception as exc:
                # The exception TYPE only: its message and the request body may contain financial data.
                get_logger().error("unhandled error type=%s", type(exc).__name__)
                return error_response(ServerError(500, "internal_error"))

        return Route(path, endpoint, methods=["POST"])

    def get_route(path: str, handler: Callable[[], GatewayResponse] | None) -> Route:
        async def endpoint(request: Request) -> Response:
            try:
                if handler is None:
                    return respond(200, {"status": "ok"})
                result = await run_in_threadpool(handler)
                return respond(result.status_code, result.body)
            except ServerError as error:
                return error_response(error)
            except Exception as exc:
                get_logger().error("unhandled error type=%s", type(exc).__name__)
                return error_response(ServerError(500, "internal_error"))

        return Route(path, endpoint, methods=["GET"])

    return [
        # Liveness only: the documented body is {"status":"ok"}, so engine status is not reported here.
        get_route("/health", None),
        get_route("/v1/meta", gateway.meta),
        get_route("/v1/schema/analysis-request", gateway.request_schema),
        post_route("/v1/validate", gateway.validate),
        post_route("/v1/forecast", gateway.forecast),
        post_route("/v1/analyze", gateway.analyze),
    ]


async def on_http_exception(request: Request, exc: Exception) -> Response:
    assert isinstance(exc, HTTPException)
    codes = {404: "not_found", 405: "method_not_allowed"}
    return error_response(ServerError(exc.status_code, codes.get(exc.status_code, "http_error")))


async def on_unhandled(request: Request, exc: Exception) -> Response:
    get_logger().error("unhandled error type=%s", type(exc).__name__)
    return error_response(ServerError(500, "internal_error"))
