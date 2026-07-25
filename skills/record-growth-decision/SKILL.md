---
name: record-growth-decision
description: "Record evidence-backed growth decisions with alternatives, counterevidence, approval, review dates, and append-only outcomes. Use when deciding what to build, hold, test, stop, or review, including 성장 의사결정·decision log·가설 기록."
---

# Record Growth Decision

Create an auditable decision event that can be reviewed against later outcomes without rewriting history.

## Inputs

Require:

- decision context and owner;
- hypothesis;
- valid evidence IDs;
- counterevidence;
- at least one alternative;
- review date;
- success and stop conditions;
- current causal confidence.

## Workflow

1. Restate the decision in a form a reviewer can accept or reject.
2. Link supporting evidence by ID.
3. Preserve counterevidence and unresolved unknowns.
4. List alternatives, including doing nothing when relevant.
5. State expected mechanism, success condition, stop condition, and review date.
6. Mark causal confidence as unknown, low, medium, or high.
7. Keep status at `draft` or `awaiting_human_review` until a person decides.
8. Append the decision event. Never modify an earlier event to make a later result look expected.
9. Record later outcomes as new events and link superseded decisions.

## Boundaries

- Let the model identify missing evidence, alternatives, and counterarguments.
- Use deterministic checks for IDs, required fields, status transitions, and append-only history.
- Require a person to approve the decision and accept risk.
- Do not equate shipped, launched, or deployed with successful.
- Do not increase confidence because a statement appears in multiple model summaries of the same source.

## Outputs

Create or append:

- `decisions.jsonl`
- `decision-summary.md`
- `review-queue.md`

Read [references/output-contract.md](references/output-contract.md) before writing them.

## Stop conditions

Stop when evidence references are invalid, the owner or review date is absent, alternatives are missing, or approval is implied rather than explicit.

## Verification

Keep `evidence.jsonl` and `decisions.jsonl` together, then run:

```bash
python3 scripts/stg.py validate-artifacts artifacts/
```

Report draft, approved, executed, and outcome-recorded states separately.
