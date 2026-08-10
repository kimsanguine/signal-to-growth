# Output contract

## `first-user-loop.json`

Follow `contracts/first-user-loop.schema.json`. Require segment,
`evidence_basis`, evidence IDs, channel, offer, value moment, capacity,
budget, metric IDs, `proposed_metrics`, batch size, review date, stop
condition, and `external_write=false`. `decision_id` may be `null`.

`evidence_basis` is `prior_evidence` (then `evidence_ids` needs at least one
real ID) or `first_experiment` (then `evidence_ids` may stay empty — this batch
is the evidence-gathering activity, not a consumer of one). Either
`metric_ids` or `proposed_metrics` must have at least one entry: a real
contract ID when `define-growth-metrics` already produced one, or an inline
`{name, why_this_metric, how_to_measure}` candidate when it has not.
`decision_id` stays `null` until `record-growth-decision` runs, which can
happen before or after this draft.

Use `loop_mode=direct_seeding` for this skill's first-five learning batch.
The schema still accepts a backward-compatible `introduction_enabled` record,
but an introduction loop is a later iteration: it must first return to
`define-growth-metrics` and `record-growth-decision` rather than making a
referral request from this batch.

## `actions.jsonl`

Follow `contracts/action.schema.json`. `decision_id` may start `null` and
`metric_ids` may start empty — both are filled in once `record-growth-decision`
and `define-growth-metrics` catch up to this draft. Neither may stay `null`/empty
by the time `status` is `approved` or `executed`: the schema enforces a real
`decision_id` string at that point. An approved or executed external action also
requires a scoped `APR-` approval reference that exists in `approvals.jsonl` and
covers the exact action ID.

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
