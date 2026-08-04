# Signal to Growth — 고도화 PROGRESS

단일 진실 소스. Ralph Loop(`.claude/ralph-loop.local.md`, max_iterations=40, 완료조건="5개 도메인 전부 90점 이상 또는 3라운드 소진")가 매 iteration마다 이 파일을 읽고 다음 미완료 단계부터 이어간다.

## 현재 체크포인트

- **Round**: 1 / 3
- **Phase**: Wave 0 완료 → Wave 1 착수
- **다음 행동**: Wave 1 다섯 도메인 병렬 구현 에이전트 dispatch (worktree 격리)

## Decision Log

- **[2026-08-04] W0-1 작업트리 처리** — 기존 dirty 상태(README.md·skills/run-growth-loop·synthesize-interviews·contracts.py·workflow.py 수정 7건 + learner-start.md·fixture 13건 untracked)를 "WIP checkpoint" 커밋으로 보존. 근거: Rule(파괴적 작업 전 git status 확인, 불확실하면 stash/커밋 우선). 가역성: 2-way door(git revert 가능, push 안 함). 검증: 커밋 후 `git status --porcelain` 빈 값 확인.
- **[2026-08-04] W0-2 decision 계약 형태** — `harness/decisions.jsonl`(release-gate 로그, 실제 필드: decision_id/recorded_at/gate/decision/score/reasons/review_trigger/outcome/supersedes)과 `contracts/decision.schema.json`(개별 성장결정용, 18 required 필드: made_at/decision_question/evidence_ids/...)이 서로 다른 목적의 레코드임을 확인(실측: 레코드 grep + schema required 대조). **결정: 기존 decisions.jsonl을 리라이트하지 않고, 신규 `contracts/gate-decision.schema.json`을 만들어 release-gate 로그를 별도 계약으로 분리한다.** 근거: append-only 이력 재작성 금지 원칙과 상충하지 않음. 가역성: 2-way. 담당: 프로덕트.
- **[2026-08-04] W0-3 05-02 처리 방향** — 5개 페르소나 중 4명(마케팅·프로덕트·에이전트개발·콘텐츠)이 독립적으로 "신규 12번째 스킬 불필요, `design-first-user-loop`→`draft-evidence-content` 라우팅 간선만 추가"로 수렴. **결정: 라우팅 연결만 추가, 스킬 신설 안 함.** 담당: 에이전트개발(Wave 2, workflow.py 정리 후).
- **[2026-08-04] W0-4 실제 고객 인터뷰(P0-b) — 자동 실행 제외** — one-way door(실제 인물 섭외·동의·공개)이므로 ralph loop 자율 범위에서 제외. **보류: 사람 승인 대기.** 프로덕트 Wave 1 작업은 P0-a(계약 분리)·P1(로드맵 병합)·P2(점수 공시)·P3(스키마 미커버 판정)·P5(ICP 게이트 승격)만 진행. P0-b는 이 라운드에서 다루지 않음.
- **[2026-08-04] W0-5 CLI 정본** — 낮은 blast radius 기본값: 두 호출 형식(`signal-to-growth` console script / `python3 scripts/stg.py`)을 모두 유지하고 관계만 문서화(SKILL.md 17곳 변경 안 함). 담당: 콘텐츠.
- **[2026-08-04] W0-6 DLQ 저장 위치** — 자동화 페르소나 권고안 ⓐ 채택: 계약 위반 이벤트는 별도 Supabase DLQ 테이블, 가용성 실패는 구조화 로그. 외부 의존 추가 없음. 담당: 자동화.

## Wave 0 상태: ✅ 완료 (6/6 결정, 1건 보류)

## Wave 1 — 병렬 구현 (worktree 격리, 파일 소유권 배타적)

| 도메인 | worktree | 상태 |
|---|---|---|
| 자동화 | `.worktrees/wt-automation` | 대기 |
| 에이전트개발 | `.worktrees/wt-agent-dev` | 대기 |
| 프로덕트 | `.worktrees/wt-product` | 대기 |
| 콘텐츠 | `.worktrees/wt-content` | 대기 |
| 마케팅 | `.worktrees/wt-marketing` | 대기 |

## Wave 2 — 순차 (Wave 1 완료 후)

1. 자동화(훅 우회 실증) → 에이전트개발(체인 탐지 테스트 픽스처화)
2. 콘텐츠(fixture 추가) → 에이전트개발(`REQUIRED_COMPLETE_FILES` 확대 여부 결정)
3. 에이전트개발(05-02 라우팅 그래프 추가, W0-3 반영)

## Wave 3 — 통합 (README/CHANGELOG/HANDOFF, 콘텐츠 단독 최종 편집)

마케팅 포지셔닝 문구 + 프로덕트 점수공시 절충안(상단은 링크만, 하위 섹션에 67·49.2 둘 다 명시) 입력받아 콘텐츠가 1회 통합.

## Round 1 평가: 미실시

## 열린 이슈 / 사람 승인 대기

- W0-4 실제 고객 인터뷰 승인 범위 (프로덕트 P0-b) — 보류
