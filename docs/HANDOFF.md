# Continuation handoff

- Updated: 2026-07-26
- Branch: `agent/korean-cs-connectors-v0-2`
- Last implementation commit: `149cf97`
- Last probed Preview commit: `e28c563`
- Pull request: [Draft PR #1](https://github.com/kimsanguine/signal-to-growth/pull/1)
- Release gate: **HOLD / NO-GO**

This file is the continuation entry point. Read it before changing a skill,
connector, integration contract, or deployment.

## What exists

- 11 canonical skills shared by Claude Code and Codex manifests.
- Complete Draft 2020-12 runtime validation for growth and connector artifacts.
- Exact evidence-locator verification and scoped `APR-` approval references.
- Korean high-risk PII, provider/channel, delivery-state, and replay-conflict
  guards.
- Objective-aware routing based on valid artifact state.
- `pmf-radar.stg.v1` dry-run import with opaque source reference preservation.
- Pre-gate hplan intake with `hplan_gate_decision=null`.
- A 30-case evaluation dataset and five-agent static baseline.

## Verified state

| Surface | Evidence |
|---|---|
| Local suite | `make check`: 70 tests passed |
| Skill packaging | 11/11 `quick_validate.py` passed |
| Plugin packaging | Codex and Claude manifest validation passed |
| GitHub CI | Python 3.11 and 3.12 passed on Draft PR #1 |
| Latest probed Preview | `/` and `/api/health` returned HTTP 200 |
| Health semantics | `configured`, `external_write=false` |
| PMF bridge | PMF fixture imported with one event and preserved source ref |
| hplan bridge | `ready_for_gate_review`; gate decision remained `null` |

The latest probed Preview is:

`https://signal-to-growth-dj50y96e2-sanguine-s-projects.vercel.app`

The latest commit did not repeat an authorized Kakao write. The existing
Kakao-to-Supabase idempotency evidence belongs to commit `903f571`.

## Decisions that must remain visible

1. The five-agent baseline is 67/100 and `NO-GO`.
2. Post-baseline hardening passed deterministic regression tests but was not
   re-scored. Do not infer a higher score.
3. PMF Radar owns long-running provider ingress and restricted raw retention.
4. Signal to Growth imports privacy-reduced normalized events and does not
   manufacture interview evidence from a CS event.
5. hplan owns its Build Gate. A Signal to Growth intake is not a gate pass.
6. Channel Talk remains an optional paid connector in the course. Kakao Open
   Builder is the primary course E2E.
7. No Production promotion, external reply, release tag, or default-branch
   merge has been approved.

The append-only release decision is in
[`../harness/decisions.jsonl`](../harness/decisions.jsonl).

## Resume sequence

### 1. Reproduce the checkpoint

```bash
git switch agent/korean-cs-connectors-v0-2
git pull --ff-only
make check
python3 /Users/sanguinekim/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
claude plugin validate .
```

Confirm the checked-out SHA before comparing evaluation results:

```bash
git rev-parse HEAD
```

### 2. Resume the formal cross-runtime evaluation

Use `eval/cases.jsonl` and `eval/expected-behaviors.md`.

Required capture per case:

- commit SHA, runtime name and version;
- case ID, raw output, generated artifact paths;
- deterministic validator result;
- external tool calls and write boundary;
- evaluator score and hard-gate result.

Codex fixture-only capture is complete at `eval/runs/2026-07-26-8aef638/`.
Claude Code was blocked by the account monthly spend limit (HTTP 429), so the
cross-runtime release gate remains `HOLD`. When that limit is lifted, run the
same canonical and repeated-anchor commands through `scripts/run_runtime_eval.py`.
Do not use real customer data, credentials, provider accounts, or external writes.

### 3. Re-score with five fresh evaluator contexts

Do this only after both runtimes finish the same case set. Save the new run
under a new SHA-specific directory. Never overwrite
`eval/runs/2026-07-26-fe3dfc4/`.

### 4. Continue the PMF Radar bridge

Follow the PMF Radar branch
`agent/signal-to-growth-bridge-v1` and its `docs/HANDOFF.md`. The next source
change is a restricted projection contract, not a Production database write.

### 5. Submit to hplan

Generate a `ready_for_gate_review` intake, then run hplan's own human Build Gate.
Keep `hplan_gate_decision=null` until that review occurs.

### 6. Perform provider E2E

After a separate approval:

1. connect the Kakao development channel;
2. verify request identity and redaction;
3. test idempotent storage with synthetic content;
4. inspect Supabase and Vercel logs;
5. record `HOLD`, `FIX_FORWARD`, or `ROLLBACK`.

## Human decisions before the next release gate

- Approve the runtime-evaluation budget and fixed model versions.
- Decide whether evaluation stays fixture-only or permits limited read-only
  research.
- Approve PMF Radar schema/migration work before applying it to Supabase.
- Approve Draft PR merge, release tag, and Production promotion separately.
