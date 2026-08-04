# Signal to Growth v2 — 한국형 CS 연동 고도화 계획

- 작성일: 2026-07-26
- 문서 상태: P0 구현과 hosted synthetic E2E 완료, P1 Kakao 개발 채널 검증 대기
- 현재 제품: `v0.2.0` alpha source, 11개 skill
- 목표 release: `v0.2.0` 공개 및 P1 read-only 왕복 검증
- `v2`의 의미: 스킬 제품 고도화 계획 2차안. Semantic Versioning의 major `2.0.0`을 뜻하지 않음
- 대상 runtime: Claude Code, OpenAI Codex
- 외부 실행: 격리된 Supabase·Vercel Preview 설정과 합성 E2E만 완료. Kakao 개발 채널 연결·메시지 발송·template 변경은 하지 않음

---

## 0. 2026-07-26 실행 경로 변경

사용자가 Kakao Business Channel을 만들었고, Channel Talk 관리자 화면에서
Open API key 발급에 유료 결제가 필요함을 확인했다. 이에 따라 P1 순서를
다음과 같이 변경한다.

```text
핵심 E2E
  Kakao Business Channel
    → Kakao Chatbot Admin Center
    → Open Builder skill request
    → public HTTPS skill server
    → normalize → redact → dedupe
    → fixed version=2.0 response

선택형
  Channel Talk adapter 유지
    → 유료 Open API 사용 조직용
    → 강의에서는 architecture와 확장 방법만 소개
```

이 E2E는 `Kakao Channel chatbot`이다. 상담톡, 알림톡, native Channel
1:1 상담 이력 API로 표현하지 않는다. 공개 HTTPS endpoint와 Supabase
합성 왕복은 검증했고, 실제 개발 채널 연결은 별도 승인·계정 설정 게이트다.

---

## 1. 결론

한국형 CS 연동은 `triage-customer-signals` 안에 공급사 API를 모두 넣지 않는다.

새 전문 skill을 하나 추가한다.

| 항목 | 결정 |
|---|---|
| 공개 slug | `connect-customer-channels` |
| 표시명 | Connect Korean CS Channels |
| 책임 | provider 연결 진단, event 검증·정규화, backfill, 상태 대사, reply draft |
| 비책임 | 고객 문제 분류의 최종 판단, 실제 자동 답변, 마케팅 캠페인 |
| 다음 skill | `triage-customer-signals` |
| 기본 mode | `dry-run`, `read-only`, `draft-only` |
| region profile | `kr` |
| 첫 강의 fixture | Kakao Open Builder skill request + Naver TalkTalk inbound event |
| 첫 실연동 후보 | Kakao Channel chatbot development channel |
| Channel Talk | 유료 Open API 사용 조직용 선택형 adapter, 교안은 소개만 |
| Kakao 발송 실연동 | 알림톡이 필요할 때 계약한 공식 딜러 1곳만 선택 |

`connect-korean-cs`는 직관적이지만 장기적으로 tool·국가를 skill 이름에 고정한다. `connect-customer-channels`를 공개 slug로 쓰고, 설명과 `references/providers-kr.md`에서 한국형 CS를 명확히 드러내는 편이 trigger와 확장성을 함께 확보한다.

기존 제품은 9개 전문 skill과 1개 orchestrator에서, 10개 전문 skill과 1개 orchestrator로 바뀐다.

```text
plan-customer-reach
  → run-switch-interview
  → synthesize-interviews
  → connect-customer-channels
  → triage-customer-signals
  → define-growth-metrics
  → record-growth-decision
  → audit-answer-visibility
  → draft-evidence-content
  → design-first-user-loop
  → run-growth-loop
```

---

## 2. 왜 별도 skill이어야 하는가

### 2.1 연결과 해석은 다른 책임이다

`connect-customer-channels`가 답할 질문:

- 이 payload는 실제 어느 provider·channel·event인가?
- 인증·token·timestamp·replay 검사를 통과했는가?
- 같은 event를 이미 처리했는가?
- 원문을 어디까지 보존할 수 있는가?
- 공통 event schema로 어떻게 바꾸는가?
- webhook 누락을 API backfill이나 polling으로 복구할 수 있는가?
- provider의 `accepted`는 어떤 canonical status인가?

`triage-customer-signals`가 답할 질문:

- 이 대화가 어떤 고객 문제를 보여주는가?
- severity와 risk 후보는 무엇인가?
- 어떤 evidence와 연결되는가?
- 사람이 먼저 검토해야 하는가?
- 어떤 theme과 discovery 질문으로 묶이는가?

두 책임을 하나로 합치면 provider 장애가 고객 문제 분류 실패처럼 보이고, 모델 분류 결과가 실제 channel 상태처럼 기록될 위험이 있다.

### 2.2 Kakao는 하나의 API가 아니다

| 층 | 예 | skill 처리 |
|---|---|---|
| Kakao Developers | 같은 서비스 사용자 간 메시지 API | CS connector 대상에서 제외 |
| Kakao business product | 알림톡·상담톡·브랜드 메시지 | product capability로 표현 |
| 공식 딜러 | NHN Cloud·SOLAPI·Bizppurio 등 | provider adapter |
| 상담 시스템 | Happytalk·자체 상담 UI | helpdesk adapter |
| 고객 event | 문의·답변·상태·전달 결과 | canonical envelope |

공통 `api.kakao.com/bizmessage/send` 같은 endpoint를 만들지 않는다. 실제 계약한 provider의 공식 규격을 adapter로 분리한다.

---

## 3. 구체적인 사용 예

### 3.1 이 skill이 trigger되어야 하는 요청

