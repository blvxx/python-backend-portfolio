# Security threat model

## Scope and status

This is a lightweight design-level threat model for the current Telegram Business Assistant MVP. It is not a penetration-test report, compliance assessment or claim of production security certification.

The current application does not use an LLM. AI-specific threats are listed as future considerations only.

## Assets

| Asset | Why it matters |
|---|---|
| Bot token | Allows an actor to operate the Telegram bot |
| Enquiry contact details | Personal data supplied by visitors |
| Request descriptions | May contain personal or business-confidential information |
| Administrator access | Allows viewing stored enquiries |
| SQLite database and backups | Durable copy of enquiry records |
| Deployment secrets | Control access to the runtime and integrations |

## Trust boundaries

1. Visitor-controlled Telegram messages and callback data.
2. Telegram Bot API and the external network.
3. Application process and its environment variables.
4. Persistent database volume and backup storage.
5. Administrator Telegram account and configured admin chat.
6. Hosting provider and deployment control plane.

## Existing controls in code

- The bot asks for consent before collecting contact details.
- The bot warns users not to submit passwords, authentication codes or payment details.
- SQL queries use parameters.
- User-provided strings included in HTML-formatted Telegram messages are escaped.
- The leads command checks the configured administrator user ID and requires a private chat.
- Lead creation and optional notification enqueue occur in one SQLite transaction.
- Outbox updates use per-claim lease tokens so an expired worker cannot overwrite a newer claim.
- Arbitrary exception text is not stored; the outbox records exception type names only.
- The bot token is read from an environment variable.
- The Docker container runs as a non-root user, uses a read-only root filesystem, drops Linux capabilities and enables no-new-privileges.
- Docker Compose stores the SQLite directory in a named volume for that deployment mode.

These controls reduce specific risks but do not establish that the live hosted deployment is production-ready.

## Threats and gaps

| Threat | Current mitigation | Gap / next action |
|---|---|---|
| Bot token disclosure | Environment variable; env file ignored by Git | Verify host secret handling and rotate if exposure is suspected |
| Unauthorized enquiry access | leads command checks admin user ID and private chat context | Continue reviewing other admin routes as they are added |
| Malicious message content | HTML escaping and input length limits | Add abuse controls, rate limiting and broader boundary tests |
| Data loss | Docker named volume in Compose setup | Verify actual host persistence and test backup/restore |
| Excessive data retention | No retention workflow implemented | Define retention policy and deletion workflow |
| Notification failure | Transactional outbox, bounded retry, lease fencing and dead state | Add alerting and an operator replay interface; duplicate delivery remains possible in the remote-send crash window |
| Sensitive data in logs | No deliberate logging of message bodies in current handlers | Review dependency/runtime logs and operational access |
| Service abuse / flooding | No explicit application rate limit | Add per-user limits and resource bounds |
| Supply-chain risk | Dependency version ranges are declared | Add lock/constraint strategy and dependency/security scanning |
| Admin account compromise | Telegram user ID check | Define operational account protection and restrict admin chat membership |

## Future AI-specific controls

Only apply these controls if an LLM or agent capability is added:

- Treat user messages, retrieved documents and model outputs as untrusted data.
- Separate system instructions from user-controlled content.
- Do not let model output directly execute arbitrary code or SQL.
- Use allowlisted, typed tools with least-privilege credentials.
- Require human confirmation for external side effects.
- Validate model output against a strict schema before use.
- Set timeouts, token budgets, tool-call limits and cost limits.
- Evaluate prompt-injection and data-exfiltration test cases.
- Keep secrets and unnecessary personal data out of model context.
- Log model/version/prompt identifiers and outcome metadata without logging sensitive payloads by default.

## Release gate for real customer data

Do not enable real customer enquiry collection until all of the following are verified:
- persistent storage behaviour on the selected host;
- backup and restore procedure on a test copy;
- an approved retention and deletion policy;
- administrator access restrictions;
- operational ownership and incident contact;
- privacy information appropriate to the actual operator and jurisdiction.

This checklist is a project safeguard, not legal advice.
