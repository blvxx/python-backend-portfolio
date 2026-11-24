# Deploy Telegram Business Assistant — Koyeb + Neon + Upstash

This guide describes a **free-tier evaluation deployment** of the existing PostgreSQL + Redis + HTTPS webhook profile. It does not turn the project into a production-ready customer service.

> **Free-tier limitation:** Koyeb's Free Instance is a small Web Service (512 MB RAM, 0.1 vCPU, 2 GB SSD), not a separate Worker Service. It scales to zero after one hour without incoming traffic and cannot use persistent Koyeb volumes. The app must therefore run as one small webhook Web Service and keep durable leads in managed PostgreSQL rather than in the container filesystem. Do not collect real customer enquiries on this evaluation deployment. Koyeb itself describes Free Instances as for testing and hobby projects, not production. See [Koyeb instance limits](https://www.koyeb.com/docs/reference/instances) and [scale-to-zero behavior](https://www.koyeb.com/docs/run-and-scale/scale-to-zero).

## 1. Runtime architecture

```text
Telegram
   |
   | HTTPS webhook
   v
Koyeb Web Service (Docker, one replica)
   |-- aiogram webhook endpoint
   |-- /healthz, /readyz, /metrics
   |-- in-process outbox worker
   |
   +---- Neon PostgreSQL (leads + notification outbox)
   |
   +---- Upstash Redis (FSM state + event isolation)
```

The service uses the existing project Dockerfile and the `BOT_MODE=webhook` profile. PostgreSQL stores enquiries and pending notifications in one transaction; Redis stores conversational state. The Koyeb-generated public domain is read from `KOYEB_PUBLIC_DOMAIN` when `WEBHOOK_BASE_URL` is not explicitly set. The HTTP listener uses `WEB_SERVER_PORT` first and falls back to Koyeb's injected `PORT`.

## 2. Create the managed data services

### Neon PostgreSQL

