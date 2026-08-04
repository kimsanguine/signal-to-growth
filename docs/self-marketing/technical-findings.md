# Technical findings — 자기 감사

- 감사일: 2026-08-04
- 접근 상태: 로컬 checkout 읽기만. 라이브 HTTP 요청은 하지 않았다.
- `not checked`(확인 안 함)와 `not present`(확인했고 없음)를 구분한다.

| 항목 | 상태 | 근거 |
|---|---|---|
| HTTP 응답 코드 | not checked | 라이브 요청 미수행 (VIS-20260804-008) |
| canonical URL | not checked | 라이브 표면 미접근. 저장소는 정적 사이트가 아니다 |
| robots.txt | not present | 저장소 루트에 없음 (2026-08-04 `ls`). GitHub가 자체 robots를 제공하므로 저장소 부재가 곧 차단은 아니다 |
| sitemap.xml | not present | 같음. 저장소가 웹사이트가 아니므로 해당 없음에 가깝다 |
| 구조화 데이터 (JSON-LD / schema.org) | not present | grep 매치 0건 (VIS-20260804-003) |
| `llms.txt` | 감사 시점 not present → 이번에 추가 | VIS-20260804-004 |
| 헤딩 위계 | present, 편향 있음 | H1 1개 + H2 16개 + H3 14개. 질문형 헤딩 1개뿐 (VIS-20260804-002) |
| answer block (질문 → 직답 단위) | not present | FAQ·Q&A 섹션 없음 (VIS-20260804-002) |
| 출처 링크 | present | 내부 문서 링크 다수 + 외부 참고 5건 (README.md:810-814) |
| manifest homepage / websiteURL | present, 순환 참조 | 세 필드 동일 GitHub URL (VIS-20260804-005) |
| 문서 index | not present | `docs/` 진입 index 없음 (VIS-20260804-006) |
| 언어 신호 | ko-KR 본문 + 영어 tagline 1줄 | VIS-20260804-007 |
| CI·license badge | present | README.md:6-10 |
| 답변 엔진 인용 여부 | unknown | 질의하지 않음 (VIS-20260804-009) |
| 검색 순위 | unknown | 측정하지 않음 |

## 점수를 매기지 않은 이유

`skills/audit-answer-visibility/SKILL.md:40`은 자체 점수를 보정된 확률처럼
제시하지 말라고 규정합니다. 이번 감사는 라이브 관찰이 0건이므로 가중치를
공개하더라도 heuristic 점수를 낼 근거가 부족합니다. 점수 대신 관찰·미확인
목록만 남깁니다.

## 이 감사가 증명하지 않는 것

- 크롤러 접근 가능성은 답변 시스템이 이 페이지를 사용했다는 증거가 아닙니다.
- `llms.txt` 추가는 인용 증가의 증거가 아닙니다. 추가 사실만 관찰됐습니다.
- 순위·노출·인용에 대한 어떤 주장도 이 문서에 없습니다.
