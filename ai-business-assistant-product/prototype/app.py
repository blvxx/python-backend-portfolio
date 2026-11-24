from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="SME AI Business Assistant — deterministic demo",
    version="0.1.0",
    description="Read-only synthetic demo. No LLM or production integrations.",
)

AS_OF = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
# Public fixture tokens are for local demo only; never use them outside this repository.
DEMO_TOKENS = {"demo-alpha-token": "demo-alpha", "demo-beta-token": "demo-beta"}
INVOICES = {
    "demo-alpha": [
        {"id": "INV-A-1001", "customer": "Northwind Demo", "due_date": "2026-11-20", "amount": "125000.00", "currency": "RUB", "status": "unpaid"},
        {"id": "INV-A-1002", "customer": "Contoso Demo", "due_date": "2026-11-28", "amount": "54000.00", "currency": "RUB", "status": "unpaid"},
        {"id": "INV-A-1003", "customer": "Fabrikam Demo", "due_date": "2026-11-15", "amount": "800.00", "currency": "EUR", "status": "paid"},
        {"id": "INV-A-1004", "customer": "Adventure Demo", "due_date": "2026-11-22", "amount": "91000.00", "currency": "RUB", "status": "paid"},
    ],
    "demo-beta": [
        {"id": "INV-B-2001", "customer": "Tailspin Demo", "due_date": "2026-11-18", "amount": "34000.00", "currency": "RUB", "status": "unpaid"},
    ],
}

class AssistantQuery(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    tenant_id: Literal["demo-alpha", "demo-beta"]

class Evidence(BaseModel):
    source: str
    record_ids: list[str]
    as_of: datetime

class AssistantAnswer(BaseModel):
    intent: str
    answer: str
    status: Literal["answered", "clarification_required", "unsupported"]
    read_only: Literal[True] = True
    evidence: list[Evidence] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

@app.get("/health")
def health():
    return {"status": "ok", "mode": "deterministic-demo"}

@app.post("/v1/assistant/query", response_model=AssistantAnswer)
def query_assistant(
    request: AssistantQuery,
    authorization: str | None = Header(default=None),
):
    # The demo token-to-tenant mapping is public fixture data, not real authentication.
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Bearer token is required")
    token = authorization.removeprefix("Bearer ").strip()
    authenticated_tenant = DEMO_TOKENS.get(token)
    if not authenticated_tenant:
        raise HTTPException(status_code=403, detail="Invalid demo token")
    if authenticated_tenant != request.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant context mismatch")

    text = request.question.casefold()
    records = INVOICES[request.tenant_id]

    if any(term in text for term in ("оплати", "переведи", "отметь", "измени статус", "закрой счёт")):
        return AssistantAnswer(
            intent="unsupported_write",
            answer="Эта версия работает только в режиме чтения и не выполняет платежи или изменения счетов.",
            status="unsupported",
            warnings=["Write operations are disabled in the MVP."],
        )

    if any(term in text for term in ("неоплачен", "должны оплатить", "дебитор")):
        rows = [row for row in records if row["status"] == "unpaid"]
        if not rows:
            answer = "Неоплаченных счетов в демонстрационных данных не найдено."
        else:
            totals: dict[str, Decimal] = {}
            for row in rows:
                totals[row["currency"]] = totals.get(row["currency"], Decimal("0")) + Decimal(row["amount"])
            formatted = ", ".join(f"{currency} {amount:.2f}" for currency, amount in sorted(totals.items()))
            answer = f"Найдено неоплаченных счетов: {len(rows)}. Сумма по валютам: {formatted}."
        return AssistantAnswer(
            intent="unpaid_invoices",
            answer=answer,
            status="answered",
            evidence=[Evidence(source="synthetic_invoice_fixture", record_ids=[r["id"] for r in rows], as_of=AS_OF)],
            warnings=["Синтетические демонстрационные данные; не использовать для финансовых решений."],
        )

    if any(term in text for term in ("выруч", "оплачен", "поступлен", "заработ")):
        if not any(term in text for term in ("за весь", "за период", "с ", "по ", "ноябрь", "2026")):
            return AssistantAnswer(
                intent="paid_revenue",
                answer="Укажите период: дату начала и дату окончания.",
                status="clarification_required",
                warnings=["Для полноценного расчёта требуется согласованное определение выручки и диапазон дат."],
            )
        rows = [row for row in records if row["status"] == "paid"]
        totals: dict[str, Decimal] = {}
        for row in rows:
            totals[row["currency"]] = totals.get(row["currency"], Decimal("0")) + Decimal(row["amount"])
        formatted = ", ".join(f"{currency} {amount:.2f}" for currency, amount in sorted(totals.items()))
        return AssistantAnswer(
            intent="paid_revenue",
            answer=f"Сумма счетов со статусом paid в демонстрационном наборе: {formatted}.",
            status="answered",
            evidence=[Evidence(source="synthetic_invoice_fixture", record_ids=[r["id"] for r in rows], as_of=AS_OF)],
            warnings=["Это сумма оплаченных счетов в demo fixture, не бухгалтерская выручка."],
        )

    return AssistantAnswer(
        intent="unknown",
        answer="Пока доступны вопросы о неоплаченных счетах и сумме оплаченных счетов. Уточните запрос.",
        status="unsupported",
    )
