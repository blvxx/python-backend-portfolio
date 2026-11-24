"""Configuration contract tests for horizontally-scalable deployment mode."""

import pytest

from src.config import Settings


def test_webhook_mode_requires_postgres_and_redis(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.setenv("BOT_MODE", "webhook")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("WEBHOOK_BASE_URL", "https://bot.example.com")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret")

    with pytest.raises(ValueError, match="PostgreSQL"):
        Settings.from_env()


def test_webhook_mode_requires_public_https_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.setenv("BOT_MODE", "webhook")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://assistant:secret@localhost:5432/assistant"
    )
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("WEBHOOK_BASE_URL", "http://bot.example.com")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret")

    with pytest.raises(ValueError, match="HTTPS"):
        Settings.from_env()



def test_koyeb_domain_is_used_when_webhook_url_is_not_set(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.setenv("BOT_MODE", "webhook")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://assistant:secret@localhost:5432/assistant"
    )
    monkeypatch.setenv("REDIS_URL", "rediss://default:secret@redis.example.com:6379")
    monkeypatch.delenv("WEBHOOK_BASE_URL", raising=False)
    monkeypatch.setenv("KOYEB_PUBLIC_DOMAIN", "bot-demo-org.koyeb.app")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret")
    monkeypatch.delenv("WEB_SERVER_PORT", raising=False)
    monkeypatch.setenv("PORT", "8080")

    settings = Settings.from_env()

    assert settings.webhook_base_url == "https://bot-demo-org.koyeb.app"
    assert settings.web_server_port == 8080


def test_explicit_webhook_url_and_port_override_platform_defaults(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.setenv("BOT_MODE", "webhook")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://assistant:secret@localhost:5432/assistant"
    )
    monkeypatch.setenv("REDIS_URL", "rediss://default:secret@redis.example.com:6379")
    monkeypatch.setenv("WEBHOOK_BASE_URL", "https://custom.example.com/")
    monkeypatch.setenv("KOYEB_PUBLIC_DOMAIN", "bot-demo-org.koyeb.app")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("WEB_SERVER_PORT", "9090")
    monkeypatch.setenv("PORT", "8080")

    settings = Settings.from_env()

    assert settings.webhook_base_url == "https://custom.example.com"
    assert settings.web_server_port == 9090
