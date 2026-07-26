# Five-agent baseline evaluation

- Snapshot: `fe3dfc4`
- Date: 2026-07-26
- Mode: independent read-only static and adversarial review
- Release decision: **NO-GO**
- Mean score: **67/100**

| Evaluator | Score | Decision |
|---|---:|---|
| Primary User | 71 | NO-GO |
| Product Rigor | 67 | NO-GO |
| Korean CS Ops | 72 | NO-GO |
| Cross-runtime | 79 | HOLD |
| Red Team | 46 | NO-GO |

## Confirmed baseline failures

1. Evidence locator line mismatches could pass validation.
2. The core CLI did not enforce the complete JSON Schema contract.
3. Empty artifacts could be treated as complete, and routing was filename-led.
4. Provider/product and provider-status mappings allowed false operational claims.
5. High-risk Korean identifiers were not covered by the portable redaction gate.
6. An unauthenticated Channel Talk production input could be accepted.
7. The same event ID with different content could be silently deduplicated.
8. Bare approval strings could be mistaken for scoped external-write approval.
9. Metric, decision, outcome, and first-user-loop contracts were under-specified.
10. Plugin manifest version drift was not checked.
11. Real Claude Code and Codex install, discovery, and invocation parity was not
    demonstrated.

## Scope boundary

This baseline was not a formal execution of all 30 canonical cases. It reviewed
the same repository snapshot from five specialist perspectives and supplied
reproducible hardening targets. The 30-case runtime suite in `cases.jsonl`,
including repeated nondeterministic anchors and real runtime invocation evidence,
remains pending. Post-remediation scores must not be inferred from this baseline.
