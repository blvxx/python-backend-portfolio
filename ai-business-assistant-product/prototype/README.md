# Runnable deterministic API prototype

This prototype demonstrates the request/response boundary, intent planning, synthetic business data, tenant scoping, evidence metadata and safe fallbacks.

By default it uses a deterministic planner so CI and local tests run without an API key. An optional OpenAI Responses API planner can classify intent and extract explicit date ranges into a strict schema. The LLM planner has no tools and cannot read business data; the backend verifies the plan and executes only allow-listed read-only skills. No external accounting/banking system is connected.

## Setup

~~~bash
python -m venv .venv
# Activate the environment
pip install -r requirements.txt
uvicorn app:app --reload
~~~

Open http://127.0.0.1:8000/docs.

## Example request

~~~bash
curl -X POST http://127.0.0.1:8000/v1/assistant/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo-alpha-token" \
  -d '{"question":"Покажи неоплаченные счета","tenant_id":"demo-alpha"}'
~~~

Paid revenue with a date range:

~~~bash
curl -X POST http://127.0.0.1:8000/v1/assistant/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo-alpha-token" \
  -d '{"question":"Покажи выручку за ноябрь","tenant_id":"demo-alpha","period":{"from":"2026-11-01","to":"2026-11-30"}}'
~~~

## Verification

~~~bash
pytest -q
~~~

Tests cover tenant isolation, unsupported writes, revenue date filtering, invalid/unverified periods, deterministic intent routing and the optional OpenAI planner's structured output contract. The current CI run passes 15 tests. Live model calls are not run in CI.

The demo tokens are public fixture values intentionally stored in source code. They only demonstrate server-side token-to-tenant mapping for local tests and provide no real security. Production authentication must validate credentials through a trusted identity provider and derive tenant and actor from verified claims.
