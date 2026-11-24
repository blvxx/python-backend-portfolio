# Monitoring profile

The Compose stack starts Prometheus on 127.0.0.1:9090. The Prometheus server scrapes the bot's internal /metrics endpoint every 15 seconds and evaluates alert rules from alerts.yml.

## Included alert rules

- Metrics target down for 2 minutes.
- One or more dead-letter notification events.
- More than 10 pending notifications for 5 minutes.
- Pending notifications with no delivery outcome for 10 minutes.

The alert rules become visible under the Alerts view in the Prometheus UI. They are alert conditions, not proof that a notification destination is configured. For external notifications, connect Alertmanager to an approved email/chat webhook and manage the destination credentials outside Git.

## Local check

    docker compose up -d --build
    docker compose ps
    curl http://127.0.0.1:9090/-/ready
    curl http://127.0.0.1:9090/api/v1/rules

Prometheus is bound to loopback in the provided local Compose file. Do not expose its UI publicly without authentication and network restrictions.

## Production configuration

For a hosted deployment, configure a Prometheus-compatible service to scrape the bot's internal metrics endpoint, load alerts.yml, and attach an Alertmanager notification receiver. Configure credentials and routing using the host's secret manager. Verify delivery with a test alert and document the responsible on-call recipient.

Dada Cloud has not yet been configured with this monitoring stack. Do not claim that alerts are being delivered there until a live test notification is recorded.
