from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.infrastructure.telegram_notifications import TelegramLeadNotificationSender


@pytest.mark.asyncio
async def test_sender_escapes_untrusted_html_in_all_text_fields() -> None:
    bot = SimpleNamespace(send_message=AsyncMock())
    sender = TelegramLeadNotificationSender(bot)

    await sender.send_lead_notification(
        chat_id=98765,
        lead={
            "id": 12,
            "telegram_user_id": 12345,
            "customer_name": "<b>Customer</b>",
            "contact": "demo@example.com",
            "service": "<script>alert(1)</script>",
            "details": "Need <i>help</i> & a quote",
        },
    )

    bot.send_message.assert_awaited_once()
    chat_id, text = bot.send_message.await_args.args
    assert chat_id == 98765
    assert "&lt;b&gt;Customer&lt;/b&gt;" in text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in text
    assert "Need &lt;i&gt;help&lt;/i&gt; &amp; a quote" in text
    assert "<script>" not in text


@pytest.mark.asyncio
async def test_sender_propagates_telegram_delivery_errors() -> None:
    bot = SimpleNamespace(
        send_message=AsyncMock(side_effect=RuntimeError("delivery failed"))
    )
    sender = TelegramLeadNotificationSender(bot)

    with pytest.raises(RuntimeError, match="delivery failed"):
        await sender.send_lead_notification(
            chat_id=98765,
            lead={
                "id": 12,
                "telegram_user_id": 12345,
                "customer_name": "Customer",
                "contact": "demo@example.com",
                "service": "Support",
                "details": "Please call me back.",
            },
        )
