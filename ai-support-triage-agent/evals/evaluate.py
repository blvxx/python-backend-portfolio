"""Small live-model regression evaluator; requires an explicit API key."""

import asyncio
import json
import os
from pathlib import Path

from src.agent import CaseTriageAgent
from src.knowledge import KnowledgeBase
from src.provider import OpenAITriageProvider


async def main() -> None:
    root = Path(__file__).resolve().parents[1]
    cases = json.loads((root / "evals" / "cases.json").read_text(encoding="utf-8"))
    knowledge = KnowledgeBase.from_json(root / "knowledge_base" / "runbooks.json")
    provider = OpenAITriageProvider(
        api_key=os.environ["OPENAI_API_KEY"],
        model=os.getenv("OPENAI_MODEL", "gpt-6.2-astra"),
    )
    agent = CaseTriageAgent(knowledge, provider)

    passed = 0
    grounded = 0
    rows = []
    for case in cases:
        result = await agent.triage(case["report"])
        severity_ok = result.severity.value == case["expected_severity"]
        category_ok = result.category.value == case["expected_category"]
        evidence_ok = set(case["required_evidence"]).issubset(result.evidence_ids)
        passed += int(severity_ok and category_ok)
        grounded += int(evidence_ok)
        rows.append(
            {
                "case_id": case["case_id"],
                "severity_ok": severity_ok,
                "category_ok": category_ok,
                "evidence_ok": evidence_ok,
                "escalation_required": result.escalation_required,
            }
        )

    summary = {
        "cases": len(cases),
        "severity_category_accuracy": passed / len(cases),
        "required_evidence_recall": grounded / len(cases),
        "results": rows,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["severity_category_accuracy"] < 0.75 or summary["required_evidence_recall"] < 1.0:
        raise SystemExit("Evaluation did not meet its configured threshold")


if __name__ == "__main__":
    asyncio.run(main())