- “네이버 톡톡 webhook payload를 Signal to Growth event로 정규화해 줘.”
- “채널톡 대화를 read-only로 가져와 중복 없이 `cs-events.jsonl`을 만들어 줘.”
- “해피톡 상담방 event schema와 우리 canonical schema의 차이를 보여 줘.”
- “NHN Cloud 알림톡 요청 접수와 최종 전달 결과를 대사해 줘.”
- “SOLAPI callback을 검증하고 fallback SMS를 별도 attempt로 기록해 줘.”
- “상담톡 reply 초안을 만들되 active session과 사람 승인을 확인해 줘.”
- “이 provider는 webhook 누락 시 backfill이 가능한지 capability report를 만들어 줘.”

### 3.2 이 skill이 trigger되면 안 되는 요청

- “CS 100건에서 핵심 theme을 찾아 줘.” → `triage-customer-signals`
- “이 고객 요청을 roadmap에 넣을지 결정해 줘.” → `record-growth-decision`
- “카카오 광고 캠페인을 발송해 줘.” → 제품 범위 밖
- “고객에게 자동 환불 답변을 보내 줘.” → 기본 정책상 차단
- “Kakao Developers 친구 메시지 API를 주문 알림에 연결해 줘.” → 제품 선택 오류를 설명하고 중단

### 3.3 stop condition

다음이면 partial artifact와 이유를 남기고 중단한다.

- provider와 business product가 구분되지 않음
- webhook 인증 방법을 공식 규격에서 확인하지 못함
- raw payload 보관·삭제 정책이 없음
- 실제 고객 data인데 처리 근거·권한이 불명확함
- PII redaction이 실패함
- event identity가 없어 duplicate를 안전하게 구분할 수 없음
- outbound action인데 human approval ID가 없음
- 상담톡 session이 active인지 확인할 수 없음
- template·sender·message purpose가 확인되지 않음
- provider 접수 여부가 불명확한 timeout 뒤 재발송을 요구함

---

## 4. 국내 CS·메시징 공식 문서 조사

이 표는 사용량 순위가 아니다. 공개 공식 규격의 확인 가능성, 강의 재현성, 안전한 read-only 연결 가능성을 기준으로 한다.

| 도구·상품 | Inbound | Read/backfill | Reply/send | 상태 | 공개 규격 | 권고 |
|---|:---:|:---:|:---:|---|---|---|
| Kakao Channel chatbot / Open Builder | O, synchronous skill request | X | skill response O | 5초 응답, delivery/read 없음 | Kakao 공식 가이드 | 핵심 P1 E2E |
| Naver TalkTalk Chat Bot API | O | event 이후 자체 저장, 공개 backfill 미확인 | O | API 처리 성공, delivery/read 미확인 | 공식 GitHub | P0 강의 fixture, P1 event-only |
| Channel Talk | O | UserChat·message read 가능 | O | chat state, 최종 delivery semantics 일부 미확인 | 높음, Open API key는 유료 plan 전제 | 선택형 read-only connector, 강의 소개 |
| Happytalk | O | 상담방·message·상태 조회 가능 | O | room·read date, delivery 일부 미확인 | 높음, credential 협의형 | P1 조건부 |
| Kakao 상담톡 | O | 딜러·상담 시스템별 | session 내 O | 딜러별 | 제품 가이드 공개 | Kakao inbound P1, 계약 필요 |
| Kakao 알림톡 | X | 결과 조회 | O | 접수와 최종 결과 분리 | 제품 가이드 + 딜러 API | outbound P1 |
| Kakao 브랜드 메시지 | X | 결과 조회 | O | 공급사별 | 제품 가이드 + 딜러 API | P2, marketing 기본 비활성 |
| NHN Cloud | X | polling | O | idempotency key·message results | 높음 | Kakao adapter 후보 |
| SOLAPI | X | message/group 조회 | O | webhook·polling | 높음 | Kakao·Naver adapter 후보 |
| Bizppurio | X | webhook·polling·report recovery | O | 접수·최종 결과 분리 | 높음, simulator | Kakao provider adapter 후보 |

### 4.1 Kakao product boundary

확인한 사실:

- Kakao Chatbot Admin Center는 Kakao Channel에 bot을 연결하고 public skill server와 `HTTP POST` JSON으로 통신한다.
- skill server는 5초 안에 `version=2.0` JSON을 반환해야 하며 요청에는 `X-Request-Id`가 전달된다.
- Kakao Developers 메시지 API는 같은 서비스 사용자 간 상호작용용이다.
- 주문·결제·배송과 같은 정보성 안내는 알림톡 상품을 선택한다.
- 알림톡과 브랜드 메시지는 공식 딜러를 통해 제공된다.
- 상담톡은 이용자가 먼저 상담을 시작하며, 카카오는 상담원용 시스템 자체를 제공하지 않는다.
- 상담톡 정식 전환 시 기존 채널 관리자 웹·앱의 채팅 메뉴와 이력 접근에 영향이 있으므로 migration 계획이 필요하다.
- 요청 접수와 고객 단말 전달은 다른 상태다.

설계 영향:

- `kakao_user_message`와 `kakao_bizmessage`를 다른 provider family로 둔다.
- `kakao_openbuilder`와 `kakao_channel_chatbot`을 ConsultTalk와 분리한다.
- `product=alimtalk|consulttalk|brand_message`를 명시한다.
- `provider`는 계약한 딜러 ID다.
- `sender_profile`, `template`, `message_purpose`, `recipient_basis`를 발송 전 검사한다.
- 상담톡은 `session_state=active`가 아니면 reply를 만들더라도 전송하지 않는다.

### 4.2 Naver TalkTalk

공식 `navertalk/chatbot-api`에서 확인한 범위:

