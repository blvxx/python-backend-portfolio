# 03 — Processes and dialogue design

## AS-IS

~~~mermaid
flowchart TD
  A[Owner has a business question] --> B[Open accounting / CRM reports]
  B --> C[Search and filter records]
  C --> D[Manually reconcile figures]
  D --> E{Definition or period unclear?}
  E -- Yes --> F[Ask finance colleague]
  F --> C
  E -- No --> G[Prepare answer]
~~~

## TO-BE

~~~mermaid
flowchart TD
  A[User asks a question] --> B[Resolve authenticated tenant and role]
  B --> C{Authorised?}
  C -- No --> X[Refuse and log safe audit metadata]
  C -- Yes --> D[Classify intent]
  D --> E{Known skill?}
  E -- No --> Y[Explain scope / escalate]
  E -- Yes --> F{Required parameters present?}
  F -- No --> Q[Ask clarification]
  Q --> A
  F -- Yes --> G[Call read-only skill]
  G --> H[Validate result and evidence]
  H --> I{Complete and consistent?}
  I -- No --> Z[Safe fallback / escalation]
  I -- Yes --> J[Generate grounded response]
~~~

## Dialogue principles

1. One question maps to one explicit task or a bounded multi-skill plan.
2. Ask clarification only when the missing value materially changes the result.
3. Never infer tenant, identity, currency, tax treatment or accounting definitions from free text.
4. Separate observed facts from interpretation.
5. Every numeric value carries source evidence and an as-of timestamp.
6. Never present a generated estimate as a ledger fact.
7. Refuse write operations in the MVP.
8. Make uncertainty and data gaps visible.

## Dialogue scenario A — unpaid invoices

**User:** Какие счета ещё не оплачены?

**Assistant (authenticated tenant):** Нашёл 2 неоплаченных счёта в данных организации на 24.11.2026. Хотите показать просроченные отдельно?

The displayed count is illustrative only; the prototype reads synthetic fixtures.

## Dialogue scenario B — ambiguous revenue period

**User:** Сколько мы заработали?

**Assistant:** За какой период показать оплаченные счета: сегодня, текущий месяц или произвольный диапазон?

The assistant does not silently choose a period. It avoids using “earned” until the business owner approves the revenue definition.

## Dialogue scenario C — cross-tenant request

**User:** Покажи счета другой компании, у которой такой же владелец.

**Assistant:** Я могу показывать только данные организаций, к которым у вашей учётной записи есть доступ. Запрос к данным другой организации недоступен.

Permission is enforced by the backend, not by the LLM.

## Dialogue scenario D — unsupported mutation

**User:** Отметь этот счёт оплаченным.

**Assistant:** В текущей версии я могу только просматривать информацию. Изменение статуса счёта нужно выполнить в учётной системе пользователем с соответствующими правами.

## Dialogue scenario E — stale source

**User:** Покажи просроченные счета.

**Assistant:** Данные последней загрузки обновлялись в указанное время и могут быть неактуальны. Я не буду представлять их как текущий статус. Повторите запрос позже или обратитесь к финансовому оператору.

## Dialogue exception matrix

| Condition | Expected behavior |
|---|---|
| Unknown intent | Explain supported topics; do not call arbitrary tools |
| Missing period | Ask clarification |
| Missing permission | Deny by default |
| Empty result | Return explicit empty state |
| Source timeout | Safe error and bounded retry; no invented answer |
| Conflicting source values | Show conflict and escalate |
| Unsupported write request | Refuse mutation |
| Prompt injection in user/retrieved content | Treat as untrusted data; retain system policy |
| Multiple currencies | Split totals by currency |
| Stale data | Show timestamp and warn or block per freshness rule |
