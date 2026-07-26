# Output contract

## `first-user-loop.json`

Follow `contracts/first-user-loop.schema.json`. Require segment, evidence IDs,
decision ID, channel, offer, value moment, capacity, budget, metric IDs, batch
size, review date, stop condition, and `external_write=false`.

## `actions.jsonl`

Follow `contracts/action.schema.json`. Link one decision and at least one
metric. An approved or executed external action requires a scoped `APR-`
approval reference.

## `experiment-cards.md`

For each experiment include hypothesis, evidence, channel, batch, expected mechanism, success, counter-metric, stop condition, and learning for positive, negative, or inconclusive results.

## `channel-backlog.md`

Keep unselected channels as alternatives with the evidence needed to reconsider them.

## `learning-review.md`

Link outcomes to the original decision. Do not rewrite the original hypothesis.

## Completion gate

The experiment fits delivery capacity, can be measured, and has not performed an unapproved external action.
