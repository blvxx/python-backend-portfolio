"""Versioned, forward-only SQLite schema migrations."""

from collections.abc import Awaitable, Callable

import aiosqlite

Migration = Callable[[aiosqlite.Connection], Awaitable[None]]


async def _create_initial_schema(connection: aiosqlite.Connection) -> None:
    """Version 1: base lead table and lookup index."""
    await connection.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
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
        "CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at)"
    )


async def _create_notification_outbox(connection: aiosqlite.Connection) -> None:
    """Version 2: durable notification events and worker claim metadata."""
    await connection.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_outbox (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            aggregate_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'processing', 'delivered', 'dead')),
            attempts INTEGER NOT NULL DEFAULT 0,
            available_at TEXT NOT NULL,
            locked_at TEXT,
            lease_token TEXT,
            last_error TEXT,
            created_at TEXT NOT NULL,
            delivered_at TEXT,
            UNIQUE(event_type, aggregate_id)
        )
        """
    )
    await connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_outbox_due
        ON notification_outbox(status, available_at, locked_at)
        """
    )



async def _add_enquiry_idempotency_key(connection: aiosqlite.Connection) -> None:
    """Version 3: make Telegram message replay safe for lead creation."""
    cursor = await connection.execute("PRAGMA table_info(leads)")
    columns = {row[1] for row in await cursor.fetchall()}
    if "idempotency_key" not in columns:
        await connection.execute(
            "ALTER TABLE leads ADD COLUMN idempotency_key TEXT"
        )
    await connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_idempotency_key
        ON leads(idempotency_key)
        """
    )


MIGRATIONS: tuple[tuple[int, Migration], ...] = (
    (1, _create_initial_schema),
    (2, _create_notification_outbox),
    (3, _add_enquiry_idempotency_key),
)
LATEST_SCHEMA_VERSION = MIGRATIONS[-1][0]


async def migrate(connection: aiosqlite.Connection) -> int:
    """Apply all pending migrations atomically, one version at a time.

    Migrations are forward-only. A database created by a newer application is
    rejected rather than being silently opened by older code.
    """
    cursor = await connection.execute("PRAGMA user_version")
    row = await cursor.fetchone()
    current_version = int(row[0]) if row else 0

    if current_version > LATEST_SCHEMA_VERSION:
        raise RuntimeError(
            "Database schema version "
            f"{current_version} is newer than supported version "
            f"{LATEST_SCHEMA_VERSION}"
        )

    for target_version, migration in MIGRATIONS:
        if target_version <= current_version:
            continue

        await connection.execute("BEGIN IMMEDIATE")
        try:
            await migration(connection)
            await connection.execute(f"PRAGMA user_version = {target_version}")
            await connection.commit()
        except Exception:
            await connection.rollback()
            raise

    return LATEST_SCHEMA_VERSION
