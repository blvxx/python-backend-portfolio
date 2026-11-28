# ADR-0001: Storage and conversation state

- Status: Accepted for the local, single-instance profile; notification delivery is specified in ADR-0002
- Scope: SQLite and local conversation state / single-instance profile
- Date: 2026-11-22
- Project: Telegram Business Assistant

## Context

The portfolio MVP needs to save structured enquiries and guide one visitor through a multi-step Telegram conversation. The current deployment is a single long-polling worker.

The application currently uses SQLite through aiosqlite for saved enquiries and aiogram MemoryStorage for in-progress conversation state.

## Decision

Keep SQLite for the documented single-instance MVP while persistence, backup and restore behaviour are verified in the target hosting environment. Manage schema evolution with forward-only migrations tracked by PRAGMA user_version.

Keep MemoryStorage for the demo's conversational state, with the explicit limitation that in-progress flows are lost when the process restarts.

Do not claim multi-instance readiness or guaranteed delivery of administrator notifications.

## Rationale

- SQLite has no separate database service to provision for a small single-instance demonstration.
- The schema and access patterns are simple.
- The current project has no demonstrated multi-replica requirement.
- MemoryStorage keeps setup simple for a disposable demo.

## Consequences and limitations

Positive:
- Few infrastructure dependencies.
- Simple local setup and Docker Compose deployment.
- Low operational complexity for a portfolio MVP.

Negative:
- SQLite is not a shared write store for multiple replicas.
- Data durability depends on the storage volume being persistent and backed up.
- MemoryStorage loses unfinished conversations on restart.
- The database schema uses forward-only migrations tracked with SQLite PRAGMA user_version; automated downgrade is intentionally unsupported.
- Administrator notification intent is persisted through the SQLite transactional outbox described in ADR-0002; delivery remains at-least-once.
- The current hosted storage persistence is unverified.

## Revisit this decision when

- more than one application replica is required;
- concurrent write load exceeds the operational envelope of the single-instance SQLite setup;
- durable cross-replica conversation state is required;
- formal recovery objectives require tested automated backups and restore procedures.

## Migration direction

When requirements justify it, evaluate PostgreSQL for durable enquiry data and Redis for shared FSM state. Migration should include schema migrations, data export/import validation, rollback procedures and restore testing.

Do not add Redis or PostgreSQL solely to make the technology list longer. Add them when system requirements justify the operational cost.
