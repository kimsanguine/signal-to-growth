# Output contract

## `decisions.jsonl`

Follow `contracts/decision.schema.json`. Append one immutable event per decision or later change.

Require evidence IDs, counterevidence, alternatives, owner, review date, success condition, stop condition, causal confidence, approval, and optional supersedes link.

## `decision-summary.md`

Explain the decision, evidence, uncertainty, trade-off, and next review in plain language. Keep approval state visible.

## `review-queue.md`

List upcoming review dates, owners, pending outcomes, and blocked evidence. Do not treat a missed review as silent approval.

## Completion gate

The decision is approved only when reference validation passes and `approved_by` names the human reviewer.
