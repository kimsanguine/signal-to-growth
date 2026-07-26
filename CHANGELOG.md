# Changelog

This file records user-visible changes. Signal to Growth follows semantic
versioning once a version is tagged.

## Unreleased

### Added

- A portable `connect-customer-channels` skill shared by Claude Code and Codex.
- Korean CS connector contracts, public dummy fixtures, and deterministic
  validation for Kakao Open Builder, Naver TalkTalk, and Channel Talk.
- A fail-closed Kakao Open Builder test endpoint backed by a restricted Supabase
  event sink.
- Approval-reference persistence and a seven-day deletion-eligibility marker for
  synthetic Kakao test events.
- GitHub issue and pull-request templates.

### Changed

- The skill suite now contains 11 skills and reports version `0.2.0`.
- CI runs once for feature pull requests, runs pushes only on `main`, cancels
  superseded runs, and pins third-party actions to commit SHAs.
- The hosted root route now returns safe service metadata instead of a 404.

### Security

- Kakao test requests require a separate shared key and redact customer
  identifiers before persistence.
- Supabase browser roles have no access to the test event table.
- Approval references must be non-secret identifiers beginning with `APR-`.

## 0.1.0

### Added

- Initial 10-skill evidence-to-growth workflow.
- Cross-runtime Claude Code and Codex manifests.
- Core artifact schemas, validators, public dummy examples, and safety policies.
