# Output contract

## `decisions.jsonl`

Follow `contracts/decision.schema.json`. Append one immutable event per decision or later change.

Require the decision question, selected option, evidence IDs, counterevidence,
alternatives, `not_build`, reversibility, owner, review date, success condition,
stop condition, causal confidence, approval, and optional supersedes link.

When status is `approved`, `approved_by` is an `APR-` reference that exists in
`approvals.jsonl` and covers the exact decision ID.

`event_type` is optional and classifies the kind of change: `initial_decision`,
`scope_change`, `success_metric_review`, `outcome_review`, or `reversal`. The
four change kinds require a non-null `supersedes`, and `initial_decision`
requires `supersedes` to be null. Omit the field when the kind is unclear —
omission means unclassified, never `initial_decision`.

## `approvals.jsonl`

Follow `contracts/approval.schema.json`. Append only after a person approves in
a later user turn. Record `approver_type=human`, `user_turn_ref`, the exact
decision ID, status, and optional expiry.

## `hplan-intake.json`

Follow `contracts/hplan-intake-brief.schema.json`. It is an intake to hplan
gates, not an approved implementation handoff. Keep missing values in
`unknown_fields` and `hplan_gate_decision=null`.

## `decision-summary.md`

Explain the decision, evidence, uncertainty, trade-off, and next review in plain language. Keep approval state visible.

For an introduction-loop decision, also state the loop coefficient definition,
HOLD condition, resume condition, and reward-experiment choice. Treat a reward
as `not selected` unless a later scoped human approval covers the exact external
action and spend.

## Conditional `introduction-loop-decision.md`

Create only after `introduction-loop-metric-recipe.md` exists for an
introduction or referral objective. It must name the coefficient definition,
HOLD condition, resume condition, reward-experiment choice, decision owner,
review date, and current approval state. Never represent the file itself as
human approval.

## `review-queue.md`

List upcoming review dates, owners, pending outcomes, and blocked evidence. Do not treat a missed review as silent approval.

## Completion gate

The decision is approved only when reference validation passes and
`approved_by` resolves to a scoped, approved human record covering that
decision ID.
