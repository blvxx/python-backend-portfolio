"""Telegram handlers for the business enquiry assistant."""

import html

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.application.enquiries import (
    CreateEnquiry,
    EnquiryPolicyError,
    EnquiryService,
)
from src.config import Settings
from src.database import Database
from src.keyboards import SERVICES, consent_menu, main_menu, service_menu
from src.states import RequestFlow
from src.validation import validate_contact

router = Router()


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "<b>Business Assistant</b>\n\n"
        "Помогаю принять обращение, уточнить задачу и передать заявку ответственному "
        "специалисту. Выберите, что нужно сделать:",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "info:services")
async def show_services(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "<b>Что можно автоматизировать</b>\n\n"
            "• Приём заявок и контактов\n"
            "• Ответы на типовые вопросы\n"
            "• Каталог услуг и первичный заказ\n"
            "• Передачу обращений в CRM или таблицу\n\n"
            "Сценарий и интеграции подбираются под процесс компании.",
            reply_markup=main_menu(),
        )


@router.callback_query(F.data == "info:process")
async def show_process(callback: CallbackQuery) -> None:
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "<b>Как работает сценарий</b>\n\n"
            "1. Клиент выбирает тип обращения.\n"
            "2. Оставляет контакт и описание задачи.\n"
            "3. Бот сохраняет заявку в SQLite.\n"
            "4. При настройке ADMIN_CHAT_ID уведомление ставится в очередь доставки.\n\n"
            "В демонстрационной версии нет подключённой CRM или платёжной системы.",
            reply_markup=main_menu(),
        )


@router.callback_query(F.data == "request:start")
async def request_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(RequestFlow.waiting_consent)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "<b>Перед отправкой заявки</b>\n\n"
            "Бот сохранит указанные вами имя, контакт, выбранную услугу и описание "
            "задачи, чтобы передать обращение ответственному специалисту. "
            "Не отправляйте пароли, коды подтверждения или платёжные данные. "
            "Продолжая, вы соглашаетесь на обработку этих сведений для ответа на запрос.",
            reply_markup=consent_menu(),
        )


@router.callback_query(F.data == "consent:yes", StateFilter(RequestFlow.waiting_consent))
async def consent_yes(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_data({"consent": True})
    await state.set_state(RequestFlow.waiting_service)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            "Выберите, с какой задачей нужна помощь:",
            reply_markup=service_menu(),
        )


@router.callback_query(F.data == "consent:yes")
async def stale_consent_yes(callback: CallbackQuery) -> None:
    await callback.answer("Сначала начните оформление заявки.", show_alert=True)


