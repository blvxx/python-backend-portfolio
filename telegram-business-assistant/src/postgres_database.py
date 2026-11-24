"""PostgreSQL adapter for shared, multi-replica application state."""

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import asyncpg


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


class PostgresDatabase:
    """PostgreSQL implementation of the enquiry and notification-outbox ports.

    Outbox workers coordinate through row locks with SKIP LOCKED. Enquiry
    creation and outbox insertion are committed in the same transaction.
    """

    _MIGRATION_LOCK_ID = 742_026_112

    def __init__(self, database_url: str, *, max_size: int = 10) -> None:
        self.database_url = database_url
        self.max_size = max(2, max_size)
        self._pool: asyncpg.Pool | None = None

    async def initialize(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                self.database_url,
                min_size=1,
                max_size=self.max_size,
                command_timeout=15,
            )

        async with self._pool.acquire() as connection:
            await connection.execute("SELECT pg_advisory_lock($1)", self._MIGRATION_LOCK_ID)
            try:
                await connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
                applied = await connection.fetchval(
                    "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
                )
                if applied > 3:
                    raise RuntimeError(
                        f"Database schema version {applied} is newer than supported version 3"
                    )

                for version in range(applied + 1, 4):
                    async with connection.transaction():
                        if version == 1:
                            await connection.execute(
                                """
                                CREATE TABLE leads (
                                    id BIGSERIAL PRIMARY KEY,
                                    telegram_user_id BIGINT NOT NULL,
                                    username TEXT,
                                    customer_name TEXT NOT NULL,
                                    contact TEXT NOT NULL,
                                    service TEXT NOT NULL,
                                    details TEXT NOT NULL,
                                    created_at TIMESTAMPTZ NOT NULL
                                )
                                """
                            )
                            await connection.execute(
                                "CREATE INDEX idx_leads_created_at ON leads(created_at)"
                            )
                        elif version == 2:
                            await connection.execute(
                                """
                                CREATE TABLE notification_outbox (
                                    id BIGSERIAL PRIMARY KEY,
                                    event_type TEXT NOT NULL,
                                    aggregate_id BIGINT NOT NULL
                                        REFERENCES leads(id) ON DELETE CASCADE,
                                    payload_json JSONB NOT NULL,
                                    status TEXT NOT NULL DEFAULT 'pending'
                                        CHECK (status IN
                                            ('pending', 'processing', 'delivered', 'dead')),
                                    attempts INTEGER NOT NULL DEFAULT 0,
                                    available_at TIMESTAMPTZ NOT NULL,
                                    locked_at TIMESTAMPTZ,
                                    lease_token TEXT,
                                    last_error TEXT,
                                    created_at TIMESTAMPTZ NOT NULL,
                                    delivered_at TIMESTAMPTZ,
                                    UNIQUE(event_type, aggregate_id)
                                )
                                """
                            )
                            await connection.execute(
                                """
                                CREATE INDEX idx_outbox_due
                                ON notification_outbox(status, available_at, locked_at, id)
                                """
                            )
                        elif version == 3:
                            await connection.execute(
                                "ALTER TABLE leads ADD COLUMN idempotency_key TEXT"
                            )
                            await connection.execute(
                                """
                                CREATE UNIQUE INDEX idx_leads_idempotency_key
                                ON leads(idempotency_key)
                                """
                            )
                        await connection.execute(
                            "INSERT INTO schema_migrations(version) VALUES($1)", version
                        )
            finally:
                await connection.execute(
                    "SELECT pg_advisory_unlock($1)", self._MIGRATION_LOCK_ID
                )

    def _require_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            raise RuntimeError("PostgreSQL database is not initialized")
        return self._pool

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def ping(self) -> None:
        await self._require_pool().fetchval("SELECT 1")

    async def add_lead(
        self,
        *,
        telegram_user_id: int,
        username: str | None,
        customer_name: str,
        contact: str,
        service: str,
        details: str,
        admin_chat_id: int | None = None,
        idempotency_key: str | None = None,
    ) -> int:
        now = _utc_now()
        async with self._require_pool().acquire() as connection:
            async with connection.transaction():
                row = await connection.fetchrow(
                    """
                    INSERT INTO leads (
                        telegram_user_id, username, customer_name, contact,
                        service, details, created_at, idempotency_key
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING id
                    """,
                    telegram_user_id,
                    username,
                    customer_name,
                    contact,
                    service,
                    details,
                    now,
                    idempotency_key,
                )
                if row is None:
                    existing_id = await connection.fetchval(
                        "SELECT id FROM leads WHERE idempotency_key = $1",
                        idempotency_key,
                    )
                    if existing_id is None:
                        raise RuntimeError("Idempotent lead insert returned no existing row")
                    return int(existing_id)

                lead_id = int(row["id"])
                if admin_chat_id is not None:
                    await connection.execute(
                        """
                        INSERT INTO notification_outbox (
                            event_type, aggregate_id, payload_json,
                            status, attempts, available_at, created_at
                        )
                        VALUES (
                            'lead.created', $1, jsonb_build_object('chat_id', $2::BIGINT),
                            'pending', 0, $3, $3
                        )
                        """,
                        lead_id,
                        admin_chat_id,
                        now,
                    )
                return lead_id

    async def get_recent_leads(self, limit: int = 10) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 50))
        rows = await self._require_pool().fetch(
            """
            SELECT id, telegram_user_id, username, customer_name,
                   contact, service, details, created_at
            FROM leads
            ORDER BY id DESC
            LIMIT $1
            """,
            safe_limit,
        )
        result = []
        for row in rows:
            item = dict(row)
            if isinstance(item.get("created_at"), datetime):
                item["created_at"] = item["created_at"].isoformat()
            result.append(item)
        return result

    async def claim_notification(
        self, *, lease_seconds: int = 120
    ) -> dict[str, Any] | None:
        now = _utc_now()
        stale_before = now - timedelta(seconds=max(1, lease_seconds))
        pool = self._require_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                candidate = await connection.fetchrow(
                    """
                    SELECT id
                    FROM notification_outbox
                    WHERE
                        (status = 'pending' AND available_at <= $1)
                        OR
                        (status = 'processing' AND locked_at <= $2)
                    ORDER BY id ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                    """,
                    now,
                    stale_before,
                )
                if candidate is None:
                    return None

                event_id = int(candidate["id"])
                row = await connection.fetchrow(
                    """
                    UPDATE notification_outbox
                    SET status = 'processing',
                        locked_at = $1,
                        lease_token = $2,
                        attempts = attempts + 1
                    WHERE id = $3
                    RETURNING id, aggregate_id, payload_json, attempts, lease_token
                    """,
                    now,
                    uuid.uuid4().hex,
                    event_id,
                )
                lead = await connection.fetchrow(
                    """
                    SELECT telegram_user_id, username, customer_name, contact,
                           service, details, created_at
                    FROM leads WHERE id = $1
                    """,
                    int(row["aggregate_id"]),
                )
                if lead is None:
                    return None

                payload = row["payload_json"]
                if isinstance(payload, str):
                    payload = json.loads(payload)
                event = {
                    "notification_id": event_id,
                    "lead_id": int(row["aggregate_id"]),
                    "attempts": int(row["attempts"]),
                    "lease_token": str(row["lease_token"]),
                    **dict(lead),
                    "chat_id": int(payload["chat_id"]),
                }
                if isinstance(event.get("created_at"), datetime):
                    event["created_at"] = event["created_at"].isoformat()
                return event

    async def mark_notification_delivered(
        self, notification_id: int, *, lease_token: str
    ) -> None:
        status = await self._require_pool().execute(
            """
            UPDATE notification_outbox
            SET status = 'delivered',
                delivered_at = $1,
                locked_at = NULL,
                lease_token = NULL,
                last_error = NULL
            WHERE id = $2 AND status = 'processing' AND lease_token = $3
            """,
            _utc_now(),
            notification_id,
            lease_token,
        )
        if status != "UPDATE 1":
            raise RuntimeError("Notification event is no longer leased by this worker")

    async def reschedule_notification(
        self,
        notification_id: int,
        *,
        error_code: str,
        lease_token: str,
        max_attempts: int = 5,
        base_delay_seconds: int = 5,
    ) -> str:
        pool = self._require_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                row = await connection.fetchrow(
                    """
                    SELECT attempts, status, lease_token
                    FROM notification_outbox WHERE id = $1 FOR UPDATE
                    """,
                    notification_id,
                )
                if row is None:
                    raise ValueError(f"Unknown notification event: {notification_id}")
                if row["status"] != "processing" or row["lease_token"] != lease_token:
                    raise RuntimeError(
                        "Notification lease is no longer owned by this worker"
                    )

                attempts = int(row["attempts"])
                now = _utc_now()
                if attempts >= max(1, max_attempts):
                    next_status = "dead"
                    available_at = now
                else:
                    next_status = "pending"
                    delay = min(
                        3600, max(0, base_delay_seconds) * (2 ** (attempts - 1))
                    )
                    available_at = now + timedelta(seconds=delay)

                status = await connection.execute(
                    """
                    UPDATE notification_outbox
                    SET status = $1,
                        available_at = $2,
                        locked_at = NULL,
                        lease_token = NULL,
                        last_error = $3
                    WHERE id = $4 AND status = 'processing' AND lease_token = $5
                    """,
                    next_status,
                    available_at,
                    error_code[:80],
                    notification_id,
                    lease_token,
                )
                if status != "UPDATE 1":
                    raise RuntimeError(
                        "Notification lease changed before retry state was saved"
                    )
                return next_status

    async def get_notification_event(
        self, notification_id: int
    ) -> dict[str, Any] | None:
        row = await self._require_pool().fetchrow(
            """
            SELECT id, event_type, aggregate_id, status, attempts,
                   available_at, locked_at, last_error, created_at, delivered_at
            FROM notification_outbox WHERE id = $1
            """,
            notification_id,
        )
        return dict(row) if row else None

    async def get_notification_for_lead(
        self, lead_id: int
    ) -> dict[str, Any] | None:
        row = await self._require_pool().fetchrow(
            """
            SELECT id, status, attempts
            FROM notification_outbox
            WHERE aggregate_id = $1 AND event_type = 'lead.created'
            """,
            lead_id,
        )
        return dict(row) if row else None

    async def get_notification_stats(self) -> dict[str, int]:
        rows = await self._require_pool().fetch(
            "SELECT status, COUNT(*) AS count FROM notification_outbox GROUP BY status"
        )
        stats = {"pending": 0, "processing": 0, "delivered": 0, "dead": 0}
        for row in rows:
            stats[str(row["status"])] = int(row["count"])
        return stats
