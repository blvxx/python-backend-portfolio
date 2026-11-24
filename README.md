# Artem Kalinin — Python Backend Portfolio

**Python Developer · Backend Developer · API Integrations · Automation**

I build Python-based backend tools and integrations, with a focus on REST APIs, asynchronous workflows, data persistence, automation, reliability and testable service behavior.

**Target roles:** Python Developer · Backend Developer · Junior / Middle Python Engineer · Integration Developer

[GitHub profile](https://github.com/blvxx) · [Email](mailto:blvx8x@gmail.com) · [Telegram](https://t.me/blvlxx)

## Technical stack

- **Language and runtime:** Python, async programming.
- **Backend and APIs:** FastAPI, REST, HTTP, webhooks, request validation and structured responses.
- **Data:** PostgreSQL, SQL, Redis, data validation and persistence.
- **Bots and integrations:** aiogram, Telegram Bot API, external API integrations.
- **Engineering:** Docker, Docker Compose, Git, GitHub Actions, pytest, logging and error handling.
- **AI-assisted workflows:** retrieval from internal runbooks, structured triage, citation validation and human approval boundaries.

## Selected projects

Project implementations are currently maintained in the original engineering repository. This repository is the dedicated Backend entry point; links below open source code, architecture and CI evidence.

### 1. Telegram Business Assistant

[Open source project](https://github.com/blvxx/portfolio/tree/main/telegram-business-assistant)

An asynchronous Telegram workflow built with Python and aiogram, PostgreSQL and Redis.

Engineering topics:
- Async message and callback handling.
- Persistent data and conversation state.
- Idempotency and safe processing of repeated events.
- Transactional outbox pattern for reliable notification workflows.
- Integration tests and operational checks.

[Successful CI run](https://github.com/blvxx/portfolio/actions/runs/45102741553)

### 2. AI Support Triage Agent

[Open source project](https://github.com/blvxx/portfolio/tree/main/ai-support-triage-agent)

A prototype for structured support triage with runbook retrieval and controlled AI assistance.

Engineering topics:
- Retrieval of relevant operational documentation.
- Structured triage output.
- Citation validation and unsupported-answer checks.
- Human approval boundaries for actions with operational impact.
- Evaluation and failure-case thinking.

### 3. FinTech QA Platform — Backend and Integration

[Open source project](https://github.com/blvxx/portfolio/tree/main/fintech-qa-platform)

A fictional Payment/Ledger service environment using FastAPI, PostgreSQL and Docker Compose.

Engineering topics:
- Service boundaries and HTTP integration.
- Payment and ledger state transitions.
- Idempotent retries and transaction invariants.
- Database-backed integration checks.
- Prometheus/Grafana observability and controlled dependency recovery.

[Successful CI run](https://github.com/blvxx/portfolio/actions/runs/45100258032)

### 4. Python API Automation

[Open source project](https://github.com/blvxx/portfolio/tree/main/api-automation)

Reusable Python HTTP client and pytest suite covering REST methods, schemas, negative cases, pagination, timeouts and safe retry behavior.

[Successful CI run — 62 tests](https://github.com/blvxx/portfolio/actions/runs/45102695248)

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

The commercial casebook describes problem statements, solution boundaries and validation metrics: [QA & Commercial Problem-Solving Casebook](https://github.com/blvxx/portfolio/blob/main/qa-commercial-casebook.md).

These are independent projects and solution concepts. I do not present them as paid production deployments or claim customer revenue/savings without measured evidence.

## Running and verification

Each source project contains its own dependencies and setup instructions. Start with the linked README before running a service. CI links above show the checks that have actually completed successfully; a passing workflow does not imply a public production deployment.

## Scope and transparency

This repository is a curated Backend portfolio landing page. The source projects remain in the original repository for now and will be migrated here after the destination structure and full file history are checked. Some targets are prototypes or synthetic environments, not production customer systems.

---

**Artem Kalinin** · [GitHub](https://github.com/blvxx)
