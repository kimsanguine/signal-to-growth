# Output contract

## `first-user-loop.json`

Follow `contracts/first-user-loop.schema.json`. Require segment, evidence IDs,
decision ID, channel, offer, value moment, capacity, budget, metric IDs, batch
size, review date, stop condition, and `external_write=false`.

Use `loop_mode=direct_seeding` for this skill's first-five learning batch.
The schema still accepts a backward-compatible `introduction_enabled` record,
but an introduction loop is a later iteration: it must first return to
`define-growth-metrics` and `record-growth-decision` rather than making a
referral request from this batch.

## `actions.jsonl`

Follow `contracts/action.schema.json`. Link one decision and at least one
metric. An approved or executed external action requires a scoped `APR-`
approval reference that exists in `approvals.jsonl` and covers the exact action
ID.

## `approvals.jsonl`

Follow `contracts/approval.schema.json`. Append a record only after a person
approves in a later user turn. Require `approver_type=human`, the
`user_turn_ref`, exact action IDs, `external_write=true`, status, and optional
expiry. A model-created `APR-` string is not an approval.

## `experiment-cards.md`

For each experiment include hypothesis, evidence, channel, first-five batch,
expected mechanism, value-moment observation, counter-metric, stop condition,
and learning for positive, negative, or inconclusive results. Do not combine a
direct-seeding result with a later introduction or referral result.

## `channel-backlog.md`

Keep unselected channels as alternatives with the evidence needed to reconsider them.

## `learning-review.md`

Link outcomes to the original decision. Do not rewrite the original hypothesis.

## Completion gate

The first-five experiment fits delivery capacity, can be measured, and has not
performed an unapproved external action.
