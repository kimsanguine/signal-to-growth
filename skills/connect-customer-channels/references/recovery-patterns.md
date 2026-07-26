# Recovery patterns

Recover missing or ambiguous connector state without duplicating customer-visible effects.

## Inbound pattern

Process inbound requests in this order:

```text
raw request
  -> verify provider contract
  -> check freshness and replay
  -> write durable inbox identity
  -> acknowledge provider
  -> parse
  -> normalize
  -> redact
  -> deduplicate
  -> append CS event
  -> hand off to triage
```

- Verify against the raw body before parsing when the contract requires it.
- Keep model work outside the provider acknowledgement path.
- Persist only an encrypted restricted pointer to the raw payload.
- Use a unique provider identity or stable documented fields.
- Dead-letter an event when identity cannot be derived safely.

## Outbound pattern

Keep outbound disabled by default. When a later approved writer executes, use:

```text
approved immutable action
  -> transactional outbox
  -> provider validation
  -> one idempotent submission
  -> accepted receipt
  -> callback or polling
  -> append delivery event
  -> project current state
```

- Keep provider acceptance separate from delivery and read.
- Preserve every attempt.
- Keep a fallback provider or SMS attempt separate from the original attempt.
- Reconcile an ambiguous timeout before considering another submission.

## Idempotency

- Derive inbox identity from the provider event ID and scoped connection.
- Derive a canonical event ID deterministically from stable provider fields.
- Reject model-generated or timestamp-only identity when the provider can resend.
- Place a uniqueness check before downstream processing.
- Reuse the same immutable approved action ID for safe provider retries only when the provider contract supports it.
- Treat authentication nonce or replay protection as distinct from message idempotency.

## Status projection

Append observations and project state; do not rewrite history.

Use:

```text
draft -> validated -> approved -> submitted
submitted -> accepted | failed | unknown
accepted -> queued | sent | delivered | failed | expired | unknown
queued -> sent | delivered | failed | expired | unknown
sent -> delivered | read | failed | expired | unknown
delivered -> read
```

- Allow only evidence-backed forward transitions.
- Preserve late or conflicting events without regressing a terminal projection.
- Keep `unknown` visible until reconciliation resolves it.
- Do not convert an HTTP success, provider acceptance code, or queue entry into `delivered`.
- Do not convert fallback success into original-attempt success.

## Provider recovery

### Naver TalkTalk

- Treat inbound storage as the primary event record.
- Mark public historical backfill as `unconfirmed`.
- Expose the missing time window when webhook delivery is absent.
- Reconcile only against an approved stronger provider contract if one becomes available.
- Do not blind-send a reply to compensate for a missing event.

### Channel Talk

- Pair message webhooks with UserChat and message read APIs.
- Backfill from the last confirmed cursor after a webhook outage.
- Reconcile webhook and REST records by provider message and conversation identity.
- Keep webhook URL-token assurance distinct from App Function signature assurance.
- Disable writes while recovering read-only state.

### Happytalk

- Select the exact Biz API, customer API, or Embedded contract before recovery.
- Use approved development or test endpoints and credentials.
- Pair room or message queries with webhook events when the active contract permits it.
- Mark Biz receive authenticity unconfirmed when the contract lacks verification.
- Record message-template and schema versions before replaying archived data.

### Kakao dealer

- Reconcile AlimTalk or other outbound products with the contracted dealer's callback, poll, or report endpoint.
- Preserve accepted and terminal results separately.
- Keep callback and polling as complementary recovery paths.
- Keep ConsultTalk session recovery separate from AlimTalk delivery recovery.
- Leave fallback off unless a separate approval and attempt exists.

## Failure handling

| Failure | Action |
|---|---|
| Malformed payload | Dead-letter with safe parse code; do not guess fields. |
| Invalid auth or signature | Reject before inbox or state mutation. |
| Stale or replayed event | Record duplicate or freshness failure without downstream processing. |
| Missing stable identity | Stop; do not synthesize an event ID from prose. |
| 401 or 403 | Stop, mark connection unhealthy, and request credential-owner review. |
| 404 | Recheck environment, version, and resource scope before retrying. |
| 409 or duplicate response | Reconcile with the existing provider record. |
| 429 | Apply provider policy and server hints; preserve cursor and idempotency. |
| 5xx before acceptance evidence | Retry only under provider policy with the same safe identity. |
| Timeout after possible acceptance | Mark ambiguous and query status before any resubmission. |
| Missing callback | Backfill, poll, or mark the recovery capability unsupported or unconfirmed. |
| Out-of-order status | Append the event and prevent current-state regression. |
| Schema drift | Quarantine the new variant, update the contract version, and rerun fixtures. |
| PII masking failure | Stop processing and keep content out of model and general logs. |
| Webhook blocked | Diagnose failure evidence, backfill when supported, and require approval before re-enabling. |

Do not add universal retry counts, response-time promises, or retention periods. Read provider policy and local configuration.

## Dead-letter recovery

- Keep restricted content out of the dead-letter record.
- Store the failure stage, safe error code, first and last timestamps, retry eligibility, and owner.
- Reprocess from the restricted source pointer only after the blocking contract, auth, schema, or privacy issue is resolved.
- Preserve the original event identity during reprocessing.
- Prevent a corrected dead-letter record from producing a duplicate canonical event.

## Health and reconciliation report

Report:

- last verified webhook, backfill, poll, and reconciliation times;
- cursor or missing-window state;
- duplicate, late, conflicting, and dead-letter counts;
- auth assurance and contract version;
- unsupported and unconfirmed recovery paths;
- whether the connector remains read-only;
- whether any external write occurred.

Treat unchanged external state as a valid observation, not as proof of failure. Treat missing evidence as unknown, not healthy.
