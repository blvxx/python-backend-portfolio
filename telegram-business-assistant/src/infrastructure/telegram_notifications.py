"""Telegram Bot API adapter for lead notifications."""

import html
from typing import Any

from aiogram import Bot


class TelegramLeadNotificationSender:
    """Translate an outbox lead event into an administrator Telegram message."""

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    async def send_lead_notification(
        self, *, chat_id: int, lead: dict[str, Any]
    ) -> None:
        text = (
            f"<b>Новая заявка №{lead['id']}</b>\n"
            f"<b>Имя:</b> {html.escape(lead['customer_name'])}\n"
            f"<b>Контакт:</b> {html.escape(lead['contact'])}\n"
            f"<b>Услуга:</b> {html.escape(lead['service'])}\n"
            f"<b>Описание:</b> {html.escape(lead['details'])}\n"
            f"<b>Telegram ID:</b> <code>{lead['telegram_user_id']}</code>"
        )
        await self._bot.send_message(chat_id, text)
