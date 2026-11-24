"""Command-line entry point for the support triage agent."""

import argparse
import asyncio
import json
import os
from pathlib import Path

from src.agent import CaseTriageAgent
from src.knowledge import KnowledgeBase
from src.provider import OpenAITriageProvider


async def _run(report: str) -> None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required; configure it through your secret manager.")
    model = os.getenv("OPENAI_MODEL", "gpt-6.2-astra").strip()
    root = Path(__file__).resolve().parents[1]
    knowledge = KnowledgeBase.from_json(root / "knowledge_base" / "runbooks.json")
    provider = OpenAITriageProvider(api_key=api_key, model=model)
    result = await CaseTriageAgent(knowledge, provider).triage(report)
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve runbook evidence and triage an incident.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="Incident description (do not include credentials or PII).")
    group.add_argument("--file", type=Path, help="UTF-8 file containing a synthetic incident report.")
    args = parser.parse_args()
    report = args.text if args.text is not None else args.file.read_text(encoding="utf-8")
    asyncio.run(_run(report))


if __name__ == "__main__":
    main()
