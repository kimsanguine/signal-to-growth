# Continuation handoff

- Updated: 2026-07-27
- Branch: `main` (feature branch merged)
- Merge commit: `9ab08d2`
- Last probed Preview commit: `e28c563`
- Pull request: [PR #1](https://github.com/kimsanguine/signal-to-growth/pull/1) — **MERGED 2026-07-27**
- Release gate: **HOLD / NO-GO** (unchanged)

`main` now publishes version `0.4.0` with 11 skills. The 2026-07-27 merge
recorded `0.3.0`; the version has moved since and that decision record is
append-only, so it is not edited. This merge was approved for one purpose only:
the Part 6 course exercise needs `connect-customer-channels`, which previously
existed only on the feature branch, so a student installing from `main` could not
complete the clip. See `harness/decisions.jsonl`
(`dec-stg-course-distribution-20260727-001`).

The merge did **not** change the release gate. Release tag, Vercel Production
promotion, provider operation, and external writes remain unapproved and the
`hold` in `dec-stg-release-20260726-001` stays in force.

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
7. The default-branch merge was approved on 2026-07-27 for course distribution
   only. No Production promotion, external reply, or release tag has been
   approved.

The append-only release decision is in
[`../harness/decisions.jsonl`](../harness/decisions.jsonl).

## Resume sequence

This section is the **canonical ordered backlog**. It previously existed in four
places that drifted apart. The other three now point here and keep only the
material that is not sequencing:

| Document | What it still owns |
|---|---|
| [`../eval/remediation-backlog.md`](../eval/remediation-backlog.md) | The record of hardening already implemented after the baseline |
| [`v2-korean-cs-integration-plan.md`](v2-korean-cs-integration-plan.md) | Connector design detail and per-gate pass conditions |
| [`skill-evaluation-plan.md`](skill-evaluation-plan.md) | Evaluation method, rubric, and release judgement criteria |

Work the steps in order. A step may not start until every earlier step is
complete, unless the step says otherwise.

### 0. Reproduce the checkpoint

The feature branch was merged on 2026-07-27, so the checkpoint is now `main`.

```bash
git switch main
git pull --ff-only
make check
python3 /Users/sanguinekim/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
claude plugin validate .
```

Confirm the checked-out SHA before comparing evaluation results:

```bash
git rev-parse HEAD
```

### 1. Fix the pre-run evaluation decisions — human, blocking

These five are listed in
[`skill-evaluation-plan.md` §9](skill-evaluation-plan.md#9-정식-runtime-평가-시작-전-결정할-것)
and must be fixed before any case runs, because changing them mid-run
invalidates the results.

1. Evaluation snapshot SHA.
2. Fixed Claude Code and Codex model and version.
3. Fixture-only versus permitted read-only research ratio.
4. Cost and time ceiling.
5. **ICP: general SaaS or AI B2B SaaS.** This is now a hard gate condition for
   release `GO`, not only a pre-run setting. Its input is the customer interview
   round, which is **on hold pending human approval to recruit real
   participants**. Until that decision is recorded, release cannot reach `GO`.

### 2. Run the Claude Code 30-case evaluation

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
same canonical commands through `scripts/run_runtime_eval.py`. Do not use real
customer data, credentials, provider accounts, or external writes.

This step was not attempted during the 2026-08-04 upgrade round because the
account spend limit was still in force. The plan remains to run all 30 cases
in one `scripts/run_runtime_eval.py` batch once the limit resets, then re-score
step 5 before any release decision.

### 3. Repeat the five nondeterministic anchors three times in Claude Code

Codex repetition is complete. Codex completion does not establish parity.

### 4. Verify real installation, discovery, and explicit invocation

Do this in both Claude Code and Codex. A passing manifest validator is not
evidence that installation and discovery work.

### 5. Re-score with five fresh evaluator contexts

Do this only after both runtimes finish the same case set. Save the new run
under a new SHA-specific directory. Never overwrite
`eval/runs/2026-07-26-fe3dfc4/` or `eval/runs/2026-07-26-8aef638/`.

### 6. Re-judge the release gate

Score the result against the `GO` conditions in
[`skill-evaluation-plan.md` §7](skill-evaluation-plan.md#7-판정-기준). Release
stays `NO-GO` while any hard-gate failure remains. Record the verdict by
appending to [`../harness/decisions.jsonl`](../harness/decisions.jsonl) with the
`append-record` command; never edit that file in place.

### 7. Perform provider E2E — requires separate approval

1. connect the Kakao development channel;
2. verify request identity and redaction;
3. test idempotent storage with synthetic content;
4. inspect Supabase and Vercel logs;
5. record `HOLD`, `FIX_FORWARD`, or `ROLLBACK`.

### 8. Continue the PMF Radar bridge

Follow the PMF Radar branch `agent/signal-to-growth-bridge-v1` and its
`docs/HANDOFF.md`. The next source change is a restricted projection contract,
not a Production database write.

### 9. Submit to hplan

The public dummy intake is `fixtures/public-dummy/hplan-intake.json`. It is
`ready_for_gate_review` only for a fixture decision, then run hplan's own human
Build Gate with real reviewed evidence. Keep `hplan_gate_decision=null` until
that review occurs.

## Human decisions before the next release gate

These are the one-way doors inside the backlog above. None may be taken by an
agent.

- Approve recruiting real interview participants, which unblocks step 1 item 5
  (ICP) and therefore the release gate.
- Approve the runtime-evaluation budget and fixed model versions (step 1).
- Decide whether evaluation stays fixture-only or permits limited read-only
  research (step 1).
- Approve the Kakao development-channel E2E (step 7).
- Approve PMF Radar schema/migration work before applying it to Supabase
  (step 8).
- Approve the release tag and Production promotion separately. (The default-branch
  merge was approved on 2026-07-27 for course distribution and is done.)
