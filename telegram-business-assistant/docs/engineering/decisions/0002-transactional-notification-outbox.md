# ADR-0002: Transactional outbox for administrator notifications

- Status: Accepted
- Date: 2026-11-22
- Project: Telegram Business Assistant

## Context

The previous implementation persisted an enquiry and then attempted to call Telegram directly from the message handler. A process failure or Telegram API outage after the database commit could lose the administrator notification. Retrying the visitor's request was not a safe recovery strategy because it could create another lead.

The notification is a side effect outside the SQLite transaction. The application needs to preserve the intent to notify even when Telegram is temporarily unavailable.

## Decision

Use a transactional outbox stored in the same SQLite database as the lead.

When an administrator chat is configured, the repository inserts the lead and a `lead.created` outbox event in one `BEGIN IMMEDIATE` transaction. If either insert fails, both changes roll back.

The outbox event stores:
- event type;
- lead ID;
- notification destination chat ID;
- delivery state and attempt count;
- availability time, lease timestamp and lease token;
- safe error type metadata;
- created and delivered timestamps.

The payload deliberately does not duplicate the lead's contact details or request description. The worker loads the lead data by ID when it claims an event.

## Delivery lifecycle

```text
pending
   |
   v
processing -- success --> delivered
   |
   +-- retryable failure --> pending (exponential backoff)
   |
   +-- maximum attempts --> dead
   |
   +-- expired lease --> processing (reclaimed by another worker)
```

Current policy:
- one event per lead-created notification, enforced by a unique `(event_type, aggregate_id)` key;
- at most five send attempts;
- retry delay starts at five seconds and doubles after each failure, capped at one hour;
- a 120-second worker lease;
- a random per-claim lease token fences stale workers from marking a newer worker's event as delivered or rescheduled;
- only the exception class name is persisted, not arbitrary exception text that could contain request URLs or secrets;
- the worker polls every two seconds while idle.

## Delivery guarantee

The outbox provides **at-least-once delivery**, not exactly-once delivery.

There is an unavoidable failure window: Telegram can accept a message, then the process can crash before the local event is marked delivered. After the lease expires, another worker may send the same message again. Telegram's sendMessage operation does not provide an idempotency key for this application flow.

The lead-created outbox event itself is unique per lead, and lease fencing prevents stale workers from overwriting a newer claim. These controls do not eliminate the remote-send/acknowledgement ambiguity.

## Why this design

- Enquiry persistence and notification intent commit atomically.
- The Telegram API call no longer blocks the visitor's final handler after the lead is saved.
- Temporary Telegram failures are retried without asking the visitor to resubmit.
- Worker claims are serialized through SQLite write transactions.
- Lease tokens prevent an expired worker from changing a newer worker's state.
- A bounded retry policy prevents infinite rapid retries.

## Consequences and limitations

Positive:
- A process restart does not erase queued notification intent if the database file is on persistent storage.
- Delivery outcomes are inspectable from the outbox table.
- Unit tests can exercise the workflow without a Telegram token or network access.

Negative:
- SQLite remains a single-instance/single-writer choice and is not a shared multi-replica database.
- A dead event requires operator review; there is no admin replay UI or alert integration yet.
- Delivery remains at-least-once, so duplicate remote notifications are possible in the crash window.
- A database failure prevents both lead creation and outbox enqueue, which is intentional atomic behaviour.
- The live hosting environment's persistent-storage guarantee remains unverified.
- The current schema is created idempotently at startup; a general versioned migration framework remains future work.

## Operational requirements

- Do not collect real customer enquiries until host persistence, backup and restore are verified.
- Protect the SQLite file and backups as personal data.
- Review dead events only after checking the destination chat and failure cause.
- Requeue only an event that an operator has reviewed.
- Do not claim exactly-once delivery or production availability from these mechanisms alone.

## Revisit this decision when

- the system needs multiple independent bot replicas;
- the database outgrows SQLite's single-writer operational envelope;
- a managed PostgreSQL database is available and appropriate;
- notification volume or recovery objectives require a dedicated queue/broker;
- operators need automated alerting, replay controls or delivery SLOs.
