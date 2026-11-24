# AI Support Triage Agent

A retrieval-grounded LLM workflow for first-pass L2 support triage. It retrieves relevant internal runbook snippets, asks an LLM to produce a strict structured diagnosis, validates source references, removes state-changing suggestions and hands the result to a human for approval.

**This is an independently developed portfolio case.** The data and incidents are synthetic. The code is designed for a real OpenAI API connection, but no live API evaluation is claimed until run with an API key and model access.

## Workflow

1. Accept a bounded synthetic incident report (do not include credentials or personal data).
2. Search a small, versioned runbook knowledge base using deterministic keyword retrieval.
3. Send the report as untrusted content and the retrieved documents as evidence context to the OpenAI Responses API.
4. Parse the response into a strict Pydantic schema using Structured Outputs.
5. Verify that cited evidence IDs came from the retrieved documents.
6. Remove any suggested state-changing operation and require escalation.
7. Return a triage result and customer reply draft for human review.

The agent does not restart services, alter configuration, deploy code, query private infrastructure, message customers or create tickets. This design deliberately keeps diagnosis separate from privileged operations.

## Example

Run from this directory:

    python -m venv .venv
    # Activate the virtual environment, then:
    pip install -r requirements.txt

Set the API key through your shell or a secret manager:

    export OPENAI_API_KEY="..."
    export OPENAI_MODEL="gpt-6.2-astra"

Analyse a synthetic incident:

    python -m src.cli --text "Nginx returns 502 Bad Gateway. The upstream connection is refused after a deploy."

Or pass a UTF-8 incident file:

    python -m src.cli --file examples/nginx-502.txt

The output includes severity, category, concise summary, hypotheses, read-only diagnostic checks, evidence IDs, confidence, escalation decision and a customer reply draft.

## Engineering controls

- Structured Outputs with a Pydantic contract; refusal and non-completed responses are handled as errors.
- Retrieved evidence IDs are allow-listed; hallucinated citations are removed and force escalation.
- The incident report is treated as untrusted input; prompt injection instructions inside it are explicitly ignored.
- State-changing suggestions (restart, delete, deploy, permission changes and similar) are removed and force escalation.
- No agent tool can execute shell commands or modify external systems.
- Logs contain a short case fingerprint and triage metadata, not the raw report or user data.
- The CLI requires an API key and never embeds credentials in the repository.

## Testing and evaluation

Run offline checks:

    ruff check src tests
    pytest -q

The unit tests use a fake provider and require no API key. They verify retrieval grounding, invalid citation removal, escalation policy, and state-changing suggestion removal.

A separate live regression evaluator is available:

    OPENAI_API_KEY=... python -m evals.evaluate

It checks severity/category accuracy and required evidence recall against four synthetic cases. This is a small regression set, not a statistically significant model benchmark. The live evaluator is not run in ordinary CI because it requires an API key and incurs API usage.

## Limitations

- Keyword retrieval is intentionally small and transparent; a production knowledge base should use document versioning, richer retrieval and access controls.
- Model output is a proposed triage, not an authoritative root-cause determination.
- Human approval is mandatory before external communication or operational changes.
- Evaluation coverage is small; thresholds and cases should be expanded using reviewed, de-identified incidents.
- Live API latency, spend, rate limits, retention and privacy configuration must be validated in the target environment.

## Evidence status

| Evidence | Status |
|---|---|
| Responses API integration code | Implemented; live credentialed call not yet run |
| Structured result schema | Implemented |
| Retrieval and evidence validation | Unit tested |
| Prompt injection and action guardrails | Unit tested |
| Offline CI | Runs without API key |
| Live model regression | Available; requires API key |
| Production integrations / customer data | Not implemented |

