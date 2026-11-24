# ADR-0004: PostgreSQL, Redis and webhook runtime for horizontal scaling

- Status: Accepted in source code; host deployment not yet verified
- Date: 2026-11-22

## Context

The original runtime used Telegram long polling, SQLite and aiogram MemoryStorage. That is a reasonable local/single-instance MVP, but it has three scaling and reliability limits:

1. Telegram long polling must not be active in several replicas for the same bot token.
2. SQLite is not the intended shared database for independently scaled application replicas.
3. MemoryStorage loses unfinished conversations on restart and cannot share FSM state across replicas.

## Decision

Keep polling + SQLite + MemoryStorage as an explicit local/single-instance fallback. Add a separate shared deployment profile with:

- Telegram HTTPS webhooks handled by aiogram's aiohttp integration.
- PostgreSQL as the shared source of truth for leads and notification outbox.
- RedisStorage for shared FSM state/data with a bounded TTL.
- Redis event isolation so updates for the same FSM key are processed sequentially across replicas.
- PostgreSQL row locking with SKIP LOCKED so independent outbox workers do not claim the same row.
- PostgreSQL advisory locking for serialized forward-only schema migrations.
- /healthz, /readyz and /metrics endpoints for orchestration and monitoring.

Webhook mode is rejected at configuration time unless a PostgreSQL URL, Redis URL, public HTTPS webhook URL and secret token are configured.

## Consequences

### Positive

- Conversation state is shared and survives process restart until TTL expiry.
- Multiple webhook replicas can accept updates behind a load balancer.
- Multiple outbox workers can coordinate through PostgreSQL row locks.
- The service exposes liveness, dependency readiness and Prometheus metrics.
- PostgreSQL backup and restore scripts are available and exercised by CI against a disposable database.

### Trade-offs and remaining work

- The multi-replica profile requires managed/operated PostgreSQL, Redis, TLS termination and a load balancer.
- The Dada Cloud demo has not been migrated to these services; the currently verified hosted topology remains a single polling worker.
- CI restore verification is not a production backup schedule and does not prove off-host retention.
- Telegram notification delivery remains at-least-once, not exactly-once.
- Capacity limits, pool sizing, rate limits and SLO alert thresholds must be validated against a real workload.

## Validation

GitHub Actions uses PostgreSQL and Redis service containers to test:

- Concurrent idempotent submission from separate database pools.
- Two workers claiming two different outbox events with SKIP LOCKED.
- FSM state surviving storage reconnect and being visible through a second Redis connection.
- Per-FSM-key event isolation shared by separate Redis storage instances.
- PostgreSQL dump/restore to a separate disposable database.

These tests validate the integration contracts; they do not represent a production load test or a Dada Cloud deployment verification.
