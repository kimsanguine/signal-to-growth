---
name: record-growth-decision
description: "Record evidence-backed growth decisions with alternatives, counterevidence, approval, review dates, and append-only outcomes. Use when deciding what to build, hold, test, stop, or review, including 성장 의사결정·decision log·가설 기록. Do not use for granting the approval itself, claiming an hplan gate result, or rewriting an earlier decision."
---

# Record Growth Decision

Create an auditable decision event that can be reviewed against later outcomes without rewriting history.

## Inputs

Require:

- decision question, selected option, context, and owner;
- hypothesis;
- valid evidence IDs;
- counterevidence;
- at least one alternative;
- an explicit `not_build` list and reversibility assessment;
- review date;
- success and stop conditions;
- current causal confidence.

## Workflow

1. Restate the decision question and selected option in a form a reviewer can accept or reject.
2. Link supporting evidence by ID.
3. Preserve counterevidence and unresolved unknowns.
4. List alternatives, including doing nothing when relevant, and record what will not be built.
5. Classify the decision as reversible, partially reversible, or hard to reverse.
6. State expected mechanism, success condition, stop condition, and review date.
7. Mark causal confidence as unknown, low, medium, or high.
8. Keep status at `draft` or `awaiting_human_review` until a person decides in a later user turn.
9. Append a scoped `approvals.jsonl` record covering the exact decision ID before setting status to `approved`.
10. Append the decision event. Never modify an earlier event to make a later result look expected.
11. At review time, compare mature outcomes with the original metric contract and record continue, change, stop, or hold.
12. Link a superseding decision instead of rewriting the original, and classify
    the new event with `event_type` — `initial_decision`, `scope_change`,
    `success_metric_review`, `outcome_review`, or `reversal` — so the log states
    what kind of change it is, not only which record it replaces. Leave
    `event_type` out rather than guessing; an unclassified event is honest,
    a wrong one is not.

## Introduction-loop decision example

After reviewing the first-five direct-seeding batch, record one explicit
decision instead of assuming that referral is the next action:

- **Question:** should the team test a draft-only introduction loop for this segment?
- **Metric rule:** name the `loop coefficient` numerator, denominator, cohort, and maturity window from `define-growth-metrics`.
- **HOLD condition:** name the observed condition that prevents a request, such as no repeat value, recipient-fit evidence, or support capacity.
- **Resume condition:** name the new evidence, owner, and review date needed to leave HOLD.
- **Reward experiment:** choose `not selected`, `draft for later review`, or a separately approved experiment. A reward is never implied by a referral objective and may not be promised, sent, or funded without scoped human approval.

Record the resulting continue, hold, change, or stop as a later append-only
event. Do not retrofit the original first-five decision to make the next loop
look pre-approved.

## Boundaries

- Let the model identify missing evidence, alternatives, and counterarguments.
- Use deterministic checks for IDs, required fields, status transitions, and append-only history.
- Require a person to approve the decision and accept risk.
- Do not equate shipped, launched, or deployed with successful.
- Do not increase confidence because a statement appears in multiple model summaries of the same source.
- Do not treat an immature cohort, missing query, or unrelated interview quote as outcome evidence.
- Export an hplan intake only as `draft_for_gate` or `ready_for_gate_review`; never claim the hplan gate decision.

## Outputs

Create or append:

- `decisions.jsonl`
- `approvals.jsonl` only after a person approves in a later turn
- `hplan-intake.json` as a pre-gate intake, never as an hplan gate decision
- `decision-summary.md`
- `review-queue.md`
- `introduction-loop-decision.md`

For an introduction or referral objective, additionally create
`introduction-loop-decision.md`. It captures the loop-coefficient definition,
HOLD and resume conditions, reward-experiment choice, approval state, owner,
and review date. It is a draft decision until a person approves in a later
turn.

Read [references/output-contract.md](references/output-contract.md) before writing them.

Add every new record to `decisions.jsonl` and `approvals.jsonl` with the
`append-record` command, never by writing or editing the file:

```bash
python3 scripts/stg.py append-record <artifact-directory>/decisions.jsonl '<json-object>'
```

It takes an exclusive lock and hash-chains each line to the one before it, so a
later reader can tell whether history was rewritten. In a packaged runtime the
same command is `signal-to-growth append-record`.

## Stop conditions

Stop when evidence references are invalid, the owner or review date is absent, alternatives are missing, or approval is implied rather than explicit.

## Verification

Keep `evidence.jsonl` and `decisions.jsonl` together, then run:

```bash
python3 scripts/stg.py validate-artifacts artifacts/
python3 scripts/stg.py export-hplan --artifacts artifacts/
```

Report draft, approved, executed, and outcome-recorded states separately.
