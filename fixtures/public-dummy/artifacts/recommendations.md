# Recommendations

`audit-answer-visibility`의 네 번째 산출물이다. 모든 권고는
관찰 ID(`visibility-observations.jsonl`)에 연결되며,
관찰이 없는 권고는 이 파일에 넣지 않는다.

## 전제: 관찰은 하나뿐이고 그 값은 `not-live`다

이 fixture에는 관찰이 `VIS-20260725-001` 하나이고 상태는 `not-live`다.
따라서 **순위·인용·트래픽에 대한 어떤 권고도 할 수 없다.**
아래 권고는 전부 "페이지가 생기기 전에 준비할 수 있는 것"에 한정된다.

> 하지 않는 권고: "구조화 데이터를 넣으면 AI 답변에 인용될 것이다",
> "이 주제로 상위 노출될 것이다" — 관찰된 surface가 없으므로 근거가 없다.

## 권고 목록

### R-01 — 초안의 주장 상태 라벨을 게시본까지 유지한다

| 항목 | 내용 |
|---|---|
| 근거 관찰 | `VIS-20260725-001` (`not-live`) |
| 기대 메커니즘 | `draft.md`의 다섯 섹션은 `claim-ledger.jsonl`의 `observed`/`reported`/`inferred`/`recommended`/`unknown`과 앵커로 1:1 대응한다. 게시 과정에서 이 구분이 뭉개지면, 답변 엔진이 인용하든 사람이 읽든 추론을 관찰로 오해할 여지가 생긴다. |
| 담당 | 콘텐츠 작성자 (`fixture-reviewer`) |
| 검증 방법 | 게시본 HTML에서 각 `CLM-` 앵커가 살아 있고, 해당 문단의 상태 라벨이 ledger의 `state`와 같은지 대조한다. |
| 갱신 리스크 | 앵커 ID를 나중에 바꾸면 ledger의 `draft_locator.anchor`가 끊긴다. ID를 바꾸려면 ledger에 새 행을 append 해야 한다(기존 행 수정 불가). |
| 상태 | `recommended` — 아직 실행되지 않음 |

### R-02 — 반증을 초안에서 제거하지 않는다

| 항목 | 내용 |
|---|---|
| 근거 관찰 | `VIS-20260725-001` (`not-live`) + `EV-20260725-002`의 반증 메모 |
| 기대 메커니즘 | `CLM-20260725-003`은 "태그 집계가 보고한 값"과 "원문에서 관찰된 값"이 어긋난 사례다. 반증(가격을 직접 언급한 고객)을 지우면 남는 문장은 근거가 아니라 선택된 이야기가 된다. |
| 담당 | 콘텐츠 작성자 (`fixture-reviewer`) |
| 검증 방법 | 게시 전 `draft.md`에서 반증 문장을 grep 하고, 편집 과정에서 삭제됐는지 확인한다. |
| 갱신 리스크 | 분량을 줄이는 편집에서 반증 문단이 가장 먼저 잘리기 쉽다. 분량 축소 시 `unknown` 섹션과 반증 문단은 축소 대상에서 제외한다. |
| 상태 | `recommended` — 아직 실행되지 않음 |

### R-03 — 페이지를 만들기 전에는 CTA를 넣지 않는다

| 항목 | 내용 |
|---|---|
| 근거 관찰 | `VIS-20260725-001` (`not-live`) |
| 기대 메커니즘 | 착지할 URL이 없는 상태에서 CTA를 쓰면, 측정할 수 없는 전환을 약속하게 된다. `first-user-loop.json`의 사람 승인도 아직 없다. |
| 담당 | 사람 (강사 / 제품 책임자) |
| 검증 방법 | [`review-checklist.md`](review-checklist.md)의 CTA 항목이 `❌`로 남아 있는지 확인한다. |
| 갱신 리스크 | 페이지가 생긴 뒤 CTA를 추가하면, 그 시점부터 이 글은 정보성에서 전환 목적으로 성격이 바뀐다. 그때는 brief의 intent부터 다시 쓴다. |
| 상태 | `recommended` — 사람 결정 대기 |

### R-04 — 페이지 공개 시 technical 항목을 `not checked`에서 실제 값으로 바꾼다

| 항목 | 내용 |
|---|---|
| 근거 관찰 | `VIS-20260725-001` (`not-live`) |
| 기대 메커니즘 | [`technical-findings.md`](technical-findings.md)의 canonical·robots·structured data·heading·answer block·source-link 6개 항목은 현재 전부 `not checked`다. 페이지가 생기면 이 값들은 관찰 가능한 값으로 바뀔 수 있다. |
| 담당 | 배포 담당자 |
| 검증 방법 | 실제 URL에 대해 각 항목을 확인하고, `visibility-observations.jsonl`에 새 관찰 행을 append 한다. |
| 갱신 리스크 | `not checked`를 `not present`로 잘못 바꾸면, 검사 대상이 없었던 상태가 "검사했는데 없었다"로 왜곡된다. 두 값은 끝까지 구분한다. |
| 상태 | `recommended` — 선행 조건(페이지 공개) 미충족 |

## 아직 모르는 것 (`unknown`)

- 이 글이 어떤 답변 엔진에 인용될지: 관찰된 surface가 없어 판단 불가.
- 어떤 질문 표현으로 유입될지: 검색 질의 관찰 데이터가 없다.
- 위 권고들이 실제로 효과가 있는지: 실행된 것이 하나도 없으므로 결과가 없다.

이 세 항목은 추정으로 채우지 않고 `unknown`으로 남긴다.

## 완료 기준 대비 현황

`observed`(R-01~R-04의 근거 관찰), `reported`(태그 집계 값),
`inferred`(세 인터뷰 종합), `recommended`(위 4건), `unknown`(위 3건)이
이 파일 안에서 서로 구분돼 있다. 순위·인용에 대한 무근거 주장은 없다.
다만 관찰이 1건뿐이므로, 이 audit은 **완료가 아니라 착수 가능 상태**다.
