"""Application service for validating and creating business enquiries."""

from dataclasses import dataclass
from typing import Protocol

from src.validation import validate_contact, validate_details


class EnquiryPolicyError(ValueError):
    """Raised when an enquiry violates an application-level rule."""


@dataclass(frozen=True, slots=True)
class CreateEnquiry:
    """Input required to create an enquiry, independent of Telegram types."""

    telegram_user_id: int
    username: str | None
    customer_name: str
    contact: str
    service: str
    details: str
    consent_given: bool
    admin_chat_id: int | None = None
    idempotency_key: str | None = None


class EnquiryRepository(Protocol):
    """Persistence boundary required by the application service."""

    async def add_lead(
        self,
        *,
        telegram_user_id: int,
        username: str | None,
        customer_name: str,
        contact: str,
        service: str,
        details: str,
        admin_chat_id: int | None = None,
        idempotency_key: str | None = None,
    ) -> int:
        """Persist one enquiry and return its generated identifier."""
        ...


class EnquiryService:
    """Enforce enquiry policy and coordinate durable creation."""

    def __init__(self, repository: EnquiryRepository) -> None:
        self._repository = repository

    async def submit(self, command: CreateEnquiry) -> int:
        """Validate an enquiry and persist it through the repository boundary."""
        if not command.consent_given:
            raise EnquiryPolicyError(
                "Нужно подтвердить согласие перед отправкой заявки."
            )

        if command.telegram_user_id <= 0:
            raise EnquiryPolicyError("Не удалось определить отправителя заявки.")

        customer_name = command.customer_name.strip()
        if not customer_name or len(customer_name) > 256:
            raise EnquiryPolicyError("Не удалось определить корректное имя отправителя.")

        contact = command.contact.strip()
        if not validate_contact(contact):
            raise EnquiryPolicyError(
                "Укажите корректный номер телефона или email для обратной связи."
            )

        service = command.service.strip()
        if not service or len(service) > 100:
            raise EnquiryPolicyError("Выберите корректную категорию обращения.")

        details = command.details.strip()
        valid, error = validate_details(details)
        if not valid:
            raise EnquiryPolicyError(error)

        username = (command.username or "").strip() or None
        if username is not None and len(username) > 64:
            raise EnquiryPolicyError("Некорректное имя пользователя Telegram.")

        idempotency_key = command.idempotency_key
        if idempotency_key is not None:
            idempotency_key = idempotency_key.strip()
            if not idempotency_key or len(idempotency_key) > 200:
                raise EnquiryPolicyError("Некорректный ключ повторной обработки заявки.")

        return await self._repository.add_lead(
            telegram_user_id=command.telegram_user_id,
            username=username,
            customer_name=customer_name,
            contact=contact,
            service=service,
            details=details,
            admin_chat_id=command.admin_chat_id,
            idempotency_key=idempotency_key,
        )
