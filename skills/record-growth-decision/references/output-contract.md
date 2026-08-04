# Output contract

## `decisions.jsonl`

Follow `contracts/decision.schema.json`. Append one immutable event per decision or later change.

Require the decision question, selected option, evidence IDs, counterevidence,
alternatives, `not_build`, reversibility, owner, review date, success condition,
stop condition, causal confidence, approval, and optional supersedes link.

When status is `approved`, `approved_by` is an `APR-` reference that exists in
`approvals.jsonl` and covers the exact decision ID.

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

## `review-queue.md`

List upcoming review dates, owners, pending outcomes, and blocked evidence. Do not treat a missed review as silent approval.

## Completion gate

The decision is approved only when reference validation passes and
`approved_by` resolves to a scoped, approved human record covering that
decision ID.
