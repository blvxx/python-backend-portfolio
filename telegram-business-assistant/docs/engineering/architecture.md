# Architecture: Telegram Business Assistant

## Document status

The repository contains two runtime profiles:

- Local/single-instance: Telegram long polling, SQLite and optional in-memory FSM fallback.
- Shared/multi-replica: Telegram HTTPS webhook, PostgreSQL, Redis FSM and Redis event isolation.

The shared profile is implemented in source and is exercised by GitHub Actions service-backed integration tests. It has not yet been deployed to the Dada Cloud demo host. This is an independently developed portfolio project, not a commercial client deployment.

## Product workflow

1. A visitor starts the bot and reviews the consent notice.
2. The visitor selects a service category.
3. The visitor provides a phone number, email address or Telegram contact.
4. The visitor describes the request.
5. EnquiryService validates a typed CreateEnquiry command.
6. The selected persistence adapter stores the lead and, when configured, its notification event in one transaction.
7. The visitor receives confirmation.
8. An outbox worker delivers the administrator notification with bounded retry.

There is no CRM/payment integration. The assistant does not run an LLM in this project; AI support-triage is a separate portfolio case.

## Runtime profiles

### Local / single-instance

Telegram Bot API
  -> aiogram Dispatcher (long polling)
  -> Telegram Router / Handlers
  -> EnquiryService
  -> SQLite transaction: leads + notification_outbox
  -> outbox worker
  -> Telegram notification

- SQLite is a local/single-instance persistence adapter.
- MemoryStorage is a development fallback only. It loses unfinished flows on process restart.
- This mode is not the recommended production profile for multiple replicas.

### Shared / multi-replica

Telegram Bot API
  -> HTTPS webhook / load balancer
  -> aiogram webhook handler (one or more replicas)
       -> Redis FSM state + data + event isolation
       -> EnquiryService
       -> PostgreSQL transaction: leads + notification_outbox
  -> outbox workers using PostgreSQL row-level locks
  -> Telegram notification

The shared profile requires BOT_MODE=webhook, PostgreSQL DATABASE_URL, Redis REDIS_URL, public HTTPS WEBHOOK_BASE_URL, WEBHOOK_SECRET and WEBHOOK_PATH. Configuration validation rejects webhook mode when PostgreSQL, Redis, HTTPS URL or the secret is missing. Long polling and webhook delivery must not run simultaneously for the same bot token.

Redis FSM state/data use a configurable TTL. Redis event isolation serializes updates for the same FSM key across replicas, reducing races when two webhook workers receive updates for one conversation.

PostgreSQL is the shared source of truth for leads and notification events. A database advisory lock serializes schema migrations. Outbox workers use FOR UPDATE SKIP LOCKED so multiple workers can claim different due events without taking the same row. Lead creation and outbox enqueue share one transaction. Idempotency keys derived from Telegram chat/message identity make repeated submissions converge on one lead. Delivery remains at-least-once; a process crash after the Telegram send succeeds but before the delivered marker commits can produce a duplicate remote message.

## Components

| Component | Responsibility | Implementation |
|---|---|---|
| Runtime / lifecycle | Configure dependencies, start polling or webhook mode, shut down workers | src/bot.py |
| Settings | Validate runtime profile and endpoints | src/config.py |
| Telegram interface | Commands, callbacks, consent and FSM conversation | src/handlers.py |
| Conversation state | Persist user state between events/restarts | RedisStorage in shared profile; MemoryStorage fallback locally |
| Event isolation | Serialize updates for a conversation across replicas | Redis event isolation |
| Application policy | Validate consent, identity, contact and request | src/application/enquiries.py |
| Persistence | Store leads, outbox state and schema migrations | src/database.py, src/postgres_database.py, src/migrations.py |
| Notification dispatch | Claim, retry and dead-letter outbox records | src/application/notifications.py |
| Telegram notification adapter | Render and send admin notification | src/infrastructure/telegram_notifications.py |
| Observability | Liveness, dependency readiness and Prometheus metrics | src/observability.py, src/metrics.py |

## Data and migrations

The lead record stores a generated ID, Telegram sender ID, optional username, customer display name, submitted contact, selected service, request description, UTC timestamp and nullable idempotency key.

The SQLite adapter uses forward-only migrations tracked by PRAGMA user_version. The PostgreSQL adapter tracks versions in schema_migrations, applies them under a transaction and serializes startup migrations with an advisory lock.

Both adapters implement the same repository behaviour used by EnquiryService and the notification dispatcher. PostgreSQL is the multi-replica option; SQLite remains for local development. The unique nullable idempotency key prevents replay duplication.

## Observability and operations

- /healthz is a liveness endpoint.
- /readyz checks the configured database and Redis dependency.
- /metrics exports Prometheus outbox state gauges, dependency-readiness gauge and notification delivery counters. The Compose monitoring profile evaluates Prometheus alert rules for unavailable targets/dependencies, dead letters and stalled backlog.
- Logs identify worker/event outcomes and exception type without persisting arbitrary exception messages or user contact details.

The repository includes PostgreSQL custom-format backup and guarded restore scripts. CI creates a backup, validates the archive, restores into a disposable database, and verifies a row. This proves the scripted mechanism on CI infrastructure, not a production backup schedule, off-host retention or successful restore on Dada Cloud. Those require host-level configuration and a separate drill.

