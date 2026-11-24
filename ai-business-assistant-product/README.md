# SME AI Business Assistant — Business Analysis Case Study

[![AI Business Assistant CI](https://github.com/blvxx/python-backend-portfolio/actions/workflows/ai-business-assistant.yml/badge.svg)](https://github.com/blvxx/python-backend-portfolio/actions/workflows/ai-business-assistant.yml)

> Independent portfolio case study. The business, stakeholders, requirements, data and examples are fictional/synthetic. This is not a bank implementation or paid client delivery.

**Role focus:** AI Business Analyst · IT Business Analyst · AI Product Analyst · LLM Product Analyst

A structured end-to-end case for an AI assistant that helps SME owners understand invoices, receivables and revenue. It demonstrates translating a business problem into requirements, user journeys, dialogue behavior, API contracts, safety rules, acceptance criteria and an evaluation plan.

## What is included

- Business context, scope, stakeholders and explicit assumptions.
- Functional and non-functional requirements with stable IDs.
- AS-IS / TO-BE flow and dialogue scenarios, including clarification and fallback paths.
- AI behavior policy: evidence grounding, tenant isolation, permissions, prompt-injection handling and human escalation.
- Requirements traceability matrix and prioritised MVP backlog.
- OpenAPI contract for the assistant endpoint.
- Runnable deterministic API prototype with synthetic tenant data and read-only invoice/revenue skills.

**Implementation boundary:** the prototype demonstrates API orchestration, skill routing, access boundaries and structured evidence. It does not call an LLM. LLM prompting, model selection, live evaluation and production integrations are specified as design work, not claimed as implemented.

## Project map

| Artifact | Purpose |
|---|---|
| [Business context](docs/01-business-context.md) | Problem statement, actors, outcomes, scope and assumptions |
| [Requirements](docs/02-requirements.md) | Business requirements, functional/non-functional requirements and acceptance criteria |
| [Process and dialogues](docs/03-process-and-dialogue.md) | AS-IS / TO-BE, conversation flows and edge cases |
| [AI safety and behavior](docs/04-ai-safety.md) | Grounding, permissions, refusal, escalation and hallucination controls |
| [Traceability](docs/05-traceability.md) | Business goals → requirements → stories → acceptance tests |
| [Evaluation plan](docs/06-evaluation.md) | Quality dimensions, synthetic test set and release gates |
| [Backlog](docs/07-delivery-backlog.md) | MVP scope, priorities and definition of done |
| [OpenAPI contract](docs/08-openapi.yaml) | API request/response contract |
| [Runnable prototype](prototype/README.md) | Local run and verification instructions |

## Run the demo

The prototype exposes POST /v1/assistant/query. It recognises a small set of read-only intents (unpaid invoices and paid revenue), enforces a demo tenant boundary, and returns structured results with evidence IDs and a data timestamp.

~~~bash
cd ai-business-assistant-product/prototype
python -m venv .venv
# Activate the environment, then:
pip install -r requirements.txt
uvicorn app:app --reload
~~~

OpenAPI docs: http://127.0.0.1:8000/docs

Run tests:

~~~bash
pytest -q
~~~

The demo data is synthetic. Tenant IDs are demo identifiers, not real organisations. No financial transactions are executed.

## How to review the case

1. Start with the business problem and scope.
2. Review requirements and acceptance criteria.
3. Follow one successful and one negative dialogue path.
4. Inspect the safety policy and traceability.
5. Run the API and execute the tests.
6. Compare prototype behavior with the documented release gates.


## Latest verification

- [AI Business Assistant Prototype CI — successful run on 24 November 2026](https://github.com/blvxx/python-backend-portfolio/actions/runs/45414339077)
- The workflow compiles the FastAPI application and runs the API test suite, including tenant isolation, unsupported writes, revenue date filtering and invalid period boundaries.

## Evidence and limitations

- Requirements and BA artifacts: authored for this independent case study.
- API prototype: implemented with deterministic routing and synthetic data.
- LLM provider integration: not implemented.
- Model accuracy / hallucination metrics: evaluation design only; no live-model score is claimed.
- Banking systems, real customer data, production identity provider and external accounting APIs: not connected.

## Related engineering work

- [AI Support Triage Agent](../ai-support-triage-agent/) — separate LLM-assisted support prototype with retrieval-grounded outputs and human-review boundaries.
- [Python Backend Portfolio](../README.md)
- [QA Engineering Portfolio](https://github.com/blvxx/qa-engineering-portfolio)

---
Maintainer: [Artem Kalinin](https://github.com/blvxx)
