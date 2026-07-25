# Artifact contracts

## Lineage

```text
source
  └── evidence
        ├── signal
        └── decision
              └── action
                    ├── metric
                    └── outcome
```

`run-state.json` records which artifacts and approvals are ready. It is not a substitute for the artifacts themselves.

## Claim states

Use one of:

- `observed`: directly checked;
- `reported`: stated by a participant or source;
- `inferred`: interpretation derived from evidence;
- `recommended`: proposed action;
- `unknown`: not supported by current evidence.

Never express `inferred` or `recommended` as `observed`.

## Approval states

```text
draft
  → awaiting_human_review
  → approved
  → executed
  → outcome_pending
  → outcome_recorded
```

`rejected`, `blocked`, and `superseded` preserve why a path stopped or changed. Approval cannot be inferred from the existence of a file.

## Reference rules

- A decision references existing evidence IDs.
- An action references one existing decision and at least one metric.
- An outcome references one existing action and metric.
- An approved evidence strength names a human reviewer.
- An approved decision names a human reviewer.
- An executed external action names a human reviewer.
- Updates append events or use `supersedes`; they do not rewrite history.

## Versioning

Schema IDs contain stable URLs. Release metadata and `artifact_versions` record compatibility. A breaking required-field or state change requires a major version and migration note.
