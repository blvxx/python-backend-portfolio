# Python Backend — Engineering Projects & Evidence

> **Portfolio navigation:** the single employer-facing entry point is the [career portfolio](https://blvxx.github.io/portfolio/). This repository is a technical project library for Python, backend APIs, integrations and automation.


**Python Developer · Backend Developer · API Integrations · Automation**

I build Python-based backend tools and integrations, with a focus on REST APIs, asynchronous workflows, data persistence, automation, reliability and testable service behavior.

> **Supporting product-analysis case:** the [SME AI Business Assistant — Business Analysis Case Study](./ai-business-assistant-product) contains a complete set of product-analysis artefacts alongside the deterministic FastAPI prototype. It contains the business context, BRD/FRD, AS-IS / TO-BE flows, user stories, acceptance criteria, AI safety policy, requirements traceability, evaluation plan, backlog and API contract. The companion FastAPI demo uses deterministic routing and synthetic invoice data.

**Target roles:** Python Developer · Backend Developer · Junior / Middle Python Engineer · Integration Developer

[GitHub profile](https://github.com/blvxx) · [Email](mailto:blvx8x@gmail.com) · [Telegram](https://t.me/blvlxx)

## Technical stack

- **Language and runtime:** Python, async programming.
- **Backend and APIs:** FastAPI, REST, HTTP, webhooks, request validation and structured responses.
- **Data:** PostgreSQL, SQL, Redis, data validation and persistence.
- **Bots and integrations:** aiogram, Telegram Bot API, external API integrations.
- **Engineering:** Docker, Docker Compose, Git, GitHub Actions, pytest, logging and error handling.
- **AI-assisted workflows:** retrieval from internal runbooks, structured triage, citation validation and human approval boundaries.

## AI product analysis case

### SME AI Business Assistant — Business Analyst case study

[Open project](./ai-business-assistant-product)

End-to-end product analysis for a fictional SME assistant: business context, BRD/FRD, user stories, acceptance criteria, AS-IS/TO-BE, dialogue scenarios, AI guardrails, requirements traceability, evaluation plan and prioritised backlog. Includes a deterministic FastAPI prototype with synthetic tenant-scoped invoice data.

The prototype uses deterministic intent routing by default and also includes an optional OpenAI Responses API intent planner. The model only classifies intent and extracts explicitly stated dates; it has no tools and cannot access business records. The backend independently blocks write requests and executes only allow-listed read-only skills. The integration is implemented in code, but a live credentialed model call and model-accuracy evaluation are not claimed as completed.

## Selected projects

The source projects are included in this repository with their code, configuration, tests and engineering documentation. Cross-disciplinary QA/integration examples remain linked from the dedicated QA portfolio.

### 1. Telegram Business Assistant

[Open source project](./telegram-business-assistant)

An asynchronous Telegram workflow built with Python and aiogram, PostgreSQL and Redis.

Engineering topics:
- Async message and callback handling.
- Persistent data and conversation state.
- Idempotency and safe processing of repeated events.
- Transactional outbox pattern for reliable notification workflows.
- Integration tests and operational checks.

[Successful CI run](https://github.com/blvxx/python-backend-portfolio/actions/workflows/telegram-business-assistant.yml)

### 2. AI Support Triage Agent

[Open source project](./ai-support-triage-agent)

A prototype for structured support triage with runbook retrieval and controlled AI assistance.

Engineering topics:
- Retrieval of relevant operational documentation.
- Structured triage output.
- Citation validation and unsupported-answer checks.
- Human approval boundaries for actions with operational impact.
- Evaluation and failure-case thinking.

### 3. FinTech QA Platform — Backend and Integration

[Open source project](https://github.com/blvxx/qa-engineering-portfolio/tree/main/fintech-qa-platform)

A fictional Payment/Ledger service environment using FastAPI, PostgreSQL and Docker Compose.

Engineering topics:
- Service boundaries and HTTP integration.
- Payment and ledger state transitions.
- Idempotent retries and transaction invariants.
- Database-backed integration checks.
- Prometheus/Grafana observability and controlled dependency recovery.

[Successful CI run](https://github.com/blvxx/qa-engineering-portfolio/actions/workflows/fintech-qa-platform.yml)

### 4. Python API Automation

[Open source project](https://github.com/blvxx/qa-engineering-portfolio/tree/main/api-automation)

Reusable Python HTTP client and pytest suite covering REST methods, schemas, negative cases, pagination, timeouts and safe retry behavior.

[Successful CI run — 62 tests](https://github.com/blvxx/qa-engineering-portfolio/actions/workflows/api-automation.yml)

## Engineering approach

1. Clarify the use case, inputs, outputs and failure conditions.
2. Define API contracts and data ownership.
3. Keep business rules and integration boundaries explicit.
4. Validate inputs and handle external-service failures.
5. Make repeated events and retries safe where required.
6. Add tests for normal behavior, edge cases and failure paths.
7. Package repeatable environments and automate checks in CI.
8. Document setup, configuration, limitations and operational behavior.

## Business-oriented problem solving

I focus on small systems that remove repetitive work and improve operational reliability:

- Telegram-based workflows for receiving and routing business requests.
- Internal assistants that search runbooks and prepare structured support triage.
- API integrations that normalise data between services.
- Excel/CSV order validation as a potential wholesale automation workflow.

The commercial casebook describes problem statements, solution boundaries and validation metrics: [QA & Commercial Problem-Solving Casebook](https://github.com/blvxx/qa-engineering-portfolio/blob/main/qa-commercial-casebook.md).

These are independent projects and solution concepts. I do not present them as paid production deployments or claim customer revenue/savings without measured evidence.

## Running and verification

Each source project contains its own dependencies and setup instructions. Start with the linked README before running a service. CI links above show the checks that have actually completed successfully; a passing workflow does not imply a public production deployment.

## Scope and transparency

This repository contains the dedicated Backend project sources and documentation. FinTech QA Platform and API Automation are linked from the QA portfolio because those examples are presented there as quality-engineering case studies. Some targets are prototypes or synthetic environments, not production customer systems.

---

**Artem Kalinin** · [GitHub](https://github.com/blvxx)
