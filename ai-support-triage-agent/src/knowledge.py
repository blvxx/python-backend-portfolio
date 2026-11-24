"""Small local runbook retrieval layer with stable evidence identifiers."""

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    source_id: str
    title: str
    product: str
    keywords: tuple[str, ...]
    facts: tuple[str, ...]
    read_only_checks: tuple[str, ...]
    escalation_notes: tuple[str, ...]


def _tokens(value: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[a-zA-Z0-9_./:-]{2,}", value)
        if token.lower() not in {"the", "and", "for", "with", "from", "this", "that"}
    }


class KnowledgeBase:
    """Read-only keyword retriever. No external systems or customer data are queried."""

    def __init__(self, documents: list[KnowledgeDocument]) -> None:
        self._documents = documents
        self._by_id = {document.source_id: document for document in documents}

    @classmethod
    def from_json(cls, path: str | Path) -> "KnowledgeBase":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        documents = [
            KnowledgeDocument(
                source_id=item["source_id"],
                title=item["title"],
                product=item["product"],
                keywords=tuple(item["keywords"]),
                facts=tuple(item["facts"]),
                read_only_checks=tuple(item["read_only_checks"]),
                escalation_notes=tuple(item["escalation_notes"]),
            )
            for item in payload
        ]
        return cls(documents)

    def search(self, query: str, *, limit: int = 4) -> list[KnowledgeDocument]:
        query_tokens = _tokens(query)
        scored: list[tuple[int, str, KnowledgeDocument]] = []
        for document in self._documents:
            indexed = _tokens(
                " ".join(
                    (document.title, document.product, *document.keywords, *document.facts)
                )
            )
            score = len(query_tokens & indexed)
            if score >= 2:
                scored.append((score, document.source_id, document))
        scored.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in scored[: max(1, min(limit, 8))]]

    def get(self, source_id: str) -> KnowledgeDocument | None:
        return self._by_id.get(source_id)
