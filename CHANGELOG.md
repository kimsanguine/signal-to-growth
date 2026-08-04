# Changelog

This file records user-visible changes. Signal to Growth follows semantic
versioning once a version is tagged.

## 0.4.0

### Added

- An `append-record` CLI command and matching `PreToolUse` plugin hook that
  deny direct Edit/Write or recognized Bash overwrite patterns on the thirteen
  append-only JSONL artifacts, so
  concurrent agents cannot interleave writes or silently rewrite history.
- A scoped `approvals.jsonl` contract that requires a human approver, later
  user-turn reference, exact decision or action IDs, and approval status.
- A `reason` field on `next-step` output explaining in plain language why a
  given skill is next.
- A portable `connect-customer-channels` skill shared by Claude Code and Codex.
- Korean CS connector contracts, public dummy fixtures, and deterministic
  validation for Kakao Open Builder, Naver TalkTalk, and Channel Talk.
- A fail-closed Kakao Open Builder test endpoint backed by a restricted Supabase
  event sink.
- Hosted synthetic Kakao request → Vercel Preview → Supabase persistence →
  `version=2.0` response evidence, including live idempotency.
- Approval-reference persistence and a seven-day deletion-eligibility marker for
  synthetic Kakao test events.
- PMF Radar normalized-event import and source-reference contracts.
- A pre-gate hplan intake export that preserves unknowns and never claims a
  Build Gate decision.
- A versioned 30-case evaluation dataset and five-agent static baseline report.
- GitHub issue and pull-request templates.
- A complete `draft-evidence-content` golden example in the public dummy
  fixtures — `content-brief.md`, `draft.md`, and a `claim-ledger.jsonl` that
  carries one row per claim state (observed, reported, inferred, recommended,
  unknown), each anchored to the exact sentence it supports in `draft.md`.
- The missing `recommendations.md` output for `audit-answer-visibility`, with
  every recommendation tied to an observation ID, mechanism, owner,
  verification method, and update risk.
- An explicit six-part preview list in `README.md` and `docs/learner-start.md`,
  so a learner can tell a healthy install from a stale plugin cache.
- A documented relationship between the `signal-to-growth` console script and
  the `python3 scripts/stg.py` wrapper used by every `SKILL.md`.

### Changed

- The skill suite now contains 11 skills and reports version `0.4.0`.
- `README.md` is reordered so a reader reaches installation, the Python-free
  preview, and the optional five-minute local run before the philosophy
  sections; the CLI reference and the Kakao deployment procedure moved to the
  second half.
- `README.md` now carries a curriculum × skill × artifact mapping table, and
  records 05-02 as a routing edge between `design-first-user-loop` and
  `draft-evidence-content` rather than a twelfth skill.
- The release-status section now publishes both evaluation scores — 67/100 at
  `fe3dfc4` and 49.2/100 at `8aef638` — with the scoring-scope difference that
  explains why the later number is lower. The verdict stays `HOLD / NO-GO`.
- Cross-runtime claims in `README.md` now carry a footnote stating that the
  append-only PreToolUse hook exists only on the Claude Code adapter and that
  30-case runtime parity is unverified.
- `run-growth-loop` now defaults to a read-only six-part learning/preview
  response and waits for explicit confirmation in a later turn before apply.
- `next-step` now reads outcome-review state and routes an immature or held
  outcome to a follow-up growth decision instead of stopping at file completeness.
- Core artifacts now use complete Draft 2020-12 runtime validation, exact
  evidence-locator checks, and stronger metric, decision, outcome, and
  first-user-loop contracts.
- Workflow routing now uses objective and schema-valid dependency state instead
  of filename existence.
- Connector validation now enforces provider/channel and
  provider-status/canonical-status consistency.
- CI runs once for feature pull requests, runs pushes only on `main`, cancels
  superseded runs, and pins third-party actions to commit SHAs.
- The hosted root route now returns safe service metadata instead of a 404.
- Provider setup and verification documents now distinguish hosted synthetic
  E2E from a Kakao development-channel connection and Production operation.
- A five-agent static and adversarial baseline recorded a 67/100 mean and a
  `NO-GO`; formal 30-case runtime evaluation remains pending.

### Security

- Kakao test requests require a separate shared key and redact customer
  identifiers before persistence.
- Supabase browser roles have no access to the test event table.
- An explicit deny policy protects the test event table from browser roles even
  if table grants drift later.
- External-write approval references must resolve to scoped human approval
  records; an `APR-`-looking string alone is rejected.
- Conflicting same-ID events now fail instead of being silently deduplicated.
- High-risk Korean identifiers and unauthenticated Channel Talk production
  ingress fail the portable connector gate.

## 0.1.0

### Added

- Initial 10-skill evidence-to-growth workflow.
- Cross-runtime Claude Code and Codex manifests.
- Core artifact schemas, validators, public dummy examples, and safety policies.
