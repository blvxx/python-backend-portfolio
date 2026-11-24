"""Environment-based application settings."""

import os
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv


def _optional_int(name: str) -> int | None:
    value = os.getenv(name, "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer Telegram ID") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    database_path: str = "data/leads.sqlite3"
    admin_chat_id: int | None = None
    admin_user_id: int | None = None
    database_url: str | None = None
    redis_url: str | None = None
    bot_mode: str = "polling"
    webhook_base_url: str | None = None
    webhook_secret: str | None = None
    webhook_path: str = "/telegram/webhook"
    web_server_host: str = "0.0.0.0"
    web_server_port: int = 8080
    fsm_state_ttl_seconds: int = 86400

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError(
                "BOT_TOKEN is missing. Copy .env.example to .env and add your token."
            )

        database_url = os.getenv("DATABASE_URL", "").strip() or None
        redis_url = os.getenv("REDIS_URL", "").strip() or None
        bot_mode = os.getenv("BOT_MODE", "polling").strip().lower()
        if bot_mode not in {"polling", "webhook"}:
            raise ValueError("BOT_MODE must be either 'polling' or 'webhook'")

        configured_webhook_url = os.getenv("WEBHOOK_BASE_URL", "").strip().rstrip("/")
        koyeb_public_domain = os.getenv("KOYEB_PUBLIC_DOMAIN", "").strip().rstrip("/")
        if configured_webhook_url:
            webhook_base_url = configured_webhook_url
        elif koyeb_public_domain:
            # Koyeb exposes its generated public domain without a URL scheme.
            webhook_base_url = (
                koyeb_public_domain
                if koyeb_public_domain.startswith(("http://", "https://"))
                else f"https://{koyeb_public_domain}"
            )
        else:
            webhook_base_url = None
        webhook_secret = os.getenv("WEBHOOK_SECRET", "").strip() or None
        webhook_path = os.getenv("WEBHOOK_PATH", "/telegram/webhook").strip()
        if not webhook_path.startswith("/"):
            raise ValueError("WEBHOOK_PATH must start with '/'")

        if bot_mode == "webhook":
            if not database_url or not database_url.startswith(
                ("postgres://", "postgresql://")
            ):
                raise ValueError("Webhook/multi-replica mode requires PostgreSQL DATABASE_URL")
            if not redis_url:
                raise ValueError("Webhook/multi-replica mode requires REDIS_URL")
            if not webhook_base_url or urlparse(webhook_base_url).scheme != "https":
                raise ValueError("Webhook mode requires an HTTPS WEBHOOK_BASE_URL")
            if not webhook_secret or not all(
                char.isalnum() or char in "_-" for char in webhook_secret
            ):
                raise ValueError("WEBHOOK_SECRET must use only letters, digits, '_' or '-'")

        port = int(os.getenv("WEB_SERVER_PORT", "").strip() or os.getenv("PORT", "8080").strip())
        if not 1 <= port <= 65535:
            raise ValueError("WEB_SERVER_PORT must be between 1 and 65535")

        state_ttl = int(os.getenv("FSM_STATE_TTL_SECONDS", "86400"))
        if state_ttl < 60:
            raise ValueError("FSM_STATE_TTL_SECONDS must be at least 60")

        return cls(
            bot_token=token,
            database_path=os.getenv("DATABASE_PATH", "data/leads.sqlite3").strip(),
            admin_chat_id=_optional_int("ADMIN_CHAT_ID"),
            admin_user_id=_optional_int("ADMIN_USER_ID"),
            database_url=database_url,
            redis_url=redis_url,
            bot_mode=bot_mode,
            webhook_base_url=webhook_base_url,
            webhook_secret=webhook_secret,
            webhook_path=webhook_path,
            web_server_host=os.getenv("WEB_SERVER_HOST", "0.0.0.0").strip(),
            web_server_port=port,
            fsm_state_ttl_seconds=state_ttl,
        )
