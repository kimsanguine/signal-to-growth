# README 매핑표 초안 — 커리큘럼 × 스킬 × 산출물

- 작성일: 2026-08-04
- 상태: **초안**. README.md는 수정하지 않았습니다. Wave 3 콘텐츠 담당자가 통합합니다.
- 목적: README 「11개 스킬」 표(현재 README.md:55-67)가 스킬 순서만 보여주고
  강의 클립과의 대응은 보여주지 않는 문제를 메웁니다.

## 매핑표 (README 삽입안)

| 커리큘럼 | 스킬 | 산출물 |
|---|---|---|
| 01-01 고객 접촉 계획 | `plan-customer-reach` | `reach-plan.json`, `contact-drafts.md`, `recruitment-log.csv` |
| 01-02 인터뷰 설계와 증거화 | `run-switch-interview` → `synthesize-interviews` | `interview-guide.md` → `evidence.jsonl`, `counterevidence.md` |
| 02-01 신호 분류와 고위험 처리 | `triage-customer-signals` | `signals.jsonl`, `risk-queue.jsonl`, `dead-letter.jsonl` |
| 02-02 한국형 CS 채널 연결 | `connect-customer-channels` | `channel-connection.json`, `cs-events.jsonl`, `connector-state.json` |
| 03-01 지표 계약 | `define-growth-metrics` | `metrics.jsonl`, `measurement-plan.md` |
| 03-02 성장 결정 기록 | `record-growth-decision` | `decisions.jsonl`, `decision-summary.md` |
| 04-01 답변 가시성 감사 | `audit-answer-visibility` | `visibility-observations.jsonl`, `citation-gaps.md`, `technical-findings.md` |
| 04-02 근거 기반 콘텐츠 초안 | `draft-evidence-content` | `claim-ledger.jsonl`, `draft.md`, `review-checklist.md` |
| 05-01 첫 사용자 루프 설계 | `design-first-user-loop` | `first-user-loop.json`, `experiment-cards.md` |
| 05-02 승인 경계 아래의 실행 | `design-first-user-loop` + `draft-evidence-content` 조합 (라우팅 간선 추가 예정) | `first-user-loop.json` → `claim-ledger.jsonl`, `approvals.jsonl` |
| 전 구간 (오케스트레이션) | `run-growth-loop` | `run-state.json`, `next-action.md`, `blocked-items.md` |

11개 스킬이 모두 한 번 이상 등장합니다.

## 05-02 행에 대한 메모

05-02는 **신규 스킬이 아닙니다.** 5개 페르소나 중 4명이 독립적으로
"12번째 스킬 불필요, `design-first-user-loop` → `draft-evidence-content`
라우팅 간선만 추가"로 수렴했고, 그 결정이 이미 기록돼 있습니다
(`docs/PROGRESS.md:15`). 라우팅 간선 구현은 에이전트개발 담당의 Wave 2
작업입니다 (`docs/PROGRESS.md:36`).

따라서 README에는 "조합"으로만 표기하고, 새 스킬처럼 읽히는 표현
(`05-02 스킬`, `12번째 스킬`)을 쓰지 않습니다.

## 각 행의 근거 상태

표의 3열 형식을 유지하기 위해 근거 표시를 아래로 분리했습니다.
통합 담당자는 **제안** 행의 클립 번호를 실제 교안과 대조해 주세요.

| 커리큘럼 | 근거 | 상태 |
|---|---|---|
| 01-02 | `docs/v2-korean-cs-integration-plan.md:966` — "quote locator와 evidence contract" | 문서 확인됨 |
| 02-01 | 같은 문서 :967 — "manual signal taxonomy와 high-risk" | 문서 확인됨 |
| 02-02 | 같은 문서 :968 — "Kakao Open Builder request fixture, safe response, connector state" | 문서 확인됨 |
| 03-01 | 같은 문서 :969 — "connector coverage·false negative·counter-metric" | 문서 확인됨 |
| 03-02 | 같은 문서 :970 — "provider 선택 decision과 outcome backfill" | 문서 확인됨 |
| 05-02 | 같은 문서 :971 + `docs/PROGRESS.md:15` | 문서 확인됨 |
| 01-01, 04-01, 04-02, 05-01, 전 구간 | 저장소 문서에 클립 번호 기록 없음 | **제안** — 스킬 순서와 산출물 의존 관계에서 배치했습니다 |

산출물 이름은 모두 각 `skills/<name>/SKILL.md`의 `## Outputs` 절에서 그대로
가져왔습니다. 지어낸 파일 이름은 없습니다.

## 통합 시 주의

1. 이 표는 README.md:53-69의 기존 「11개 스킬」 표를 **대체하지 않고 보완**하는
   용도로 설계했습니다. 두 표를 모두 두면 중복이 커지므로, 통합 담당자가
   둘 중 하나를 고르거나 병합해 주세요. 매핑표만 남긴다면 기존 표의 "하는 일"
   열이 사라지므로, 스킬 설명이 다른 곳에 남는지 확인이 필요합니다.
2. `record-growth-decision`의 `approvals.jsonl`은 **사람이 승인한 뒤에만**
   생성됩니다 (`skills/record-growth-decision/SKILL.md`의 Outputs 주석).
   표에서 이 조건을 지우지 마세요.
3. 산출물 열의 파일명이 바뀌면 `skills/*/references/output-contract.md`가
   정본입니다. README를 먼저 고치지 마세요.
