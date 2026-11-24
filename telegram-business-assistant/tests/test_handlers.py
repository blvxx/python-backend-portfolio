from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.application.enquiries import EnquiryPolicyError
from src.config import Settings
from src.handlers import (
    cancel,
    cancel_flow,
    choose_service,
    consent_no,
    consent_yes,
    list_leads,
    receive_details,
    stale_consent_no,
    stale_consent_yes,
)
from src.states import RequestFlow


def make_message(*, full_name: str = "Demo Customer"):
    bot = SimpleNamespace(send_message=AsyncMock())
    return SimpleNamespace(
        from_user=SimpleNamespace(
            id=12345,
            username="demo_user",
            full_name=full_name,
        ),
        text="<b>Please contact me</b> about the service.",
        chat=SimpleNamespace(id=9876, type="private"),
        message_id=555,
        answer=AsyncMock(),
        bot=bot,
    )


def make_state():
    return SimpleNamespace(
        get_data=AsyncMock(
            return_value={
                "consent": True,
                "contact": "demo@example.com",
                "service": "Приём заявок",
            }
        ),
        clear=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_receive_details_submits_enquiry_and_notifies_admin() -> None:
    message = make_message(full_name="<b>Demo Customer</b>")
    state = make_state()
    enquiry_service = SimpleNamespace(submit=AsyncMock(return_value=17))
    settings = Settings(bot_token="test-token", admin_chat_id=98765)

    await receive_details(message, state, enquiry_service, settings)

    command = enquiry_service.submit.await_args.args[0]
    assert command.telegram_user_id == 12345
    assert command.username == "demo_user"
    assert command.customer_name == "<b>Demo Customer</b>"
    assert command.contact == "demo@example.com"
    assert command.service == "Приём заявок"
    assert command.consent_given is True
    assert command.admin_chat_id == 98765
    assert command.idempotency_key == "telegram:9876:555"

    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once()
    assert "Заявка №17 сохранена" in message.answer.await_args.args[0]
    assert "очередь доставки" in message.answer.await_args.args[0]
    message.bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_receive_details_keeps_flow_open_when_application_policy_rejects() -> None:
    message = make_message()
    state = make_state()
    enquiry_service = SimpleNamespace(
        submit=AsyncMock(side_effect=EnquiryPolicyError("policy rejected"))
    )
    settings = Settings(bot_token="test-token", admin_chat_id=98765)

    await receive_details(message, state, enquiry_service, settings)

    message.answer.assert_awaited_once_with("policy rejected")
    state.clear.assert_not_awaited()
    message.bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_receive_details_skips_notification_when_admin_chat_is_not_configured() -> None:
    message = make_message()
    state = make_state()
    enquiry_service = SimpleNamespace(submit=AsyncMock(return_value=18))
    settings = Settings(bot_token="test-token")

    await receive_details(message, state, enquiry_service, settings)

    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once()
    command = enquiry_service.submit.await_args.args[0]
    assert command.admin_chat_id is None
    assert "очередь доставки" not in message.answer.await_args.args[0]
    message.bot.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_receive_details_rejects_message_without_sender() -> None:
    message = make_message()
    message.from_user = None
    state = make_state()
    enquiry_service = SimpleNamespace(submit=AsyncMock(return_value=19))
    settings = Settings(bot_token="test-token", admin_chat_id=98765)

    await receive_details(message, state, enquiry_service, settings)

    message.answer.assert_awaited_once()
    assert "Не удалось определить отправителя" in message.answer.await_args.args[0]
    state.get_data.assert_not_awaited()
    state.clear.assert_not_awaited()
    enquiry_service.submit.assert_not_awaited()
    message.bot.send_message.assert_not_awaited()



@pytest.mark.asyncio
async def test_list_leads_rejects_non_admin_without_reading_database() -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=111),
        chat=SimpleNamespace(type="private"),
        answer=AsyncMock(),
    )
    database = SimpleNamespace(get_recent_leads=AsyncMock(return_value=[]))
    settings = Settings(bot_token="test-token", admin_user_id=12345)

    await list_leads(message, database, settings)

    message.answer.assert_awaited_once()
    assert "настроенному администратору" in message.answer.await_args.args[0]
    database.get_recent_leads.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_leads_rejects_admin_command_in_group_chat() -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=12345),
        chat=SimpleNamespace(type="supergroup"),
        answer=AsyncMock(),
    )
    database = SimpleNamespace(get_recent_leads=AsyncMock(return_value=[]))
    settings = Settings(bot_token="test-token", admin_user_id=12345)

    await list_leads(message, database, settings)

    message.answer.assert_awaited_once()
    assert "личном чате" in message.answer.await_args.args[0]
    database.get_recent_leads.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_leads_allows_configured_admin_in_private_chat_and_escapes_data() -> None:
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=12345),
        chat=SimpleNamespace(type="private"),
        answer=AsyncMock(),
    )
    database = SimpleNamespace(
        get_recent_leads=AsyncMock(
            return_value=[
                {
                    "id": 9,
                    "service": "<script>service</script>",
                    "customer_name": "<b>Customer</b>",
                    "contact": "demo@example.com",
                    "details": "Need <i>help</i> & advice",
                    "created_at": "2026-11-22T12:00:00+00:00",
                }
            ]
        )
    )
    settings = Settings(bot_token="test-token", admin_user_id=12345)

    await list_leads(message, database, settings)

    database.get_recent_leads.assert_awaited_once_with(limit=10)
    message.answer.assert_awaited_once()
    response = message.answer.await_args.args[0]
    assert "&lt;script&gt;service&lt;/script&gt;" in response
    assert "&lt;b&gt;Customer&lt;/b&gt;" in response
    assert "Need &lt;i&gt;help&lt;/i&gt; &amp; advice" in response
    assert "<script>" not in response



