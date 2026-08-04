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

`approvals.jsonl` follows `contracts/approval.schema.json`. Each approval names
a human approver, the later user turn that granted authority, exact decision or
action IDs, external-write scope, status, and optional expiry. An `APR-` prefix
by itself is not approval.

## Reference rules

- A decision references existing evidence IDs.
- An action references one existing decision and at least one metric.
- An outcome references one existing action and metric.
- An approved evidence strength names a human reviewer.
- An approved decision's approval artifact names a human reviewer.
- An approved decision references a scoped `APR-` approval artifact covering
  the exact decision ID.
- An approved or executed external action's approval artifact names a human reviewer.
- An approved or executed external action references a scoped `APR-` approval artifact.
- The referenced approval is `approved`, has `approver_type=human`, records a
  `user_turn_ref`, and covers the exact decision or action ID.
- A connector stores secret references, never credential values.
- A normalized event records provider identity, verification assurance, and an idempotency key.
- A reply remains `external_write=false` until a separate approval artifact authorizes the exact target and content.
- `accepted` and `submitted` do not imply `delivered`.
- A fallback transport is a separate attempt and does not overwrite the original result.
- Updates append events or use `supersedes`; they do not rewrite history.

## Cross-repository bridges

- `pmf-radar.stg.v1` wraps one redacted canonical CS event with product scope
  and a restricted PMF Radar source reference.
- `integration-references.jsonl` preserves external IDs without copying raw
  provider data.
- `hplan-intake.json` is a draft input to hplan gates. It never represents a
  passed Build Gate.

## Versioning

Schema IDs contain stable URLs. Release metadata and `artifact_versions` record compatibility. A breaking required-field or state change requires a major version and migration note.
