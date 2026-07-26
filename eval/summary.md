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

## Post-hardening runtime attempt — 2026-07-26

- Snapshot: `8aef638` (the deterministic hardening implementation is `89eea7e`).
- Codex CLI `0.145.0`: all 30 fixture-only semantic cases returned `pass` with
  `external_write=false`; five anchor cases repeated three times had identical
  selected skill, verdict, and hard-gate result.
- Claude Code `2.1.220`: no usable result. The Sonnet batch was blocked by the
  account monthly spend limit (HTTP 429), which is an environment blocker.
- Five fresh Codex evaluator contexts scored the available evidence 62, 35, 81,
  38, and 30 (mean 49.2). Their shared conclusion is `HOLD/NO-GO`: generated
  artifact E2E, real plugin installation, provider operation, and Claude/Codex
  parity are still unverified.

Structured capture is under `runs/2026-07-26-8aef638/`. Raw model outputs are
tracked; verbose local tool traces are intentionally ignored. This result does
not supersede the release gate.
