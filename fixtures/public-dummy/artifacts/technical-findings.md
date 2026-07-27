# Technical findings

## Surface: `VIS-20260725-001` (public-dummy)

| 항목 | 상태 |
|---|---|
| status | `not-live` — 이 fixture는 실제 공개 URL이 없다 |
| canonical | not checked (페이지가 없으므로 검사 대상 자체가 없음) |
| robots | not checked |
| structured data | not checked |
| heading | not checked |
| answer block | not checked |
| source-link | not checked |

## "확인 안 함"과 "없음"의 구분

이 표의 모든 항목이 `not checked`인 이유는, 페이지가 아예 `not-live`이기 때문이다. 이것은 "확인했는데 구조화 데이터가 없었다"(`not present`)와 다르다. `not present`라고 잘못 적으면 마치 페이지가 있는데 결함이 있는 것처럼 읽힌다. 실제로는 검사할 대상 자체가 아직 없다.

## 다음에 실제 URL이 생기면 다시 확인할 것

- canonical 태그가 있는가
- robots.txt/meta robots가 크롤러를 막고 있지 않은가
- FAQ/HowTo 등 구조화 데이터가 있는가
- H1이 질문과 직접 대응하는가
- 첫 문단이 answer-first인가
- 인용한 수치·주장에 소스 링크가 붙어 있는가

이 항목들은 `claim-ledger.jsonl`의 `CLM-20260725-001`이 실제 페이지에 실린 뒤에만 관찰(observed) 값으로 바뀔 수 있다.