## Deployment status

The existing @blvlxxbot hosted demo was previously verified as a single Dada Cloud background worker using long polling. That validation predates the PostgreSQL/Redis/webhook changes. The new multi-replica profile is source-complete only after CI passes; it must not be described as already deployed or live-tested on Dada Cloud.

Do not collect real customer data on the current hosted demo until its persistent storage/managed services, backup schedule, retention policy and restore procedure are verified. Local Docker Compose persistent volumes are not evidence that the hosted provider guarantees persistence.

## Failure semantics and limits

| Failure | Expected behaviour | Remaining operational control |
|---|---|---|
| Replica restart | Redis FSM survives until its TTL expires | Verify external Redis persistence and availability |
| PostgreSQL unavailable | Readiness fails; writes do not silently fall back | Configure alerts and database recovery |
| Redis unavailable | Readiness fails; FSM-dependent shared mode is not ready | Configure alerts and Redis recovery |
| Admin send fails | Outbox retries with bounded exponential backoff; exhausted events become dead | Alert and review dead events |
| Worker concurrency | PostgreSQL row locks distribute work | Load-test pool sizes and throughput |
| Remote send succeeds then process crashes | A later retry may send a duplicate | Delivery is at-least-once, not exactly-once |
| Host / volume is lost | Recovery depends on external backup | Verify off-host backup and restore on actual host |

## Security and design principles

- No secrets belong in Git, logs, screenshots or chat transcripts.
- Personal data is excluded from ordinary logs.
- User content is escaped before Telegram HTML rendering.
- Admin enquiry listing requires configured admin user ID and a private chat.
- Webhook mode requires an HTTPS public endpoint and secret header token.
- Databases and Redis must remain private behind the application network.
- LLM outputs, when used in a separate AI project, are untrusted; external actions require human approval.
- Start with a modular monolith; do not introduce microservices without a clear scaling or ownership requirement.

## Evidence still required

- Deploy this branch to the hosted environment and run a safe non-personal-data Telegram smoke test.
- Verify managed PostgreSQL/Redis persistence across restart/redeployment.
- Configure off-host scheduled backups, retention and alert delivery.
- Run and record a restore drill against the actual host.
- Establish workload-specific pool limits, SLOs and alert thresholds.


## Recorded engineering decisions

### Decision 1 — Transactional outbox with at-least-once delivery

**Context:** enquiry persistence and administrator notification are separate operations. Sending before the database commit can notify about an enquiry that was never stored; sending after commit without a durable event can lose the notification if the process exits.

**Decision:** persist the enquiry and outbox event in one PostgreSQL transaction. Workers claim due rows using `FOR UPDATE SKIP LOCKED`, attach a lease token, and perform the external Telegram send outside the database transaction. Failed sends are retried with bounded exponential backoff; exhausted events are dead-lettered.

**Trade-off:** PostgreSQL cannot atomically commit a remote Telegram send. If Telegram accepts a message and the process crashes before the delivered marker commits, a later retry can send a duplicate. The guarantee is at-least-once, not exactly-once.

**Operational consequence:** dead-letter review, alert delivery, workload-specific lease tuning and a real-host recovery drill remain operational requirements, not claims made by this demo.

### Decision 2 — Enforce replay safety at the persistence boundary

**Context:** Telegram updates can be delivered or processed more than once. In-memory duplicate checks alone would not protect against concurrent handlers or process restarts.

**Decision:** derive a stable idempotency key from the Telegram chat/message identity and pass it through a typed application command. PostgreSQL enforces uniqueness with a unique index. A conflicting insert returns the existing lead identifier and does not enqueue another outbox event.

**Trade-off and scope:** the replay-protection guarantee applies when a non-null key is supplied. Calls without a key do not receive that guarantee. The key is specific to Telegram-originated submissions; it is not a general external-client idempotency API.

### Decision 3 — Keep local and shared runtime profiles explicit

**Context:** SQLite and in-memory FSM storage simplify local development but are not suitable as shared state across multiple replicas.

**Decision:** retain SQLite / long polling as a local single-instance profile and use PostgreSQL / Redis / HTTPS webhook for the shared multi-replica profile. Configuration validation rejects incomplete shared-mode configuration rather than silently falling back to local storage.

**Trade-off:** the shared profile has more operational dependencies. This is deliberate: a deployment must fail visibly when a required shared dependency is unavailable instead of presenting a misleading partially working mode.

## Verification checklist for reviewers

- [ ] Run the application unit tests and service-backed PostgreSQL/Redis integration tests.
- [ ] Submit the same Telegram chat/message identity twice and verify that one lead and one outbox event exist.
- [ ] Run more than one outbox worker and verify that row claiming does not intentionally double-claim an active lease.
- [ ] Simulate a send failure and inspect retry scheduling and terminal dead-letter behavior.
- [ ] Verify that readiness fails when PostgreSQL or Redis is unavailable in shared mode.
- [ ] Inspect CI backup/restore evidence, while keeping the distinction between disposable CI restore and a real-host restore.

The checklist is a reviewer guide. Items must not be marked complete unless they have actually been executed and evidence is available.