1. Create a project in [Neon](https://neon.com/).
2. Choose a region close to the Koyeb service, if available.
3. Copy the pooled or direct connection string for the primary database.
4. Ensure it uses TLS, for example `sslmode=require`.
5. Store it privately; do not commit it to Git.

The Neon Free plan currently includes 1 GB of storage and 100 CU-hours per project per month. Compute can scale down while idle; the first database connection after idle may have a cold-start delay. Watch usage in the Neon console. Source: [Neon Free plan update, 2 October 2026](https://neon.com/blog/neon-free-plan-1-gb-per-project).

### Upstash Redis

1. Create a Redis database in [Upstash](https://upstash.com/).
2. Select a region near the Koyeb service if available.
3. Copy the TLS connection URL / Redis URL.
4. It should use the `rediss://` scheme for TLS, for example `rediss://default:<password>@<host>:6379`.
5. Store the URL privately.

Upstash's current Free Redis tier includes 250 MB of data, 500,000 commands per month and 10 GB monthly bandwidth. Monitor usage; requests above free limits may require an upgrade or be rate-limited. Source: [Upstash Redis pricing](https://upstash.com/pricing/redis).

## 3. Prepare the Telegram bot

1. Create the bot through Telegram's official `@BotFather`, or use the existing bot token.
2. Keep the token in a password manager or Koyeb Secret. Never paste it into Git, a README, a screenshot or a chat.
3. Initially leave `ADMIN_CHAT_ID` and `ADMIN_USER_ID` empty. Add them only after the first smoke test and administrator identity check.
4. Do not run polling and webhook mode simultaneously for the same bot token. This deployment uses webhook mode.

## 4. Create a Koyeb Web Service from GitHub

1. Open [Koyeb](https://app.koyeb.com/) and choose **Create Web Service**.
2. Choose **GitHub** as the source and authorise the Koyeb GitHub App for this repository only.
3. Select `blvxx/portfolio`, branch `main`.
4. Set the work directory / root directory to `telegram-business-assistant`.
5. Choose the **Dockerfile** builder and Dockerfile path `Dockerfile`.
6. Choose a **Web Service**, not a separate Worker Service.
7. For a no-charge evaluation, select the **Free Instance** if the account and region offer it. The Free Instance is available only in supported regions (currently Frankfurt or Washington, D.C.) and one per organisation.
8. Expose port `8080` with protocol **HTTP**. The container listens on `0.0.0.0`.
9. Configure an HTTP health check to `/readyz` on the exposed port if the control panel offers it; otherwise the platform's default TCP probe still checks whether the listener accepts connections.
10. Note the generated public Koyeb domain after the service is created. The application reads `KOYEB_PUBLIC_DOMAIN` automatically; you do not need to commit a fixed host name.

Koyeb's official GitHub deployment flow: [Deploy with GitHub](https://www.koyeb.com/docs/build-and-deploy/deploy-with-git). Port and health-check configuration: [Exposing your Service](https://www.koyeb.com/docs/build-and-deploy/exposing-your-service) and [Health Checks](https://www.koyeb.com/docs/run-and-scale/health-checks).

## 5. Set runtime environment variables

Add these in the Koyeb Service's environment/Secrets configuration. Mark credentials as **Secret** rather than plain text when the console supports it.

| Variable | Value |
|---|---|
| `BOT_TOKEN` | Secret from BotFather |
| `BOT_MODE` | `webhook` |
| `DATABASE_URL` | Neon PostgreSQL connection string with TLS |
| `REDIS_URL` | Upstash TLS URL beginning `rediss://` |
| `WEBHOOK_SECRET` | Random secret using only letters, digits, underscore and hyphen |
| `WEBHOOK_PATH` | `/telegram/webhook` |
| `WEB_SERVER_HOST` | `0.0.0.0` |
| `WEB_SERVER_PORT` | `8080` (or omit to use Koyeb's `PORT`) |
| `FSM_STATE_TTL_SECONDS` | `86400` |
| `ADMIN_CHAT_ID` | Leave blank for initial smoke test |
| `ADMIN_USER_ID` | Leave blank for initial smoke test |

Do not set `WEBHOOK_BASE_URL` on the first deployment unless you already know the exact Koyeb public URL. The application uses the platform-provided `KOYEB_PUBLIC_DOMAIN` as an HTTPS fallback. An explicitly supplied `WEBHOOK_BASE_URL` takes precedence.

Do not set `POSTGRES_PASSWORD` or `DATABASE_URL` to example values from `.env.example`; Neon provides the real connection string.

## 6. First deployment and smoke test

After Koyeb reports a healthy deployment:

1. Open the Koyeb public URL in a browser and confirm that `/healthz` returns a liveness response.
2. Check `/readyz`; it should return HTTP 200 with `{"status":"ready"}` only when PostgreSQL and Redis are reachable.
3. Check `/metrics` and confirm the metrics endpoint responds.
4. Open the Telegram bot from a **test account** and send `/start`.
5. Complete one enquiry using clearly synthetic contact details and no real personal information.
6. Confirm the user-facing success message.
7. If an administrator destination has been safely configured, confirm one notification reaches the intended private chat.
8. Check Koyeb logs for startup errors, database reconnects and webhook registration. Do not paste logs containing secret values into public issues.

### Configure administrator notifications after the smoke test

1. Open the bot from the intended administrator account and send `/start`.
2. Send `/my_id` and read the IDs in Telegram.
3. Set `ADMIN_CHAT_ID` to the private chat ID where notifications should be delivered.
4. Set `ADMIN_USER_ID` to the numeric Telegram user ID allowed to use `/leads`.
5. Redeploy and verify with a synthetic test enquiry.

Keep the IDs private. The bot's administrator command is restricted to the configured user ID and a private chat.

## 7. Operational limitations and data safety

- **Cold start:** Koyeb Free scales the web service to zero after one hour without inbound traffic. A Telegram webhook can wake the service, but the first delivery may experience a startup delay. Telegram may retry failed webhook deliveries; monitor this behavior instead of assuming immediate delivery.
- **No dedicated Worker Service:** the free plan does not permit a separate Worker Service. The app's outbox worker runs inside the web process while that process is alive; it stops while the service is asleep.
- **Memory/CPU:** 512 MB RAM and 0.1 vCPU are suitable only for a low-volume evaluation. Memory pressure, cold starts and rate limits are possible.
- **Database usage:** Neon compute has a monthly CU-hour limit and scales down while idle. Watch for connection/cold-start latency and usage exhaustion.
- **Redis usage:** Upstash has monthly storage, bandwidth and command limits on the free plan. Watch the dashboard.
- **No Koyeb volume:** do not use the container filesystem as durable storage. Leads must remain in external PostgreSQL.
- **Backups:** CI proves the repository backup/restore scripts against disposable PostgreSQL services, not a real Neon restore. Configure and test a separate backup and restore procedure before real customer data is accepted.
- **Privacy:** before production, publish an appropriate privacy notice and retention period, define access controls, validate off-host backups, and test an actual restore.
- **Not production:** do not market this free-tier configuration as an uptime-guaranteed service. Koyeb explicitly positions Free Instances for testing and hobby projects.

## 8. Troubleshooting

| Symptom | Check |
|---|---|
| App exits with missing BOT_TOKEN | Add the token as a Koyeb Secret and redeploy |
| Webhook mode rejects DATABASE_URL | Ensure the Neon URL starts with `postgresql://` or `postgres://` |
| Webhook mode rejects REDIS_URL | Use the Upstash Redis TLS URL, normally `rediss://` |
| HTTPS WEBHOOK_BASE_URL missing | Confirm the service is a public Koyeb Web Service and `KOYEB_PUBLIC_DOMAIN` is present; optionally set the exact HTTPS `WEBHOOK_BASE_URL` |
| Koyeb port check fails | Expose HTTP port 8080 and set `WEB_SERVER_HOST=0.0.0.0`; verify `WEB_SERVER_PORT` / `PORT` |
| `/readyz` fails | Inspect PostgreSQL/Redis credentials, TLS and service availability |
| Bot is slow after an idle period | This may be Koyeb Free scale-to-zero; inspect cold-start and webhook retry logs |
| Admin does not receive enquiries | Confirm the admin sent `/start`, then verify `ADMIN_CHAT_ID` and `ADMIN_USER_ID` |

## Deployment status

This document is a deployment runbook. It does not claim that the bot has already been deployed to Koyeb. A deployment is complete only after the Koyeb service is created, the first health checks pass, a synthetic Telegram enquiry is accepted, and the recovery/backup limitations are understood.