@router.callback_query(F.data == "flow:cancel")
async def cancel_flow(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel the request flow from its inline keyboard."""
    await state.clear()
    await callback.answer("Сценарий отменён")
    if callback.message:
        await callback.message.answer(
            "Текущий сценарий отменён.", reply_markup=main_menu()
        )


@router.callback_query(F.data == "consent:no", StateFilter(RequestFlow.waiting_consent))
async def consent_no(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Заявка не создавалась")
    if callback.message:
        await callback.message.answer(
            "Хорошо. Заявка не создавалась.", reply_markup=main_menu()
        )


@router.callback_query(F.data == "consent:no")
async def stale_consent_no(callback: CallbackQuery) -> None:
    await callback.answer("Сначала начните оформление заявки.", show_alert=True)


@router.callback_query(F.data.startswith("service:"), StateFilter(RequestFlow.waiting_service))
async def choose_service(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("consent"):
        await callback.answer(
            "Сначала подтвердите согласие на обработку заявки.", show_alert=True
        )
        return

    slug = (callback.data or "").partition(":")[2]
    service = SERVICES.get(slug)
    if not service:
        await callback.answer("Неизвестный тип заявки.", show_alert=True)
        return

    await state.update_data(service=service)
    await state.set_state(RequestFlow.waiting_contact)
    await callback.answer()
    if callback.message:
        await callback.message.answer(
            f"Вы выбрали: <b>{html.escape(service)}</b>.\n\n"
            "Оставьте телефон или email для обратной связи. "
            "Можно отправить номер как текст или поделиться контактом Telegram."
        )


async def accept_contact(message: Message, state: FSMContext, contact: str) -> None:
    normalized = contact.strip()
    if not validate_contact(normalized):
        await message.answer(
            "Не удалось распознать контакт. Отправьте номер телефона или email."
        )
        return

    await state.update_data(contact=normalized)
    await state.set_state(RequestFlow.waiting_details)
    await message.answer(
        "Теперь коротко опишите задачу. Например: «Нужен бот для записи клиентов "
        "на консультацию и уведомления администратора». От 10 до 1000 символов."
    )


@router.message(RequestFlow.waiting_contact, F.contact)
async def receive_shared_contact(message: Message, state: FSMContext) -> None:
    if message.contact:
        await accept_contact(message, state, message.contact.phone_number)


@router.message(RequestFlow.waiting_contact, F.text)
async def receive_text_contact(message: Message, state: FSMContext) -> None:
    if message.text:
        await accept_contact(message, state, message.text)


@router.message(RequestFlow.waiting_details, F.text)
async def receive_details(
    message: Message,
    state: FSMContext,
    enquiry_service: EnquiryService,
    settings: Settings,
) -> None:
    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить отправителя. Попробуйте ещё раз.")
        return

    data = await state.get_data()
    command = CreateEnquiry(
        telegram_user_id=user.id,
        username=user.username,
        customer_name=user.full_name,
        contact=data.get("contact") or "",
        service=data.get("service") or "",
        details=message.text or "",
        consent_given=bool(data.get("consent")),
        admin_chat_id=settings.admin_chat_id,
        idempotency_key=f"telegram:{message.chat.id}:{message.message_id}",
    )
    try:
        lead_id = await enquiry_service.submit(command)
    except EnquiryPolicyError as exc:
        await message.answer(str(exc))
        return

    await state.clear()
    confirmation = f"Спасибо! Заявка №{lead_id} сохранена."
    if settings.admin_chat_id is not None:
        confirmation += " Уведомление поставлено в очередь доставки."
    await message.answer(confirmation, reply_markup=main_menu())


@router.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Текущий сценарий отменён.", reply_markup=main_menu())


@router.message(Command("my_id"))
async def show_ids(message: Message) -> None:
    """Show the numeric IDs needed for private administrator configuration."""
    user = message.from_user
    if user is None:
        await message.answer("Не удалось определить Telegram ID.")
        return

    await message.answer(
        "<b>Данные этого чата</b>\n"
        f"User ID: <code>{user.id}</code>\n"
        f"Chat ID: <code>{message.chat.id}</code>\n\n"
        "Используйте эти значения в ADMIN_USER_ID и ADMIN_CHAT_ID. "
        "Не публикуйте их вместе с персональными данными заявок."
    )


@router.message(Command("leads"))
async def list_leads(message: Message, db: Database, settings: Settings) -> None:
    user = message.from_user
    if (
        user is None
        or settings.admin_user_id is None
        or user.id != settings.admin_user_id
        or message.chat.type != "private"
    ):
        await message.answer(
            "Команда доступна только настроенному администратору в личном чате."
        )
        return

    leads = await db.get_recent_leads(limit=10)
    if not leads:
        await message.answer("Пока нет сохранённых заявок.")
        return

    lines = ["<b>Последние заявки</b>"]
    for lead in leads:
        lines.extend(
            [
                "",
                f"<b>#{lead['id']} · {html.escape(lead['service'])}</b>",
                f"Имя: {html.escape(lead['customer_name'])}",
                f"Контакт: {html.escape(lead['contact'])}",
                f"Описание: {html.escape(lead['details'])}",
                f"<i>{html.escape(lead['created_at'])}</i>",
            ]
        )
    await message.answer("\n".join(lines))


@router.message(StateFilter(None), F.text)
async def fallback(message: Message) -> None:
    await message.answer(
        "Используйте кнопки меню, чтобы посмотреть возможности или оставить заявку.",
        reply_markup=main_menu(),
    )
