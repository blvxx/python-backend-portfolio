"""Application-level dispatcher for durable notification events."""

import asyncio
import logging
from typing import Any, Protocol

from src.metrics import OUTBOX_DELIVERIES

logger = logging.getLogger(__name__)


class NotificationOutbox(Protocol):
    async def claim_notification(
        self, *, lease_seconds: int = 120
    ) -> dict[str, Any] | None: ...

    async def mark_notification_delivered(
        self, notification_id: int, *, lease_token: str
    ) -> None: ...

    async def reschedule_notification(
        self,
        notification_id: int,
        *,
        error_code: str,
        lease_token: str,
        max_attempts: int = 5,
        base_delay_seconds: int = 5,
    ) -> str: ...


class LeadNotificationSender(Protocol):
    async def send_lead_notification(
        self, *, chat_id: int, lead: dict[str, Any]
    ) -> None: ...


class NotificationOutboxDispatcher:
    """Deliver outbox messages with bounded exponential retry.

    Delivery is at-least-once. A process can crash after the remote send succeeds
    but before the delivered marker is committed, so duplicate remote messages
    remain possible in that narrow failure window.
    """

    def __init__(
        self,
        outbox: NotificationOutbox,
        sender: LeadNotificationSender,
        *,
        max_attempts: int = 5,
        base_delay_seconds: int = 5,
        lease_seconds: int = 120,
    ) -> None:
        self._outbox = outbox
        self._sender = sender
        self._max_attempts = max(1, max_attempts)
        self._base_delay_seconds = max(0, base_delay_seconds)
        self._lease_seconds = max(1, lease_seconds)

    async def dispatch_once(self) -> bool:
        """Process at most one due event; return whether an event was claimed."""
        event = await self._outbox.claim_notification(
            lease_seconds=self._lease_seconds
        )
        if event is None:
            return False

        notification_id = int(event["notification_id"])
        chat_id = int(event["chat_id"])
        lead = {
            "id": int(event["lead_id"]),
            "telegram_user_id": int(event["telegram_user_id"]),
            "username": event.get("username"),
            "customer_name": str(event["customer_name"]),
            "contact": str(event["contact"]),
            "service": str(event["service"]),
            "details": str(event["details"]),
            "created_at": str(event["created_at"]),
        }

        try:
            await self._sender.send_lead_notification(chat_id=chat_id, lead=lead)
        except Exception as exc:
            # Persist only the exception type. External API exceptions may contain
            # request URLs or other sensitive details; avoid storing/logging them.
            error_code = type(exc).__name__
            status = await self._outbox.reschedule_notification(
                notification_id,
                error_code=error_code,
                lease_token=str(event["lease_token"]),
                max_attempts=self._max_attempts,
                base_delay_seconds=self._base_delay_seconds,
            )
            OUTBOX_DELIVERIES.labels(result=status).inc()
            logger.warning(
                "Lead notification delivery failed",
                extra={
                    "notification_id": notification_id,
                    "attempt": int(event["attempts"]),
                    "next_status": status,
                    "error_type": error_code,
                },
            )
            return True

        await self._outbox.mark_notification_delivered(
            notification_id, lease_token=str(event["lease_token"])
        )
        OUTBOX_DELIVERIES.labels(result="delivered").inc()
        logger.info(
            "Lead notification delivered",
            extra={
                "notification_id": notification_id,
                "lead_id": int(event["lead_id"]),
                "attempt": int(event["attempts"]),
            },
        )
        return True


async def run_outbox_worker(
    dispatcher: NotificationOutboxDispatcher,
    stop_event: asyncio.Event,
    *,
    idle_poll_seconds: float = 2.0,
) -> None:
    """Run one dispatcher loop until a graceful shutdown is requested."""
    while not stop_event.is_set():
        try:
            processed = await dispatcher.dispatch_once()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "Notification outbox worker iteration failed",
                extra={"error_type": type(exc).__name__},
            )
            processed = False

        if not processed:
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=max(0.1, idle_poll_seconds)
                )
            except TimeoutError:
                pass
