# 01 — Business context and scope

> Fictional SME product scenario for portfolio practice.

## Problem statement

Owners and finance operators of small and medium businesses receive information about invoices, payments and revenue from several systems. Answering a routine operational question can require opening several reports, applying filters and reconciling statuses manually.

The proposed assistant provides a conversational, read-only entry point to approved business information. It should explain where an answer came from, identify missing context and decline requests it cannot answer safely.

## Business objective

Reduce the effort required to obtain routine operational information without weakening access control, data correctness or user trust.

### Pilot hypotheses (targets, not measured results)

- At least 80% of in-scope questions can be completed without manual report preparation.
- 100% of numeric answers include a source reference and an as-of timestamp.
- 0 cross-tenant data disclosures in the acceptance and security test set.
- 100% of ambiguous or unsupported requests are clarified, refused or escalated rather than answered with invented facts.

These are proposed acceptance targets, not actual results.

## Stakeholders

| Stakeholder | Need / concern | Decision or contribution |
|---|---|---|
| SME owner | Fast, understandable answers | Business priorities and acceptable language |
| Finance operator | Correct invoice/payment details | Domain definitions and reconciliation rules |
| Product owner | Usable scope and adoption | MVP priority and success measures |
| Business analyst | Complete, traceable requirements | Elicitation, modelling and acceptance criteria |
| System analyst / architect | Consistent service boundaries | API, data model and integration contracts |
| Backend / AI engineers | Implementable behavior | Feasibility, orchestration and model integration |
| Security / privacy reviewer | Access and data protection | Permission model, audit and data handling |
| QA engineer | Testable requirements | Coverage, negative cases and release evidence |

## MVP scope

**In scope:** intent identification for invoice/revenue questions; authenticated organisation context; approved read-only skills; clarification when context is missing; structured answers with evidence IDs and timestamps; refusal of unsupported or unauthorised requests; escalation for unavailable or contradictory source data.

**Out of scope:** payments or invoice edits; tax/legal/investment advice; cross-company benchmarking; autonomous external communication; unrestricted SQL generation or direct database access by an LLM; production banking integrations, real authentication and customer data.

## Assumptions and open questions

| ID | Assumption / question | Treatment |
|---|---|---|
| A-01 | User identity and tenant are supplied by a trusted identity layer | Must be verified by the system; never trust a tenant name typed in chat |
| A-02 | Source systems expose stable invoice identifiers and update timestamps | Validate during integration discovery |
| A-03 | Revenue has an agreed accounting definition | Finance stakeholder must approve inclusions/exclusions |
| A-04 | Users may have different permissions inside one tenant | Role/permission matrix required before production |
| OQ-01 | Which source is authoritative for invoice state? | Resolve during discovery |
| OQ-02 | Are amounts gross or net of tax? | Finance decision required |
| OQ-03 | What timezone defines a reporting day? | Product and finance decision required |
| OQ-04 | What is the permitted data freshness per skill? | Define per metric and source |

## Success measurement

Measure task completion, answer correctness, grounded evidence, clarification rate, refusal quality, latency, cost per resolved task and user correction rate. A pilot requires a reviewed test set and human assessment; model confidence alone is not proof of correctness.
