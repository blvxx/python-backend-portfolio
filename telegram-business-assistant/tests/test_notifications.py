import asyncio
import json

import aiosqlite
import pytest

from src.application.notifications import NotificationOutboxDispatcher
from src.database import Database


async def create_lead(database: Database, *, admin_chat_id: int | None = 98765) -> int:
    return await database.add_lead(
        telegram_user_id=12345,
        username="demo_user",
        customer_name="Demo Customer",
        contact="demo@example.com",
        service="Приём заявок",
        details="Нужна автоматизация обработки обращений.",
        admin_chat_id=admin_chat_id,
    )


class FakeSender:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.sent: list[tuple[int, dict[str, object]]] = []

    async def send_lead_notification(
        self, *, chat_id: int, lead: dict[str, object]
    ) -> None:
        if self.error is not None:
            raise self.error
        self.sent.append((chat_id, lead))


@pytest.mark.asyncio
async def test_lead_and_outbox_event_are_created_together(tmp_path) -> None:
    database = Database(str(tmp_path / "outbox.sqlite3"))
    await database.initialize()

    lead_id = await create_lead(database)
    event = await database.get_notification_for_lead(lead_id)

    assert event is not None
    assert event["status"] == "pending"
    assert event["attempts"] == 0


@pytest.mark.asyncio
async def test_lead_without_admin_target_does_not_create_notification(tmp_path) -> None:
    database = Database(str(tmp_path / "outbox.sqlite3"))
    await database.initialize()

    lead_id = await create_lead(database, admin_chat_id=None)

    assert await database.get_notification_for_lead(lead_id) is None


@pytest.mark.asyncio
async def test_outbox_insert_failure_rolls_back_lead_insert(tmp_path) -> None:
    database = Database(str(tmp_path / "outbox.sqlite3"))
    await database.initialize()

    async with aiosqlite.connect(database.path) as connection:
        await connection.execute(
            """
            CREATE TRIGGER reject_notification
            BEFORE INSERT ON notification_outbox
            BEGIN
                SELECT RAISE(ABORT, 'simulated outbox failure');
            END
            """
        )
        await connection.commit()

    with pytest.raises(aiosqlite.IntegrityError, match="simulated outbox failure"):
        await create_lead(database)

    assert await database.get_recent_leads() == []


@pytest.mark.asyncio
async def test_notification_claim_is_exclusive_across_workers(tmp_path) -> None:
    path = str(tmp_path / "outbox.sqlite3")
    first_worker = Database(path)
    second_worker = Database(path)
    await first_worker.initialize()
    await create_lead(first_worker)

    claims = await asyncio.gather(
        first_worker.claim_notification(),
        second_worker.claim_notification(),
    )

    assert sum(claim is not None for claim in claims) == 1


@pytest.mark.asyncio
async def test_expired_lease_can_be_reclaimed_and_old_worker_is_fenced(tmp_path) -> None:
    database = Database(str(tmp_path / "outbox.sqlite3"))
    await database.initialize()
    lead_id = await create_lead(database)
    event = await database.get_notification_for_lead(lead_id)
    assert event is not None

    old_claim = await database.claim_notification()
    assert old_claim is not None

    async with aiosqlite.connect(database.path) as connection:
        await connection.execute(
            "UPDATE notification_outbox SET locked_at = ? WHERE id = ?",
            ("2000-01-01T00:00:00+00:00", event["id"]),
        )
        await connection.commit()

    new_claim = await database.claim_notification(lease_seconds=1)
    assert new_claim is not None
    assert new_claim["lease_token"] != old_claim["lease_token"]

    with pytest.raises(RuntimeError, match="no longer leased"):
        await database.mark_notification_delivered(
            int(event["id"]), lease_token=str(old_claim["lease_token"])
        )

    await database.mark_notification_delivered(
        int(event["id"]), lease_token=str(new_claim["lease_token"])
    )
    final = await database.get_notification_event(int(event["id"]))
    assert final is not None
    assert final["status"] == "delivered"


@pytest.mark.asyncio
async def test_dispatcher_marks_successful_notification_delivered(tmp_path) -> None:
    database = Database(str(tmp_path / "outbox.sqlite3"))
    await database.initialize()
    lead_id = await create_lead(database)
    event = await database.get_notification_for_lead(lead_id)
    assert event is not None

    sender = FakeSender()
    dispatcher = NotificationOutboxDispatcher(database, sender)

    assert await dispatcher.dispatch_once() is True
    assert await dispatcher.dispatch_once() is False
    assert len(sender.sent) == 1
    chat_id, lead = sender.sent[0]
    assert chat_id == 98765
    assert lead["id"] == lead_id
    assert lead["contact"] == "demo@example.com"

    final = await database.get_notification_event(int(event["id"]))
    assert final is not None
    assert final["status"] == "delivered"
    assert final["attempts"] == 1


@pytest.mark.asyncio
async def test_dispatcher_retries_then_dead_letters_without_persisting_error_text(
    tmp_path,
) -> None:
    database = Database(str(tmp_path / "outbox.sqlite3"))
    await database.initialize()
    lead_id = await create_lead(database)
    event = await database.get_notification_for_lead(lead_id)
    assert event is not None

    sender = FakeSender(RuntimeError("sensitive token=do-not-persist"))
    dispatcher = NotificationOutboxDispatcher(
        database,
        sender,
        max_attempts=2,
        base_delay_seconds=0,
    )

    assert await dispatcher.dispatch_once() is True
    first = await database.get_notification_event(int(event["id"]))
    assert first is not None
    assert first["status"] == "pending"
    assert first["attempts"] == 1
    assert first["last_error"] == "RuntimeError"
    assert "do-not-persist" not in json.dumps(first)

    assert await dispatcher.dispatch_once() is True
    final = await database.get_notification_event(int(event["id"]))
    assert final is not None
    assert final["status"] == "dead"
    assert final["attempts"] == 2
