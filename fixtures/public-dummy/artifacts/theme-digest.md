# Theme digest

- 관찰 기간: 2026-07-25 (합성 fixture, 단일 시점 스냅샷)
- 채널 커버리지: `interview` 1건, `kakao_channel_chatbot` 1건
- 승인된 signal: SIG-20260725-001, SIG-20260725-002 (2건 중 2건 승인 상태 — 하나는 `approved`, 하나는 `awaiting_human_review`)

## 테마 1 — 초기 설정 실패가 태그보다 먼저 있었다

- 근거: SIG-20260725-001 (severity: medium, channel: interview)
- 원문 사유: 해지 사유를 태그로만 집계하면 가격 문제로 보이지만, 원문에서는 초기 설정 실패가 먼저 발생한 사례가 많다.
- 반증: 가격을 직접 언급한 고객도 존재한다 (`counterevidence.md` 참조). 이 테마를 단독 결정 근거로 쓰지 않는다.

## 테마 2 — 결제 분쟁은 반드시 사람이 본다

- 근거: SIG-20260725-002 (severity: high, channel: kakao_channel_chatbot)
- 이 테마는 빈도로 판단하지 않는다. 1건이어도 severity가 high면 즉시 human review 큐로 간다 (`risk-queue.jsonl` 참조).
- 자동 응답 경로로 절대 보내지 않는다.

## 커버되지 않은 것

- 이탈(churn) 완료 고객 표본이 0건이다. 이 다이제스트로 이탈률이나 이탈 원인을 설명할 수 없다.
- 채널 커버리지가 interview와 kakao_channel_chatbot 2개뿐이다. Naver TalkTalk, Channel Talk 채널의 신호는 아직 이 다이제스트에 없다.
