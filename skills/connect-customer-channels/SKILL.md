---
name: connect-customer-channels
description: "Diagnose, verify, normalize, reconcile, and prepare draft-only replies for customer-channel integrations, especially Korean CS channels. Use when working with a Kakao Channel chatbot through Kakao i Open Builder, Naver TalkTalk, Channel Talk, Happytalk, Kakao Channel 1:1 chat, Kakao ConsultTalk or AlimTalk through an approved provider; validating skill requests, webhooks, backfills, delivery states, or connector health; creating channel connection, CS event, delivery, reply-draft, or connector-state artifacts; or handing normalized events to triage-customer-signals. Default to dry-run, read-only, and draft-only. Do not use for classifying signal themes, recruiting research participants, or sending any live message."
---

# Connect Customer Channels

Connect customer-channel evidence to Signal to Growth without turning ingestion into an unapproved outbound-action system.

## Inputs

Require:

- the requested provider, product, channel, and region;
- an official provider contract or a public dummy fixture with a source URL and checked date;
- an approved connection reference, or an explicit offline dry-run;
- privacy, retention, and processing-basis references;
- the permitted raw request or an encrypted restricted-storage pointer;
- the intended artifacts and downstream owner;
- an approval artifact for any requested external write.

Do not request or persist a raw credential. Accept only a secret reference from an approved runtime.

## Read the references

Read:

- [references/providers-kr.md](references/providers-kr.md) before selecting or mapping a Korean provider;
- [references/output-contract.md](references/output-contract.md) before creating artifacts;
- [references/approval-boundaries.md](references/approval-boundaries.md) before using a real account or preparing an outbound operation;
- [references/recovery-patterns.md](references/recovery-patterns.md) before retrying, backfilling, polling, or reconciling status.

## Workflow

1. Set `dry-run`, `read-only`, and `draft-only` as the initial operating modes.
2. Identify the provider, business product, transport surface, environment, and contract version.
3. Separate confirmed capabilities from unsupported and unconfirmed capabilities.
4. Select an approved connection reference. Otherwise, use a public dummy fixture and make no network call.
5. Verify the raw request before parsing provider-controlled JSON when the provider contract supports verification.
6. Reject stale, replayed, malformed, unauthorized, or unverifiable production input.
7. Persist a restricted inbox pointer and stable provider identity before acknowledging valid webhook input.
8. Normalize the verified input into a provider-neutral CS event without erasing provider-specific status.
9. Redact content, HMAC-reference customer identity per tenant, and retain only allowed attachment metadata.
10. Derive the idempotency key and event ID from stable provider fields. Never invent identity from model text.
11. Record duplicate, unsupported, and dead-letter outcomes explicitly.
12. Backfill or poll only when the confirmed provider capability and approved connection allow it.
13. Reconcile webhook and API records without creating a second canonical event.
14. Preserve each delivery attempt and project its current state without equating acceptance with delivery.
15. Create a reply draft only when the product, session, risk, purpose, and approval requirements can be evaluated.
16. Keep `external_write=false` and do not call a send, reply, handover, assignment, tag, template, or fallback endpoint.
17. Hand only verified and redacted CS events to `triage-customer-signals`.
18. When PMF Radar is the operational inbox, accept only its
    `pmf-radar.stg.v1` export and validate it with `import-pmf-radar`.
19. Report artifact validation, round-trip evidence, blocked capabilities, and unverified operational claims separately.

## Kakao product boundary

Keep these surfaces separate:

