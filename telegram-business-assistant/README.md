# Telegram Business Assistant

A Telegram bot MVP for small businesses to collect structured enquiries and route them to an administrator.

**Demo status:** the former Dada Cloud single-worker demo is retired and is not presented as a live service. The current PostgreSQL/Redis/webhook profile is validated in CI but has not been deployed to a public host.

This portfolio project demonstrates a lead-capture workflow with consent, validation, shared PostgreSQL persistence, Redis-backed conversation state and a durable administrator-notification outbox. SQLite remains available as a local, single-instance fallback.

## What it does

- Shows a clear entry menu and explains the available service scenarios.
- Collects explicit consent before asking for personal contact details.
- Lets a visitor choose the type of enquiry.
- Accepts a phone number, email address or Telegram shared contact.
- Validates the contact and request description.
- Stores each enquiry through the configured persistence adapter: PostgreSQL for the shared runtime, or SQLite for the local single-instance fallback. Records include a UTC timestamp and a stable Telegram message idempotency key.
- Repeated processing of the same chat/message identity returns the existing enquiry instead of creating a duplicate.
- When ADMIN_CHAT_ID is configured, inserts a notification event in the same database transaction as the enquiry.
- Runs a background worker that claims notification events, sends them through Telegram and records delivery/retry state.
- Provides /my_id to display the numeric IDs needed for administrator setup.
- Provides a restricted /leads command for an administrator configured with ADMIN_USER_ID.
- Includes /cancel to stop an unfinished request.

## Stack

- Python 3.11+
- aiogram 3.x
- PostgreSQL / asyncpg for shared multi-instance persistence; SQLite / aiosqlite for local fallback
- Redis for persistent FSM state and cross-instance event isolation
- aiohttp health/readiness endpoints, validated `X-Request-ID` correlation and Prometheus metrics, plus Prometheus rules for target/dependency failures, dead letters and stalled outbox
- pytest, pytest-asyncio and service-backed integration tests
- GitHub Actions with PostgreSQL and Redis service containers

## Architecture

    Telegram Update
          |
          v
    Polling (one replica) OR HTTPS webhook (multiple replicas)
          |
          v
    aiogram Router + Redis FSM/Event Isolation
          |
          v
    Enquiry Application Service
          |
          v
    PostgreSQL transaction
       |                 |
       v                 v
     leads          notification_outbox
                           |
                           v
                 workers using SKIP LOCKED
                           |
                           v
                 Telegram notification

The multi-replica deployment profile uses PostgreSQL for shared lead/outbox data and Redis for persistent FSM state plus per-user event isolation. Webhook mode is required for horizontal scaling; Telegram long polling must remain a single active poller. Every replica can run an outbox worker because PostgreSQL row locks with SKIP LOCKED prevent two workers from claiming the same event. SQLite and MemoryStorage remain optional local-development fallbacks only and are not a multi-replica deployment option.

PostgreSQL schema migrations are serialized with a database advisory lock. Lead creation and outbox enqueue are one transaction, repeated Telegram message IDs are replay-safe, and delivery remains at-least-once (a remote send followed by a process crash can still produce a duplicate). The process exposes /healthz, /readyz and /metrics on WEB_SERVER_PORT. HTTP requests receive a validated or generated `X-Request-ID` echoed in the response; access logs include only the request ID, method, path and status code, never query strings or request bodies. The backup and restore scripts verify the dump archive before use; CI restores a dump into a separate disposable database and checks restored data. This is a tested procedure in CI, not proof of a production backup schedule, host-level persistence or a host-level restore.

## Run locally

1. Use Python 3.11 or newer.
2. Create a virtual environment and install dependencies:

       python -m venv .venv
       # Windows:
       .venv\\Scripts\\activate
       # macOS / Linux:
       source .venv/bin/activate
       pip install -r requirements-dev.txt

3. Copy .env.example to .env.
4. Create a Telegram bot with @BotFather and place its token in BOT_TOKEN.
5. Optionally set ADMIN_CHAT_ID and ADMIN_USER_ID.
6. Start the bot:

       python -m src.bot

To receive private notifications, the administrator must open the bot and send /start first. Use the numeric Telegram chat ID for ADMIN_CHAT_ID and the numeric Telegram user ID for ADMIN_USER_ID. Keep both IDs and the bot token out of source control.

## Hosted deployment status

The former Dada Cloud demo ran as one background worker using Telegram long polling. It is retired and is not maintained as a live deployment. No public-host deployment of the current PostgreSQL/Redis/webhook runtime is claimed.

The current source has CI evidence for PostgreSQL and Redis integration, a disposable-database backup/restore drill, Prometheus rule validation and a Docker image build. These checks do not prove that a particular host has persistent storage, scheduled off-host backups, working alert notifications or a successful host-level restore.

For a low-volume evaluation deployment on a free web-hosting stack, see the [Koyeb + Neon + Upstash guide](docs/deploy-koyeb-neon-upstash.md). The guide uses webhook mode and explicitly documents scale-to-zero, free-tier limits and the non-production boundary. No public host deployment is claimed until the runbook's smoke test is completed.

Do not collect real customer enquiries through an unverified deployment. Use the Docker Compose instructions below for local evaluation. Before using a new host with real data, provision persistent PostgreSQL and Redis, configure secrets and HTTPS webhook delivery, then complete the smoke, restart, backup and restore checks in the operations runbook.

## Docker deployment

The repository includes a Dockerfile and Docker Compose configuration with PostgreSQL and Redis volumes. The default local profile uses polling (one bot replica); the same image can run in webhook mode behind an HTTPS reverse proxy/load balancer for multiple replicas.

