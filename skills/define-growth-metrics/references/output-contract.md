# Output contract

## `metrics.jsonl`

Follow `contracts/metric.schema.json`. A metric must define:

- entity and eligible population;
- numerator and denominator;
- value event;
- observation window and maturity;
- data source and query version;
- baseline or explicit unknown;
- target and source, or explicit unknown;
- owner;
- counter-metric references.

## `growth-loop-map.md`

Connect acquisition, activation, retention, revenue, and referral only where the product model supports the connection. Label assumptions.

## `measurement-plan.md`

State instrumentation gaps, query validation steps, review cadence, and who can approve target changes.

## Completion gate

The metric can be independently reconstructed and no unsupported benchmark is presented as a target.
