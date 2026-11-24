# Operations runbook

## Scope and evidence boundary

This runbook covers the PostgreSQL + Redis Docker Compose deployment and the single-process local fallback. The former Dada Cloud single-worker demo is retired; no current public-host deployment is claimed. This runbook does not certify any provider's storage, network, backup or alert-notification guarantees.

Never paste bot tokens, database credentials or webhook secrets into chat, issues, screenshots or shell transcripts.

## Prerequisites

- Linux host with Docker Engine and Docker Compose V2.
- Reviewed repository commit.
- .env file created on the host with a valid BOT_TOKEN.
- Non-default POSTGRES_PASSWORD, matching DATABASE_URL.
- Persistent storage for PostgreSQL and Redis.
- Access-controlled off-host backup destination and a defined retention period before collecting real personal data.

## Local/shared service startup

From telegram-business-assistant:

    cp .env.example .env
    chmod 600 .env
    # Edit .env: replace BOT_TOKEN and every default password/secret.
    docker compose config
    docker compose up -d --build
    docker compose ps
    docker compose logs --tail=100 bot

The Compose file starts PostgreSQL, Redis and the bot. PostgreSQL and Redis use named volumes. The bot container runs non-root, read-only except tmpfs, drops Linux capabilities and enables no-new-privileges.

Check readiness from inside the container:

    docker compose exec -T bot python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/readyz', timeout=3).read().decode())"

Expected response:

    {"status": "ready"}

Liveness check:

    docker compose exec -T bot python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3).read().decode())"

Prometheus metrics:

    docker compose exec -T bot python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/metrics', timeout=3).read().decode())"

Do not expose PostgreSQL or Redis ports publicly. Expose the bot's HTTP port only through a trusted reverse proxy/load balancer and allow only required paths.

## Runtime modes

### Single polling worker

Set BOT_MODE=polling. Use one active polling process for the bot token. Do not start multiple polling replicas against the same token.

### Multi-replica webhook mode

Set BOT_MODE=webhook, WEBHOOK_BASE_URL=https://bot.example.com, WEBHOOK_SECRET to a random value containing only letters/digits/underscore/hyphen, WEBHOOK_PATH=/telegram/webhook, DATABASE_URL and REDIS_URL.

Requirements:

1. The public URL must use HTTPS.
2. TLS terminates at a trusted reverse proxy/load balancer.
3. The proxy forwards /telegram/webhook, /healthz, /readyz and /metrics to the bot service on port 8080.
4. PostgreSQL and Redis are shared services available to every replica.
5. Configure the hosting platform's health check against /readyz.
6. Scale the bot process only after the first webhook replica is ready.
7. Never run polling and webhook delivery simultaneously for the same bot token.

Redis stores FSM state/data with FSM_STATE_TTL_SECONDS and serializes events by FSM key across replicas. PostgreSQL advisory locks serialize schema migration. Outbox workers use FOR UPDATE SKIP LOCKED to coordinate claims.

## Post-deployment smoke test

Use a test Telegram account and synthetic details only:

1. Open the bot and run /start.
2. Start a new request and confirm the consent step.
3. Complete the form using clearly synthetic contact details.
4. Confirm the bot returns the submission confirmation.
5. Verify one new lead and one outbox event exist in PostgreSQL.
6. Verify the outbox event transitions to delivered when an admin destination is configured.
7. Restart one replica during a deliberately unfinished test conversation; confirm the FSM state survives through Redis.
8. Confirm /readyz stays successful during a rolling restart.
9. Confirm /metrics reflects delivery and outbox counts.
10. Confirm no sensitive fields or tokens appear in logs.

A CI integration test is not a substitute for this live smoke test.

## Outbox inspection (PostgreSQL)

Read aggregate counts:

    docker compose exec -T postgres psql -U assistant -d assistant -c "SELECT status, count(*) FROM notification_outbox GROUP BY status ORDER BY status;"

Inspect event metadata without customer content:

    docker compose exec -T postgres psql -U assistant -d assistant -c "SELECT id, aggregate_id, status, attempts, last_error, created_at FROM notification_outbox WHERE status IN ('pending', 'dead') ORDER BY id DESC LIMIT 20;"

