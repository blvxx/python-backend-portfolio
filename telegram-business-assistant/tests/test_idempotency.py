import asyncio

import aiosqlite
import pytest

from src.database import Database


async def submit(database: Database, *, key: str) -> int:
    return await database.add_lead(
        telegram_user_id=12345,
        username="demo_user",
        customer_name="Demo Customer",
        contact="demo@example.com",
        service="Приём заявок",
        details="Нужна автоматизация обработки обращений.",
        admin_chat_id=98765,
        idempotency_key=key,
    )


@pytest.mark.asyncio
async def test_repeated_idempotency_key_returns_existing_lead_and_outbox_event(
    tmp_path,
) -> None:
    path = str(tmp_path / "idempotency.sqlite3")
    database = Database(path)
    await database.initialize()

    first_id = await submit(database, key="telegram:9876:555")
    replayed_id = await submit(database, key="telegram:9876:555")

    assert replayed_id == first_id
    leads = await database.get_recent_leads()
    assert len(leads) == 1
    event = await database.get_notification_for_lead(first_id)
    assert event is not None
    assert event["status"] == "pending"

    async with aiosqlite.connect(path) as connection:
        cursor = await connection.execute(
            "SELECT COUNT(*) FROM notification_outbox WHERE aggregate_id = ?",
            (first_id,),
        )
        row = await cursor.fetchone()

    assert row == (1,)


@pytest.mark.asyncio
async def test_concurrent_replays_with_same_key_create_one_lead(tmp_path) -> None:
    path = str(tmp_path / "concurrent-idempotency.sqlite3")
    first_worker = Database(path)
    second_worker = Database(path)
    await first_worker.initialize()

    results = await asyncio.gather(
        submit(first_worker, key="telegram:9876:777"),
        submit(second_worker, key="telegram:9876:777"),
    )

    assert results[0] == results[1]
    assert len(await first_worker.get_recent_leads()) == 1
    event = await first_worker.get_notification_for_lead(results[0])
    assert event is not None
    assert event["status"] == "pending"


@pytest.mark.asyncio
async def test_different_idempotency_keys_create_distinct_leads(tmp_path) -> None:
    database = Database(str(tmp_path / "distinct-idempotency.sqlite3"))
    await database.initialize()

    first_id = await submit(database, key="telegram:9876:100")
    second_id = await submit(database, key="telegram:9876:101")

    assert first_id != second_id
    assert len(await database.get_recent_leads()) == 2
