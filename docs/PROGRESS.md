# Signal to Growth — 고도화 PROGRESS

단일 진실 소스. Ralph Loop(`.claude/ralph-loop.local.md`, max_iterations=40, 완료조건="5개 도메인 전부 90점 이상 또는 3라운드 소진")가 매 iteration마다 이 파일을 읽고 다음 미완료 단계부터 이어간다.

## 현재 체크포인트

- **Round**: 2 / 3 진행 중. Round 1 push+CI 확인 완료 후, 자율 모드로 좁힌 범위 착수(사용자 승인: "점수가 낮으면 알아서 개선작업을 진행해").
- **Phase**: Round 2 Wave 1 진행 중 — 프로덕트 제외 4개 도메인(에이전트개발·콘텐츠·마케팅·자동화) 병렬 구현 dispatch 완료.
- **HEAD**: `f1fa50c` (Round 2 분기점, origin/main과 동일, push+CI 확인 완료).
- **Round 2 범위(구조적 상한 제외, 구체 결함만)**: 에이전트개발 4건(append-record 명시, 체인 13종 확장+fixture 재생성, audit-answer-visibility 라우터 편입, CLAUDE.md/AGENTS.md 절대경로 정리) / 콘텐츠 2건(citation-gaps.md 자기모순 정정, 목차+용어집) / 마케팅 1건(llms.txt 17→20) / 자동화 2건(정책 파일 런타임 강제, dead-letter runbook). **프로덕트는 제외**(남은 리스크 전부 W0-4 보류에 묶임).
- **다음 행동**: 4개 완료 대기 → main 머지 → Round 2 평가(fresh 5페르소나, 5개 전부 재평가 — 프로덕트도 변화 없는지 재확인 차원에서 포함).

## Round 0 (사전 이력, 이번 세션 착수 전) vs Round 1 점수

| 도메인 | Round 0 | Round 1 | 변화 |
|---|---:|---:|---|
| 마케팅 | 58 | 58 | 동일 |
| 프로덕트 | 62 | 61 | -1 |
| 자동화 | 68 | 68 | 동일 |
| 에이전트개발 | 82 | 74 | **-8** |
| 콘텐츠 | 74 | 72 | -2 |
| 평균 | 68.8 | 66.6 | -2.2 |

**5개 전부 HOLD, 90점 도달 0건.**

## ⚠️ 구조적 상한 발견 (Round 2 착수 전 사람 판단 필요)

Round 1에서 실제 엔지니어링 작업(Wave 1-3, 5개 도메인)을 했음에도 점수가 오르지 않거나 내려간 이유가 도메인별로 다르다:

