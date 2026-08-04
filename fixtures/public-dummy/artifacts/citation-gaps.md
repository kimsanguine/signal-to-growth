# Citation gaps

## Claim `CLM-20260725-001`

- 주장: "고객 발화와 해석을 분리하면 근거를 다시 확인할 수 있다."
- 대상 질문: "왜 인터뷰 요약이 아니라 evidence.jsonl 형식으로 남겨야 하는가?"
- 근거로 연결된 evidence: `EV-20260725-001`, `EV-20260725-002`
- **격차**: `visibility-observations.jsonl`의 `VIS-20260725-001`에 따르면 이 주장을 실을 공개 페이지가 `not-live` 상태다. claim은 존재하지만 audit할 실제 URL이 없다 — 아직 "인용 가능한 상태"가 아니다.
- 경쟁사 해석: 없음. 이 claim에 대해 경쟁사 문서를 참조하지 않았으므로 `[추론]` 라벨을 붙일 대상도 없다.

## 인용되지 않은 evidence 점검 (결과: 없음)

- 대상 질문: "근거로 수집해 놓고 아무 주장에도 쓰이지 않은 관찰이 남아 있는가?"
- 점검 결과: `evidence.jsonl`의 3건(`EV-20260725-001`·`002`·`003`)이 모두
  `claim-ledger.jsonl`의 최소 1개 claim에 인용돼 있다. 인용되지 않은 evidence는 없다.
  (`EV-20260725-003`은 `CLM-20260725-004`·`CLM-20260725-005`가 인용한다.)
- 재현 방법:

  ```bash
  python3 - <<'PY'
  import json
  ev = [json.loads(l)["evidence_id"] for l in open("evidence.jsonl") if l.strip()]
  cited = set()
  for l in open("claim-ledger.jsonl"):
      if l.strip():
          cited.update(json.loads(l).get("evidence_ids") or [])
  print("uncited:", [e for e in ev if e not in cited])
  PY
  ```

- 근거 없는 claim은 별개 항목이다: `CLM-20260725-006`은 `evidence_ids`가 비어 있지만
  `state`가 `unknown`이고 note에 "근거가 없다는 사실 자체를 기록한 상태"라고 적혀 있다.
  이는 인용 격차가 아니라 **공시된 미확인 상태**다 — 두 가지를 같은 칸에 넣지 않는다.

## 완료 기준까지 남은 것

이 파일은 claim이 하나 이상 있고 공개 페이지가 하나도 없는 상태를 보여준다. 완료 기준(모든 material claim이 근거를 갖고, 미공개 상태가 명시됨)은 현재 후자만 충족한다 — 페이지가 없다는 사실 자체가 명시돼 있다.
