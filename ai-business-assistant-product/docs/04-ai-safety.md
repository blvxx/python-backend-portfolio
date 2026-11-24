# 04 — AI behavior, risks and guardrails

## Core design decision

The LLM is a language interface and planner within a constrained system. It is not an authority for identity, permissions, accounting truth or execution of business operations.

The backend owns authenticated actor and tenant context, authorization decisions, skill allow-list and parameter validation, source-system access, business calculations, evidence validation, audit metadata and escalation policy.

## Guardrails and verification

| ID | Risk | Control | Verification |
|---|---|---|---|
| AI-01 | Hallucinated amounts or invoice facts | Facts originate from skill output; no free-form numeric completion | Inject unsupported values into model output and assert rejection |
| AI-02 | Cross-tenant disclosure | Tenant comes from trusted auth context; every query is tenant-scoped | Cross-tenant negative tests |
| AI-03 | Prompt injection | User/retrieved content is untrusted; policy and tool permissions are external | Adversarial prompt tests |
| AI-04 | Unsafe write action | Read-only tool allow-list; no mutation tool in MVP | Attempt payment/status-change requests |
| AI-05 | Ambiguous metric definition | Versioned metric dictionary and clarification behavior | Missing/ambiguous period and definition tests |
| AI-06 | Stale or partial source | Data freshness metadata and completeness checks | Stale timestamp and partial-load scenarios |
| AI-07 | Currency aggregation error | Group currencies separately; conversion only with approved FX rule | Multi-currency fixtures |
| AI-08 | Sensitive data in logs | Data minimisation, redaction and retention policy | Inspect logs for prohibited fields |
| AI-09 | Unsupported citations | Evidence IDs must match returned records | Unknown-source and fabricated-ID tests |
| AI-10 | Overconfident answer | Confidence is not treated as truth; uncertain results escalate | Low-evidence scenarios |

## LLM planner boundary

The optional OpenAI Responses API component returns only a typed intent plan: allowed intent, explicit ISO date boundaries, clarification status and a short reason. It is not given any tool definitions or business records. It cannot access the tenant, invoice fixtures, database, external APIs or write operations.

The API performs authentication/tenant validation before calling the planner. After parsing, the backend validates the intent against the allow-list, validates date boundaries and executes the deterministic skill. A planner error returns a service-unavailable response; it does not silently invent a business answer. The default deterministic planner is used in CI.

## Tool and skill contract

Each skill declares stable ID/version, purpose and allowed roles, required parameters, permitted data sources, read/write classification, output schema, evidence format, error types, retry policy and maximum data scope.

The router selects only allow-listed skills. The model may propose an intent, but the backend validates it against actor permissions and the skill contract.

## Hallucination and answer validation

Before rendering a response:
1. Validate the skill response against a typed schema.
2. Check tenant scope and permission context.
3. Check source timestamps and freshness.
4. Recalculate totals in deterministic service code, not free-form model text.
5. Verify evidence IDs against returned records.
6. Reject values not supported by evidence.
7. If a mandatory check fails, return a safe fallback or escalation.

## Human-in-the-loop

Human review is mandatory for ambiguous accounting definitions, conflicting sources, data-quality failures, unsupported/high-impact requests, any future write-capable skill and customer-facing communications that could create legal/financial commitments.

## Risk acceptance

No production launch should occur until security, privacy, finance definitions, model-provider retention, identity integration, monitoring, red-team testing and incident ownership have been approved.
