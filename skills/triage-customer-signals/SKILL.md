---
name: triage-customer-signals
description: "Normalize, de-duplicate, classify, and safely route customer signals from support, reviews, surveys, and interviews. Use when handling CS feedback, VOC streams, 위험 신호, 고객 문의 분류, or building a human-reviewed signal radar."
---

# Triage Customer Signals

Convert channel-specific inputs into a shared signal contract while preserving source, privacy, and risk context.

## Inputs

Require:

- raw channel payload or a permitted redacted copy;
- source and observation timestamp;
- channel contract;
- privacy, retention, and routing policy;
- any related evidence IDs.

## Workflow

1. Preserve a permitted source pointer. Do not copy restricted raw payloads into public artifacts.
2. Create an idempotency key from stable channel identifiers.
3. Detect and mask configured private-data patterns before model classification.
4. Normalize channel, category, severity, summary, privacy, and status.
5. Link the signal to evidence IDs when a source excerpt has been approved.
6. Route high and critical signals to human review.
7. Place malformed inputs in a dead-letter artifact with a reason.
8. Create a digest from approved records, not from raw private content.

## Boundaries

- Let the model propose category, summary, and severity.
- Use deterministic code for masking, schema, deduplication, retention tags, and routing.
- Require a person to approve high-risk classifications and any response.
- Do not auto-reply to safety, legal, billing, account-access, or high-severity issues.
- Do not report a channel as integrated until a real input-to-output round trip is verified.

## Outputs

Create:

- `signals.jsonl`
- `risk-queue.jsonl`
- `theme-digest.md`
- `dead-letter.jsonl`

Read [references/output-contract.md](references/output-contract.md) before writing them.

## Stop conditions

Stop when masking fails, the source is not permitted, retention is undefined, channel identity is ambiguous, or a critical signal has no human owner.

## Verification

Store related `evidence.jsonl` in the same artifact directory, then run:

```bash
python3 scripts/stg.py validate-artifacts artifacts/
python3 scripts/stg.py scan-privacy theme-digest.md
```

Reprocessing the same channel item must not create a second signal.
