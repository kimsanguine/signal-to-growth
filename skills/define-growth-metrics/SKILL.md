---
name: define-growth-metrics
description: "Define SaaS growth metrics as explicit contracts with population, numerator, denominator, window, value event, baseline, target provenance, and counter-metrics. Use when designing activation, retention, revenue, PMF, 성장 지표, KPI, or cohort measurement. Do not use for running queries against production data, setting universal benchmark targets, or deciding what to build."
---

# Define Growth Metrics

Turn a metric name into a reproducible measurement contract. Keep targets tied to a baseline, source, owner, and decision context.

## Inputs

Require:

- product and business model;
- user or account entity;
- candidate value event;
- available event and billing data;
- current baseline or an explicit unknown;
- decision owner and review cadence.

## Workflow

1. State the decision the metric should inform.
2. Define the entity and eligible population.
3. Define numerator and denominator in plain language.
4. Define observation window, cohort maturity, time zone, and exclusions.
5. Name the value event and explain why it represents delivered value.
6. Record source tables or events and query version.
7. Record baseline with date and source, or set it to `null`.
8. Propose a target only with provenance, rationale, and human owner.
9. Add at least one counter-metric for quality, risk, or cost.
10. Separate activation, retention, revenue, and satisfaction rather than merging them into one score.

## Boundaries

- Let the model propose metric candidates and diagnostic questions.
- Use deterministic checks for required fields, denominator, cohort maturity, target provenance, and references.
- Require a person to approve the value event, target, and trade-off.
- Do not use an industry benchmark as a default target.
- Do not calculate immature cohorts as failures.
- Do not treat shipping or signup as demonstrated value without a stated rationale.

## Outputs

Create:

- `metrics.jsonl`
- `growth-loop-map.md`
- `measurement-plan.md`
- optional query stubs that are clearly marked unverified until executed

Read [references/output-contract.md](references/output-contract.md) before writing them.

Add every new record to `metrics.jsonl` with the `append-record` command, never
by writing or editing the file:

```bash
python3 scripts/stg.py append-record <artifact-directory>/metrics.jsonl '<json-object>'
```

It takes an exclusive lock and hash-chains each line to the one before it, so a
later reader can tell whether history was rewritten. In a packaged runtime the
same command is `signal-to-growth append-record`.

## Stop conditions

Stop when the value event is undefined, the denominator cannot be reconstructed, the requested target has no source, or the available data cannot answer the question.

## Verification

Run:

```bash
python3 scripts/stg.py validate-artifacts artifacts/
```

Report query generation, local query execution, warehouse execution, and reviewed metric output as separate verification states.
