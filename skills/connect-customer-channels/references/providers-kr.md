# Korean provider reference

Use this reference to identify a provider and product before mapping events. Recheck official sources when behavior, policy, or API versions may have changed.

For each active provider record, retain:

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

Use `supported`, `unsupported`, or `unconfirmed`. Mark every missing public contract `[HOLD]`.

## Kakao product selection

### Kakao Channel 1:1 chat

- Treat the Channel manager web or app chat as a native operator surface.
- Do not assume that enabling a Kakao Channel creates an external conversation API.
- Do not use Channel 1:1 chat history as proof that ConsultTalk or a dealer API is connected.
- Review migration and history-access effects before moving a channel to a separate consultation system.

### Kakao ConsultTalk (`상담톡`)

- Treat ConsultTalk as a customer-initiated consultation product.
- Require an official dealer and a counselor or helpdesk system; do not expect Kakao to provide the operator system.
- Model inbound customer events and replies as session-bound consultation activity.
- Require `session_state=active` before proposing a reply for approval.
- Keep ConsultTalk history, reply, handover, and delivery capabilities specific to the contracted dealer and helpdesk.

### Kakao AlimTalk (`알림톡`)

- Treat AlimTalk as outbound informational messaging, not as a customer-initiated conversation.
- Require an official dealer, approved sender profile, approved template, allowed message purpose, and recipient basis.
- Model request acceptance and final delivery results as separate events.
- Do not use an AlimTalk request or callback as a ConsultTalk session or inbound customer reply.
- Keep SMS or LMS fallback disabled and represent any approved fallback as a separate attempt.

### Kakao Developers message APIs

- Treat these APIs as same-service user interaction APIs.
- Exclude them from customer-service and transactional BizMessage adapters.
- Stop when a request attempts to substitute them for ConsultTalk or AlimTalk.

### Kakao Brand Message

- Treat this as a separate outbound marketing-capable product.
- Keep it disabled by default.
- Require explicit purpose, consent or legal-basis review, audience, template, provider, and human approval before any execution design.

Official product sources checked on 2026-07-26:

- Kakao Developers message API: https://developers.kakao.com/docs/ko/kakaotalk-message/common
- Kakao product-selection FAQ: https://developers.kakao.com/docs/ko/kakaotalk-message/faq
- Kakao AlimTalk: https://business.kakao.com/info/infotalk/
- Kakao ConsultTalk: https://kakaobusiness.gitbook.io/main/ad/cstalk
- Kakao Brand Message: https://business.kakao.com/info/brandmessage/

## Naver TalkTalk

Use the public Chat Bot API as an event-only contract until a stronger official contract is verified.

Confirmed:

- Receive `open`, `send`, `echo`, `leave`, `friend`, `action`, and related webhook events.
- Test webhook input locally with the official examples.
- Use a Partner Center authorization value for the Send API.
- Reply synchronously within the provider window or acknowledge and use the asynchronous Send API.
- Observe counselor handover state through the BETA handover contract.
- Create a test account and exclude it from search with the documented `[테스트]` profile prefix.

Hold:

- Mark historical conversation backfill `unconfirmed`.
- Mark message-level delivered and read receipts `unconfirmed`.
- Mark payload-bound webhook signature verification `unconfirmed`.
- Mark stable counselor assignment and tag-management APIs `unconfirmed`.

Implementation:

- Store each valid inbound event durably before processing.
- Expose missing windows because public backfill is unconfirmed.
- Keep Send API and handover disabled in the read-only adapter.
- Do not treat Send API success as delivered.

Official sources checked on 2026-07-26:

- Chat Bot API V1: https://github.com/navertalk/chatbot-api
- Handover API V1 BETA: https://github.com/navertalk/chatbot-api/blob/master/handover_v1.md

## Channel Talk

Use Channel Talk as the first read-only real-connector candidate.

Confirmed:

- Receive message-creation webhooks.
- Read UserChat lists, individual chats, and messages.
- Backfill and reconcile conversations with stable provider identifiers.
- Read conversation state and manager or tag metadata.
- Access send, manager-invite, and tag-mutation APIs as separate write capabilities.
- Authenticate Open API requests with an access-key and access-secret pair.

Authentication boundary:

- Treat the legacy webhook URL token as weak assurance and add secret-path and network controls.
- Treat App Function `X-Signature` HMAC as a different transport contract.
- Do not claim that every Channel Talk webhook uses HMAC.

