import asyncio
from types import SimpleNamespace

import pytest

from planner import (
    DeterministicIntentPlanner,
    IntentPlan,
    OpenAIIntentPlanner,
    PlannerError,
)


def test_deterministic_planner_prioritises_write_refusal():
    plan = asyncio.run(
        DeterministicIntentPlanner().plan(
            question="Покажи выручку и отметь счёт оплаченным",
            period_supplied=True,
        )
    )
    assert plan.intent == "unsupported_write"


def test_deterministic_planner_requests_missing_revenue_period():
    plan = asyncio.run(
        DeterministicIntentPlanner().plan(
            question="Сколько мы заработали?",
            period_supplied=False,
        )
    )
    assert plan.intent == "paid_revenue"
    assert plan.requires_clarification is True
    assert plan.date_from is None
    assert plan.date_to is None


def test_deterministic_planner_extracts_only_explicit_iso_date_range():
    plan = asyncio.run(
        DeterministicIntentPlanner().plan(
            question="Покажи выручку с 2026-11-01 по 2026-11-30",
            period_supplied=False,
        )
    )
    assert plan.intent == "paid_revenue"
    assert plan.requires_clarification is False
    assert plan.date_from == "2026-11-01"
    assert plan.date_to == "2026-11-30"


def test_structured_period_from_api_resolves_period_clarification():
    plan = asyncio.run(
        DeterministicIntentPlanner().plan(
            question="Покажи выручку",
            period_supplied=True,
        )
    )
    assert plan.intent == "paid_revenue"
    assert plan.requires_clarification is False


def test_openai_planner_uses_structured_output_and_no_tools():
    expected = IntentPlan(
        intent="paid_revenue",
        date_from="2026-11-01",
        date_to="2026-11-30",
        requires_clarification=False,
        clarification_question=None,
        reason="Explicit date range was present.",
    )

    class FakeResponses:
        def __init__(self):
            self.kwargs = None

        async def parse(self, **kwargs):
            self.kwargs = kwargs
            return SimpleNamespace(status="completed", output_parsed=expected)

    fake_responses = FakeResponses()
    fake_client = SimpleNamespace(responses=fake_responses)
    planner = OpenAIIntentPlanner(api_key="not-used-in-test", model="mock-model", client=fake_client)

    actual = asyncio.run(planner.plan(question="Revenue from 2026-11-01 to 2026-11-30", period_supplied=False))

    assert actual == expected
    assert fake_responses.kwargs["text_format"] is IntentPlan
    assert "tools" not in fake_responses.kwargs
    assert "do not access invoice data" in fake_responses.kwargs["input"][0]["content"]


def test_openai_planner_rejects_incomplete_model_response():
    class FakeResponses:
        async def parse(self, **kwargs):
            return SimpleNamespace(status="incomplete", output_parsed=None)

    planner = OpenAIIntentPlanner(
        api_key="not-used-in-test",
        model="mock-model",
        client=SimpleNamespace(responses=FakeResponses()),
    )
    with pytest.raises(PlannerError):
        asyncio.run(planner.plan(question="Покажи выручку", period_supplied=False))
