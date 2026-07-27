# Measurement plan

## `MET-20260725-001` — first-value activation rate

- 계측 공백: `data_source: product_events`가 이 fixture 환경에는 실제로 연결돼 있지 않다. 지금은 `decisions.jsonl`의 승인된 decision을 값 이벤트 대용으로 쓰고 있다.
- 쿼리 검증 단계: (1) `evidence_ids`가 유효한 EV- 참조인지 확인 (2) workspace 생성일 기준 7일 cohort maturity rule 적용 (3) 삭제된 test workspace 제외 확인.
- 리뷰 주기: cohort 단위(생성 후 7일)이므로 주 단위로 신규 cohort가 성숙할 때마다 재계산한다.
- target 변경 승인자: `owner` 필드(`growth-owner`)만 target을 바꿀 수 있다. baseline이 아직 `null`이므로 target도 `null`로 유지한다 — 미성숙 baseline 위에 target을 얹지 않는다.

## `MET-20260725-002` — unsupported decision rate (counter-metric)

- 계측 공백: `decision_log` 자체가 소스이므로 별도 계측 파이프라인은 필요 없다. 다만 evidence reference validation 실패를 자동으로 집계하는 스크립트가 아직 없다 — 현재는 `scripts/stg.py validate-artifacts`를 수동 실행해 확인한다.
- 쿼리 검증 단계: 해당 기간 승인된 decision 전체를 validator에 통과시키고 실패 건수를 센다.
- 리뷰 주기: calendar week. week가 완전히 끝난 뒤에만 확정 집계한다(진행 중인 week는 집계하지 않는다).
- target 변경 승인자: `owner` 필드(`product-owner`).

## 두 지표를 함께 보는 이유

`MET-20260725-001`이 올라가는데 `MET-20260725-002`도 같이 올라가면, activation 증가가 근거 없는 결정 증가로 만들어진 착시일 수 있다. 두 지표는 `counter_metric_ids`로 서로를 참조한다 — 하나만 보고 판단하지 않는다.
