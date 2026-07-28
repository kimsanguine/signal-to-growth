# Changelog

This file records user-visible changes. Signal to Growth follows semantic
versioning once a version is tagged.

## Unreleased

### Added

- An `append-record` CLI command and matching `PreToolUse` plugin hook that
  deny direct Edit/Write on the twelve append-only JSONL artifacts, so
  concurrent agents cannot interleave writes or silently rewrite history.
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

### Changed

- The skill suite now contains 11 skills and reports version `0.3.0`.
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
- Approval references must be non-secret identifiers beginning with `APR-`.
- Conflicting same-ID events now fail instead of being silently deduplicated.
- High-risk Korean identifiers and unauthenticated Channel Talk production
  ingress fail the portable connector gate.

## 0.1.0

### Added

- Initial 10-skill evidence-to-growth workflow.
- Cross-runtime Claude Code and Codex manifests.
- Core artifact schemas, validators, public dummy examples, and safety policies.