Hold:

- Mark isolated Open API sandbox availability `unconfirmed`.
- Mark final end-user delivery and read-receipt semantics `unconfirmed` unless a checked contract and test evidence establish them.
- Treat webhook event types other than the clearly documented new-message path as contract-version dependent.

Implementation:

- Ingest webhooks and read UserChat or message backfill only.
- Reconcile a webhook event and matching backfill record into one canonical event.
- Keep reply, assignment, and tag mutation disabled.

Official sources checked on 2026-07-26:

- Open API: https://developers.channel.io/en/articles/What-is-Open-API-c8c76fba
- Authentication: https://developers.channel.io/en/articles/Authentication-20516f31
- Webhook setup: https://developers.channel.io/en/articles/Getting-started-f2a30b58
- Webhook events: https://developers.channel.io/en/articles/Webhook-events-7bd9b8e2
- App Function: https://developers.channel.io/en/articles/77250b17

## Happytalk

Treat each Happytalk product surface as a separate contract.

Confirmed:

- Receive Biz API message and room-close events at a customer endpoint.
- Receive Embedded room, status, counselor, classification, flag, and tag-change webhooks.
- Read rooms, messages, counselor metadata, tags, room status, send time, and read time.
- Use counselor-list and direct or automatic assignment APIs as separate write capabilities.
- Use documented development or test hosts when credentials and access are approved.
- Verify Embedded webhook requests with the documented app-signature surface.

Authentication boundary:

- Obtain credentials only after purpose and condition review with Happytalk.
- Do not apply Embedded webhook signature rules to Biz message-receive endpoints.
- Mark Biz receive authenticity `unconfirmed` when the active contract provides no verification rule.

Hold:

- Mark a public self-service API sandbox `unconfirmed`.
- Mark a public tag-write API `unconfirmed`.
- Mark delivery beyond the documented room status and message read time `unconfirmed`.

Implementation:

- Start read-only only after obtaining an approved test credential and retention policy.
- Record the exact product surface and provider contract version.
- Track schema drift, including message-template changes.
- Keep message send and counselor assignment disabled.

Official sources checked on 2026-07-26:

- Developer Center: https://developer-center.happytalk.io/
- Biz API: https://developer-center.happytalk.io/Biz-API/
- Biz message receive: https://developer-center.happytalk.io/Biz-API/counsel/Receive/message/
- Conversation lookup: https://developer-center.happytalk.io/Happytalk/customer/counsel_detail_search/counsel_room_id/
- Embedded webhook: https://developer-center.happytalk.io/open_api/embedded_happytalk/webhook/receive_data/

## Kakao dealer candidates

Select one real adapter only after identifying the user's contracted provider.

### NHN Cloud

- Confirm AlimTalk send, message-result polling, sender, template, and provider idempotency contracts.
- Keep application-level idempotency even when a provider key exists.
- Use polling as a first-class recovery path when callback assurance remains unconfirmed.

Source: https://docs.nhncloud.com/ko/Notification/KakaoTalk%20Bizmessage/ko/alimtalk-api-guide-v2.2/

### SOLAPI

- Confirm HMAC API authentication, message or group lookup, webhook, and webhook testing.
- Keep authentication replay protection separate from message idempotency.
- Store Kakao and SMS or LMS fallback as separate attempts.

Sources:

- https://solapi.com/developers/api/start
- https://solapi.com/developers/api/messages
- https://solapi.com/developers/api/webhook

### Bizppurio

- Confirm operation and test environments, Bearer authentication, IP controls, callback, polling, report recovery, and simulator behavior.
- Treat provider success code `1000` as acceptance, not delivery.
- Do not treat `refkey` as guaranteed deduplication without an explicit contract.
- Deduplicate repeated results and reconcile callbacks with polling.

Sources:

- https://bizppurio.github.io/bizapi/
- https://bizppurio.github.io/guides/operations/
- https://bizppurio.github.io/sandbox/

## Drift handling

- Recheck the official contract before enabling a provider or product.
- Preserve checked date, source URL, API version, contract version, and known drift.
- Prefer the stricter permission, consent, approval, and status interpretation when official sources conflict.
- Keep the capability `[HOLD]` until the contracted provider resolves the conflict.
- Require a new test-account round trip after a breaking schema, auth, endpoint, or product-policy change.