- Treat **Kakao Channel chatbot through Kakao i Open Builder** as a synchronous skill-request and skill-response surface. It can connect a bot to a Kakao Channel, but it is not ConsultTalk and does not expose native 1:1 counselor history.
- Treat **Kakao Channel 1:1 chat** as the native channel-management chat surface. Do not assume it exposes the same external API contract as a dealer-operated business-messaging product.
- Treat **Kakao ConsultTalk (상담톡)** as a customer-initiated, session-bound consultation product delivered through an official dealer and a separate counselor/helpdesk system. Require an active session before even proposing a reply for approval.
- Treat **Kakao AlimTalk (알림톡)** as outbound informational messaging through an official dealer using an approved sender profile and template. Do not model it as an inbound conversation or ConsultTalk reply.
- Treat **Kakao Developers message APIs** as same-service user interaction APIs, not as a customer-service or transactional BizMessage substitute.
- Treat **Kakao Brand Message** as a separate outbound marketing-capable product. Keep it disabled by default.

Do not invent a common Kakao endpoint. Identify the contracted dealer and exact product before using a provider contract.

## Capability decisions

Use exactly one of:

- `supported`: Cite a checked official contract and name the usable environment.
- `unsupported`: Record that the provider contract explicitly lacks the capability.
- `unconfirmed`: Record `[HOLD]` and avoid production use.

Return `unsupported` or `unconfirmed` directly. Do not hide either state behind an empty successful result.

## Responsibility split

- Let the model explain provider differences, propose mappings, summarize safe redacted content, and draft a reply.
- Use deterministic code to verify authenticity, parse payloads, redact private data, derive identity, validate schema, deduplicate, project status, and enforce approval.
- Require a person to approve every connection change, reply, send, handover, assignment, tag mutation, template change, fallback, and production expansion.
- Route safety, legal, privacy, security, billing, refund, account-access, deletion, harassment, vulnerable-person, and contractual-promise cases to human review.
- Let `triage-customer-signals` classify the customer problem, severity, and theme. Do not duplicate that judgment here.
- Let PMF Radar own long-running provider ingestion, retry, raw retention, and operator queues. This skill owns setup, contract validation, and the portable handoff.

## Outputs

Create only the artifacts required by the requested operation:

- `channel-connection.json`
- `cs-events.jsonl`
- `reply-drafts.jsonl`
- `delivery-events.jsonl`
- `connector-state.json`
- `connector-capabilities.md`
- `reconciliation-report.md`
- `connector-dead-letter.jsonl`

Follow [references/output-contract.md](references/output-contract.md).

## Stop conditions

Stop and create a partial artifact when:

- the provider, business product, or transport surface is ambiguous;
- the official authentication or webhook verification contract is unconfirmed;
- the source, checked date, API version, or contract version is missing;
- a production event cannot be authenticated or assigned stable identity;
- a Kakao Open Builder request lacks `X-Request-Id`, or the configured test header does not match;
- raw-payload retention, processing basis, or redaction policy is undefined;
- masking fails or restricted content would enter a general log;
- a capability is unconfirmed and the next step would depend on it;
- a ConsultTalk session is not confirmed active;
- a template, sender profile, message purpose, or recipient basis is unconfirmed;
- an external write lacks a valid, scoped human approval ID;
- a timeout may have followed provider acceptance and safe reconciliation has not run.

Do not claim that a channel is connected, live, or operational from documentation, fixture, build, or credential issuance alone.

## Verification

Run the connector validator when the v0.2 command is available:

```bash
python3 scripts/stg.py validate-connectors connectors/
python3 scripts/stg.py validate-artifacts artifacts/
python3 scripts/stg.py import-pmf-radar --input pmf-radar-export.jsonl
```

Confirm all of the following:

- Reprocess the same provider event without creating another canonical event.
- Keep secrets, direct customer identifiers, and restricted content out of general artifacts.
- Preserve `accepted != delivered` and keep fallback as a separate attempt.
- Leave every reply at `status=draft`, `approval_id=null`, and `external_write=false` by default.
- Mark absent capabilities as `unsupported` or `unconfirmed`.
- Verify a real test-account input-to-output round trip before reporting an integration as verified.

Report documentation-reviewed, fixture-validated, locally tested, test-account verified, and production-operational states separately.
