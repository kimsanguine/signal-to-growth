# Contract coverage decisions

- Recorded: 2026-08-04
- Question: for each artifact without a root contract, write a contract or
  declare it a deliberate non-contract output?
- Scope: this document records judgements and reasons. It does not change
  `hooks/`, which another owner maintains.

## 1. Judgements

| Artifact | Judgement | Why |
|---|---|---|
| `claim-ledger.jsonl` | **(a) New contract** — `contracts/claim-ledger.schema.json` | Append-only protected, carries IDs and evidence references, and encodes the claim-state rule that a release hard gate depends on |
| `visibility-observations.jsonl` | **(a) New contract** — `contracts/visibility-observation.schema.json` | Same reasoning: append-only protected and carries a claim state that must not be overstated |
| `reach-plan.json` | **(b) Deliberate non-contract output** | Not append-only protected, holds no ID and no lineage reference, and is a human planning input rather than an audited record |
| `interview-guide.md` | **(b) Deliberate non-contract output** | Prose. A JSON Schema cannot express what makes an interview guide good; `lint-questions` already covers the risk that matters (leading questions) |

### Why the first two were the priority

`hooks/guard_append_only.py` already refused direct writes to both files. That
produced a contradictory state: the repository asserted the records were
important enough to be immutable history, while nothing defined what a valid
record was. Immutability without a contract preserves malformed history rather
than preventing it. Both now have a contract, and both are validated by
`validate-artifacts`.

### Why the last two are not a gap

Declaring a non-contract output is a judgement, not an omission, and the test is
whether the artifact carries auditable state that a downstream gate reads.

- `reach-plan.json` records a research question, a segment, exclusions, and
  `external_send: false`. Nothing references it by ID and no gate reads it. Its
  one safety-relevant field, the external-send boundary, is already enforced
  where it is acted on, not where it is declared.
- `interview-guide.md` is instructional prose for a human interviewer. Schema
  validation of prose produces a passing check that means nothing, which is worse
  than no check because it reads as coverage.

Both remain reviewable as ordinary files. If either later gains an ID or is read
by a gate, this judgement should be reopened.

## 2. Cross-check: `APPEND_ONLY_FILES` versus `contracts/`

Cross-checked mechanically against `hooks/guard_append_only.py`
(13 entries) after this round's additions.

| Append-only file | Contract | Enforced by |
|---|---|---|
| `evidence.jsonl` | `evidence.schema.json` | `validate-artifacts` |
| `signals.jsonl` | `signal.schema.json` | `validate-artifacts` |
| `metrics.jsonl` | `metric.schema.json` | `validate-artifacts` |
| `decisions.jsonl` | `decision.schema.json` | `validate-artifacts` |
| `actions.jsonl` | `action.schema.json` | `validate-artifacts` |
| `outcomes.jsonl` | `outcome.schema.json` | `validate-artifacts` |
| `approvals.jsonl` | `approval.schema.json` | `validate-artifacts` |
| `claim-ledger.jsonl` | `claim-ledger.schema.json` | `validate-artifacts` (new) |
| `visibility-observations.jsonl` | `visibility-observation.schema.json` | `validate-artifacts` (new) |
| `cs-events.jsonl` | `cs-event.schema.json` | `validate-connectors` |
| `reply-drafts.jsonl` | `reply-draft.schema.json` | `validate-connectors` |
| `delivery-events.jsonl` | `delivery-event.schema.json` | `validate-connectors` |
| `integration-references.jsonl` | `integration-reference.schema.json` | `import-pmf-radar` at write time |

**Result: no remaining mismatch.** Before this round, `claim-ledger.jsonl` and
`visibility-observations.jsonl` were the only two protected files with no
contract.

### Contracts that protect no append-only file

`channel-connection.schema.json`, `connector-state.schema.json`,
`run-state.schema.json`, `first-user-loop.schema.json`,
`hplan-intake-brief.schema.json`, `pmf-radar-export.schema.json`,
`gate-decision.schema.json`.

This is not a mismatch. The first six describe **current-state JSON documents**
that are meant to be rewritten as state advances — a cursor, a health record, a
run's phase. Making them append-only would be wrong. `gate-decision.schema.json`
is the exception and is discussed below.

### One filename, two contracts

`decisions.jsonl` appears in two places under two different contracts, which is
deliberate and easy to misread:

| Path | Contract | Content |
|---|---|---|
| `<artifacts>/decisions.jsonl` | `decision.schema.json` | `DEC-` growth decisions traced to evidence IDs |
| `harness/decisions.jsonl` | `gate-decision.schema.json` | `dec-` repository build/release gate verdicts |

