"""Inline keyboards used by the bot."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

SERVICES = {
    "lead": "Приём заявок",
    "faq": "Ответы на частые вопросы",
    "catalog": "Каталог и заказы",
    "integration": "Интеграция с CRM или таблицами",
    "custom": "Другая задача",
}


def main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Оставить заявку", callback_data="request:start")
    builder.button(text="Какие задачи решает бот", callback_data="info:services")
    builder.button(text="Как проходит работа", callback_data="info:process")
    builder.adjust(1)
    return builder.as_markup()


def consent_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Согласен, продолжить", callback_data="consent:yes"
                )
            ],
            [InlineKeyboardButton(text="Не сейчас", callback_data="consent:no")],
        ]
    )


def service_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slug, title in SERVICES.items():
        builder.button(text=title, callback_data=f"service:{slug}")
    builder.button(text="Отмена", callback_data="flow:cancel")
    builder.adjust(1)
    return builder.as_markup()