- `open`, `send`, `echo`, `leave`, `friend`, `action` 등의 webhook event
- 로컬 `curl`을 이용한 webhook 입력 시험
- partner center에서 발급한 `Authorization`을 사용하는 Send API
- 5초 안에 동기 응답하거나 먼저 `200 OK` 후 Send API를 쓰는 비동기 방식
- 상담원 handover BETA와 `standby` 상태

확인하지 못한 범위:

- 과거 conversation backfill API
- message별 최종 delivery/read receipt
- webhook payload-bound signature
- 안정된 상담원·tag 관리 API

따라서 첫 구현은 event-only다. reply/send와 handover는 별도 write adapter로 미룬다.

### 4.3 Channel Talk

확인한 범위:

- Open API와 webhook
- message 생성 event
- UserChat 목록·단건·message 조회
- bot message 발송과 manager·tag 관련 API
- legacy webhook의 URL query token
- App Function 요청의 `X-Signature` HMAC

중요한 경계:

- legacy webhook과 App Function은 인증 방식이 다르다.
- “Channel Talk webhook은 HMAC”이라고 일반화하지 않는다.
- 유료 Open API가 이미 있는 조직만 webhook ingest와 REST backfill을 검증한다.
- 강의 본편에서는 architecture와 capability 차이만 소개한다.
- reply/send·assignee·tag mutation은 사람 승인 기반 P2다.

### 4.4 Happytalk

확인한 범위:

- 카카오톡·네이버 톡톡·웹채팅 통합
- 신규 상담방, 상태, 상담사, 분류, flag, tag 변경 webhook
- 상담방·message 조회
- message send와 상담원 배정 API
- 개발·테스트 endpoint
- Embedded webhook의 signature

주의:

- credential은 사용 목적과 조건 협의 후 발급된다.
- Biz message 수신 문서와 Embedded webhook의 인증 계약이 같다고 가정하지 않는다.
- 2026년 template V2 전환과 같은 schema drift를 provider version에 기록한다.

### 4.5 Kakao 공식 딜러 후보

#### NHN Cloud

- 알림톡 발송과 `message-results` polling
- raw-message API의 `X-NC-API-IDEMPOTENCY-KEY`
- template 상태와 sender key
- 대체 발송 설정

제약:

- native idempotency의 시간 범위만 믿지 않고 application idempotency를 둔다.
- 검토한 문서 범위에서 결과 webhook signature를 확인하지 못했으므로 polling을 1급 recovery 경로로 둔다.

#### SOLAPI

- HMAC-SHA256 API 인증
- 알림톡·브랜드 메시지·네이버 스마트 알림 등 통합 발송
- message/group 조회와 webhook
- webhook test API
- 현재 문서의 친구톡 종료·브랜드 메시지 전환 안내

제약:

- API authentication replay protection과 message idempotency는 다른 문제다.
- webhook secret 검증 수준을 별도 assurance로 기록한다.
- 카카오 실패 뒤 SMS/LMS fallback을 별도 attempt로 저장한다.

#### Bizppurio

- 운영·검수 환경 분리
- 단일 `/v3/message`와 알림톡·브랜드 메시지·Naver TalkTalk
- Bearer token, IP allowlist
- webhook, polling, report recovery
- simulator

제약:

- `code=1000`은 접수다.
- `refkey`는 중복 방지 key가 아니다.
- 같은 result가 반복될 수 있으므로 inbox idempotency가 필요하다.
- callback assurance가 낮다면 polling reconciliation을 함께 사용한다.

### 4.6 source drift 처리

`친구톡`, `브랜드 메시지`, template·targeting 규칙은 시점과 공급사에 따라 다르게 보일 수 있다.

provider reference에는 다음 header를 둔다.

```yaml
provider:
product:
document_url:
checked_at:
api_version:
contract_version:
known_drift:
live_account_verified: false
```

공식 문서가 충돌하면 더 강한 권한·동의·승인 gate를 적용하고, 계약한 provider에 확인하기 전까지 `[HOLD]`로 남긴다.

---

## 5. target architecture

### 5.1 저장소 구조

```text
signal-to-growth/
├── skills/
│   ├── connect-customer-channels/
│   │   ├── SKILL.md
│   │   ├── agents/openai.yaml
│   │   └── references/
│   │       ├── output-contract.md
│   │       ├── providers-kr.md
│   │       ├── approval-boundaries.md
│   │       └── recovery-patterns.md
│   └── triage-customer-signals/
├── contracts/
│   ├── cs-event.schema.json
│   ├── channel-connection.schema.json
│   ├── reply-draft.schema.json
│   ├── delivery-event.schema.json
│   └── connector-state.schema.json
├── policies/
│   ├── default-policy.json
│   └── providers-kr.example.json
├── fixtures/
│   ├── public-dummy/providers/
│   │   ├── naver-talktalk/
│   │   ├── channel-talk/
│   │   ├── happytalk/
│   │   ├── kakao-nhn/
│   │   ├── solapi/
│   │   └── bizppurio/
│   └── negative/providers/
├── src/signal_growth/
│   ├── channel_contracts.py
│   ├── connector_validation.py
│   ├── connector_state.py
│   └── adapters/
│       ├── base.py
│       ├── naver_talktalk.py
│       ├── channel_talk.py
│       ├── happytalk.py
│       ├── nhn_cloud.py
│       ├── solapi.py
│       └── bizppurio.py
└── tests/
    ├── test_channel_contracts.py
    ├── test_connector_security.py
    ├── test_connector_recovery.py
    └── test_connector_workflow.py
```

초기 release에 모든 adapter 파일을 만들지 않는다. 실제 P0 구현은 base,
Naver event fixture, Channel Talk read-only, Kakao Open Builder skill request
adapter까지다. Kakao 발송 공급사 adapter는 선택된 하나만 구현하고 나머지는
capability reference와 fixture로 남긴다.

