import pytest

from src.application.enquiries import (
    CreateEnquiry,
    EnquiryPolicyError,
    EnquiryService,
)


class FakeEnquiryRepository:
    def __init__(self) -> None:
        self.saved: dict[str, object] | None = None

    async def add_lead(self, **kwargs: object) -> int:
        self.saved = kwargs
        return 42


def valid_command(**overrides: object) -> CreateEnquiry:
    values: dict[str, object] = {
        "telegram_user_id": 12345,
        "username": "demo_user",
        "customer_name": " Demo Customer ",
        "contact": " demo@example.com ",
        "service": " Приём заявок ",
        "details": " Нужна автоматизация обработки обращений. ",
        "consent_given": True,
    }
    values.update(overrides)
    return CreateEnquiry(**values)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_submit_valid_enquiry_normalizes_fields_and_persists() -> None:
    repository = FakeEnquiryRepository()
    service = EnquiryService(repository)

    lead_id = await service.submit(valid_command())

    assert lead_id == 42
    assert repository.saved == {
        "telegram_user_id": 12345,
        "username": "demo_user",
        "customer_name": "Demo Customer",
        "contact": "demo@example.com",
        "service": "Приём заявок",
        "details": "Нужна автоматизация обработки обращений.",
        "admin_chat_id": None,
        "idempotency_key": None,
    }


@pytest.mark.asyncio
async def test_submit_rejects_missing_consent_without_persisting() -> None:
    repository = FakeEnquiryRepository()

    with pytest.raises(EnquiryPolicyError, match="согласие"):
        await EnquiryService(repository).submit(valid_command(consent_given=False))

    assert repository.saved is None


@pytest.mark.asyncio
async def test_submit_rejects_invalid_contact_without_persisting() -> None:
    repository = FakeEnquiryRepository()

    with pytest.raises(EnquiryPolicyError, match="телефона или email"):
        await EnquiryService(repository).submit(valid_command(contact="invalid"))

    assert repository.saved is None


@pytest.mark.asyncio
async def test_submit_rejects_short_details_without_persisting() -> None:
    repository = FakeEnquiryRepository()

    with pytest.raises(EnquiryPolicyError, match="10 символов"):
        await EnquiryService(repository).submit(valid_command(details="short"))

    assert repository.saved is None


@pytest.mark.asyncio
async def test_submit_rejects_invalid_identity_and_service() -> None:
    repository = FakeEnquiryRepository()
    service = EnquiryService(repository)

    with pytest.raises(EnquiryPolicyError, match="отправителя"):
        await service.submit(valid_command(telegram_user_id=0))

    with pytest.raises(EnquiryPolicyError, match="категорию"):
        await service.submit(valid_command(service="  "))

    assert repository.saved is None


@pytest.mark.asyncio
async def test_submit_normalizes_empty_username_to_none() -> None:
    repository = FakeEnquiryRepository()

    await EnquiryService(repository).submit(valid_command(username="  "))

    assert repository.saved is not None
    assert repository.saved["username"] is None



@pytest.mark.asyncio
async def test_submit_normalizes_and_passes_idempotency_key() -> None:
    repository = FakeEnquiryRepository()

    await EnquiryService(repository).submit(
        valid_command(idempotency_key="  telegram:123:456  ")
    )

    assert repository.saved is not None
    assert repository.saved["idempotency_key"] == "telegram:123:456"


@pytest.mark.asyncio
async def test_submit_rejects_blank_or_oversized_idempotency_key() -> None:
    repository = FakeEnquiryRepository()
    service = EnquiryService(repository)

    with pytest.raises(EnquiryPolicyError, match="ключ повторной обработки"):
        await service.submit(valid_command(idempotency_key="  "))

    with pytest.raises(EnquiryPolicyError, match="ключ повторной обработки"):
        await service.submit(valid_command(idempotency_key="x" * 201))

    assert repository.saved is None