The append-only hook matches on **basename**, so it protects both. Validation
routes by **path**: `validate-artifacts` applies the growth contract to a run's
artifact directory, and `validate-repo` applies the gate contract to
`harness/decisions.jsonl`. The two record shapes do not overlap — every gate
record violates the growth contract on many required fields — which is why the
gate log was given its own contract rather than being rewritten. Rewriting it
would have destroyed append-only history to satisfy a contract it was never
written against.

`tests/test_gate_decision_contract.py` asserts this divergence directly, so if
the two contracts ever converge the test fails and the seam is reconsidered
rather than kept out of habit.

## 3. Known gap: schema floor versus prose output contract

The two new contracts enforce **less** than their skills' prose output contracts
ask for, and this is a deliberate, bounded compromise rather than an oversight.

| Contract | Prose asks for, schema does not require |
|---|---|
| `claim-ledger.schema.json` | source date, owner, refresh date |
| `visibility-observation.schema.json` | URL or file, locale, question, result, source pointer |

Reason: the only records that exist are in the frozen public fixture, and that
fixture predates the fuller prose contract. Because both files are append-only,
a missing field **cannot be backfilled** — the record can only be superseded by
appending a new one. Requiring those fields today would make the shipped public
fixture permanently invalid and break `make check` for every student.

Each field above is therefore declared and typed in the schema but optional, so a
record that supplies it is still validated. Raising them to required is a
follow-up that needs a superseding fixture record appended through
`append-record`, which is a separate change.

Do not read these two contracts as full coverage of their skills' output
contracts. They are an enforced floor.

## 4. `docs/self-marketing/` — contract-shaped files outside `validate-artifacts`

Recorded: 2026-08-04 (Round 3).

Round 1 ran `audit-answer-visibility` and `draft-evidence-content` on this
repository itself and wrote the results to `docs/self-marketing/`. Both ledgers
carry contract file names but were written against no contract:
`claim-ledger.jsonl` used `claim_state`, `source_locators`,
`public_eligibility`, `source_checked_at`, `approval`, and `refresh_by`, and
`visibility-observations.jsonl` used `url_or_file` and `access_state`. Measured
before the fix: 19/19 claim records and 12/12 observation records failed their
schema. Nothing reported it, because no module, script, Makefile target, or
test named the directory.

### Why `validate-artifacts` cannot own this directory

`validate-artifacts` validates one **run's** artifact directory, and two of its
checks are relative to that directory:

- `_check_evidence_sources` resolves each evidence locator under the artifact
  directory's parent and rejects anything above it;
- `check_many("claim", "evidence_ids", "evidence")` resolves claim evidence IDs
  against a sibling `evidence.jsonl`.

This ledger's sources are files across the whole repository — `src/`, `hooks/`,
`policies/`, `README.md` — which sit outside `docs/`. Registering the folder
would report `locator.file escapes the approved source root` for citations that
are correct. The directory is a self-referential ledger, not a run.

### What is enforced instead

`tests/test_self_marketing_artifacts.py` checks the part that is checkable:
every record against its schema, the append chain of both ledgers, and whether
every `file:line` pointer in the directory still resolves. `make check` picks it
up through unittest discovery. The pointer check is a floor — it catches a
missing file or a line past the end, not a pointer that still lands inside the
file but on different content.

### The anchor rule in `claim-ledger.schema.json`

`skills/draft-evidence-content/references/output-contract.md` asks each claim
for "evidence IDs **or** source URLs", but the schema required at least one
evidence ID for every `observed` or `reported` claim. A claim whose source is a
repository file has a locator and no `EV-` record, so the only ways to pass were
to invent an evidence ID that resolves to nothing or to downgrade an observed
claim to a weaker state. Both defeat the contract's purpose. The rule now
accepts a non-empty `evidence_ids` **or** a non-empty `source_urls`, and still
rejects a claim that names neither.

### The one-time rewrite

Both ledgers are append-only protected by basename, so the 2026-08-04
normalization is a deliberate exception, not a precedent: the records were
rebuilt through `append_record` — the same writer the guard points at — so the
hash chain is genuine, the pre-migration file stays in git history, and
`CLM-20260804-020` states in the ledger itself what was renamed and why
`public` became `false`. A later correction to either ledger appends a
superseding record instead, as `CLM-20260804-018` and `VIS-20260804-013` do.

