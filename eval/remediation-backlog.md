# Evaluation remediation backlog

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

1. Complete Claude's 30 canonical cases after the monthly spend limit is lifted;
   Codex capture is complete but does not establish parity.
2. Repeat the five nondeterministic anchors three times in Claude after that
   runtime becomes available; Codex repetition is complete.
3. Verify real installation, discovery, and explicit invocation in both Claude
   Code and Codex.
4. Re-score with five fresh evaluator contexts after deterministic tests pass.
5. Keep release `NO-GO` until hard-gate failures are zero.
