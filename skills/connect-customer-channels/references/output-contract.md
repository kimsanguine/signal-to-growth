# Output contract

Create only the artifacts required for the current operation. Follow the root JSON Schema when a matching contract exists. Preserve provider evidence rather than filling unknown fields with guesses.

## `channel-connection.json`

Follow `contracts/channel-connection.schema.json`.

Require:

- `connection_id`, `provider`, `region`, `environment`, and `mode`;
- a `credential_ref` such as an approved secret-store pointer, never a credential value;
- confirmed capabilities and explicit unsupported or unconfirmed capabilities;
- a retention-policy reference;
- `approved_by`, nullable until a person approves use of the connection;
- `external_write_enabled=false` for read-only and draft-only modes;
- a checked provider source in each capability `source_ref`;
- nullable `verified_at` until an approved round trip succeeds.

Keep the initial mode read-only. Do not infer production readiness from a valid credential.

## `cs-events.jsonl`

Follow `contracts/cs-event.schema.json`. Append one immutable normalized event per provider event or delivery observation.

Require:

- `event_id`, `provider`, `provider_event_id`, `channel`, `direction`, and `event_type`;
- `occurred_at` and `received_at`;
- `conversation_ref` and optional `message_ref`;
- a tenant-scoped `customer_ref_hmac`, never a direct identifier;
- `content_redacted` and safe `attachment_metadata`;
- an encrypted restricted-storage `raw_payload_ref`;
- privacy and processing-basis references;
- `idempotency_key`, `auth_verified`, and `verification_assurance`;
- both `provider_status` and `canonical_status`;
- approved source evidence IDs.

Set delivery semantics to `unknown` when the official contract does not define them. Keep inbound message events, outbound attempts, and delivery results distinct.

For Kakao i Open Builder skill requests:

- use the HTTP `X-Request-Id` as the provider request identity;
- keep `channel=kakao_channel_chatbot`;
- use the server receipt time when the payload has no provider event timestamp;
- record static `x-api-key` verification as weak assurance, not a payload signature;
- never relabel the event as ConsultTalk or native Channel 1:1 counselor chat.

## `reply-drafts.jsonl`

Follow `contracts/reply-draft.schema.json`.

Require:

- `draft_id`, source event IDs, conversation reference, provider, and product;
- session state when the product is session-bound;
- redacted draft content and any approved template reference or variables;
- risk class and expiration;
- `status`, `approval_id`, and `external_write`.

Use these defaults:

```json
{
  "status": "draft",
  "approval_id": null,
  "external_write": false
}
```

Never treat a generated draft as approval or evidence that a message was sent.

## `delivery-events.jsonl`

Follow `contracts/delivery-event.schema.json`. Append provider observations without rewriting earlier events.

Use only:

```text
draft
validated
approved
submitted
accepted
queued
sent
delivered
read
failed
cancelled
expired
unknown
```

Preserve provider status alongside the canonical status. Keep each provider and fallback attempt separate. Do not advance to `delivered` or `read` without the provider contract and event evidence required for that state.

## `connector-state.json`

Follow `contracts/connector-state.schema.json`.

Record:

- connection and provider;
- mode and cursor;
- last webhook, backfill, and reconciliation times;
- ingested, duplicate, and dead-letter counts;
- blocked reasons;
- health and verification level.

Represent an unsupported backfill or status API explicitly. Do not use an empty cursor as evidence that reconciliation succeeded.

## `connector-capabilities.md`

List each requested capability as `supported`, `unsupported`, or `unconfirmed`.

For every `supported` capability, include:

- official source URL;
- checked date;
- API or document version;
- environment;
- auth or verification surface;
- live-account verification state.

Label public-document findings separately from test-account observations.

## `reconciliation-report.md`

Describe:

- the comparison window and connection;
- webhook, backfill, poll, and provider-status coverage;
- matched, missing, duplicate, late, and conflicting events;
- projected state and the evidence that supports it;
- retry or manual-review decisions;
- unsupported recovery paths and missing windows.

Never hide a gap by reducing the comparison window after processing.

## `connector-dead-letter.jsonl`

Record:

- a safe event or restricted source pointer;
- provider and failure stage;
- stable safe error code;
- first and latest observation timestamps;
- retry eligibility and required recovery action;
- blocked reason and human owner when needed.

Do not include credentials, direct identifiers, message content, or a full restricted payload.

## Triage handoff

Pass only validated `cs-events.jsonl` records to `triage-customer-signals`.

Preserve:

- source evidence IDs;
- conversation and message references;
- auth and verification assurance;
- privacy and retention references;
- provider and canonical statuses;
- any missing-window or duplicate notes.

Let the triage skill create signal, risk-queue, and theme artifacts.

## PMF Radar bridge

Accept only `pmf-radar.stg.v1` records following
`contracts/pmf-radar-export.schema.json`. Validate the nested event against the
canonical CS event contract.

Create `integration-references.jsonl` following
`contracts/integration-reference.schema.json`. Preserve `product_scope` and
segment in bridge context. Do not copy a PMF Radar raw payload or infer evidence
and signal records during deterministic import.

## Completion gate

Complete the connector operation only when:

- artifact schemas and reference integrity pass;
- reprocessing is idempotent;
- privacy checks pass;
- every unsupported or unconfirmed capability is visible;
- accepted, delivered, and read states remain distinct;
- all external-write fields remain false without scoped approval;
- verification level matches the evidence actually collected.
