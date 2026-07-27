# Review queue

## `DEC-20260725-001` — 온보딩 검토 실험

- 상태: `approved`
- Owner: `product-owner`
- Review 예정일: `2026-08-08`
- **결과: review일에 확인, 결론 미확정.** `OUT-20260725-001`이 같은 날짜(`2026-08-08`)에 기록됐지만 `sample_size: 0`, `maturity_status: not_mature`, `comparison: inconclusive`, `conclusion: hold`다. review 날짜가 지났다고 결정이 자동으로 재확정되지 않는다 — 새 review_at을 append-only로 다시 잡아야 한다.
- Blocked evidence: 7일 관찰 기간을 채운 cohort가 아직 없다. 이 항목이 채워지기 전에는 `MET-20260725-001`의 값 자체가 존재하지 않는다.
- 다음 행동: `record-growth-decision`으로 돌아가 새 review_at을 설정하는 후속 decision(또는 supersede)을 기록한다. 이전 decision을 고쳐 쓰지 않는다.

## 놓치면 안 되는 것

review 날짜가 지났는데 이 큐에 아무 항목도 없다면, 그것은 "검토를 통과했다"는 뜻이 아니라 "검토를 놓쳤다"는 뜻이다. 이 파일이 비어 있는 것과 검토가 끝난 것은 다르다.
