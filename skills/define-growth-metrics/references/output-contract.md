# Output contract

## `metrics.jsonl`

Follow `contracts/metric.schema.json`. A metric must define:

- entity and eligible population;
- numerator and denominator;
- value event;
- observation window, time zone, cohort-maturity rule, and exclusions;
- data source and query version;
- baseline measurement with value, observation time, source, and maturity, or `null`;
- target with value, review date, rationale, and source, or `null`;
- owner;
- counter-metric references.

## `growth-loop-map.md`

Connect acquisition, activation, retention, revenue, and referral only where the product model supports the connection. Label assumptions.

For an introduction-enabled first-user loop, map qualified introduction,
referred user's first value, referred user's reuse, and the eligible-reuser
population separately. Define the activation-based loop coefficient as referred
users reaching first value divided by eligible reusers in the same mature cohort.
Its baseline and target stay `null` until observed and owned; an invite click is
not evidence of value or a successful referral.

## `measurement-plan.md`

State instrumentation gaps, query validation steps, review cadence, and who can approve target changes.

## Conditional `introduction-loop-metric-recipe.md`

Create only for an introduction or referral objective that follows a complete
first-five direct-seeding batch. Name qualified introduction, referred user's
first value, referred user's reuse, the activation-based loop coefficient,
cohort, maturity window, baseline state, owner, and counter-metric. It is a
handoff to `record-growth-decision`, not evidence that a message was sent.

## Completion gate

The metric can be independently reconstructed and no unsupported benchmark is presented as a target.
