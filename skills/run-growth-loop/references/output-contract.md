# Output contract

## Learning / preview response

Do not write an artifact. Return six labeled parts: inputs read, model
interpretation, deterministically verified facts, unverified or blocked facts,
human decisions, and proposed file changes plus one next skill. Use `not
verified` when the deterministic runtime did not run.

The response may be reviewed in the same turn, but `apply` requires explicit
confirmation in a later user turn.

## Apply artifacts

Create or update the following only after the preview has been confirmed.

## `run-state.json`

Follow `contracts/run-state.schema.json`. Record objective, phase, status, completed skills, blockers, approvals, and artifact versions.

## `next-action.md`

Name one specialist skill, the missing input, why it is next, and the proof needed to complete it.

## `blocked-items.md`

For each blocker include owner, missing authority or evidence, safe work still possible, and resume condition.

## `handoff.md`

Separate:

- created;
- statically validated;
- locally executed;
- externally executed;
- outcome observed;
- not verified.

## Completion gate

All required artifacts pass validation, important decisions are approved, external actions have explicit approval, and outcomes or pending observation windows are stated accurately.
