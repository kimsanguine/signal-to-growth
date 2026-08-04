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

## Gate decisions

`harness/decisions.jsonl` records build and release gate verdicts for this
repository and follows `contracts/gate-decision.schema.json`. It is **not** the
same artifact as a run's `decisions.jsonl`, which holds `DEC-` growth decisions
under `contracts/decision.schema.json`. A gate record states a verdict
(`build`, `hold`, `pivot`), at least one reason, and the trigger that reopens it.
`validate-repo` checks it. See
[`contract-coverage-decisions.md`](contract-coverage-decisions.md) for why the
two contracts are separate.

## Claim states

`claim-ledger.jsonl` follows `contracts/claim-ledger.schema.json` and
`visibility-observations.jsonl` follows
`contracts/visibility-observation.schema.json`. Both enforce the vocabulary
below, and both enforce a floor rather than their skills' full prose output
contract — see [`contract-coverage-decisions.md`](contract-coverage-decisions.md).

Use one of:

- `observed`: directly checked;
- `reported`: stated by a participant or source;
- `inferred`: interpretation derived from evidence;
- `recommended`: proposed action;
- `unknown`: not supported by current evidence.

Never express `inferred` or `recommended` as `observed`.

## Content brief

`content-brief.json` follows `contracts/content-brief.schema.json`. It is the
one place the topic is decided, and both content surfaces read it: the blog
draft from `draft-evidence-content` and the visual prompts and video script from
`osmu-fanout`. Deciding once is what makes the surfaces reuse of one source
rather than three separately invented stories.

Unlike the ledgers above, a brief is **not** append-only. It is a plan file that
is rewritten until the person named in `owner` stops changing it, so it carries
no hash chain.

| Field | Why it is required |
|---|---|
| `source_signal_ids` / `source_observation_ids` | A topic must name where it came from; at least one of the two must be non-empty |
| `evidence_ids` | The scope a draft may cite, required whenever `planned_outputs` includes `blog-draft` |
| `planned_outputs` | The surfaces this one decision covers |
| `limitations` | A brief with no stated limit reads as unlimited |
| `owner` | Choosing what to publish is a promise to customers, so a person owns it |

`cta: null` is a decision, not a missing field. Record it when no validated
landing point exists yet.

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
- A content brief references existing signal, observation, and evidence IDs.
- A content brief's signals are `approved` and not `restricted`; an unreviewed
  or restricted signal cannot justify public content.
- A fanout reuses claims from an existing ledger and never raises a claim state
  to make a stronger picture.
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
