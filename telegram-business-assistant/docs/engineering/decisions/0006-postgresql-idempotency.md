# ADR-0006: PostgreSQL idempotency for enquiry submissions

- **Status:** Accepted
- **Scope:** Shared PostgreSQL runtime for Telegram Business Assistant
- **Decision owners:** Project maintainer
- **Date:** 2026-11-23

## Context

Telegram updates can be delivered more than once, and handlers or infrastructure may retry processing after an interruption. Without a replay guard, one user action could create multiple lead records and duplicate notification events.

The application needs a stable identifier for one logical submission and a persistence-level uniqueness guarantee.

## Decision

For Telegram-originated submissions, derive an idempotency key from the Telegram chat/message identity and pass it to the application service as part of the typed `CreateEnquiry` command.

The PostgreSQL adapter stores the nullable key under a unique index. The insert uses `ON CONFLICT (idempotency_key) DO NOTHING`; when the key already exists, the adapter returns the existing lead identifier and does not enqueue a second notification event.

Input policy validates a supplied key before it reaches the persistence adapter. The application service remains independent of Telegram framework types; Telegram-specific identity is translated at the interface boundary.

## Contract and limits

- Reprocessing the same non-null key returns the identifier of the original lead.
- A duplicate key does not create another outbox event.
- A different key represents a different submission, even when the visible enquiry fields happen to match.
- The key is nullable for adapter compatibility. Calls made without a key do not receive the replay-protection guarantee.
- The current key is scoped to the Telegram chat/message identity; it is not a general-purpose deduplication scheme for arbitrary external clients.

## Consequences

### Benefits

- Replay protection is enforced by the database, not only by in-memory handler state.
- Concurrent attempts with the same key converge on one persisted lead.
- Application policy is testable without importing Telegram-specific types.

### Trade-offs

- The identity source must remain stable across retries of the same logical Telegram submission.
- Reusing a key for a different logical action would cause the second insert to resolve to the earlier record; key construction therefore belongs at the transport boundary and must be covered by tests.
- Requests without a key remain outside the idempotency guarantee.

## Evidence in the codebase

- `src/application/enquiries.py`: typed command, validation and repository boundary.
- `src/postgres_database.py`: unique index and conflict-safe insert.
- `docs/engineering/architecture.md`: description of replay-safe enquiry creation.
