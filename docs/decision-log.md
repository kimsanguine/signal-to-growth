# Decision log

이 문서는 `harness/decisions.jsonl`을 사람이 읽는 형태로 렌더링한 결과입니다.
직접 편집하지 마세요. 갱신은 다음 명령으로 합니다.

```bash
python3 scripts/render_decision_log.py
```

기록 원본은 append-only이므로 이 문서도 기록 순서(오래된 것부터)를 그대로
따릅니다. 판정이 바뀌면 앞선 항목을 고치지 않고 새 항목을 추가하며, 새 항목이
어떤 판정을 대체하는지는 `대체 대상`에 남습니다.

각 항목은 판정(`decision`), 그 판정을 뒤집는 조건(`review_trigger`), 그리고
관측된 결과(`outcome`)를 분리해 적습니다. 결과가 `아직 관측되지 않음`이면 그
판정은 아직 검증된 것이 아니라 기록된 것입니다.

## dec-stg-release-20260726-001

- 판정: **hold (보류)**
- 기록 시각: 2026-07-26T13:31:23+09:00
- 대상 gate: build / project: signal-to-growth
- 점수: 67
- 대체 대상: 없음 (선행 판정을 대체하지 않음)
- 관측된 결과: 아직 관측되지 않음

**판정 근거**

- Five-agent static and adversarial baseline returned NO-GO.
- Formal 30-case Claude Code and Codex runtime evaluation is pending.
- Kakao development-channel E2E and latest-commit authorized write are not verified.
- PMF Radar production wiring and hplan Build Gate remain separate pending gates.

**재검토 조건**

Review after identical 30-case runtime runs in Claude Code and Codex, zero hard-gate failures, and five fresh evaluator scorecards.

## dec-stg-course-distribution-20260727-001

- 판정: **build (진행)**
- 기록 시각: 2026-07-27T17:37:16+09:00
- 대상 gate: build / project: signal-to-growth
- 점수: 해당 없음
- 대체 대상: 없음 (선행 판정을 대체하지 않음)
- 관측된 결과: 아직 관측되지 않음

**판정 근거**

- Course distribution scope only: Part 6 C02-Clip02 requires connect-customer-channels, which existed only on the unmerged feature branch.
- Public main was v0.1.0 with 10 skills, so a student installing from main could not complete the clip exercise.
- Local suite 70 tests passed and CI validate (3.11, 3.12) plus Vercel checks passed on PR #1 before merge.
- Merge commit 9ab08d2; origin/main now reports version 0.3.0 with 11 skills.

**재검토 조건**

Re-review when the 30-case cross-runtime evaluation completes, before any release tag or Production promotion.

**범위 경계**

This decision does NOT supersede dec-stg-release-20260726-001. That hold governs release readiness (runtime evaluation, provider E2E, Production promotion) and remains in force. Approved here: default-branch merge for course use. Not approved: release tag, Vercel Production promotion, provider operation, external writes.
