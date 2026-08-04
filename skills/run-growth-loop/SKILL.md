---
name: run-growth-loop
description: "Route an evidence-to-growth workflow by validating artifacts, approval states, blockers, and the next specialist skill. Use when coordinating the full Signal to Growth loop, resuming a paused run, checking 다음 단계, or creating a growth-operations handoff. Do not use for doing the specialist work itself, approving decisions, or executing external writes."
---

# Run Growth Loop

Coordinate state and handoffs. Do not replace the specialist judgment contained in the other eleven skills.

## Inputs

Require:

- workspace or artifact directory;
- user objective;
- operating mode: `learning`/`preview` or `apply`;
- selected policy set;
- current `run-state.json`, if one exists;
- approval and blocker context.

Default to `learning`/`preview` when the mode is omitted, the request is
educational, or the authority to modify files is unclear.

## Operating modes

### Learning / preview

Use this mode on the first turn. Read and validate available artifacts without
creating, editing, appending, sending, publishing, or deploying anything.
Return these six labeled parts in plain language:

1. inputs read;
2. model interpretation;
3. deterministically verified facts;
4. unverified or blocked facts;
5. decisions that require a person;
6. proposed file changes and exactly one next skill with its reason.

If the deterministic CLI cannot run, keep working from readable artifacts but
label deterministic validation `not verified`. Do not require a learner to
install Python merely to receive the preview.

### Apply

Enter `apply` only after the person reviews the preview and explicitly confirms
the named files and authority in a later user turn. A prior generic approval,
an `APR-`-looking model string, or the existence of an output file is not that
confirmation. External writes additionally require a valid scoped human record
in `approvals.jsonl`.

## Workflow

1. Set the operating mode and default to `learning`/`preview`.
2. Validate repository and available artifacts when the deterministic runtime is available.
3. Read the run objective, completed skills, approvals, and blockers.
4. Reconcile stated completion with files and reference integrity.
5. Identify the first missing or invalid gate.
6. Route to exactly one specialist skill unless independent work is explicitly requested.
7. Preserve partial outputs and explain why the run cannot advance.
8. Ask for human approval at decision and external-action transitions.
9. In `apply` mode only, update `run-state.json` as a new auditable state.
10. In `apply` mode only, create a handoff that distinguishes completed, locally validated, externally executed, and outcome-recorded work.

A schema-valid primary file is not a completed skill by itself. Require every
artifact named in that skill's output contract. In particular, evidence with
`strength=awaiting_human_tag` is a valid intermediate record but blocks signals,
decisions, and outcomes until a person records both strength and `approved_by`.

## Routing graph

```text
research objective
  → plan-customer-reach → run-switch-interview → synthesize-interviews

configured CS source
  → connect-customer-channels → triage-customer-signals

validated evidence or signal
  → define-growth-metrics → record-growth-decision → design-first-user-loop

approved decision needing build review
  → export-hplan → hplan gates

optional content branch
  → audit-answer-visibility → draft-evidence-content
  → design-first-user-loop → draft-evidence-content
  → draft-evidence-content → osmu-fanout
```

Route from the stated objective and valid available artifacts, not from a
mandatory universal sequence. Keep the manual signal path when no connector
artifact exists. Route to `connect-customer-channels` when any connector
artifact exists but the required connection, event, or state artifact is
incomplete. Keep visibility and content work optional unless the objective asks
for them.

When the objective asks for a product introduction page or other answer-first
content, route to `draft-evidence-content` only after `design-first-user-loop`
is complete, so the page describes a loop that was actually validated. While
that loop is incomplete, route to `design-first-user-loop` first and say why.

When the objective asks to reuse existing content on other surfaces, route to
`osmu-fanout` only after `draft-evidence-content` is complete and a
`content-brief.json` validates against `contracts/content-brief.schema.json`.
The brief is the shared input both surfaces read; without it each surface would
re-decide the topic on its own.

## Boundaries

- Let the model interpret blockers and propose the next specialist.
- Use deterministic checks for artifact existence, schema, references, state transitions, and approval.
- Require a person to approve important decisions and every external write.
- Keep `learning`/`preview` read-only and wait for a later user turn before `apply`.
- Do not recreate interview, metric, content, or channel analysis inside the router.
- Do not call provider APIs directly or treat an unconfigured connector as a blocker for manual signal input.
- Do not mark a run complete because files exist; required validation and approval must also pass.

## Outputs

In `learning`/`preview`, return only the six-part preview and do not write files.

In `apply`, create or update:

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
python3 scripts/stg.py next-step artifacts/ --objective "현재 사용자 목표"
```

Treat the CLI result as routing evidence. The user still owns prioritization and approval.
