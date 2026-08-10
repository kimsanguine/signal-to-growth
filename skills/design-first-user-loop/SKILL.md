---
name: design-first-user-loop
description: "Use when planning the first five users (초기 사용자 확보, 첫 유저 5명 확보), direct seeding, early traction, or a bounded channel experiment (채널 실험 설계). Do not use for referral activation, sending outreach, publishing content, or recording the growth decision itself."
---

# Design First User Loop

Turn a channel idea into a bounded experiment that can create learning without exceeding delivery capacity or making unapproved promises.

## Inputs

Require:

- a stated segment;
- capacity, budget, and channel constraints;
- external communication policy.

Evidence, a formal metric contract, and a decision record are useful when they
already exist, but none of the three is a precondition to draft this
experiment — this batch is often how a founder gets the first evidence at all.
State whichever of them exist by ID; for whichever do not, say so honestly
instead of blocking or inventing one.

## Workflow

1. State the segment, trigger, and evidence behind the experiment — real
   evidence IDs if they exist, or the working hypothesis if this is the first
   experiment with this segment. Either is fine; an unstated segment is not.
2. Define the promised value and the first value moment.
3. Start in `direct_seeding`: choose one primary channel based on access and fit, not popularity.
4. Cap the learning batch at the first five users. State who counts toward the five, the support capacity per user, and the condition that stops further invitations.
5. Create a value-moment observation plan; do not turn the first five into a referral or incentive experiment.
6. Propose 1–2 candidate success metrics and one counter-metric, with a short
   reason each one would actually indicate the promised value was delivered —
   reference an existing `metrics.jsonl` record by ID if one already fits, or
   propose a new candidate inline (`proposed_metrics`) when none does. A metric
   that only counts posts, invites, or signups is not a candidate.
7. State what will be learned if the result is positive, negative, or inconclusive, and what a good result would let the team do next.
8. Require human approval in a later user turn before spend, posting, email, direct message, or customer promise.
9. Record that approval in `approvals.jsonl` with the exact action ID before changing an external action to approved or executed.
10. Record outcomes and return them to the decision log. If no decision record exists yet, hand this experiment to `record-growth-decision` once results are in — the decision can follow the experiment; it does not have to precede it.

## Handoff after the first five

Do not expand the batch merely because five people were invited. When the first
five have a reviewable value observation, hand off an introduction or referral
objective to `define-growth-metrics`. That skill defines qualified introduction,
referred first value, reuse, and an activation-based loop coefficient before a
later decision considers a new loop, a reward, or additional external activity.

## Boundaries

- Let the model propose channel, offer, learning-loop options, and candidate success metrics — a plausible metric proposed now beats a validated one that arrives after capacity is spent.
- Use deterministic checks for capacity, ownership, metric references, approval state, and external-write flag.
- Require a person to approve spend, targets, public activity, and delivery commitments.
- Do not count posts, messages, or signups as delivered value unless the metric contract or the proposed-metric rationale says why.
- Do not run multiple channels when the experiment cannot distinguish their effects.
- Do not show unverified social proof, invent testimonials, or treat an invite click as a value moment.
- Do not treat a missing evidence ID, metric ID, or decision ID as a reason to stop — treat an unstated segment, an unmeasurable value moment, or an unbounded batch as one.

## Outputs

Create:

- `first-user-loop.json`
- `experiment-cards.md`
- `channel-backlog.md`
- append a draft event to `actions.jsonl`
- append a scoped record to `approvals.jsonl` only after a person approves in a later turn
- `learning-review.md`

Read [references/output-contract.md](references/output-contract.md) before writing them.

Add every new record to `actions.jsonl` and `approvals.jsonl` with the `append-
record` command, never by writing or editing the file:

```bash
python3 scripts/stg.py append-record <artifact-directory>/actions.jsonl '<json-object>'
```

It takes an exclusive lock and hash-chains each line to the one before it, so a
later reader can tell whether history was rewritten. In a packaged runtime the
same command is `signal-to-growth append-record`.

## Stop conditions

Stop when support capacity is unknown, the segment is unstated with no evidence or working hypothesis behind it, success cannot be measured by any real or proposed metric, the first-five batch is full without a review decision, or an external action lacks explicit approval.

## Verification

Keep metrics, decisions, and actions in one artifact directory, then run:

```bash
python3 scripts/stg.py validate-artifacts artifacts/
```

Confirm that every newly created external action starts with `external_write=true` and a non-executed status.