## 4. Classifying a decision event: `event_type`

- Recorded: 2026-08-04
- Question: `contracts/decision.schema.json` records *which* decision an event
  replaces. Should it also record *what kind* of change the event is?
- Judgement: **yes, as an optional `event_type` enum on the existing contract**,
  not as a new `decision-trace.schema.json`.

### The gap

`supersedes` carries lineage and nothing else. Three very different events —
narrowing what will be built, redefining a success condition, and stopping a
decision after mature outcomes arrived — produce records that are structurally
identical: same fields, same `supersedes` link, different prose. A reviewer
reading the log has to reconstruct the kind of change from `decision_question`
and `selected_option`, which is exactly the reconstruction an audited contract
exists to prevent.

`event_type` names the change: `initial_decision`, `scope_change`,
`success_metric_review`, `outcome_review`, `reversal`.

The five values are derived from this repository's own loop
(evidence → decision → action → outcome → review), not copied from a source
project. Notably absent is a spec-revision kind: this contract records growth
decisions, and a document edit is not a decision event here.

### Why extend the existing contract instead of adding a trace contract

A separate `decision-trace.schema.json` would create a second place where a
decision's history lives, and `contracts.py`, `workflow.py`,
`hooks/guard_append_only.py`, and the `record-growth-decision` output contract
would each have to agree on which of the two to read. `decisions.jsonl` is
already an append-only, hash-chained, one-event-per-line log — it *is* the
trace. The missing part was a classification field, so that is what was added.

This does not merge the growth-decision and gate-decision contracts. They stay
separate for the reason stated in section 3: a per-run product decision and a
repository gate verdict answer different questions.

### Backward compatibility

Three properties, each verified in `tests/test_decision_event_type.py`:

1. **The field is optional.** It is absent from `required` in the schema and
   from `REQUIRED_FIELDS["decision"]` in `contracts.py`, so every decision
   written before it existed still validates. `test_event_type_is_not_required`
   asserts this against the public fixture, unmodified.
2. **Absence means unclassified, not `initial_decision`.** Defaulting would
   assert something about historical records that nobody recorded. This is why
   `event_type` is deliberately **not** in `ENUM_FIELDS`: that table reports a
   missing value as a violation, which is right for a required enum and wrong
   for an optional one. The check lives in `_decision_event_type_issues`.
3. **No fixture or artifact was rewritten.** The hash chain in
   `fixtures/public-dummy/artifacts/decisions.jsonl` is untouched, so no
   migration is needed. Adopting the field is opt-in per record.

There is no migration path to write because nothing is required to migrate. A
record that wants the classification adds one field through `append-record`; a
record that does not stays valid indefinitely.

### The consistency rule, and why it is enforced twice

A present `event_type` must agree with the lineage the record carries: the four
change kinds require a non-null `supersedes`, and `initial_decision` requires
`supersedes` to be null. Without that rule the field is decoration — a label
that can contradict the record it labels.

It is enforced in both `contracts/decision.schema.json` (`allOf`/`if`-`then`)
and `contracts.py`, matching how `status: approved` → `approved_by` is already
handled. `test_schema_and_deterministic_check_share_one_enum` fails if the two
layers' enums drift apart.

## 5. Publishing the repository's own gate log

- Recorded: 2026-08-04
- Question: `harness/decisions.jsonl` holds this repository's real gate verdicts,
  but it is machine-shaped and unreferenced from the README. Publish it?
- Judgement: **render it to `docs/decision-log.md`, generated, never authored.**

The repository asks users to record decisions with reasons, review triggers, and
an unobserved-outcome state, while its own two such records sat in a JSONL file
no reader would open. Rendering them is the cheapest way to stop asking for a
discipline the project does not visibly practice.

`src/signal_growth/decision_log.py` holds the projection,
`scripts/render_decision_log.py` writes it, and `--check` compares without
writing. Three constraints shaped it:

- **The ledger stays the source.** The script refuses to render a gate log that
  fails `validate_gate_decision_log`, so an invalid record cannot be laundered
  into readable prose.
- **The page cannot drift.** `tests/test_decision_log.py` re-renders and
  compares, so a hand-edit to `docs/decision-log.md` fails the suite rather than
  quietly becoming a second, divergent account.
- **`outcome: null` renders as "아직 관측되지 않음", never as a result.** A
  recorded verdict is not a verified one, and the rendering must not blur that.

Static-site publication is out of scope. A Markdown file in the repository is
already readable by everyone the log is for.
