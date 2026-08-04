# Content brief — "요약 대신 evidence를 남기는 이유"

이 brief는 `draft-evidence-content` skill의 출력 계약 중 첫 산출물이다.
초안(`draft.md`)을 쓰기 **전에** 무엇을 쓰고 무엇을 쓰지 않을지 먼저 고정한다.

## 대상 독자 (audience)

고객 문의가 여러 채널로 들어오기 시작한 3~10인 규모의 초기 SaaS 팀에서,
"다음에 무엇을 고칠지"를 결정하는 사람. 리서치 전담 인력이 없고,
인터뷰를 해도 정리는 스프레드시트나 메모로 끝나는 상태.

## 답하려는 질문 (question)

> "인터뷰를 요약해서 남기면 되는데, 왜 굳이 발화와 해석을 나눠서
> `evidence.jsonl` 같은 형식으로 남겨야 하는가?"

## 의도 (intent)

정보성(informational). 제품 구매를 설득하지 않는다.
독자가 자기 팀의 기록 방식을 한 번 점검하게 만드는 것까지가 목표다.

## 직접 답 (direct answer)

요약은 근거를 지운다. 요약본만 남기면 나중에 우선순위를 다시 따질 때
"고객이 실제로 한 말"과 "그때 우리가 내린 해석"을 구분할 수 없다.
발화와 해석을 분리해 저장하면, 판단이 바뀌어도 근거는 그대로 남는다.

## 근거 범위 (evidence scope)

| 쓸 수 있는 것 | 위치 | 강도 |
|---|---|---|
| `EV-20260725-001` | `../interviews/P-20260725-001.md:12` | strong |
| `EV-20260725-002` | `../interviews/P-20260725-002.md:10` | medium |
| `EV-20260725-003` | `../interviews/P-20260725-003.md:12` | medium |

- 이 세 건은 모두 **공개 가능한 합성 인터뷰**다. 실제 고객 데이터가 아니다.
- `evidence.jsonl`에 없는 사실은 초안에 쓰지 않는다.
- 외부 통계·경쟁사 자료는 이번 초안에서 인용하지 않는다.

## 한계 (limitations)

- 표본이 3명이다. 어떤 비율·확률 주장도 할 수 없다.
- 세 인터뷰 모두 합성 데이터라서, 실제 시장에서 재현된 적이 없다.
- `EV-20260725-002`에는 반증이 함께 기록돼 있다(가격을 직접 언급한 고객도 존재).
  이 반증은 초안에서 지우지 않고 그대로 노출한다.
- 초안이 다루지 못한 질문은 [모르는 것](draft.md#CLM-20260725-006)에 남긴다.

## CTA

**이번 초안에는 CTA를 넣지 않는다.**
`first-user-loop.json`이 아직 사람 승인을 받지 않았고,
`visibility-observations.jsonl`의 `VIS-20260725-001`이 `not-live`이므로
전환을 유도할 착지점 자체가 없다. CTA는 그 두 조건이 풀린 뒤에 다시 논의한다.

## 게시 경계 (publication boundary)

- 이 brief와 `draft.md`는 **게시되지 않았다.** 초안 파일 생성까지만 수행한다.
- 게시·발송·배포는 `approvals.jsonl`에 범위가 명시된 사람 승인 기록이
  있을 때만 가능하다. 현재 그 기록은 없다.
- 최종 상태는 [`review-checklist.md`](review-checklist.md)에서 확인한다.
  현재 최종 게시 승인은 **미승인**이다.

## 관련 산출물

- 초안: [`draft.md`](draft.md)
- 주장 대장: [`claim-ledger.jsonl`](claim-ledger.jsonl)
- 인용 격차: [`citation-gaps.md`](citation-gaps.md)
- 검토 체크리스트: [`review-checklist.md`](review-checklist.md)
