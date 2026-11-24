import aiosqlite
import pytest

from src.database import Database
from src.migrations import LATEST_SCHEMA_VERSION


async def schema_version(path: str) -> int:
    async with aiosqlite.connect(path) as connection:
        cursor = await connection.execute("PRAGMA user_version")
        row = await cursor.fetchone()
        return int(row[0])


@pytest.mark.asyncio
async def test_fresh_database_applies_all_migrations(tmp_path) -> None:
    path = str(tmp_path / "fresh.sqlite3")
    database = Database(path)

    await database.initialize()

    assert await schema_version(path) == LATEST_SCHEMA_VERSION
    async with aiosqlite.connect(path) as connection:
        cursor = await connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in await cursor.fetchall()}

    assert {"leads", "notification_outbox"} <= tables


@pytest.mark.asyncio
async def test_existing_version_one_database_upgrades_to_latest(tmp_path) -> None:
    path = str(tmp_path / "existing.sqlite3")
    async with aiosqlite.connect(path) as connection:
        await connection.execute(
            """
            CREATE TABLE leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                username TEXT,
                customer_name TEXT NOT NULL,
                contact TEXT NOT NULL,
                service TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await connection.execute(
            """
            INSERT INTO leads (
                telegram_user_id, username, customer_name, contact,
                service, details, created_at
            )
            VALUES (123, NULL, 'Legacy', 'legacy@example.com',
                    'Support', 'Existing request', '2026-01-01T00:00:00+00:00')
            """
        )
        await connection.execute("PRAGMA user_version = 1")
        await connection.commit()

    await Database(path).initialize()

    assert await schema_version(path) == LATEST_SCHEMA_VERSION
    async with aiosqlite.connect(path) as connection:
        cursor = await connection.execute(
            "SELECT customer_name FROM leads WHERE telegram_user_id = 123"
        )
        lead = await cursor.fetchone()
        cursor = await connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='notification_outbox'"
        )
        outbox_tables = await cursor.fetchall()
        cursor = await connection.execute("PRAGMA table_info(leads)")
        lead_columns = {row[1] for row in await cursor.fetchall()}
        cursor = await connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_leads_idempotency_key'"
        )
        idempotency_indexes = await cursor.fetchall()

    assert lead == ("Legacy",)
    assert outbox_tables == [("notification_outbox",)]
    assert "idempotency_key" in lead_columns
    assert idempotency_indexes == [("idx_leads_idempotency_key",)]


@pytest.mark.asyncio
async def test_initialization_is_idempotent(tmp_path) -> None:
    path = str(tmp_path / "repeat.sqlite3")
    database = Database(path)

    await database.initialize()
    await database.initialize()

    assert await schema_version(path) == LATEST_SCHEMA_VERSION


@pytest.mark.asyncio
async def test_database_newer_than_application_is_rejected(tmp_path) -> None:
    path = str(tmp_path / "future.sqlite3")
    async with aiosqlite.connect(path) as connection:
        await connection.execute("PRAGMA user_version = 999")
        await connection.commit()

    with pytest.raises(RuntimeError, match="newer than supported"):
        await Database(path).initialize()
