# 05 — Requirements traceability matrix

| Business goal | Requirement | User story / scenario | Acceptance evidence | Status |
|---|---|---|---|---|
| BG-01 Reduce manual invoice lookup | BR-01 / FR-03 | US-01 unpaid invoices | Tenant-scoped invoice query tests | Prototype implemented with synthetic data |
| BG-02 Reduce time to revenue answer | BR-02 / FR-04 | US-02 paid revenue | Deterministic aggregate and currency tests | Prototype partially represents flow |
| BG-03 Build user trust | BR-03 / FR-05 | Evidence shown for each numeric answer | Evidence ID and timestamp assertions | Structured response implemented |
| BG-04 Avoid fabricated answers | BR-04 / FR-06 / FR-07 | Ambiguous, no-match and source-failure dialogues | Clarification/fallback test cases | Specification defined |
| BG-05 Protect company data | BR-05 / FR-02 | Cross-tenant request | 403 / no data leakage test | Demo boundary implemented; production auth absent |
| BG-06 Prevent unintended actions | BR-06 | Request to update invoice or initiate transfer | Refusal and no-mutation assertions | Read-only demo only |
| BG-07 Operate reliably | FR-08 / FR-09 / NFR-08 | Timeout, source error and audit flow | Error contract and observability plan | Partially specified |
| BG-08 Maintain changeability | NFR-06 | Add a new skill | Versioned skill contract and backlog story | Design specified |

## Coverage rules

- A requirement is not done because it appears in a document; it needs implementation evidence or an explicit design-only status.
- Every Must requirement needs at least one positive and one relevant negative acceptance test.
- Security requirements need adversarial cases, not only happy paths.
- A release gate points to a test/evaluation artifact and named environment.
