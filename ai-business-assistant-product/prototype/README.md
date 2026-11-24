# Runnable deterministic API prototype

This prototype demonstrates the request/response boundary, simple skill routing, synthetic business data, tenant scoping, evidence metadata and safe fallbacks.

It does **not** connect to an LLM or external accounting/banking system. The intent router is deterministic so that authorization and business behavior can be reproduced without model variability or API spend.

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
  -H "X-Demo-Tenant: demo-alpha" \
  -d '{"question":"Покажи неоплаченные счета","tenant_id":"demo-alpha"}'
~~~

## Verification

~~~bash
pytest -q
~~~

Tests cover supported intents, unknown intent, missing tenant context, mismatched tenant context and evidence metadata.

The tenant header is a demo-only stand-in. Production authentication must derive tenant and actor from a trusted identity provider, not from user-controlled request fields.