def make_callback(data: str = "service:lead"):
    message = SimpleNamespace(answer=AsyncMock())
    return SimpleNamespace(
        data=data,
        message=message,
        answer=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_consent_yes_moves_flow_to_service_selection() -> None:
    callback = make_callback("consent:yes")
    state = SimpleNamespace(
        set_data=AsyncMock(),
        set_state=AsyncMock(),
    )

    await consent_yes(callback, state)

    state.set_data.assert_awaited_once_with({"consent": True})
    state.set_state.assert_awaited_once_with(RequestFlow.waiting_service)
    callback.answer.assert_awaited_once()
    callback.message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_consent_no_clears_state_and_does_not_collect_data() -> None:
    callback = make_callback("consent:no")
    state = SimpleNamespace(clear=AsyncMock())

    await consent_no(callback, state)

    state.clear.assert_awaited_once()
    callback.answer.assert_awaited_once_with("Заявка не создавалась")
    callback.message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_stale_consent_callbacks_are_rejected() -> None:
    yes_callback = make_callback("consent:yes")
    no_callback = make_callback("consent:no")

    await stale_consent_yes(yes_callback)
    await stale_consent_no(no_callback)

    yes_callback.answer.assert_awaited_once_with(
        "Сначала начните оформление заявки.",
        show_alert=True,
    )
    no_callback.answer.assert_awaited_once_with(
        "Сначала начните оформление заявки.",
        show_alert=True,
    )
    yes_callback.message.answer.assert_not_awaited()
    no_callback.message.answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_choose_service_requires_recorded_consent() -> None:
    callback = make_callback("service:lead")
    state = SimpleNamespace(
        get_data=AsyncMock(return_value={"consent": False}),
        update_data=AsyncMock(),
        set_state=AsyncMock(),
    )

    await choose_service(callback, state)

    callback.answer.assert_awaited_once_with(
        "Сначала подтвердите согласие на обработку заявки.",
        show_alert=True,
    )
    state.update_data.assert_not_awaited()
    state.set_state.assert_not_awaited()
    callback.message.answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_choose_service_rejects_unknown_service_slug() -> None:
    callback = make_callback("service:not-a-real-service")
    state = SimpleNamespace(
        get_data=AsyncMock(return_value={"consent": True}),
        update_data=AsyncMock(),
        set_state=AsyncMock(),
    )

    await choose_service(callback, state)

    callback.answer.assert_awaited_once_with(
        "Неизвестный тип заявки.",
        show_alert=True,
    )
    state.update_data.assert_not_awaited()
    state.set_state.assert_not_awaited()
    callback.message.answer.assert_not_awaited()


@pytest.mark.asyncio
async def test_choose_service_updates_state_for_valid_service() -> None:
    callback = make_callback("service:lead")
    state = SimpleNamespace(
        get_data=AsyncMock(return_value={"consent": True}),
        update_data=AsyncMock(),
        set_state=AsyncMock(),
    )

    await choose_service(callback, state)

    state.update_data.assert_awaited_once_with(service="Приём заявок")
    state.set_state.assert_awaited_once_with(RequestFlow.waiting_contact)
    callback.answer.assert_awaited_once()
    callback.message.answer.assert_awaited_once()
    assert "Вы выбрали:" in callback.message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_inline_cancel_clears_fsm_and_returns_main_menu() -> None:
    callback = make_callback("flow:cancel")
    state = SimpleNamespace(clear=AsyncMock())

    await cancel_flow(callback, state)

    state.clear.assert_awaited_once()
    callback.answer.assert_awaited_once_with("Сценарий отменён")
    callback.message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_cancel_command_clears_fsm_and_confirms_cancellation() -> None:
    message = SimpleNamespace(answer=AsyncMock())
    state = SimpleNamespace(clear=AsyncMock())

    await cancel(message, state)

    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once()
    assert message.answer.await_args.args[0] == "Текущий сценарий отменён."
