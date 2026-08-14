# Evaluation remediation backlog

The ordered backlog of remaining work lives in one place:
The private handoff's "Resume sequence". This file keeps
only the record of what the post-baseline hardening actually changed, because
that record is evidence rather than a plan.

## Implemented after the baseline

- Enforce full Draft 2020-12 JSON Schema validation in the runtime.
- Verify evidence excerpts at the declared source path and line.
- Reject empty and schema-invalid completion artifacts.
- Route by objective and valid dependency state.
- Enforce provider/channel and provider-status/canonical-status consistency.
- Extend high-risk Korean PII detection and redaction.
- Reject unauthenticated Channel Talk production ingress.
- Raise an identity conflict for same-ID, different-content replay.
- Require a scoped `APR-` approval reference for external writes.
- Strengthen metric, decision, outcome, and first-user-loop contracts.
- Check version parity across package and plugin manifests.
- Add PMF Radar import and pre-gate hplan intake contracts.

## Pending release gates

Moved to the private handoff. Release stays
`NO-GO` until hard-gate failures are zero. Step 2's 2026-08-04 status (blocked by
account spend limit) is recorded in HANDOFF step 2 directly.
