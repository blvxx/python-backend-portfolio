"""Prometheus metrics shared by the bot runtime and outbox dispatcher."""

from prometheus_client import Counter, Gauge

OUTBOX_DELIVERIES = Counter(
    "telegram_outbox_delivery_total",
    "Notification outbox delivery outcomes.",
    labelnames=("result",),
)
OUTBOX_PENDING = Gauge("telegram_outbox_pending", "Pending outbox events.")
OUTBOX_PROCESSING = Gauge("telegram_outbox_processing", "Leased outbox events.")
OUTBOX_DELIVERED = Gauge("telegram_outbox_delivered", "Delivered outbox events.")
OUTBOX_DEAD = Gauge("telegram_outbox_dead", "Dead-letter outbox events.")
APP_READINESS = Gauge(
    "telegram_app_readiness",
    "Readiness of the bot and its required database/Redis dependencies (1=ready, 0=not ready).",
)
