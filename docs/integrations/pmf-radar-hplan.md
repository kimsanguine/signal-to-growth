# PMF Radar and hplan integration

## Ownership

```text
customer channels
  → PMF Radar: ingest, authentication, redaction, retry, operator queue
  → Signal to Growth: evidence, signal, decision, metric, action, outcome
  → hplan: Evidence/Product/Build Gate and implementation handoff
  → outcome and new CS signals return to the loop
```

PMF Radar is the operational reference implementation. Signal to Growth owns
the portable event and growth-artifact contracts. hplan owns the decision to
enter implementation. Do not copy provider workers into skills or duplicate
hplan skill bodies in this repository.

## PMF Radar import contract

PMF Radar emits `pmf-radar.stg.v1` JSONL records. Each record contains:

- one canonical, redacted `event` following `contracts/cs-event.schema.json`;
- a restricted `source_record_ref`, never the raw payload;
- `product_scope` and optional `segment`;
- no credential or direct customer identifier.

Validate without writing:

```bash
signal-to-growth import-pmf-radar \
  --input fixtures/public-dummy/integrations/pmf-radar/stg-export.jsonl
```

Materialize the validated bridge artifacts only after reviewing the report:

```bash
signal-to-growth import-pmf-radar \
  --input pmf-radar-export.jsonl \
  --output-directory artifacts/pmf-import \
  --write
```

The command creates only:

- `cs-events.jsonl`;
- `integration-references.jsonl`.

The integration reference preserves PMF Radar's opaque `source_record_ref`.
The import does not create evidence or signals from model inference. Complete the
connection/state artifacts, then route the verified events to
`triage-customer-signals`.

## hplan intake contract

The hplan export is a gate input, not proof that a Build Gate passed.

```bash
signal-to-growth export-hplan \
  --artifacts artifacts/ \
  --decision-id DEC-20260725-001
```

The output keeps `hplan_gate_decision=null`. Missing product, JTBD, COGS,
latency, counter-position, or MVP fields appear in `unknown_fields`.

To require a gate-review-ready brief:

```bash
signal-to-growth export-hplan \
  --artifacts artifacts/ \
  --decision-id DEC-20260725-001 \
  --product-name "Signal to Growth" \
  --jtbd "고객 근거를 잃지 않고 다음 성장 결정을 내린다." \
  --functional-requirement "근거 ID를 결정과 연결한다." \
  --cogs-ceiling "프로젝트 정책에서 사람이 설정" \
  --latency-budget "프로젝트 정책에서 사람이 설정" \
  --counter-position "상담 자동화가 아니라 근거 계보를 관리한다." \
  --mvp-slice "한 고객 신호를 승인된 결정까지 연결한다." \
  --require-ready \
  --output hplan-intake.json
```

`ready_for_gate_review` means only that the intake fields are complete and the
source STG decision is approved. hplan still owns Evidence, Product, COGS, and
Build Gate decisions.

## Operational claims

Report these states separately:

- contract-validated;
- fixture-validated;
- locally executed;
- test-account verified;
- Preview verified;
- Production operational.

PMF Radar exports do not upgrade a fixture or Preview event to Production.
An hplan intake does not upgrade an STG decision to a Build Gate approval.
