# Output contract

## `signals.jsonl`

Follow `contracts/signal.schema.json`. Link `source_evidence_ids` only to approved evidence records.

## `risk-queue.jsonl`

Include signal ID, risk reason, owner, review status, and deadline. Use a pointer to restricted content instead of copying it.

## `theme-digest.md`

Summarize approved counts and patterns without exposing private payloads. Label observation period and channel coverage.

## `dead-letter.jsonl`

Include source pointer, failure stage, safe error code, retry eligibility, and timestamp. Never include a credential or full restricted payload.

## Completion gate

The pipeline is ready when reprocessing is idempotent, private-data checks pass, and high-risk signals have a human owner.