### 5.2 progressive disclosure

`SKILL.md`는 500줄 미만으로 유지하고 다음 핵심 절차만 둔다.

1. provider·product 식별
2. capability 확인
3. credential 없는 dry-run 또는 승인된 connection 선택
4. verify → normalize → redact → dedupe
5. backfill/reconcile 가능 여부 확인
6. draft-only output
7. `triage-customer-signals` handoff
8. stop condition

공급사별 API 세부사항은 `references/providers-kr.md`로 분리한다. 복잡한 payload 변환과 검증은 deterministic script·library로 구현한다.

### 5.3 model·code·human 책임

| 책임 | 모델 | 결정론 코드 | 사람 |
|---|:---:|:---:|:---:|
| provider 후보 설명 | O | capability lookup | 계약 provider 확인 |
| raw request 인증 | X | O | secret rotation |
| payload normalization | 보조 | O | mapping 승인 |
| PII masking | X | O | 정책·예외 승인 |
| summary·category draft | O | schema만 | high-risk 검토 |
| retry·state transition | X | O | policy 승인 |
| reply 초안 | O | 금지어·필드 검사 | 최종 문구 승인 |
| 실제 send/reply | X | approval gate | 명시 승인·실행 |
| 광고성 여부 | 후보만 | deterministic rule 보조 | 최종 판단 |
| provider 변경 | X | migration check | 명시 승인 |

---

## 6. 공통 artifact contract

### 6.1 `channel-connection.json`

실제 credential 값이 아니라 secret reference만 저장한다.

```json
{
  "connection_id": "CONN-20260726-001",
  "provider": "channel_talk",
  "region": "kr",
  "environment": "test",
  "mode": "read_only",
  "credential_ref": "secret://channel-talk/test",
  "capabilities": [
    "webhook_ingest",
    "conversation_backfill"
  ],
  "retention_policy_ref": "POL-RET-001",
  "approved_by": "connection-owner",
  "verified_at": null
}
```

### 6.2 `cs-events.jsonl`

필수 field:

```text
event_id
provider
provider_event_id
channel
direction
event_type
occurred_at
received_at
conversation_ref
message_ref
customer_ref_hmac
content_redacted
attachment_metadata
raw_payload_ref
privacy
consent_or_processing_basis_ref
idempotency_key
auth_verified
verification_assurance
provider_status
canonical_status
source_evidence_ids
```

규칙:

- `event_id`는 provider identity와 stable event field에서 결정론적으로 생성한다.
- 전화번호·email·실명은 저장하지 않는다.
- raw payload는 암호화된 제한 저장소 pointer만 둔다.
- provider가 delivery semantics를 정의하지 않으면 `unknown`이다.
- 수신 event와 발송 결과 event를 같은 type으로 합치지 않는다.

### 6.3 `reply-drafts.jsonl`

```text
draft_id
source_event_ids
conversation_ref
provider
product
session_state
content
template_ref
template_variables
risk_class
status
approval_id
expires_at
external_write
```

기본값:

```json
{
  "status": "draft",
  "approval_id": null,
  "external_write": false
}
```

### 6.4 `delivery-events.jsonl`

canonical status:

```text
draft
validated
approved
submitted
accepted
queued
sent
delivered
read
failed
cancelled
expired
unknown
```

금지:

- `submitted` 또는 `accepted`를 `delivered`로 바꾸기
- SMS fallback 성공으로 Kakao attempt를 성공 처리
- 늦게 도착한 오래된 event로 terminal state를 회귀
- 상태가 불명확한 timeout 뒤 blind resend

### 6.5 `connector-state.json`

```text
connection_id
provider
mode
cursor
last_webhook_at
last_backfill_at
last_reconciled_at
ingested_count
duplicate_count
dead_letter_count
blocked_reasons
health
verification_level
```

---

## 7. Adapter contract

### 7.1 공통 interface

```python
class ChannelAdapter(Protocol):
    def capabilities(self, context): ...
    def verify_event(self, raw_body, headers, received_at): ...
    def normalize_event(self, verified_event): ...
    def backfill(self, cursor): ...
    def healthcheck(self): ...
    def create_reply_draft(self, event, policy): ...
    def send_approved(self, draft, approval): ...
    def fetch_status(self, provider_message_id): ...
    def reconcile(self, checkpoint): ...
```

구현 규칙:

- `send_approved`는 read-only adapter에 존재하더라도 기본적으로 차단한다.
- provider가 backfill을 지원하지 않으면 명시적 `unsupported`를 반환한다.
- capability가 없다는 사실을 빈 list나 성공 상태로 숨기지 않는다.
- raw body 상태에서 provider 규격에 맞는 검증을 한 뒤 JSON을 해석한다.
- callback은 durable inbox 저장 후 빠르게 응답하고, 후속 모델 처리는 비동기로 분리한다.

### 7.2 provider verification assurance

| 등급 | 예 | 내부 보완 |
|---|---|---|
| strong | timestamp + raw body HMAC + unique invocation ID | 기본 dedupe·freshness |
| medium | raw body HMAC, timestamp 없음 | event ID dedupe·freshness window |
| weak | static token/hash, URL token, IP allowlist | secret path·network control·poll reconciliation |
| none | 검증 근거 미확인 | production ingest 차단 |

공급사 이름만으로 assurance를 고정하지 않는다. 동일 공급사에서도 webhook, App Function, polling API의 인증 규격이 다를 수 있다.

### 7.3 inbox·outbox·reconciliation

