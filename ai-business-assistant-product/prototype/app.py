import os
from datetime import date, datetime, timezone
from decimal import Decimal
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from planner import (
    DeterministicIntentPlanner,
    OpenAIIntentPlanner,
    PlannerError,
)

app = FastAPI(
    title="SME AI Business Assistant — deterministic demo",
    version="0.1.0",
    description="Read-only synthetic demo with deterministic or optional LLM intent planning. No production integrations.",
)

AS_OF = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
# Public fixture tokens are for local demo only; never use them outside this repository.
DEMO_TOKENS = {"demo-alpha-token": "demo-alpha", "demo-beta-token": "demo-beta"}
INVOICES = {
    "demo-alpha": [
        {"id": "INV-A-1001", "customer": "Northwind Demo", "invoice_date": "2026-11-01", "due_date": "2026-11-20", "amount": "125000.00", "currency": "RUB", "status": "unpaid"},
        {"id": "INV-A-1002", "customer": "Contoso Demo", "invoice_date": "2026-11-02", "due_date": "2026-11-28", "amount": "54000.00", "currency": "RUB", "status": "unpaid"},
        {"id": "INV-A-1003", "customer": "Fabrikam Demo", "invoice_date": "2026-11-03", "due_date": "2026-11-15", "amount": "800.00", "currency": "EUR", "status": "paid"},
        {"id": "INV-A-1004", "customer": "Adventure Demo", "invoice_date": "2026-11-04", "due_date": "2026-11-22", "amount": "91000.00", "currency": "RUB", "status": "paid"},
    ],
    "demo-beta": [
        {"id": "INV-B-2001", "customer": "Tailspin Demo", "invoice_date": "2026-11-01", "due_date": "2026-11-18", "amount": "34000.00", "currency": "RUB", "status": "unpaid"},
    ],
}

class QueryPeriod(BaseModel):
    start: date = Field(alias="from")
    end: date = Field(alias="to")

class AssistantQuery(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    tenant_id: Literal["demo-alpha", "demo-beta"]
    period: QueryPeriod | None = None

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

@lru_cache(maxsize=1)
def get_planner():
    mode = os.getenv("ASSISTANT_PLANNER_MODE", "deterministic").strip().casefold()
    if mode == "deterministic":
        return DeterministicIntentPlanner()
    if mode == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL")
        if not api_key or not model:
            raise RuntimeError(
                "OPENAI_API_KEY and OPENAI_MODEL are required when ASSISTANT_PLANNER_MODE=openai"
            )
        return OpenAIIntentPlanner(api_key=api_key, model=model)
    raise RuntimeError("ASSISTANT_PLANNER_MODE must be 'deterministic' or 'openai'")

@app.get("/health")
def health():
    try:
        get_planner()
    except RuntimeError:
        return {"status": "degraded", "mode": os.getenv("ASSISTANT_PLANNER_MODE", "deterministic")}
    return {"status": "ok", "mode": os.getenv("ASSISTANT_PLANNER_MODE", "deterministic")}

@app.post("/v1/assistant/query", response_model=AssistantAnswer)
async def query_assistant(
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

    try:
        plan = await get_planner().plan(
            question=request.question,
            period_supplied=request.period is not None,
        )
    except (PlannerError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="Intent planner is unavailable") from exc

    records = INVOICES[request.tenant_id]

    if plan.intent == "unsupported_write":
        return AssistantAnswer(
            intent="unsupported_write",
            answer="Эта версия работает только в режиме чтения и не выполняет платежи или изменения счетов.",
            status="unsupported",
            warnings=["Write operations are disabled in the MVP."],
        )

    if plan.intent == "unpaid_invoices":
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

    if plan.intent == "paid_revenue":
        period = request.period
        if (
            period is None
            and plan.date_from
            and plan.date_to
            and plan.date_from in request.question
            and plan.date_to in request.question
        ):
            try:
                period = QueryPeriod(
                    start=date.fromisoformat(plan.date_from),
                    end=date.fromisoformat(plan.date_to),
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="Planner returned an invalid date range") from exc

        if period is None or (plan.requires_clarification and request.period is None):
            return AssistantAnswer(
                intent="paid_revenue",
                answer=plan.clarification_question or "Укажите период: дату начала и дату окончания.",
                status="clarification_required",
                warnings=["Для расчёта требуется диапазон дат и согласованное определение выручки."],
            )
        if period.start > period.end:
            raise HTTPException(status_code=422, detail="Period start must not be after period end")
        rows = [
            row for row in records
            if row["status"] == "paid"
            and period.start <= date.fromisoformat(row["invoice_date"]) <= period.end
        ]
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
        warnings=[plan.reason],
    )
