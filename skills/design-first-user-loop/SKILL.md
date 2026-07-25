---
name: design-first-user-loop
description: "Design a capacity-aware first-user acquisition and learning loop linked to evidence, decisions, metrics, and stop conditions. Use when planning first users, early traction, channel experiments, referral loops, 초기 사용자 확보, or build-in-public experiments."
---

# Design First User Loop

Turn a channel idea into a bounded experiment that can create learning without exceeding delivery capacity or making unapproved promises.

## Inputs

Require:

- approved segment and evidence IDs;
- value proposition and value event;
- capacity, budget, and channel constraints;
- metric and counter-metric IDs;
- decision ID;
- external communication policy.

## Workflow

1. State the segment, trigger, and evidence behind the experiment.
2. Define the promised value and the first value moment.
3. Choose one primary channel based on access and fit, not popularity.
4. Define the smallest batch that the team can support.
5. Create an offer and message as drafts.
6. Link the action to a decision, success metric, counter-metric, review date, and stop condition.
7. State what will be learned if the result is positive, negative, or inconclusive.
8. Require human approval before spend, posting, email, direct message, or customer promise.
9. Record outcomes and return them to the decision log.

## Boundaries

- Let the model propose channel, offer, referral, and learning-loop options.
- Use deterministic checks for capacity, ownership, metric references, approval state, and external-write flag.
- Require a person to approve spend, targets, public activity, and delivery commitments.
- Do not count posts, messages, or signups as delivered value unless the metric contract says why.
- Do not run multiple channels when the experiment cannot distinguish their effects.

## Outputs

Create:

- `first-user-loop.json`
- `experiment-cards.md`
- `channel-backlog.md`
- append a draft event to `actions.jsonl`
- `learning-review.md`

Read [references/output-contract.md](references/output-contract.md) before writing them.

## Stop conditions

Stop when support capacity is unknown, evidence does not identify a segment, success cannot be measured, or an external action lacks explicit approval.

## Verification

Keep metrics, decisions, and actions in one artifact directory, then run:

```bash
python3 scripts/stg.py validate-artifacts artifacts/
```

Confirm that every newly created external action starts with `external_write=true` and a non-executed status.
