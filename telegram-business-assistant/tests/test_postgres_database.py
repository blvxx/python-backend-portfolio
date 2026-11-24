"""Integration tests for shared PostgreSQL persistence and worker coordination."""

import asyncio  # noqa: I001
import os
import uuid

import asyncpg
import pytest

from src.postgres_database import PostgresDatabase


DATABASE_URL = os.getenv("DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL is not configured")


@pytest.fixture
async def databases():
    assert DATABASE_URL is not None
    first = PostgresDatabase(DATABASE_URL)
    second = PostgresDatabase(DATABASE_URL)
    await first.initialize()
    await second.initialize()
    connection = await asyncpg.connect(DATABASE_URL)
    try:
        await connection.execute(
            "TRUNCATE notification_outbox, leads RESTART IDENTITY CASCADE"
        )
    finally:
        await connection.close()
    try:
        yield first, second
    finally:
        await first.close()
        await second.close()


def lead_payload(*, key: str | None, admin_chat_id: int | None) -> dict[str, object]:
    return {
        "telegram_user_id": 410001,
        "username": "integration_test",
        "customer_name": "Integration Test",
        "contact": "integration@example.invalid",
        "service": "Support",
        "details": "Synthetic integration-test enquiry.",
        "admin_chat_id": admin_chat_id,
        "idempotency_key": key,
    }


@pytest.mark.asyncio
async def test_concurrent_replay_creates_one_lead_and_one_outbox_event(databases) -> None:
    first, second = databases
    key = f"telegram:integration:{uuid.uuid4().hex}"
    command = lead_payload(key=key, admin_chat_id=987001)

    lead_ids = await asyncio.gather(
        first.add_lead(**command),
        second.add_lead(**command),
    )

    assert lead_ids[0] == lead_ids[1]
    assert len(await first.get_recent_leads(limit=50)) == 1
    event = await first.get_notification_for_lead(lead_ids[0])
    assert event is not None
    assert event["status"] == "pending"


@pytest.mark.asyncio
async def test_skip_locked_distributes_outbox_work_between_workers(databases) -> None:
    first, second = databases
    lead_ids = await asyncio.gather(
        first.add_lead(**lead_payload(key=None, admin_chat_id=987002)),
        first.add_lead(**lead_payload(key=None, admin_chat_id=987003)),
    )
    assert len(set(lead_ids)) == 2

    claims = await asyncio.gather(
        first.claim_notification(),
        second.claim_notification(),
    )

    assert all(claim is not None for claim in claims)
    claimed_ids = {int(claim["notification_id"]) for claim in claims if claim}
    assert len(claimed_ids) == 2

    for claim in claims:
        assert claim is not None
        await first.mark_notification_delivered(
            int(claim["notification_id"]),
            lease_token=str(claim["lease_token"]),
        )

    stats = await first.get_notification_stats()
    assert stats["delivered"] == 2
    assert stats["pending"] == 0
