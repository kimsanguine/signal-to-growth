# Artifact contracts

## Lineage

```text
source
  ├── evidence
  └── channel event (optional)
        └── signal
              └── decision
                    └── action
                          ├── metric
                          └── outcome
```

`run-state.json` records which artifacts and approvals are ready. It is not a substitute for the artifacts themselves.

## Connector artifacts

| Artifact | Role |
|---|---|
| `channel-connection.json` | Provider, product, environment, mode, capabilities, and secret references |
| `cs-events.jsonl` | Verified, redacted, deterministic canonical events |
| `reply-drafts.jsonl` | Draft-only responses and approval state |
| `delivery-events.jsonl` | Provider acceptance and terminal delivery events without state collapse |
| `connector-state.json` | Cursor, health, dedupe counts, recovery checkpoint, and blockers |

Connector artifacts are optional for manual signal import. Once any connector artifact exists, the connection, event, and state artifacts must be complete before the workflow can claim connector readiness.

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
- A connector stores secret references, never credential values.
- A normalized event records provider identity, verification assurance, and an idempotency key.
- A reply remains `external_write=false` until a separate approval artifact authorizes the exact target and content.
- `accepted` and `submitted` do not imply `delivered`.
- A fallback transport is a separate attempt and does not overwrite the original result.
- Updates append events or use `supersedes`; they do not rewrite history.

## Versioning

Schema IDs contain stable URLs. Release metadata and `artifact_versions` record compatibility. A breaking required-field or state change requires a major version and migration note.
