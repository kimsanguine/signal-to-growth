# Signal to Growth

> 고객 신호를 검증된 성장 행동으로<br>
> Turn customer evidence into measurable, human-approved growth actions.

[![CI](https://github.com/kimsanguine/signal-to-growth/actions/workflows/ci.yml/badge.svg)](https://github.com/kimsanguine/signal-to-growth/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-open%20standard-126E5A)](https://agentskills.io/)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-8A5CF5)](https://code.claude.com/docs/en/plugins)
[![OpenAI Codex](https://img.shields.io/badge/OpenAI%20Codex-plugin-111111)](https://github.com/openai/plugins)

Signal to Growth는 고객 인터뷰·CS·행동 지표에서 얻은 신호를 출처와 함께 정리하고, 사람이 성장 판단을 승인한 뒤, 콘텐츠·첫 사용자 루프·측정으로 연결하는 Agent Skills 제품입니다.

하나의 `skills/` 소스를 Claude Code와 OpenAI Codex에서 함께 사용합니다.
[변경 이력](CHANGELOG.md)에서 release 단위의 차이를 확인할 수 있습니다.

## 왜 만들었나

초기 SaaS 팀은 고객 신호가 부족해서만 실패하지 않습니다.

- 인터뷰 원문과 요약이 분리됩니다.
- CS 태그와 실제 고객 맥락이 달라집니다.
- 지표 이름은 있지만 분모·cohort·value event가 없습니다.
- 결정 당시 근거와 실행 후 결과가 연결되지 않습니다.
- AI가 만든 초안과 사람이 승인한 실행의 경계가 흐려집니다.

Signal to Growth는 이 연결을 하나의 artifact lineage로 관리합니다.

```text
quote
  → evidence
  → channel event (when a connector is configured)
  → signal / theme
  → decision
  → action
  → metric
  → outcome
  → learning
```

이 저장소는 “성장 prompt를 많이 제공하는 catalog”가 아닙니다. 증거 계보, 승인 상태, 설정 가능한 지표 정책, 실패 시 중단 조건을 제공하는 작은 운영 체계입니다.

## 핵심 원칙

1. **Evidence before advice** — 권고보다 원문·출처·관찰 시점을 먼저 남깁니다.
2. **AI proposes, human decides** — AI는 추출·분류·초안을 담당하고 중요한 판단과 외부 실행은 사람이 승인합니다.
3. **Policy over universal thresholds** — 인터뷰 수, retention target, 위험 기준을 보편값으로 고정하지 않습니다.
4. **Draft is not execution** — 메시지·콘텐츠 초안과 발송·게시를 분리합니다.
5. **One source, two adapters** — 공통 스킬을 유지하고 플랫폼별 manifest만 분리합니다.
6. **Artifacts connect skills** — 대화 기억보다 JSON·JSONL·Markdown 산출물로 다음 단계를 연결합니다.
7. **Fail loud** — 근거·동의·schema·승인이 부족하면 이유를 남기고 멈춥니다.

## 11개 스킬

| 순서 | 스킬 | 하는 일 | 핵심 산출물 |
|---:|---|---|---|
| 1 | `plan-customer-reach` | 조사 대상·채널·동의·draft-only 접촉 계획 | `reach-plan.json` |
| 2 | `run-switch-interview` | 실제 과거 행동 중심 Switch Interview 설계 | `interview-guide.md` |
| 3 | `synthesize-interviews` | quote·theme·반증을 evidence ID로 연결 | `evidence.jsonl` |
| 4 | `connect-customer-channels` | 한국형 CS event 검증·정규화·중복 제거·상태 대사 | `cs-events.jsonl` |
| 5 | `triage-customer-signals` | CS·review·survey 신호 정규화와 위험 분기 | `signals.jsonl` |
| 6 | `define-growth-metrics` | 분모·cohort·value event가 있는 지표 계약 | `metrics.jsonl` |
| 7 | `record-growth-decision` | 근거·대안·중단 조건·결과의 append-only 기록 | `decisions.jsonl` |
| 8 | `audit-answer-visibility` | SEO·GEO·AEO 표면의 날짜가 있는 관찰 감사 | `visibility-observations.jsonl` |
| 9 | `draft-evidence-content` | claim과 source를 연결한 answer-first 초안 | `claim-ledger.jsonl` |
| 10 | `design-first-user-loop` | capacity·metric·stop condition이 있는 초기 사용자 실험 | `first-user-loop.json` |
| 11 | `run-growth-loop` | artifact 상태와 승인에 따른 다음 스킬 routing | `run-state.json` |

각 스킬은 독립적으로 사용할 수 있습니다. connector를 설정하지 않으면 기존 manual signal flow를 그대로 사용합니다. `run-growth-loop`는 전문 스킬의 판단을 대신하지 않고 상태와 handoff만 관리합니다.

## 설치

### Claude Code

Claude Code 안에서 marketplace를 추가합니다.

```text
/plugin marketplace add kimsanguine/signal-to-growth
/plugin install signal-to-growth@signal-to-growth
/reload-plugins
```

그다음 자연어로 요청하거나 설치된 스킬을 지정합니다.

```text
이 인터뷰 3개를 원문 quote가 보존된 evidence로 합성해줘.
이 고객 신호를 바탕으로 첫 사용자 실험을 설계해줘.
```

### OpenAI Codex

터미널에서 marketplace를 추가합니다.

```bash
codex plugin marketplace add kimsanguine/signal-to-growth
```

Codex에서 `/plugins`를 열고 `signal-to-growth`를 설치한 뒤 새 세션을 시작합니다. 자연어로 요청하거나 `$skill-name`으로 특정 스킬을 선택할 수 있습니다.

```text
$synthesize-interviews 이 인터뷰를 evidence.jsonl로 합성해줘.
$run-growth-loop artifacts/를 검사하고 다음 단계를 알려줘.
```

### 범용 Agent Skills 설치

plugin을 지원하지 않는 환경이나 공통 설치가 필요하면 다음 경로를 사용할 수 있습니다.

```bash
npx skills add kimsanguine/signal-to-growth -a claude-code -a codex
```

플랫폼의 공식 plugin 설치가 1순위이며 범용 installer는 보조 경로입니다.

## 5분 로컬 체험

Python 3.11 이상만 필요합니다. 런타임 외부 dependency는 없습니다.

```bash
git clone https://github.com/kimsanguine/signal-to-growth.git
cd signal-to-growth
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
signal-to-growth demo .
```

예상 결과:

```text
Demo validation passed: repository, contracts, references, and privacy.
```

공개 가능한 합성 인터뷰와 완성된 artifact chain은 `fixtures/public-dummy/`에 있습니다.

```bash
signal-to-growth validate-artifacts \
  fixtures/public-dummy/artifacts \
  --require-complete
```

## CLI

CLI는 AI 판단을 대신하지 않습니다. schema, reference, privacy pattern, 질문 위험, workflow 상태처럼 결정론적으로 확인할 수 있는 부분을 담당합니다.

### 저장소 검사

```bash
signal-to-growth validate-repo .
```

검사 범위:

- 11개 스킬 존재 여부
- portable frontmatter
- skill 이름과 폴더 일치
- `agents/openai.yaml`
- output contract reference
- Claude·Codex manifest
- 남아 있는 placeholder

### artifact 검사

```bash
signal-to-growth validate-artifacts artifacts/
```

`--require-complete`를 사용하면 다음 7개 core artifact를 모두 요구합니다.

- `evidence.jsonl`
- `signals.jsonl`
- `metrics.jsonl`
- `decisions.jsonl`
- `actions.jsonl`
- `outcomes.jsonl`
- `run-state.json`

validator는 ID 형식, 필수 필드, 승인 상태, 외부 실행 승인, evidence→decision→action→metric→outcome 참조를 확인합니다.

Connector를 사용하는 run은 5개 추가 contract를 사용합니다.

- `channel-connection.json`
- `cs-events.jsonl`
- `reply-drafts.jsonl`
- `delivery-events.jsonl`
- `connector-state.json`

```bash
signal-to-growth validate-connectors artifacts/
signal-to-growth normalize-event \
  --provider kakao-openbuilder \
  --request-id request-public-dummy-001 \
  --input fixtures/public-dummy/providers/kakao-openbuilder/skill-request.json
```

`normalize-event`는 로컬 payload만 처리하며 provider network에 연결하거나 답변을 발송하지 않습니다.

### 한국형 CS 지원 수준

| 표면 | 현재 구현 | 아직 검증하지 않은 것 |
|---|---|---|
| Kakao Channel chatbot | Open Builder 요청 정규화·마스킹·중복 제거, Supabase restricted sink, Vercel WSGI endpoint, `version=2.0` 응답 | 배포된 endpoint→Supabase 왕복, 개발 채널 왕복, `X-Request-Id` 반복 발화 특성 |
| Naver TalkTalk | public dummy event 정규화·마스킹·중복 제거 | 실제 test account webhook, backfill, 발송 |
| Channel Talk | webhook 정규화와 injected read-only backfill·대사 | 실제 credential·HTTPS endpoint 왕복 |
| Kakao 상담톡 via Channel Talk | product boundary와 계정 설정 절차 | 실제 채널 이관·상담 event |
| Happytalk | 공식 규격 reference와 public dummy fixture | credential 기반 adapter |
| Kakao 공식 딜러 | accepted/delivered 상태 fixture와 state projection | 선택된 딜러의 simulator·callback·polling |

`fixture-validated`, `test-account verified`, `production-operational`을 서로 다른 상태로 기록합니다.

강의 핵심 E2E는 `Kakao Channel chatbot through Kakao i Open Builder`입니다.
Channel Talk는 Open API key 발급에 유료 plan이 필요한 선택형 connector로
유지하며, 강의 본편에서는 구조와 확장 경로만 소개합니다. Kakao chatbot
skill request는 상담톡이나 native 1:1 상담 이력 API가 아닙니다.

`KakaoSkillApplication`은 정규화 event를 먼저 저장한 뒤 fixed
`version=2.0` 응답을 반환하는 deployment-neutral WSGI application입니다.
`app.py`는 Vercel entry point, `SupabaseEventSink`는 server-only secret을
사용하는 저장 adapter입니다. 저장 실패 시 성공 응답을 반환하지 않습니다.
승인 참조는 canonical 고객 event와 분리된 `approval_ref` 열에 저장합니다.
공개 root route는 secret이나 설정 상태 대신 문서·health route만 반환합니다.

### Kakao test endpoint 배포

Kakao Developers API key는 사용하지 않습니다. Open Builder skill header와
서버가 공유할 임의의 `x-api-key` 하나와 고객 식별자 HMAC용 별도 secret을
생성합니다. 두 값과 Supabase secret key는 repository나 채팅에 입력하지
않고 Vercel Environment Variables에만 저장합니다.

필수 환경 변수 이름은 [`.env.example`](.env.example)에 있습니다.

```text
KAKAO_SKILL_API_KEY
STG_CUSTOMER_HMAC_KEY
STG_APPROVAL_REF
SUPABASE_URL
SUPABASE_SECRET_KEY
```

1. 별도의 Supabase test project에서 `supabase/migrations/`의 migration을
   순서대로 적용합니다.
2. Vercel project에 필수 환경 변수를 server-side secret으로 등록합니다.
3. preview를 배포하고 `GET /api/health`가 `status=configured`인지 확인합니다.
4. 합성 Kakao payload를 `POST /api/kakao/skill`로 보내 `version=2.0`을 확인합니다.
5. Supabase에서 같은 `event_id`가 한 행만 저장됐는지 확인합니다.
6. Kakao Chatbot Admin Center의 skill URL과 test header를 등록한 뒤 개발 채널에서 왕복을 확인합니다.

이 table은 RLS를 활성화하고 `anon`·`authenticated` 권한을 제거합니다.
`sb_secret_...` key는 backend 전용이며 브라우저나 교안에 노출하지 않습니다.
실제 고객 데이터가 아닌 합성 발화만 사용합니다.
`STG_APPROVAL_REF`에는 secret이나 자유 서술 대신 `APR-KAKAO-TEST-001` 같은
비민감 승인 record ID를 사용합니다. 각 행의 `expires_at`은 7일 뒤를
가리키지만 자동 삭제 작업은 아닙니다. 삭제 절차와 승인 경계는
[Kakao test retention runbook](docs/operations/kakao-test-retention.md)을
따릅니다.

### 개인정보 pattern 검사

```bash
signal-to-growth scan-privacy path/to/file.md
```

현재 email, 한국 휴대전화, 국제 전화, 일부 API key, JWT pattern을 찾습니다. 결과는 유형과 줄 번호만 출력하며 발견한 값을 다시 출력하지 않습니다.

이 검사는 완전한 DLP가 아닙니다. 민감 데이터는 입력 전에 승인된 저장·처리 정책을 적용해야 합니다.

### 인터뷰 질문 검사

```bash
signal-to-growth lint-questions interview-guide.md
```

설정된 leading, hypothetical, solution-first, compound question pattern을 찾습니다. 결과는 검토 단서이며 인터뷰 품질의 자동 판정이 아닙니다.

### 다음 단계 확인

```bash
signal-to-growth next-step artifacts/
```

artifact가 준비된 순서를 기준으로 첫 누락 스킬과 완료된 스킬을 JSON으로 반환합니다.

## 실제 사용 예

### 1. 인터뷰 합성

```text
$synthesize-interviews

fixtures/public-dummy/interviews/에 있는 합성 인터뷰를 읽고
quote와 해석을 분리한 evidence.jsonl을 만들어줘.
반증과 distinct participant 수도 별도로 보여줘.
```

완료 전에 확인할 것:

- quote가 원문과 일치하는가;
- file·line locator가 있는가;
- 여러 quote를 여러 사람으로 잘못 계산하지 않았는가;
- strength가 사람 승인 전 `awaiting_human_tag`인가;
- observed와 inferred가 구분되는가.

### 2. 지표 계약

```text
$define-growth-metrics

첫 evidence-backed decision을 activation 후보로 검토해줘.
entity, population, numerator, denominator, cohort maturity,
counter-metric을 포함하고 baseline은 모르면 null로 남겨줘.
```

### 3. 첫 사용자 루프

```text
$design-first-user-loop

승인된 evidence와 metric을 바탕으로 5팀 규모의 첫 사용자 실험을 설계해줘.
메시지는 초안까지만 만들고 실제 발송은 하지 마.
```

## 안전과 승인 경계

기본 정책은 [`policies/default-policy.json`](policies/default-policy.json)에 있습니다.

다음 작업은 어떤 스킬도 자동 승인하지 않습니다.

- email 또는 direct message 발송
- 외부 게시
- 광고비·incentive·환불 등 비용 발생
- 고객 약속
- 데이터 삭제
- 배포
- 계정·billing 변경

외부 실행에는 최소한 다음 항목이 필요합니다.

1. 명시적 사람 승인
2. 구체적인 대상과 owner
3. 검증된 action artifact
4. audit record

보안·데이터 신고는 [SECURITY.md](SECURITY.md)를 확인하세요.

## Artifact contract

Core JSON Schema:

| 객체 | Schema | ID |
|---|---|---|
| Evidence | [`evidence.schema.json`](contracts/evidence.schema.json) | `EV-YYYYMMDD-NNN` |
| Signal | [`signal.schema.json`](contracts/signal.schema.json) | `SIG-YYYYMMDD-NNN` |
| Metric | [`metric.schema.json`](contracts/metric.schema.json) | `MET-YYYYMMDD-NNN` |
| Decision | [`decision.schema.json`](contracts/decision.schema.json) | `DEC-YYYYMMDD-NNN` |
| Action | [`action.schema.json`](contracts/action.schema.json) | `ACT-YYYYMMDD-NNN` |
| Outcome | [`outcome.schema.json`](contracts/outcome.schema.json) | `OUT-YYYYMMDD-NNN` |
| Run state | [`run-state.schema.json`](contracts/run-state.schema.json) | `RUN-YYYYMMDD-NNN` |

Connector JSON Schema:

| 객체 | Schema |
|---|---|
| Channel connection | [`channel-connection.schema.json`](contracts/channel-connection.schema.json) |
| Canonical CS event | [`cs-event.schema.json`](contracts/cs-event.schema.json) |
| Reply draft | [`reply-draft.schema.json`](contracts/reply-draft.schema.json) |
| Delivery event | [`delivery-event.schema.json`](contracts/delivery-event.schema.json) |
| Connector state | [`connector-state.schema.json`](contracts/connector-state.schema.json) |

상세 연결 규칙은 [Artifact contracts](docs/artifact-contracts.md)를 확인하세요.

## Claude Code와 Codex를 함께 지원하는 방식

```text
skills/                         공통 source of truth
├── <skill>/SKILL.md
├── <skill>/references/
└── <skill>/agents/openai.yaml

.claude-plugin/                 Claude Code adapter
.codex-plugin/                  Codex adapter
.agents/plugins/                Codex marketplace
```

- 공통 `SKILL.md`는 [Agent Skills open standard](https://agentskills.io/)를 따릅니다.
- Claude Code는 `.claude-plugin/plugin.json`을 사용합니다.
- Codex는 `.codex-plugin/plugin.json`을 사용합니다.
- 플랫폼별 manifest가 skill 행동을 복제하지 않습니다.
- release metadata를 바꾸면 두 manifest와 두 marketplace를 함께 갱신합니다.

설계 근거는 [Architecture](docs/architecture.md)에 있습니다.

## 저장소 구조

```text
signal-to-growth/
├── .agents/plugins/marketplace.json
├── .claude-plugin/
├── .codex-plugin/
├── app.py
├── contracts/
├── docs/
├── fixtures/
│   ├── negative/
│   └── public-dummy/
├── policies/
├── scripts/
├── skills/
├── supabase/migrations/
├── src/signal_growth/
└── tests/
```

## 개발과 검증

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
make check
```

개별 skill은 공식 `quick_validate.py`로도 검사합니다.

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py \
  skills/synthesize-interviews
```

검증 층위:

1. **Static** — frontmatter, manifest, schema, link
2. **Trigger** — 맞는 요청과 잘못된 요청의 skill 선택
3. **Output** — artifact contract와 claim state
4. **Adversarial** — fabricated quote, PII, unapproved send, invalid reference
5. **Integration** — evidence에서 outcome까지 연결
6. **Cross-runtime** — Claude Code와 Codex의 핵심 artifact 비교

현재 release에서 자동화한 범위와 남은 runtime 검증은 [Verification](docs/verification.md)에 기록합니다.

## 경쟁 제품과 다른 점

범용·도메인 skill 저장소 18개를 비교했습니다. 자세한 조사와 채택·배제 판단은 [Competitive landscape](docs/competitive-landscape.md)에 있습니다.

Signal to Growth가 집중하는 공백:

- 인터뷰 quote에서 outcome까지의 reference integrity
- AI 제안과 사람 승인의 분리
- fixed benchmark 대신 project policy
- 초안과 실제 external write의 분리
- 한 source에서 Claude Code·Codex로 배포
- positive·negative·integration fixture를 함께 제공

## 프로젝트 상태

`v0.2.0`은 한국형 CS connector foundation을 추가한 alpha입니다.

포함:

- 11개 portable skill
- Claude Code·Codex plugin manifest
- 7개 core artifact schema와 5개 connector schema
- 표준 라이브러리만 사용하는 validator CLI
- 합성 한국어 fixture
- unit·integration·negative tests
- Naver TalkTalk event normalization
- Channel Talk read-only adapter contract
- Kakao Open Builder용 Vercel WSGI endpoint와 Supabase restricted sink
- synthetic event approval reference와 7일 deletion-eligibility marker
- provider-neutral dedupe·redaction·delivery state projection

아직 포함하지 않음:

- 실제 Kakao development channel과 배포 endpoint의 왕복 검증
- Happytalk·카카오 공식 딜러의 live adapter
- 자동 발송·게시
- 익명 telemetry
- 보편적인 SaaS benchmark

한국형 CS connector의 설계 근거와 단계별 검증 계획은 [Korean CS integration plan](docs/v2-korean-cs-integration-plan.md)에 기록합니다. 현재 source와 credential 없는 P0 fixture는 구현됐지만, 실제 provider 계정 연결이나 운영 상태를 뜻하지 않습니다.

Channel Talk·Kakao 상담톡·Naver TalkTalk test account를 준비할 때는 [Provider setup checklist](docs/provider-setup-checklist.md)를 따르세요. API secret, 고객 원문, 전화번호는 repository나 AI 대화에 입력하지 마세요.

## 기여

[CONTRIBUTING.md](CONTRIBUTING.md)를 읽고 public dummy fixture와 실패 사례를 함께 제출해 주세요. 실제 고객 데이터는 issue나 pull request에 포함하지 마세요.

## 출처와 감사

패키징과 규격 설계에 다음 공개 프로젝트를 참고했습니다.

- [Agent Skills specification](https://github.com/agentskills/agentskills)
- [Anthropic Skills](https://github.com/anthropics/skills)
- [Claude Code official plugins](https://github.com/anthropics/claude-plugins-official)
- [OpenAI Plugins](https://github.com/openai/plugins)
- [Microsoft Agent Skills](https://github.com/MicrosoftDocs/Agent-Skills)

도메인·평가 참고 자료는 [Competitive landscape](docs/competitive-landscape.md)에 license와 함께 기록합니다. 이 저장소의 구현과 문서는 별도로 작성되었으며 타 저장소의 고유 scoring 공식을 포함하지 않습니다.

## License

[MIT](LICENSE) © 2026 Sanggeun Kim
