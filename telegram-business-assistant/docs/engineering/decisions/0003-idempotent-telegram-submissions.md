# ADR-0003: Idempotent Telegram enquiry submissions

- Status: Accepted
- Scope: SQLite persistence / single-instance profile
- Date: 2026-11-22
- Project: Telegram Business Assistant

## Context

Telegram updates may be processed more than once in retry or concurrent-processing scenarios. Enquiry creation also creates an optional notification outbox event. Without an idempotency boundary, replaying the same user message could produce multiple leads and multiple administrator notifications.

The application needs to distinguish a repeated delivery of the same Telegram message from a genuinely new enquiry.

## Decision

Use a stable idempotency key derived from the Telegram chat ID and message ID:

`telegram:<chat_id>:<message_id>`

The handler places the key on the typed `CreateEnquiry` command. The application service trims and validates the key (non-empty, at most 200 characters) before calling the persistence boundary.

SQLite migration version 3 adds a nullable `idempotency_key` column to `leads` and a unique index. Existing records remain valid because the column is nullable.

The database adapter uses `BEGIN IMMEDIATE` and performs the following in one transaction:

1. Look up an existing lead with the supplied key.
2. If it exists, commit the read transaction and return its ID without inserting another lead or outbox event.
3. Otherwise insert the lead with the key.
4. Insert the optional notification outbox event.
5. Commit both records atomically.

The uniqueness constraint is the final database-level guard; the write transaction serializes concurrent replay attempts.

## Consequences

Positive:
- Repeated processing of the same Telegram message returns the original lead ID.
- Replays do not create a second outbox event.
- Concurrent requests using the same key converge on one lead.
- Existing data is preserved when upgrading through the forward-only migration.

Limitations:
- The key is scoped to Telegram chat/message identity; it is not a general-purpose API idempotency design.
- The handler still depends on the active FSM state to reach the final submission use case. The idempotency key protects repeated submissions that reach the application service, but does not make in-memory FSM state durable.
- The database currently returns the original lead for a previously used key. A future external API should define explicit same-key/different-payload conflict semantics and retention rules before reusing this pattern.
- Idempotent enquiry creation does not make Telegram message delivery exactly-once. The notification outbox remains at-least-once and can produce a duplicate in the remote-send/acknowledgement crash window.

## Validation

Tests cover:
- repeated submission with the same key returns the same lead ID;
- only one lead and one outbox event exist after a replay;
- concurrent submissions through separate database adapters with the same key converge on one lead;
- different keys create different leads;
- application-level key normalization and invalid-key rejection;
- migration adds the nullable column and unique index to an existing version-1 database.

## Revisit this decision when

- the application adds non-Telegram API clients;
- idempotency keys need an explicit expiry/retention policy;
- same-key/different-payload requests must return a conflict rather than reuse the first result;
- durable workflow recovery is redesigned independently of Telegram FSM state.
