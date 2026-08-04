# Content brief — Signal to Growth 자기 랜딩 카피

`draft-evidence-content`를 이 저장소 자신에게 적용한 결과입니다.
산출물은 초안이며, README 반영과 공개는 사람 승인 뒤에 이루어집니다.

- 실행일: 2026-08-04
- 대상 저장소: 이 checkout (`upgrade/round1-marketing` worktree)
- 실행 skill: `skills/draft-evidence-content/SKILL.md`
- 동반 산출물: `claim-ledger.jsonl`, `draft.md`, `review-checklist.md`

## Audience

1차: Claude Code 또는 Codex를 이미 쓰고 있고, 초기 SaaS·1인 제품의 고객 근거를
정리해야 하는 제품 담당자·창업자.
2차: 패스트캠퍼스 「하네스 엔지니어링」 Part 6 수강생. 실습 환경에서 계정·API
key 없이 skill을 설치하고 preview부터 확인해야 하는 학습자.

두 집단 모두 "성장 프롬프트가 부족한" 상태가 아니라 "AI 초안과 사람 승인의
경계가 흐려진" 상태에서 이 저장소를 만납니다.

## Reader question

> 성장 관련 AI 프롬프트는 이미 많은데, 이 저장소는 내 작업 흐름에서 무엇을
> 다르게 만들어 주는가?

## Desired next decision

읽은 뒤 내려야 하는 판단은 "설치할지 말지"가 아니라
**"파일을 바꾸지 않는 preview를 한 번 돌려볼지"** 입니다.
CTA를 `/run-growth-loop` preview 1회 실행으로 좁힙니다.

## Direct answer (초안의 첫 단락에 들어갈 답)

Signal to Growth는 프롬프트 모음이 아니라, 고객 인용문에서 결과까지의 참조
무결성과 승인 경계를 파일로 강제하는 작은 운영 체계입니다. 11개 스킬이 하나의
`skills/` 소스를 공유하고, 산출물은 JSON·JSONL·Markdown 계약으로 다음 단계에
연결되며, 발송·게시·배포 같은 외부 실행은 정책 기본값에서 꺼져 있습니다.

## Evidence scope

- 사용 가능: 이 저장소 안의 파일·정책·계약·검증 기록 (`file:line`으로 인용).
- 사용 가능: 이미 README와 `eval/`에 공개된 평가 점수와 그 한계 서술.
- 사용 금지: 실제 고객 인용문, 사용자 수, 도입 사례, 성과 수치.
  이 저장소에는 그런 데이터가 없고, 만들어 쓰면 skill의 hard gate 위반입니다.
- 사용 금지: 경쟁 제품의 상대 비교를 "관찰"로 제시하는 문장.
  `docs/competitive-landscape.md`의 조사 결과는 추론(inference)으로만 인용합니다.

모든 material claim은 `claim-ledger.jsonl`에 ID로 등록했고, 각 항목에 저장소 내
`file:line` locator를 연결했습니다. locator 없는 문장은 초안에 넣지 않았습니다.

## Limitations (초안에 반드시 남길 것)

1. 릴리스 게이트는 아직 통과하지 않았습니다. 정적 baseline 평균 67/100 `NO-GO`,
   post-hardening 재평가 평균 49.2 `HOLD/NO-GO`가 공개 기록입니다.
2. Claude Code 런타임에서의 30-case 재평가는 환경 blocker(지출 한도·429)로
   완료되지 않았습니다. Codex 결과만으로 parity를 주장하지 않습니다.
3. Kakao 개발 채널 왕복과 Production 운영은 검증 범위 밖입니다.
4. append-only 강제는 현재 Claude Code 훅으로만 구현돼 있습니다.
   (→ `readme-claim-corrections.md`)
5. `scan-privacy`는 완전한 DLP가 아닙니다.

한계를 뒤쪽 각주로 미루지 않고 본문 안에 둡니다. 이 저장소의 판매 논리 자체가
"검증되지 않은 것을 검증된 것처럼 쓰지 않는다"이기 때문에, 한계를 숨기면 제품
주장과 문서가 서로를 반박합니다.

## CTA

- 1순위: `/run-growth-loop` preview 1회 (파일 변경 없음, Python 불필요)
- 2순위: `signal-to-growth demo .` (선택형 deterministic CLI)
- 하지 않는 CTA: 뉴스레터 구독, 문의 폼, 도입 상담, 유료 전환 유도.
  이 저장소에는 그런 수신 경로가 없고 만들 승인도 없습니다.

## Publication boundary

- 이 초안은 `docs/self-marketing/`에만 존재합니다.
- README.md 직접 수정은 하지 않았습니다. Wave 3 콘텐츠 담당자가 통합합니다.
- 외부 게시(블로그·SNS·릴리스 노트)는 승인 대상이며 이 실행 범위 밖입니다.
- git tag·GitHub Release 생성은 사람 승인 영역입니다.
