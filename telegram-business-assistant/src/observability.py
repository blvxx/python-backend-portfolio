"""Health, readiness and Prometheus endpoints for the runtime."""

import logging
import re
import uuid
from typing import Any

from aiohttp import web
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.metrics import (
    APP_READINESS,
    OUTBOX_DEAD,
    OUTBOX_DELIVERED,
    OUTBOX_PENDING,
    OUTBOX_PROCESSING,
)

logger = logging.getLogger(__name__)
_REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,64}")


@web.middleware
async def request_context_middleware(
    request: web.Request,
    handler: Any,
) -> web.StreamResponse:
    """Attach a safe request ID and log request metadata without payloads."""
    supplied_id = request.headers.get("X-Request-ID", "")
    request_id = (
        supplied_id
        if _REQUEST_ID_PATTERN.fullmatch(supplied_id)
        else uuid.uuid4().hex
    )
    request["request_id"] = request_id

    response = await handler(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "HTTP request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.path,
            "status_code": response.status,
        },
    )
    return response


def create_observability_app(database: Any, redis_client: Any | None = None) -> web.Application:
    """Create an aiohttp app exposing liveness, dependency readiness and metrics."""

    app = web.Application(middlewares=[request_context_middleware])

    async def healthz(_request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    async def readyz(_request: web.Request) -> web.Response:
        try:
            await database.ping()
            if redis_client is not None:
                await redis_client.ping()
            APP_READINESS.set(1)
        except Exception as exc:
            APP_READINESS.set(0)
            logger.warning(
                "Readiness probe failed",
                extra={
                    "error_type": type(exc).__name__,
                    "request_id": _request["request_id"],
                },
            )
            return web.json_response({"status": "not_ready"}, status=503)
        return web.json_response({"status": "ready"})

    async def metrics(_request: web.Request) -> web.Response:
        try:
            await database.ping()
            if redis_client is not None:
                await redis_client.ping()
            APP_READINESS.set(1)
        except Exception as exc:
            APP_READINESS.set(0)
            logger.warning(
                "Metrics readiness refresh failed",
                extra={
                    "error_type": type(exc).__name__,
                    "request_id": _request["request_id"],
                },
            )
        try:
            stats = await database.get_notification_stats()
            OUTBOX_PENDING.set(stats["pending"])
            OUTBOX_PROCESSING.set(stats["processing"])
            OUTBOX_DELIVERED.set(stats["delivered"])
            OUTBOX_DEAD.set(stats["dead"])
        except Exception as exc:
            logger.warning(
                "Outbox metrics refresh failed",
                extra={"error_type": type(exc).__name__},
            )
        return web.Response(
            body=generate_latest(),
            headers={"Content-Type": CONTENT_TYPE_LATEST},
        )

    app.router.add_get("/healthz", healthz)
    app.router.add_get("/readyz", readyz)
    app.router.add_get("/metrics", metrics)
    return app