```text
Inbound:
raw request
  → verify
  → inbox unique write
  → immediate provider response
  → normalize
  → redact
  → cs-event
  → triage

Outbound:
approved action
  → transactional outbox
  → provider validate
  → send
  → accepted receipt
  → callback/poll
  → delivery event
  → outcome
```

webhook과 polling을 경쟁 구현으로 보지 않는다. callback 누락·차단·provider 장애를 복구하기 위한 reconciliation pair로 설계한다.

---

## 8. Approval·privacy·retention

### 8.1 기본 정책

다음은 human approval 전 실행하지 않는다.

- reply/send
- Kakao 알림톡·상담톡·브랜드 메시지 발송
- Naver TalkTalk Send API
- 상담원 배정·tag mutation
- template 등록·수정·삭제
- sender profile 변경
- SMS/LMS fallback 활성화
- 대량 대상 확대
- 광고성 분류
- 환불·삭제·계정·billing 변경

### 8.2 최소화

- 모델에는 redacted content만 전달한다.
- customer identifier는 tenant별 HMAC reference로 바꾼다.
- provider credential과 customer data는 별도 저장소를 사용한다.
- 일반 log에는 content, 전화번호, email, token, callback secret을 남기지 않는다.
- attachment는 MIME·size·hash·restricted pointer만 저장한다.
- raw payload retention은 provider·법적·업무 목적에 맞춘 policy reference로 관리한다.

### 8.3 high-risk

다음 category는 reply draft가 생성돼도 자동 전송하지 않는다.

- safety
- legal
- privacy
- security incident
- billing·refund
- account access
- data deletion
- threat·harassment
- vulnerable person
- 계약·가격 약속

---

## 9. 병렬 작업계획

> **순서의 출처는 이 문서가 아니다.** 남은 작업의 단일 순서 백로그는
> [`HANDOFF.md`](HANDOFF.md) "Resume sequence"에 있다. 아래 Gate 0~7은 v0.2.0
> connector 작업의 **설계 상세와 통과 조건**만 보존한다. Gate 0~3과 Gate 7은
> 이미 반영됐고(현재 11개 skill, version `0.4.0`), Gate 4~6의 실제 provider
> 검증은 `HANDOFF.md` 7단계에 남아 있다. 진행 상태를 판단할 때는 이 절이 아니라
> `HANDOFF.md`를 읽는다.

각 track은 독립적으로 진행하되 Gate에서 합친다.

| Track | 책임 | 주요 산출물 | 선행조건 |
|---|---|---|---|
| A. Contract | schema·state·policy | 5개 schema, provider policy | 없음 |
| B. Provider research | 공식 규격·capability·drift | `providers-kr.md`, source registry | 없음 |
| C. Skill UX | SKILL.md·output contract·UI metadata | 새 skill folder | A의 field draft |
| D. Deterministic core | verify·normalize·dedupe·state | Python modules·CLI | A schema |
| E. Fixture·eval | positive·negative·replay·recovery | public dummy·tests | A schema, B mapping |
| F. Runtime·course | Claude/Codex smoke·Part 6 demo | runtime evidence, teaching pack | C·D·E |

### Gate 0. 제품 범위 동결

- 공개 slug `connect-customer-channels`
- 11개 skill 체계
- default read-only·draft-only
- 강의 P0는 Kakao Open Builder와 Naver event fixture
- 첫 real connector는 Kakao Channel chatbot development channel
- Channel Talk는 유료 Open API 사용자용 선택형
- Kakao 발송 adapter는 계약 공급사 1개만

**통과 조건:** README·plan·manifest 변경 범위가 한 표에 합의된다.

### Gate 1. Contract foundation

Track A·B를 병렬 진행한다.

- `cs-event`
- `channel-connection`
- `reply-draft`
- `delivery-event`
- `connector-state`
- provider capability registry
- verification assurance
- status transition table

**통과 조건:**

- 동일 event 재처리 시 같은 `event_id`
- `accepted ≠ delivered`
- fallback이 별도 attempt
- secret·PII field가 schema에 직접 존재하지 않음
- unsupported capability가 명시적으로 표현됨

### Gate 2. Skill과 deterministic core

Track C·D를 병렬 진행한다.

- skill scaffold는 `skill-creator`의 `init_skill.py` 사용
- `SKILL.md` 500줄 미만
- `agents/openai.yaml` 생성·검증
- repository validator의 expected skill 갱신
- provider-neutral normalization
- inbox dedupe
- state projection
- CLI `validate-connectors`

**통과 조건:**

- `quick_validate.py` 통과
- 기존 10개 skill의 behavior 변경 없음
- 외부 network 없이 모든 core test 실행
- unapproved send 성공률 0

### Gate 3. P0 fixture와 강의 vertical slice

Track E·F를 병렬 진행한다.

- Naver `send` event
- Kakao Open Builder skill request와 `version=2.0` response
- duplicate event
- high-risk billing event
- Channel Talk message event
- Kakao provider accepted·failed result
- malformed·PII·auth failure fixture

**통과 조건:**

- 4분 실습에서 normalize→dedupe→risk queue→draft-only 완료
- 실제 credential 없이 실행
- 두 runtime이 같은 core artifact를 생성
- provider field 차이를 없애지 않고 canonical field로 설명

### Gate 4. Kakao Channel chatbot E2E

- Chatbot Admin Center bot
- Kakao development channel
- public HTTPS skill endpoint
- `x-api-key` test header
- `X-Request-Id` identity
- fixed safe acknowledgement
- canonical event persistence

2026-07-26 진행 상태:

- 인프라 sub-gate 완료: public Preview, test header 인증, fixed
  `version=2.0` 응답, Supabase persistence, 동일 request ID idempotency
