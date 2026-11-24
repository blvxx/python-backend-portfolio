from src.agent import CaseTriageAgent
from src.knowledge import KnowledgeBase
from src.schemas import Category, Severity, SupportTriageResult


class FakeProvider:
    def __init__(self, result: SupportTriageResult) -> None:
        self.result = result
        self.context = ""

    async def analyze(self, *, incident_report: str, retrieved_context: str):
        self.context = retrieved_context
        return self.result.model_copy(deep=True)


def result(
    *,
    severity: Severity = Severity.HIGH,
    category: Category = Category.AVAILABILITY,
    evidence_ids: list[str] | None = None,
    read_only_checks: list[str] | None = None,
    confidence: float = 0.9,
    escalate: bool = False,
) -> SupportTriageResult:
    return SupportTriageResult(
        severity=severity,
        category=category,
        summary="The upstream service may be unavailable.",
        root_cause_hypotheses=["The upstream listener may not be accepting connections."],
        read_only_checks=read_only_checks or ["Inspect recent Nginx error-log entries."],
        customer_reply_draft="We are investigating the upstream connectivity issue.",
        escalation_required=escalate,
        confidence=confidence,
        evidence_ids=evidence_ids or ["KB-NGINX-502"],
    )


def knowledge_base() -> KnowledgeBase:
    from pathlib import Path

    return KnowledgeBase.from_json(
        Path(__file__).resolve().parents[1] / "knowledge_base" / "runbooks.json"
    )


async def test_retrieval_context_is_passed_to_provider_and_valid_source_is_kept() -> None:
    provider = FakeProvider(result())
    agent = CaseTriageAgent(knowledge_base(), provider)

    output = await agent.triage(
        "Nginx returns 502 Bad Gateway. The upstream connection is refused."
    )

    assert "KB-NGINX-502" in provider.context
    assert output.evidence_ids == ["KB-NGINX-502"]
    assert output.escalation_required is False


async def test_unretrieved_source_id_is_removed_and_escalation_is_required() -> None:
    provider = FakeProvider(result(evidence_ids=["KB-NGINX-502", "KB-FAKE-999"]))
    agent = CaseTriageAgent(knowledge_base(), provider)

    output = await agent.triage("Nginx 502 upstream connection refused.")

    assert output.evidence_ids == ["KB-NGINX-502"]
    assert output.escalation_required is True


async def test_state_changing_suggestion_is_removed() -> None:
    provider = FakeProvider(
        result(read_only_checks=[
            "Restart the service to restore availability.",
            "Inspect recent Nginx error-log entries.",
        ])
    )
    agent = CaseTriageAgent(knowledge_base(), provider)

    output = await agent.triage("Nginx returns 502 Bad Gateway from its upstream.")

    assert len(output.read_only_checks) == 2
    assert all("restart" not in check.lower() for check in output.read_only_checks)
    assert output.escalation_required is True


async def test_missing_knowledge_evidence_forces_escalation() -> None:
    provider = FakeProvider(
        result(
            severity=Severity.MEDIUM,
            evidence_ids=[],
            confidence=0.8,
            category=Category.UNKNOWN,
        )
    )
    agent = CaseTriageAgent(knowledge_base(), provider)

    output = await agent.triage(
        "ZXQ9481 VVMNN2048 QPQW0098 opaque token sequence."
    )

    assert output.escalation_required is True
    assert output.evidence_ids == []


async def test_low_confidence_and_critical_severity_require_escalation() -> None:
    provider = FakeProvider(
        result(severity=Severity.CRITICAL, confidence=0.95)
    )
    output = await CaseTriageAgent(knowledge_base(), provider).triage(
        "Nginx 502 Bad Gateway. The upstream connection is refused."
    )
    assert output.escalation_required is True


async def test_short_or_oversized_incident_is_rejected() -> None:
    from src.agent import InvalidIncidentReport

    agent = CaseTriageAgent(knowledge_base(), FakeProvider(result()))
    try:
        await agent.triage("short")
    except InvalidIncidentReport:
        pass
    else:
        raise AssertionError("Short incident report must be rejected")