Review dead events manually. Confirm the admin chat configuration and transient/permanent failure cause before replay. Do not blindly reset the attempt count or resend a notification: remote delivery is at-least-once, and a crash after Telegram accepts a send but before the local marker commits may cause duplicates.

## PostgreSQL backup

The repository includes scripts/backup_postgres.sh. It uses pg_dump custom format, validates the archive with pg_restore --list, writes with restrictive permissions and prints a SHA-256 checksum.

For a manual backup from a host with the PostgreSQL client:

    export DATABASE_URL='postgresql://...'
    sh scripts/backup_postgres.sh backups/assistant.dump

Store the dump off-host in encrypted/access-controlled storage. Do not commit dumps to Git. Define a schedule, retention window, owner and alert on failed or stale backups. CI currently tests the dump/restore flow but does not schedule production backups.

## PostgreSQL restore (destructive)

Restore must target an explicitly chosen database. Never point the script at the active production URL unless this is an approved recovery event. The restore script refuses to run without a separate target URL and an explicit confirmation string.

    export RESTORE_TARGET_DATABASE_URL='postgresql://.../restore_test'
    export RESTORE_CONFIRM='I_UNDERSTAND_THIS_REPLACES_DATA'
    sh scripts/restore_postgres.sh backups/assistant.dump

After restore, run application migrations if required, verify core row counts and representative records, and run the smoke test before directing traffic to the restored system. Use a disposable database first. Define and record recovery point objective (RPO) and recovery time objective (RTO).

## Redis recovery

Redis is used for conversation state and event isolation. Configure persistence/replication on the managed Redis service according to the host's guarantees. A restart without persistent Redis may discard unfinished sessions; completed leads remain in PostgreSQL. Verify Redis recovery independently and test that multiple bot replicas share state.

## Routine monitoring and alert rules

Prometheus metrics are available at /metrics, and the Compose stack evaluates alert rules in monitoring/alerts.yml:

- telegram_outbox_delivery_total{result=...}
- telegram_outbox_pending
- telegram_outbox_processing
- telegram_outbox_delivered
- telegram_outbox_dead

Minimum alert policies to configure in the hosting/monitoring platform:

- /readyz remains non-200 for more than 2 minutes.
- bot replicas restart repeatedly within 10 minutes.
- telegram_outbox_dead > 0.
- pending notifications remain above 0 for more than 5 minutes or rise continuously.
- last successful backup exceeds the agreed backup interval.
- PostgreSQL/Redis availability or storage capacity crosses agreed thresholds.

Prometheus evaluates rules locally at 15-second intervals. The UI is bound to 127.0.0.1:9090 in the supplied Compose profile. Alertmanager notification delivery is not configured by default: connect an approved email/chat receiver through the host's secret manager and test delivery before treating alerts as operationally actionable. Thresholds must be tuned to actual traffic; CI alone cannot establish meaningful production SLOs.

## Shutdown

    docker compose down

This retains named data volumes. The following is destructive and deletes the Postgres/Redis volumes:

    docker compose down -v

Do not run the destructive command except during deliberate environment teardown.

## Deployment acceptance checklist

The former Dada Cloud deployment used one background worker and Telegram long polling. It is retired and is not a supported live environment for the current shared-runtime release.

Before treating a new host as production-ready:

- Provision PostgreSQL and Redis with documented persistent-storage and recovery guarantees.
- Add DATABASE_URL, REDIS_URL, BOT_MODE, webhook URL, webhook secret and other settings through the provider's private secret manager.
- Confirm a public HTTPS webhook endpoint and a health check against /readyz.
- Deploy one webhook replica first, then run the full smoke test and restart test.
- Configure scheduled off-host PostgreSQL backups and retention; verify an actual restore on the target host.
- Configure an Alertmanager or provider-native receiver and test notification delivery.
- Record the host, release commit, test results, backup timestamp and restore evidence.

CI tests against disposable services are useful evidence, but they do not replace host-level verification. Do not collect real customer enquiries until the required checks have passed and their results are recorded.
