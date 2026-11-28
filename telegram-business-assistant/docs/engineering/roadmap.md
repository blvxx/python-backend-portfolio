# Engineering roadmap

## Guiding rule

Items in the implemented section are supported by the current source and/or automated CI. Host-level claims are listed separately and remain open until verified on a real deployment. A planned item is not evidence that a feature exists.

## Implemented and checked in CI

- [x] Framework-independent enquiry application service, typed command and repository boundary.
- [x] Handler and application tests for consent, validation, cancellation, stale callbacks and administrator authorization.
- [x] Transactional notification outbox with bounded retries, lease fencing and dead-letter state.
- [x] Replay-safe enquiry creation keyed by Telegram chat/message identity.
- [x] Forward-only schema migrations.
- [x] Shared PostgreSQL adapter with atomic lead/outbox writes, advisory-locked migrations and SKIP LOCKED worker claims.
- [x] Redis-backed FSM state with TTL and per-conversation event isolation across replicas.
- [x] HTTPS webhook runtime profile for multi-replica operation; polling remains single-replica only.
- [x] /healthz, /readyz and /metrics endpoints.
- [x] Prometheus configuration and alert-rule validation in CI.
- [x] Service-backed CI integration against PostgreSQL and Redis, plus a PostgreSQL dump/restore drill against a disposable database.
- [x] Docker image build and Ruff checks in CI.

## Remaining host-level verification

- [ ] Deploy the shared PostgreSQL/Redis/webhook profile to a maintained host.
- [ ] Verify PostgreSQL and Redis persistence across container recreation, host restart and provider maintenance.
- [ ] Configure scheduled off-host PostgreSQL backups, retention and backup-failure alerting.
- [ ] Complete and record a restore drill on the target host, not only in disposable CI services.
- [ ] Configure Alertmanager or provider-native alert notification delivery and verify that notifications arrive.
- [ ] Run the full Telegram Bot API smoke test and restart test using synthetic data.
- [ ] Define customer-data retention, deletion and privacy-notice requirements before accepting real enquiries.
- [ ] Add structured logs with correlation identifiers and sensitive-field redaction.
- [ ] Add dependency vulnerability review and a documented release/rollback procedure.

## Acceptance before real customer data

A deployment is not considered ready for real customer enquiries until it has:

1. Documented persistent PostgreSQL and Redis storage.
2. A tested scheduled backup with off-host retention.
3. A successful host-level restore drill.
4. Tested alert notification delivery.
5. A passing live smoke test and restart/recovery test.
6. A documented retention policy and customer-facing privacy notice.

## Current project status

The former Dada Cloud demo was a single long-polling worker. It is retired and is not presented as a live service. The current PostgreSQL/Redis/webhook runtime is validated through CI, including service-backed integration tests and a disposable PostgreSQL backup/restore drill, but it has not been deployed to a public host.

- Source: https://github.com/blvxx/python-backend-projects/tree/main/telegram-business-assistant
- Operations runbook: ./operations/runbook.md
- Architecture: ./architecture.md
- CI workflow: https://github.com/blvxx/python-backend-projects/actions/workflows/telegram-business-assistant.yml

CI does not prove host-level persistence, external backup scheduling, alert-notification delivery, Telegram Bot API delivery or production uptime. Those claims remain out of scope until independently verified.
