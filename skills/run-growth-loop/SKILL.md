---
name: run-growth-loop
description: "Route an evidence-to-growth workflow by validating artifacts, approval states, blockers, and the next specialist skill. Use when coordinating the full Signal to Growth loop, resuming a paused run, checking 다음 단계, or creating a growth-operations handoff."
---

# Run Growth Loop

Coordinate state and handoffs. Do not replace the specialist judgment contained in the other ten skills.

## Inputs

Require:

- workspace or artifact directory;
- user objective;
- selected policy set;
- current `run-state.json`, if one exists;
- approval and blocker context.

## Workflow

1. Validate repository and available artifacts.
2. Read the run objective, completed skills, approvals, and blockers.
3. Reconcile stated completion with files and reference integrity.
4. Identify the first missing or invalid gate.
5. Route to exactly one specialist skill unless independent work is explicitly requested.
6. Preserve partial outputs and explain why the run cannot advance.
7. Ask for human approval at decision and external-action transitions.
8. Update `run-state.json` as a new auditable state.
9. Create a handoff that distinguishes completed, locally validated, externally executed, and outcome-recorded work.

## Routing order

```text
plan-customer-reach
→ run-switch-interview
→ synthesize-interviews
→ connect-customer-channels (only when a connector is configured)
→ triage-customer-signals
→ define-growth-metrics
→ record-growth-decision
→ audit-answer-visibility
→ draft-evidence-content
→ design-first-user-loop
```

Keep the manual signal path when no connector artifact exists. Route to `connect-customer-channels` when any connector artifact exists but the required connection, event, or state artifact is incomplete. Skip any other skill only when the run state records why its artifact is not applicable.

## Boundaries

- Let the model interpret blockers and propose the next specialist.
- Use deterministic checks for artifact existence, schema, references, state transitions, and approval.
- Require a person to approve important decisions and every external write.
- Do not recreate interview, metric, content, or channel analysis inside the router.
- Do not call provider APIs directly or treat an unconfigured connector as a blocker for manual signal input.
- Do not mark a run complete because files exist; required validation and approval must also pass.

## Outputs

Create or update:

- `run-state.json`
- `next-action.md`
- `blocked-items.md`
- `handoff.md`

Read [references/output-contract.md](references/output-contract.md) before writing them.

## Stop conditions

Stop when a required artifact is invalid, an approval is missing, policies conflict, restricted data cannot be handled safely, or the next action would expand authority.

## Verification

Run:

```bash
python3 scripts/stg.py validate-artifacts artifacts/
python3 scripts/stg.py validate-connectors artifacts/
python3 scripts/stg.py next-step artifacts/
```

Treat the CLI result as routing evidence. The user still owns prioritization and approval.