- provider sub-gate 대기: Chatbot Admin Center bot, 개발 채널 연결,
  실제 반복 발화에서 Kakao가 발급한 서로 다른 `X-Request-Id`

**통과 조건:**

- 개발 채널의 synthetic test message가 skill endpoint에 도착함
- 5초 안에 `version=2.0` 응답이 돌아옴
- 동일 발화 2회가 서로 다른 provider request identity로 기록됨
- user identifier·발화 원문·secret이 일반 log에 없음
- ConsultTalk·AlimTalk·외부 Send API 호출 없음

### Gate 5. Channel Talk 선택형 read-only

- 이미 유료 Open API plan이 있는 test channel
- webhook ingest
- UserChat/message backfill
- duplicate reconciliation
- connection health

**통과 조건:**

- 실제 test message 1건이 webhook과 backfill에서 하나의 canonical event로 합쳐짐
- customer content가 일반 log에 없음
- reply/send API 호출 없음

강의 본편 완료 조건에는 포함하지 않는다.

### Gate 6. Kakao 발송 provider 1곳과 기타 operational expansion

선택 조건:

- 사용자가 실제 계약한 provider
- test/simulator 제공
- template·sender·status 공식 문서
- callback 또는 polling recovery
- secret rotation·IP 정책

구현 후보 우선순위:

1. 기존 계약 provider
2. Bizppurio simulator
3. SOLAPI webhook test·sandbox
4. NHN Cloud polling

이 순서는 제품 우열이 아니라 검증 가능성 기준이다.

**통과 조건:**

- template·sender·purpose validation
- preview/dry-run
- approval artifact
- test recipient 또는 simulator
- accepted와 terminal status 대사
- duplicate timeout 재발송 없음
- fallback 기본 OFF

- Happytalk credential·patch environment가 확보되면 read-only 구현
- Naver event-only 실제 test account 왕복
- backfill이 없는 Naver는 durable event log와 missing-window 표시
- reply/send·handover·assignment는 별도 승인형 P2

**통과 조건:** 각 connector가 지원하지 않는 capability를 UI와 artifact에 명확히 표시한다.

### Gate 7. Orchestrator·release

- `run-growth-loop`에 connector artifact readiness 추가
- connector가 없어도 기존 manual signal flow를 유지
- Claude·Codex manifest skill count 갱신
- README·architecture·verification 갱신
- version `0.2.0`

**통과 조건:** orchestrator가 provider API를 직접 호출하거나 triage 판단을 재구현하지 않는다.

---

## 10. 테스트 계획

### 10.1 static

- 11개 skill 존재
- frontmatter에 `name`, `description`만 존재
- `SKILL.md` 500줄 미만
- output contract와 UI metadata 존재
- JSON Schema 2020-12 유효
- Claude·Codex manifest 일치
- provider source URL·checked_at·version 존재

### 10.2 deterministic

| # | 실패 주입 | 기대 결과 |
|---:|---|---|
| 1 | malformed JSON | dead-letter, retry eligibility 기록 |
| 2 | PII가 있는 content | redacted event만 생성, privacy scan 통과 |
| 3 | 동일 event 2회 | canonical event 1개 |
| 4 | event ID가 없고 stable field도 없음 | 중단, 추정 ID 생성 금지 |
| 5 | invalid token/signature | inbox·state 변경 없음 |
| 6 | replay·오래된 event | freshness policy와 duplicate 기록 |
| 7 | out-of-order status | event log 보존, current state 회귀 금지 |
| 8 | provider timeout after accept | blind resend 금지, reconcile |
| 9 | 429/5xx | policy 기반 backoff, 중복 side effect 없음 |
| 10 | callback 누락 | API backfill/poll 또는 explicit unsupported |
| 11 | accepted response | delivered로 승격하지 않음 |
| 12 | fallback SMS success | Kakao attempt 실패와 SMS attempt 성공 분리 |
| 13 | 미승인 template·변수 | send 차단 |
| 14 | inactive 상담톡 session | reply send 차단 |
| 15 | human approval 없음 | external write 0 |
| 16 | private URL·token이 log에 포함 | test 실패 |
| 17 | provider capability 없음 | `unsupported`, 성공으로 처리하지 않음 |
| 18 | model이 high-risk를 low로 분류 | deterministic rule로 human queue |

### 10.3 integration

- Naver webhook fixture → `cs-event` → `signal`
- Channel Talk webhook + backfill → one event
- Kakao accepted + delivery callback/poll → delivery state
- high-risk message → reply draft + risk queue, no action
- signal → metric → decision reference integrity
- connector unavailable → manual import fallback

### 10.4 cross-runtime

같은 fixture로 다음을 비교한다.

- 선택된 skill
- `event_id`
- privacy classification
- risk route
- approval status
- output schema
- blocked reason

자연어 요약 문장은 달라도 된다. core field와 external write 상태는 같아야 한다.

### 10.5 live verification

| 단계 | 증거 |
|---|---|
| runtime discovered | Claude Code·Codex가 skill을 목록에 표시 |
| provider test connected | 승인된 test account healthcheck |
| inbound verified | test conversation 1건의 provider event와 canonical event |
| backfill verified | webhook 누락 뒤 복구 |
| draft verified | reply draft, 실제 send 없음 |
| outbound sandbox verified | 별도 승인 뒤 simulator/test recipient 결과 |
| operational | 실제 승인 workflow, 고객 data policy, audit 완료 |

한 단계의 증거로 다음 단계를 주장하지 않는다.

---

## 11. CLI와 validator 변경

P0에서 구현한 명령:

```bash
signal-to-growth validate-connectors connectors/
signal-to-growth normalize-event \
  --provider naver-talktalk \
  --input fixtures/public-dummy/providers/naver-talktalk/send-event.json
signal-to-growth validate-artifacts artifacts/
```

