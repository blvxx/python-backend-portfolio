# 06 — AI assistant evaluation plan

> Evaluation set and thresholds below are designed for a future LLM-connected version. No live-model performance score is claimed by this deterministic prototype.

## Evaluation dimensions

| Dimension | Definition | Measurement |
|---|---|---|
| Intent accuracy | Correct skill or clarification selected | Exact match on reviewed cases |
| Parameter extraction | Period, currency and filter extracted correctly | Slot-level precision/recall |
| Groundedness | Factual statements trace to skill evidence | Supported-claim ratio |
| Numeric correctness | Amounts and counts match deterministic source result | Exact numeric assertion |
| Permission safety | No unauthorised data returned | Cross-tenant / role negative tests |
| Refusal quality | Unsupported requests are declined correctly | Reviewed refusal rubric |
| Clarification quality | Missing material inputs are requested | Required clarification recall |
| Prompt-injection resistance | Untrusted instructions do not override policy | Adversarial pass rate |
| Latency and cost | End-to-end time and cost | p50/p95 latency, cost per task |

## Proposed release gates (targets, not measured results)

- 100% pass on tenant-isolation and forbidden-action tests.
- 100% exact numeric correctness for supported deterministic invoice/revenue queries.
- At least 95% groundedness on the reviewed in-scope evaluation set.
- At least 90% correct intent selection on reviewed supported prompts.
- 100% escalation for critical evidence/permission/source-integrity failures.
- p95 latency and cost meet product-approved budgets.

Security gates are absolute for tested cases; an aggregate score must not hide a single cross-tenant disclosure.

## Synthetic evaluation categories

Clear invoice query; missing period; paid revenue with explicit range; multiple currencies; unauthorised tenant/role; invoice mutation; empty result; stale source; conflicting sources; prompt injection in user question; prompt injection in retrieved content; unsupported tax advice; ambiguous accounting term; source timeout; malformed/long query.

## Human review rubric

Reviewers score factual correctness, evidence quality, completeness, clarity, safe uncertainty handling and permission compliance. Record disagreement and adjudication. Version the evaluation set; production-like cases must be de-identified and approved before use.

## Drift and change management

Re-run the evaluation set when changing model, prompt, system policy, skill schema, retrieval data or source definition. Compare per-category failures, not only total accuracy. Roll back a model/prompt revision when a critical safety gate regresses.
