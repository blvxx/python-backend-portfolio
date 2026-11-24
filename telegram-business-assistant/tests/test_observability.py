"""HTTP endpoint tests for health, readiness and metrics."""

import re

import pytest
from aiohttp.test_utils import TestClient, TestServer

from src.observability import create_observability_app


class FakeDatabase:
    def __init__(self, *, healthy: bool = True) -> None:
        self.healthy = healthy

    async def ping(self) -> None:
        if not self.healthy:
            raise RuntimeError("database unavailable")

    async def get_notification_stats(self) -> dict[str, int]:
        return {"pending": 2, "processing": 1, "delivered": 10, "dead": 0}


class FakeRedis:
    def __init__(self, *, healthy: bool = True) -> None:
        self.healthy = healthy

    async def ping(self) -> bool:
        if not self.healthy:
            raise RuntimeError("redis unavailable")
        return True


@pytest.mark.asyncio
async def test_health_readiness_and_metrics_endpoints() -> None:
    client = TestClient(TestServer(create_observability_app(FakeDatabase(), FakeRedis())))
    await client.start_server()
    try:
        health = await client.get("/healthz")
        ready = await client.get("/readyz")
        metrics = await client.get("/metrics")

        assert health.status == 200
        assert (await health.json()) == {"status": "ok"}
        assert ready.status == 200
        assert (await ready.json()) == {"status": "ready"}
        assert metrics.status == 200
        payload = await metrics.text()
        assert "telegram_outbox_pending 2.0" in payload
        assert "telegram_outbox_dead 0.0" in payload
        assert "telegram_app_readiness 1.0" in payload
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_readiness_returns_503_when_dependency_is_unavailable() -> None:
    client = TestClient(TestServer(create_observability_app(FakeDatabase(healthy=False))))
    await client.start_server()
    try:
        ready = await client.get("/readyz")
        assert ready.status == 503
        assert (await ready.json()) == {"status": "not_ready"}
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_request_id_is_preserved_and_generated() -> None:
    client = TestClient(TestServer(create_observability_app(FakeDatabase())))
    await client.start_server()
    try:
        supplied = await client.get("/healthz", headers={"X-Request-ID": "case-42:node_a"})
        generated = await client.get("/healthz")

        assert supplied.headers["X-Request-ID"] == "case-42:node_a"
        assert re.fullmatch(r"[A-Za-z0-9._:-]{1,64}", generated.headers["X-Request-ID"])
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_invalid_request_id_is_replaced() -> None:
    client = TestClient(TestServer(create_observability_app(FakeDatabase())))
    await client.start_server()
    try:
        response = await client.get("/healthz", headers={"X-Request-ID": "unsafe value"})

        assert response.status == 200
        assert response.headers["X-Request-ID"] != "unsafe value"
        assert re.fullmatch(r"[A-Za-z0-9._:-]{1,64}", response.headers["X-Request-ID"])
    finally:
        await client.close()