1. **마케팅(58)·프로덕트(61)·자동화(68 중 상당 부분** — 다섯 평가자가 독립적으로 같은 결론에 도달: 최대 리스크가 **W0-4(실제 고객 인터뷰)**와 **provider E2E(카카오 개발 채널 실제 재시도 검증)** — 둘 다 이번 라운드에서 의도적으로 제외한 one-way door 항목에 묶여 있음. 이 두 항목이 승인되지 않는 한, 아무리 엔지니어링을 더 해도 이 세 도메인의 점수는 구조적으로 90에 도달하기 어려움.
2. **에이전트개발(74, -8)·콘텐츠(72, -2)** — 이건 다름. Round 1에서 추가한 새 장치(해시 체인, claim-ledger 골든 예제) 자체에서 **구체적이고 고칠 수 있는** 새 결함이 발견됨(아래 Round 2 후보 참조). 이 둘은 실제 엔지니어링으로 개선 가능.
3. **치명적 발견 — origin/main이 15커밋 뒤처짐.** 콘텐츠 평가자가 발견: 로컬 HEAD(`10d0a3f`)와 origin/main이 다른 문서 상태다. 실제 GitHub 방문자·`gh repo view`로 보는 README에는 six-part preview 목록이 아예 없다(로컬에만 있음). **이번 세션의 모든 개선이 push되지 않아 외부에는 보이지 않는 상태.**

**판단**: Round 2를 진행하되, 1번 범주(ICP·provider 미검증)는 목표에서 제외하고 2번 범주(에이전트개발·콘텐츠의 구체적 결함)에 집중하는 것을 권장. 1번을 포함한 채로 3라운드를 다 돌려도 W0-4/provider E2E 승인 없이는 90 도달이 물리적으로 불가능할 가능성이 높음.

## Round 1 상세 리스크 (Round 2 입력)

**에이전트개발 (82→74) — 4개 구체 항목**
1. `append-record` CLI가 11개 SKILL.md 어디에도 언급 안 됨 → Codex 세션이 존재를 모름
2. tamper-evidence(해시 체인)가 opt-in — 해시 필드 자체를 지우면 무력화됨, 배포 fixture 전량이 무체인
3. `CHAINED_KINDS`가 append-only 13종 중 5종만 커버
4. `audit-answer-visibility`가 `OBJECTIVE_ROUTES`/`SKILL_OUTPUT_FILES`에 없어 3자 drift 검사가 2자로 강등
5. (부수) `CLAUDE.md`/`AGENTS.md`가 이 머신에도 없는 절대경로 스크립트를 검증 절차로 지시(개인 경로 노출)

**콘텐츠 (74→72) — 2개 구체 항목**
1. `docs/self-marketing/citation-gaps.md`가 "EV-003는 어떤 claim에도 인용 안 됨"이라 적었지만, 실측 결과 `CLM-004`·`CLM-005`가 인용 중 — **자기 ledger와 모순**(제가 직접 재현 확인)
2. README 부피(716행)·용어 밀도(WSGI/RLS/parity 무설명) — 목차·용어집 부재

**마케팅 — 확인된 사실 오류 1건**
- `llms.txt`가 "17개 스키마"라 쓰는데 실제는 20개(README는 이미 20으로 정정됨) — llms.txt만 안 고쳐짐

**자동화 — 부분적으로 고칠 수 있는 항목**
- `policies/default-policy.json`을 런타임 코드 어디도 안 읽음(문서일 뿐, 강제 없음) — 이건 provider E2E와 무관하게 지금 고칠 수 있음
- dead-letter 조회·재처리 runbook 부재 — 마찬가지로 지금 고칠 수 있음
- (구조적 상한 항목) "503이면 카카오가 재시도한다"는 미검증 provider 동작에 의존 — provider E2E 승인 전엔 해소 불가

## Decision Log

- **[2026-08-04] W0-1 작업트리 처리** — 기존 dirty 상태를 "WIP checkpoint" 커밋(`b9bf161`)으로 보존. 가역성: 2-way door. 검증: `git status --porcelain` 빈 값.
- **[2026-08-04] W0-2 decision 계약 형태** — `harness/decisions.jsonl`(release-gate 로그)과 `contracts/decision.schema.json`(개별 성장결정용)이 다른 목적임을 확인. **결정: 리라이트 없이 신규 `contracts/gate-decision.schema.json` 분리.** 담당: 프로덕트. 완료.
- **[2026-08-04] W0-3 05-02 처리 방향** — 4/5 페르소나 독립 수렴: 신규 스킬 없이 라우팅 간선만. 담당: 에이전트개발. 완료(`workflow.py` `CONTENT_PREREQUISITE` 간선 구현 확인).
- **[2026-08-04] W0-4 실제 고객 인터뷰(P0-b) — 자동 실행 제외.** one-way door. **보류: 사람 승인 대기.** Round 1 5개 평가 전부가 이 보류를 최대 리스크로 재확인.
- **[2026-08-04] W0-5 CLI 정본** — 두 호출 형식 모두 유지, 관계만 문서화. 담당: 콘텐츠. 완료.
- **[2026-08-04] W0-6 DLQ 저장 위치** — 자동화 권고안 ⓐ(별도 Supabase DLQ 테이블 + 구조화 로그) 채택. 완료.
- **[2026-08-04] 머지 중 발견 — claim-ledger 스키마/데이터 통합 결함** — 프로덕트의 스키마와 콘텐츠의 데이터가 서로 모른 채 다른 필드 가정 → 충돌. 스키마 확장으로 해결(`60fc522`, `dc9a4fa`). 교훈: 완전 블라인드 병렬 worktree는 통합 결함을 머지 시점에만 드러낸다.
- **[2026-08-04] 커밋 실수 — add 누락** — 충돌 해결 중 파일을 추가로 Edit한 뒤 `git add` 재실행 없이 커밋해 커밋 메시지와 실제 내용이 불일치했던 사고 발생, `dc9a4fa`로 재커밋해 수정. 교훈: 커밋 직전 항상 `git status --porcelain`으로 unstaged 잔여 확인.
- **[2026-08-04] Round 1 완료, 구조적 상한 발견** — 5개 전부 HOLD, 90 미도달. 3개 도메인은 W0-4/provider E2E(둘 다 보류 항목)에 점수가 묶여 있어 추가 엔지니어링으로 해소 불가. 2개 도메인(에이전트개발·콘텐츠)은 구체적 신규 결함 발견, 해소 가능. **origin/main이 15커밋 뒤처짐 — 미push 상태로 이번 라운드 전체 작업이 외부에 안 보임.** Round 2 진행 여부 및 push 여부는 사람 결정 대기.

## Wave 0 상태: ✅ 완료 (6/6 결정, 1건 보류)

## Wave 1 — 병렬 구현 (worktree 격리, 파일 소유권 배타적) — 5/5 완료

| 도메인 | worktree | 상태 |
|---|---|---|
| 자동화 | `.worktrees/wt-automation` | ✅ 완료 `6999e86` |
| 에이전트개발 | `.worktrees/wt-agent-dev` | ✅ 완료 `c007be0` |
| 프로덕트 | `.worktrees/wt-product` | ✅ 완료 `a36c1c7` |
| 콘텐츠 | `.worktrees/wt-content` | ✅ 완료 `b35f154` |
| 마케팅 | `.worktrees/wt-marketing` | ✅ 완료 `d46eec8` |

머지 이력: `ebb063d`(content) → `7176095`(product) → `60fc522`(agent-dev) → `7542809`(automation) → `dc9a4fa`(schema fix 재커밋) → marketing 병합 → `554605a` → Wave 3 `10d0a3f`.

## Wave 2 — 05-02 라우팅 간선: 에이전트개발이 Wave 1 내 완료(`workflow.py` `CONTENT_PREREQUISITE`)

## Wave 3 — README 최종 통합: ✅ 완료 (`10d0a3f`, 콘텐츠 담당)

## 열린 이슈 / 사람 승인 대기

1. **origin push 여부** — 15커밋 로컬 전용, 공개 저장소라 push는 사용자 확인 필요.
2. **Round 2 진행 여부·범위** — 구조적 상한 3개 도메인 제외, 에이전트개발·콘텐츠·마케팅(llms.txt)·자동화(정책 강제·runbook) 구체 항목만 진행할지.
3. **W0-4 실제 고객 인터뷰 승인 범위** (프로덕트 P0-b) — 보류.
4. **provider E2E 승인** (자동화 리스크 1) — 카카오 개발 채널 실제 재시도 동작 확인 — 보류.
