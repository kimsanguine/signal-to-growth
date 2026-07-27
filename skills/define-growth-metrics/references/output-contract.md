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

## `measurement-plan.md`

State instrumentation gaps, query validation steps, review cadence, and who can approve target changes.

## Completion gate

The metric can be independently reconstructed and no unsupported benchmark is presented as a target.
