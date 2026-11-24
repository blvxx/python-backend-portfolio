# 07 — Prioritised delivery backlog

| ID | Priority | User story / task | Definition of done |
|---|---:|---|---|
| SME-01 | P0 | Resolve authenticated tenant and actor | Server-side identity context; deny by default; cross-tenant tests pass |
| SME-02 | P0 | Query unpaid invoices | Typed skill contract; source timestamp; evidence IDs; positive and negative tests |
| SME-03 | P0 | Query paid revenue | Approved metric definition; date range; separate currency groups; deterministic aggregation |
| SME-04 | P0 | Keep MVP read-only | No write tools/routes; mutation requests safely refused |
| SME-05 | P0 | Add grounded answer validator | Reject unknown evidence IDs and unsupported numeric claims |
| SME-06 | P0 | Handle missing or stale data | Clarification, freshness warning and escalation are tested |
| SME-07 | P1 | Add LLM intent and slot extraction | Model output constrained by schema; no direct tool execution |
| SME-08 | P1 | Add prompt-injection regression set | User/retrieved text cannot override policy or permission boundary |
| SME-09 | P1 | Add model evaluation harness | Versioned dataset, per-category report, human review and regression thresholds |
| SME-10 | P1 | Add audit and observability | Request ID, skill, outcome, latency and safe error metadata |
| SME-11 | P2 | Add a new approved skill | Contract, permission matrix, tests, evidence and rollback documented |
| SME-12 | P2 | Integrate a real accounting/banking source | Approved API contract, sandbox credentials, rate limits, reconciliation and security review |

## MVP release checklist

Must requirements have traceable positive and negative tests; tenant and role permissions are enforced server-side; numeric values originate from deterministic source calculations; every answer carries source evidence and freshness metadata; unsupported requests are refused or escalated; no write-capable tool is available; logs are reviewed for sensitive data; open risks are accepted by the product owner.
