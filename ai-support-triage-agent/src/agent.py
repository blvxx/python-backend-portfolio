"""Orchestrator for retrieval-grounded and human-reviewed support triage."""

import hashlib
import logging
import re

from src.knowledge import KnowledgeBase
from src.provider import TriageProvider
from src.schemas import Severity, SupportTriageResult

logger = logging.getLogger(__name__)

_STATE_CHANGING_PATTERN = re.compile(
    r"\b(restart|reboot|shutdown|stop service|delete|drop table|truncate|rm\s+-|"
    r"kill\s+-|chmod|chown|kubectl\s+delete|docker\s+rm|terraform\s+apply|"
    r"deploy|apply\s+-f|rotate credentials)\b",
    flags=re.IGNORECASE,
)


class InvalidIncidentReport(ValueError):
    """Incident report is outside the accepted input contract."""


class CaseTriageAgent:
    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        provider: TriageProvider,
        *,
        retrieval_limit: int = 4,
    ) -> None:
        self._knowledge_base = knowledge_base
        self._provider = provider
        self._retrieval_limit = max(1, min(retrieval_limit, 8))

    async def triage(self, incident_report: str) -> SupportTriageResult:
        report = incident_report.strip()
        if len(report) < 20 or len(report) > 8000:
            raise InvalidIncidentReport(
                "Incident report must contain between 20 and 8000 characters"
            )

        documents = self._knowledge_base.search(report, limit=self._retrieval_limit)
        context = "\n\n".join(
            (
                f"SOURCE_ID: {document.source_id}\n"
                f"TITLE: {document.title}\n"
                f"PRODUCT: {document.product}\n"
                f"FACTS:\n- " + "\n- ".join(document.facts)
                + "\nREAD-ONLY CHECKS:\n- "
                + "\n- ".join(document.read_only_checks)
                + "\nESCALATION NOTES:\n- "
                + "\n- ".join(document.escalation_notes)
            )
            for document in documents
        )
        result = await self._provider.analyze(
            incident_report=report,
            retrieved_context=context or "No matching runbook evidence was found.",
        )

        allowed_ids = {document.source_id for document in documents}
        invalid_ids = set(result.evidence_ids) - allowed_ids
        result.evidence_ids = [
            source_id for source_id in result.evidence_ids if source_id in allowed_ids
        ]

        unsafe_checks = [
            check for check in result.read_only_checks
            if _STATE_CHANGING_PATTERN.search(check)
        ]
        if unsafe_checks:
            result.read_only_checks = [
                check for check in result.read_only_checks
                if not _STATE_CHANGING_PATTERN.search(check)
            ]
            result.escalation_required = True
            result.read_only_checks.append(
                "A state-changing suggestion was removed; use the approved change process."
            )

        if (
            not documents
            or not result.evidence_ids
            or invalid_ids
            or result.confidence < 0.65
            or result.severity == Severity.CRITICAL
        ):
            result.escalation_required = True

        case_fingerprint = hashlib.sha256(report.encode("utf-8")).hexdigest()[:12]
        logger.info(
            "Support triage completed",
            extra={
                "case_fingerprint": case_fingerprint,
                "severity": result.severity.value,
                "category": result.category.value,
                "confidence": result.confidence,
                "evidence_count": len(result.evidence_ids),
                "escalation_required": result.escalation_required,
            },
        )
        return result
