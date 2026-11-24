# ADR 0001: Persist notifications through a transactional outbox

- **Status:** Accepted
- **Scope:** Telegram Business Assistant
- **Decision owners:** Project maintainer
- **Date:** 2026-11-23

## Context

Creating a business enquiry has two effects: persist the enquiry and notify an administrator through Telegram. Sending the remote notification before committing the enquiry can leave a notification without durable application data. Sending after the commit without recording delivery intent can lose the notification if the process stops between those operations.

The application therefore needs a durable hand-off between the database transaction and an external side effect.

## Decision

Persist the enquiry and its notification-outbox row in the same PostgreSQL transaction. A background dispatcher claims due rows and sends the notification through a separate adapter.

Workers coordinate using PostgreSQL row locks with `FOR UPDATE SKIP LOCKED`. A claimed event receives a lease token and timestamp. The lease allows another worker to reclaim a row after an interrupted worker stops making progress. A successful send is marked delivered only when the lease token still matches the active processing record.

Transient delivery failures are rescheduled with bounded exponential backoff. The dispatcher has a finite attempt limit; exhausted events move to a dead-letter state for investigation rather than retrying forever.

## Delivery semantics

The external Telegram send and the PostgreSQL delivered marker cannot be committed atomically. Delivery is therefore **at-least-once**, not exactly-once.

A process can successfully send a Telegram message and then crash before updating the outbox row. After the lease expires, another worker may send the same notification again. The system prefers a possible duplicate notification over silently losing a committed enquiry notification.

This behavior is explicitly documented and tested as a failure boundary; it must not be described as exactly-once delivery.

## Consequences

### Benefits

- Enquiry persistence and notification intent are committed atomically.
- Multiple workers can claim different due events without intentionally processing the same locked row.
- A crashed worker's lease can expire and be reclaimed.
- Retry attempts and dead-letter outcomes are observable.
- Telegram transport concerns remain outside the enquiry application service.

### Trade-offs and operational requirements

- Duplicate remote notifications remain possible in the send/acknowledgement failure window.
- Dead-letter events require an operator workflow; this repository does not claim an on-call process or production alert delivery.
- Lease duration and retry settings must be chosen with expected Telegram API latency in mind.
- The current CI restore test validates the database procedure in a disposable environment; it does not establish a production backup schedule or host-level recovery capability.

## Alternatives considered

1. **Send inline during enquiry creation.** Rejected because a slow or failed remote API would couple user-facing submission to notification delivery and leave a gap between database persistence and remote side effects.
2. **Commit first, then send without an outbox.** Rejected because process termination between the commit and send can lose the notification permanently.
3. **Claim exactly-once delivery.** Rejected because the database and remote Telegram API do not share a transaction or idempotency protocol for this message send.

## Evidence in the codebase

- `src/postgres_database.py`: atomic lead/outbox insert, row-lock claiming and lease-token updates.
- `src/application/notifications.py`: dispatcher, bounded retry, dead-letter outcome and delivery metrics.
- `docs/engineering/architecture.md`: runtime architecture and known delivery limitation.