1. Install Docker Engine and the Docker Compose V2 plugin on a Linux server.
2. Clone the repository and enter the project directory:

       git clone https://github.com/blvxx/python-backend-projects.git
       cd python-backend-projects/telegram-business-assistant

3. Create the private environment file and restrict its permissions:

       cp .env.example .env
       chmod 600 .env

4. Edit .env and set BOT_TOKEN and a non-default POSTGRES_PASSWORD / matching DATABASE_URL. Start with optional ADMIN_CHAT_ID and ADMIN_USER_ID blank.
5. Build and start PostgreSQL, Redis and the bot:

       docker compose up -d --build

6. Follow startup logs:

       docker compose logs -f --tail=100 bot

7. Confirm readiness and metrics through the internal service port:
 
       docker compose exec -T bot python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/readyz').read().decode())"

8. Open the bot in Telegram and send /start, then /my_id. Copy the displayed IDs into ADMIN_CHAT_ID and ADMIN_USER_ID in .env and restart:

       docker compose up -d

The Compose file stores PostgreSQL, Redis and Prometheus data in named volumes; SQLite is only the local single-instance fallback and is not used by this Compose stack. The bot runs as a non-root user, uses a read-only container filesystem, drops Linux capabilities and restarts the process after a failure. Keep the VPS firewall closed to inbound ports other than the SSH access you administer. Do not commit .env or share the bot token.

To stop the service without deleting data:

       docker compose down

To remove the service and its stored data permanently (destructive):

       docker compose down -v

With REDIS_URL configured, unfinished FSM conversations survive a bot process restart until their TTL expires. Local runs without Redis use MemoryStorage and are intentionally not production-ready.

## Tests

       pytest -q

Tests cover lead persistence, application policy, handler/FSM orchestration, outbox transaction atomicity, lease fencing, retries/dead-letter behaviour, migrations, idempotent replay and request-ID validation/propagation. CI additionally runs service-backed integration tests against PostgreSQL and Redis: concurrent replay, SKIP LOCKED work distribution, shared FSM persistence after reconnect and cross-instance per-user event isolation. CI exercises a PostgreSQL dump/restore to a disposable database. No live Telegram token is required for these tests.

## Latest CI evidence

The reviewed **23 November 2026** GitHub Actions run completed successfully. It passed Python linting, unit and PostgreSQL/Redis service-integration tests, a disposable PostgreSQL backup/restore verification, Prometheus scrape/alert validation and Docker image build.

[Open the successful workflow run](https://github.com/blvxx/python-backend-projects/actions/workflows/telegram-business-assistant.yml).

## Configuration

| Variable | Required | Purpose |
|---|---|---|
| BOT_TOKEN | Yes | Telegram Bot API token |
| DATABASE_URL | No | PostgreSQL URL for shared deployments; omit to use local SQLite |
| DATABASE_PATH | No | SQLite fallback path; defaults to data/leads.sqlite3 |
| REDIS_URL | Recommended | Shared Redis URL for persistent FSM; required for webhook mode |
| BOT_MODE | No | polling (single replica) or webhook (horizontal scaling) |
| FSM_STATE_TTL_SECONDS | No | Redis FSM state/data TTL, default 86400 |
| WEBHOOK_BASE_URL | Webhook only | Public HTTPS URL used by Telegram |
| WEBHOOK_SECRET | Webhook only | Telegram webhook secret token |
| WEBHOOK_PATH | No | Webhook route, default /telegram/webhook |
| WEB_SERVER_PORT | No | Health/metrics/webhook port, default 8080 |
| ADMIN_CHAT_ID | No | Chat that receives new enquiry notifications |
| ADMIN_USER_ID | No | User ID allowed to run /leads |

## Engineering documentation

The engineering notes distinguish the current implementation from future design proposals:

- [Current-state architecture and target design](./docs/engineering/architecture.md)
- [ADR-0001: storage and conversation state](./docs/engineering/decisions/0001-storage-and-state.md)
- [ADR-0002: transactional notification outbox](./docs/engineering/decisions/0002-transactional-notification-outbox.md)
- [ADR-0003: idempotent Telegram submissions](./docs/engineering/decisions/0003-idempotent-telegram-submissions.md)
- [Security threat model and control gaps](./docs/engineering/security/threat-model.md)
- [Operations runbook: deploy, backup and restore](./docs/engineering/operations/runbook.md)
- [Evidence-based engineering roadmap](./docs/engineering/roadmap.md)

The PostgreSQL backup/restore scripts are exercised by CI on a disposable database. A production backup schedule, off-host retention, a host-level restore drill and a persistent-storage guarantee still require deployment access and verification. The roadmap distinguishes code/CI evidence from host-level evidence.

## Security and data handling

- The bot asks for consent before collecting contact information.
- It does not request passwords, authentication codes or payment details.
- SQL statements use parameters rather than string interpolation.
- User-provided content is HTML-escaped before it is included in administrator messages.
- The /leads command is restricted to ADMIN_USER_ID and private chats.
- Outbox events store the destination chat ID and lead reference rather than duplicating contact and request fields in the event payload.
- Outbox error metadata stores exception type names, not arbitrary exception text.
- Tokens belong in environment variables or deployment secrets, never in commits.
- Define a retention period and publish a business-specific privacy notice before using this template with real customers.

## Production improvements

Before collecting real customer data, deploy the PostgreSQL/Redis profile on a host with persistent managed services, verify a full host-level restore, configure off-host scheduled backups and alert delivery, define a privacy notice and retention policy, and test failure/recovery under the expected traffic. The currently hosted demo has not yet been upgraded to this topology.