delivery state projection과 webhook/backfill dedupe는 Python core와 test에서
검증한다. Kakao Open Builder fixture는 `normalize-event --provider
kakao-openbuilder --request-id ...`로 실행한다. 실제 provider를 호출하는
`reconcile` CLI는 credential·durable inbox·approved test endpoint가 없는
P0에서는 노출하지 않는다. Channel Talk network command는 유료 Open API
test connection이 있는 경우에만 선택형으로 추가한다.

validator가 검사하는 것:

- provider capability
- connection mode
- secret reference format
- event identity
- raw payload pointer
- privacy
- allowed status transition
- approval ID
- fallback attempt
- connector→signal reference

CLI는 network connection을 직접 생성하지 않는다. provider API를 호출하는 command는 별도 adapter와 explicit environment·approval이 필요하다.

---

## 12. Claude Code·Codex 공용성

공통 source:

```text
skills/connect-customer-channels/
contracts/
src/signal_growth/
fixtures/
```

platform adapter:

```text
.claude-plugin/plugin.json
.claude-plugin/marketplace.json
.codex-plugin/plugin.json
.agents/plugins/marketplace.json
skills/connect-customer-channels/agents/openai.yaml
```

원칙:

- `SKILL.md`에서 Claude Code·Codex 전용 tool name을 요구하지 않는다.
- shell·filesystem·network capability가 없으면 dry-run artifact만 만든다.
- credential은 runtime 환경 변수 이름을 공통 문서에 고정하지 않고 provider config에서 secret reference로 받는다.
- external action 전에는 runtime과 관계없이 동일한 approval artifact가 필요하다.
- release metadata를 바꾸면 두 manifest와 두 marketplace를 함께 갱신한다.

---

## 13. Part 6 교안과 연결

| 교안 | 제품 개발 evidence |
|---|---|
| C01-02 | quote locator와 evidence contract |
| C02-01 | manual signal taxonomy와 high-risk |
| C02-02 | Kakao Open Builder request fixture, safe response, connector state |
| C03-01 | connector coverage·false negative·counter-metric |
| C03-02 | provider 선택 decision과 outcome backfill |
| C05-02 | connector가 있어도 human-approved growth action만 실행 |

강의 본편 실습은 repository의 synthetic Kakao Open Builder fixture를
사용한다. 강사 화면에서는 승인된 개발 채널 E2E를 짧게 시연한다.

강의 구성:

1. 본편 실습: Kakao request fixture → normalize → redact → dedupe → fixed response
2. 강사 E2E: Kakao development channel → public skill endpoint → KakaoTalk response
3. 소개만: Channel Talk paid Open API, webhook/backfill architecture
4. 선택형 부록: Naver TalkTalk event, Kakao dealer status simulator

수강생 필수 실습에는 account·business registration·template approval·API key가 없어야 한다.

---

## 14. README·release 변경 계획

`v0.2.0` 구현으로 README에서 변경한 항목:

- “10개 스킬” → “11개 스킬”
- `connect-customer-channels` 행 추가
- artifact chain에 channel event 추가
- “CRM·helpdesk connector 미포함” 상태 문구 갱신
- connector support matrix 링크
- dry-run/read-only/draft-only 원칙
- provider integration과 operational 상태 구분
- runtime 설치 후 connector credential이 자동으로 생기지 않는다는 안내

release에서 하지 않을 것:

- “모든 한국 CS 도구 지원” 주장
- 실제 고객 data fixture
- 기본 자동 답변
- 기본 SMS fallback
- provider credential 예시 값
- 공급사별 계약·법률 판단 자동화

---

## 15. 완료 기준

> 이 절은 v0.2.0 connector 범위의 **완료 정의**다. 아직 남은 항목의 실행 순서는
> [`HANDOFF.md`](HANDOFF.md) "Resume sequence"가 단일 출처이며, release 판정
> 기준 자체는 [`skill-evaluation-plan.md`](skill-evaluation-plan.md) §7에 있다.

### v0.2.0 release minimum

- `connect-customer-channels` skill 구현
- 11개 skill validator·manifest 일치
- 5개 connector artifact schema
- Naver·Channel Talk·Happytalk·Kakao provider public dummy fixture
- Naver event-only normalization
- Channel Talk read-only webhook+backfill
- Kakao Open Builder skill-request normalization과 `version=2.0` response
- Vercel Preview→Supabase hosted synthetic E2E와 live idempotency
- provider-neutral dedupe·privacy·state projection
- unapproved send 0
- Claude Code·Codex same-artifact smoke
- course 4-minute vertical slice
- README·architecture·verification 갱신

### 조건부

- Kakao Channel development-channel live E2E
- Kakao provider 1곳의 simulator/test connection
- Happytalk patch environment
- Naver actual test account event

### v0.2.0에서 제외

- production 자동 reply
- marketing send
- 모든 딜러 동시 지원
- customer assignment·tag mutation
- refund·delete·account action
- production hosted webhook service
- anonymous telemetry

---

## 16. 현재 검증 상태

### P0 source·fixture·hosted synthetic E2E 확인 완료

