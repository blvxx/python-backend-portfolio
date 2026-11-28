# Architecture Decision Records

These records describe two deliberately separate runtime profiles for Telegram Business Assistant.

- **ADR-0001–ADR-0003** describe the local, single-instance fallback (SQLite, local conversation state and Telegram polling).
- **ADR-0004–ADR-0006** describe the shared, multi-replica profile (PostgreSQL, Redis and HTTPS webhooks).

The profiles coexist. A decision scoped to SQLite or local development must not be read as a guarantee for the shared deployment profile, and CI evidence does not prove that the shared profile has been deployed to a public host.

| ADR | Decision | Scope |
|---|---|---|
| [ADR-0001](./0001-storage-and-state.md) | Storage and conversation state | Local SQLite / single instance |
| [ADR-0002](./0002-transactional-notification-outbox.md) | Transactional notification outbox | Local SQLite / single instance |
| [ADR-0003](./0003-idempotent-telegram-submissions.md) | Idempotent Telegram submissions | Local SQLite / single instance |
| [ADR-0004](./0004-shared-runtime.md) | PostgreSQL, Redis and webhook runtime | Shared multi-replica profile |
| [ADR-0005](./0005-postgresql-transactional-outbox.md) | PostgreSQL transactional outbox | Shared multi-replica profile |
| [ADR-0006](./0006-postgresql-idempotency.md) | PostgreSQL idempotency for enquiries | Shared multi-replica profile |

## Current deployment boundary

The shared profile is implemented and exercised by service-backed CI, including PostgreSQL/Redis integration and a disposable PostgreSQL backup/restore drill. It has not been deployed and verified on a public host. See the [architecture](../architecture.md), [operations runbook](../operations/runbook.md) and [engineering roadmap](../roadmap.md) for current operational gaps.
