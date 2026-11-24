# 02 — Business and functional requirements

## Business requirements

| ID | Requirement | Priority | Acceptance outcome |
|---|---|---:|---|
| BR-01 | Let an authorised SME user query approved invoice information in natural language | Must | In-scope invoice queries return records from the current tenant only |
| BR-02 | Let an authorised user ask for paid revenue over a defined period | Must | Answer uses approved revenue definition and requested period |
| BR-03 | Make answers traceable to source data | Must | Every numeric answer returns evidence IDs and data timestamp |
| BR-04 | Avoid unsupported or ambiguous answers | Must | Assistant asks a clarifying question or returns a safe fallback |
| BR-05 | Protect tenant and role boundaries | Must | Access checks occur before a skill reads data |
| BR-06 | Keep MVP read-only | Must | No mutating operation is exposed by the assistant |

## Functional requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-01 | Intent routing | Recognise unpaid-invoice and paid-revenue intents; unknown intent is not guessed |
| FR-02 | Tenant resolution | Use authenticated tenant context; reject mismatched or missing context |
| FR-03 | Invoice retrieval | Return invoice ID, due date, amount, currency and status for authorised records |
| FR-04 | Revenue aggregation | Aggregate paid invoices for the requested period and currency |
| FR-05 | Evidence | Include source name, record IDs, extraction timestamp and metric definition |
| FR-06 | Clarification | Ask for a period when the question requires one and it is not specified |
| FR-07 | Safe fallback | State the limitation when no skill or reliable source is available |
| FR-08 | Audit metadata | Record request ID, actor/tenant pseudonymous IDs, skill, outcome and latency; do not log sensitive raw content by default |
| FR-09 | Error handling | Distinguish permission denied, source unavailable, invalid request and no data |
| FR-10 | Human escalation | Mark cases requiring finance/product/support review |

## Non-functional requirements

| ID | Area | Requirement / proposed target |
|---|---|---|
| NFR-01 | Security | Tenant and permission checks are server-side and deny by default |
| NFR-02 | Privacy | Minimise prompts and logs; secrets and full financial records are not written to logs |
| NFR-03 | Reliability | Transient read failures may be retried with bounded policy; read-only MVP has no duplicate side effects |
| NFR-04 | Performance | Pilot target p95 below 5 seconds for cached/read-only demo queries; validate with measured load |
| NFR-05 | Traceability | Every answer links to the source data snapshot and definition |
| NFR-06 | Maintainability | Skills have versioned contracts and isolated tests |
| NFR-07 | Accessibility | Responses support plain-language summaries and structured details |
| NFR-08 | Observability | Capture latency, error class, skill and model usage without raw sensitive payloads |

## User stories and acceptance criteria

### US-01 — Find unpaid invoices

As an SME owner, I want to see unpaid invoices so that I can follow up on receivables.

**Given** I am authenticated for tenant A  
**When** I ask “Какие счета ещё не оплачены?”  
**Then** the assistant returns only unpaid invoices belonging to tenant A  
**And** each row includes invoice ID, due date, amount and currency  
**And** the answer includes the source timestamp.

Negative cases: tenant absent → deny; tenant mismatch → deny; source unavailable → report unavailability without inventing rows; no invoices → explicit empty result.

### US-02 — Summarise paid revenue

As a finance operator, I want a paid-revenue total for a specified period so that I can review business performance.

**Given** the approved definition includes invoices with status paid  
**When** I request the total for a supported period  
**Then** the assistant aggregates only paid invoices in that period  
**And** it groups currencies separately  
**And** it returns the definition and data freshness.

Negative cases: missing period → clarify; multiple currencies → do not silently sum unlike currencies; unknown status or invalid amount → surface a data-quality warning and escalate.

### US-03 — Handle unsupported questions

As a user, I want the assistant to explain what it can and cannot do.

**When** I ask it to change an invoice, initiate a transfer or provide tax advice  
**Then** it refuses the action and offers an in-scope read-only alternative where appropriate.