- 현재 저장소가 11개 skill과 공통 contract 구조를 사용함
- `triage-customer-signals`의 provider-neutral 책임
- Kakao Developers와 Kakao business product의 차이
- Kakao Open Builder chatbot과 ConsultTalk·native 1:1 chat의 차이
- 알림톡·상담톡·브랜드 메시지의 공식 dealer 구조
- Naver TalkTalk 공식 Chat Bot API의 webhook·Send·handover 문서
- Channel Talk Open API·webhook·backfill 관련 문서
- Happytalk webhook·conversation·assignment 관련 문서
- NHN Cloud·SOLAPI·Bizppurio의 발송·상태·recovery 규격
- 5개 connector schema와 한국 provider capability policy
- Naver event-only deterministic normalization과 duplicate 제거
- Channel Talk webhook/backfill canonical identity 통합
- PII redaction, credential-reference boundary, delivery state non-regression
- connector artifact validator와 credential 없는 public dummy vertical slice
- Vercel WSGI entry point와 fail-closed configuration health endpoint
- Supabase restricted test table migration과 idempotent REST sink
- 격리된 Supabase Pro project의 RLS·browser-role deny·server-only grant
- Vercel feature-branch Preview의 암호화 환경변수와 `READY` 배포
- 잘못된 test header의 HTTP 401과 정상 합성 요청의 HTTP 200
- 동일 request ID 2회 전송 후 Supabase 1행 저장
- Supabase Security Advisor finding 0
- remote commit `903f571`의 Python 3.11·3.12·Vercel check 통과

### P1 이후 확인할 것

- 사용자의 실제 계약 provider
- 실제 Kakao development channel 연결과 skill endpoint 왕복
- 실제 반복 발화에서 Kakao가 생성한 `X-Request-Id` 특성
- Kakao 발송을 선택할 경우 template·sender 상태
- provider credential·test tenant
- live callback signature·IP·retry 동작
- production retention·위수탁 계약
- Claude Code·Codex runtime discovery
- 실제 test message의 webhook·backfill round trip
- hosted restricted inbox와 운영 webhook endpoint
- 실제 외부 발송

P0와 hosted synthetic E2E 완료는 실제 Kakao provider 계정 연결이나
Production 운영 상태를 뜻하지 않는다. 위 미확인 항목을 확인하기 전에는
connector가 “Kakao 개발 채널에 연동됐다”거나 “운영된다”고 보고하지 않는다.

전체 11개 skill의 사용자 task success, cross-runtime parity, evidence
fidelity, safety를 확인하는 5-agent 평가는
[skill evaluation plan](skill-evaluation-plan.md)에 분리했다. 현재는
평가 설계만 완료했으며 evaluator 실행과 점수 산출은 시작하지 않았다.

---

## 17. 공식 source registry

### Kakao

- [챗봇 관리자센터 개요](https://kakaobusiness.gitbook.io/main/tool/chatbot/start/overview)
- [봇 설정과 개발 채널](https://kakaobusiness.gitbook.io/main/tool/chatbot/main_notions/bot_setting)
- [Open Builder 스킬 만들기](https://kakaobusiness.gitbook.io/main/tool/chatbot/skill_guide/make_skill)
- [SkillPayload와 응답 JSON](https://kakaobusiness.gitbook.io/main/tool/chatbot/skill_guide/answer_json_format)
- [Request payload와 X-Request-Id](https://kakaobusiness.gitbook.io/main/tool/chatbot/main_notions/setting_parameter)
- [Kakao Developers 메시지 API](https://developers.kakao.com/docs/ko/kakaotalk-message/common)
- [Kakao Developers 제품 선택 FAQ](https://developers.kakao.com/docs/ko/kakaotalk-message/faq)
- [카카오 알림톡](https://business.kakao.com/info/infotalk/)
- [카카오 상담톡](https://kakaobusiness.gitbook.io/main/ad/cstalk)
- [카카오 브랜드 메시지](https://business.kakao.com/info/brandmessage/)
- [카카오 알림톡 심사 가이드](https://kakaobusiness.gitbook.io/main/ad/infotalk/audit)

### 한국 CS

- [Naver TalkTalk Chat Bot API](https://github.com/navertalk/chatbot-api)
- [Naver TalkTalk Handover API](https://github.com/navertalk/chatbot-api/blob/master/handover_v1.md)
- [Channel Talk Open API](https://developers.channel.io/en/articles/What-is-Open-API-c8c76fba)
- [Channel Talk Webhook](https://developers.channel.io/en/articles/Getting-started-f2a30b58)
- [Channel Talk Webhook Events](https://developers.channel.io/en/articles/Webhook-events-7bd9b8e2)
- [Channel Talk App Function](https://developers.channel.io/en/articles/77250b17)
- [Happytalk Embedded Webhook](https://developer-center.happytalk.io/open_api/embedded_happytalk/webhook/receive_data/)
- [Happytalk Biz message receive](https://developer-center.happytalk.io/Biz-API/counsel/Receive/message/)
- [Happytalk channel integration](https://happybook-basic.happytalk.io/get-started/channel-integration)

### Kakao provider

- [NHN Cloud AlimTalk API v2.2](https://docs.nhncloud.com/ko/Notification/KakaoTalk%20Bizmessage/ko/alimtalk-api-guide-v2.2/)
- [SOLAPI REST API](https://solapi.com/developers/api/start)
- [SOLAPI Message API](https://solapi.com/developers/api/messages)
- [SOLAPI Webhook](https://solapi.com/developers/api/webhook)
- [Bizppurio BIZAPI](https://bizppurio.github.io/bizapi/)
- [Bizppurio Operations](https://bizppurio.github.io/guides/operations/)
- [Bizppurio Sandbox](https://bizppurio.github.io/sandbox/)

### Webhook assurance 참고

- [Zendesk webhook signature](https://developer.zendesk.com/documentation/webhooks/verifying/)
- [Zendesk webhook request anatomy](https://developer.zendesk.com/documentation/webhooks/anatomy-of-a-webhook-request/)
- [Intercom webhook setup](https://developers.intercom.com/docs/webhooks/setting-up-webhooks)
- [Intercom webhook delivery](https://developers.intercom.com/docs/webhooks/webhook-notifications)
