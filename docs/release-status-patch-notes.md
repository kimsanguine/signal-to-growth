# Release status patch notes

Draft text for whoever integrates the README release-status section. **This file
does not modify `README.md`.** It exists because the repository currently
publishes one evaluation number (67) while a second, lower number (49.2) exists
in `eval/summary.md`, and a reader who sees only the first will overestimate
readiness.

- Prepared: 2026-08-04
- Source of both numbers: [`../eval/summary.md`](../eval/summary.md)
- Release gate: **HOLD / NO-GO** (unchanged by this document)

## 1. Why two numbers exist

They are not a before/after improvement pair, and neither supersedes the other.
They score **different things over different evidence**:

| | 67 / 100 | 49.2 / 100 |
|---|---|---|
| Snapshot | `fe3dfc4` | `8aef638` |
| Date | 2026-07-26 | 2026-07-26 (post-hardening) |
| Mode | Static and adversarial review of the repository | Re-score of *available evidence* after the hardening |
| Evaluators | 5 independent perspectives | 5 fresh Codex contexts |
| Spread | 46–79 | 30–81 |
| Verdict | `NO-GO` | `HOLD / NO-GO` |

The scoring scope differs in a way that matters. The 67 baseline scored the
repository as written. The 49.2 re-score scored **the available evidence** — that
is, what could actually be demonstrated at that snapshot. Because generated
artifact E2E, real plugin installation, provider operation, and Claude/Codex
parity were still unverified, those dimensions scored as unproven rather than as
absent-and-therefore-ignored. A lower number after successful hardening is
therefore expected: the deterministic fixes landed and passed regression tests,
while the evidence bar the evaluators applied went up.

## 2. Draft paragraph for the README release-status section

> **Release gate: HOLD / NO-GO.** Two evaluation numbers are published on
> purpose. A five-agent static and adversarial baseline scored **67/100
> (`NO-GO`)** at snapshot `fe3dfc4`. After the deterministic hardening landed,
> five fresh evaluator contexts re-scored the **available evidence** at snapshot
> `8aef638` and returned **49.2/100 (`HOLD / NO-GO`, individual scores 30–81)**.
> The second number is lower because it scores what can be demonstrated, not
> what is written: generated-artifact E2E, real plugin installation, provider
> operation, and Claude Code/Codex parity remain unverified, and unverified
> dimensions score as unproven. Neither number is a runtime result — the formal
> 30-case cross-runtime evaluation is still incomplete, because the Claude Code
> batch was blocked by an account spend limit (HTTP 429) while the Codex batch
> finished. Do not read the hardening work, the passing test suite, or the
> merged default branch as a higher score. Release tag, Production promotion,
> provider operation, and external writes remain unapproved.

## 3. GO conditions, summarized

From [`skill-evaluation-plan.md` §7](skill-evaluation-plan.md#7-판정-기준).
Release reaches `GO` only when **all** hold:

1. **Zero hard-gate failures.** No fabricated quote or source, no credential or
   customer-text exposure, no unapproved send/publish/deploy/delete, no
   synthetic fixture reported as production, no `accepted`-as-`delivered` or
   Kakao-chatbot-as-ConsultTalk confusion, no broken artifact reference reported
   as complete.
2. **Deterministic artifact validation at 100%.**
3. **Overall task success at 85% or above.**
4. **Every critical skill at 80 points or above.**
5. **Cross-runtime semantic parity at 90% or above.**
6. **ICP fixed** — general SaaS versus AI B2B SaaS recorded as a human-approved
   decision.

Condition 6 was promoted in this round from a pre-run setting
(`skill-evaluation-plan.md` §9-5) to an explicit hard gate. The original list had
five conditions; anyone reconciling this against an older copy should expect six.
Its input is the customer interview round, which is on hold pending human
approval to recruit real participants — so condition 6 is currently unmet and
`GO` is unreachable regardless of any score.

## 4. What this document does not do

- It does not change the release verdict.
- It does not modify `README.md` or `CHANGELOG.md`.
- It does not re-score anything. Both numbers are quoted from `eval/summary.md`.
