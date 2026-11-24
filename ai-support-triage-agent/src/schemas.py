"""Typed input and output contracts for support triage."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Category(StrEnum):
    AVAILABILITY = "availability"
    PERFORMANCE = "performance"
    DATABASE = "database"
    NETWORK = "network"
    DEPLOYMENT = "deployment"
    SECURITY = "security"
    UNKNOWN = "unknown"


class SupportTriageResult(BaseModel):
    """Strict machine-readable support triage result."""

    model_config = ConfigDict(extra="forbid")

    severity: Severity
    category: Category
    summary: str
    root_cause_hypotheses: list[str]
    read_only_checks: list[str]
    customer_reply_draft: str
    escalation_required: bool
    confidence: float
    evidence_ids: list[str]
