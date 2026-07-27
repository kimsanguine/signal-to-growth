# Kakao Open Builder fixture scenarios

`X-Request-Id` is an HTTP header, not part of the skill-request JSON body, so
each scenario pairs a fixture file with a specific header value. Verified by
running `KakaoOpenBuilderAdapter.verify_event` + `normalize_event` against
each pair (see `tests/test_connector_workflow.py` for the harness pattern).

| Fixture | `X-Request-Id` to send | Expected `event_id` behavior |
|---|---|---|
| `skill-request.json` | `request-public-dummy-001` | baseline, single event |
| `duplicate-request-id-replay.json` | `request-public-dummy-002` (sent twice) | same `event_id` both times — idempotent replay |
| `same-utterance-new-request-id.json` | `request-public-dummy-003` | different `event_id` from the replay above, even though `bot.id`, `action.id`, and `utterance` are byte-identical to `duplicate-request-id-replay.json` — identity comes from the header, not the words |
| `high-risk-billing-request.json` | `request-public-dummy-004` | normalizes to `event_id = CSE-1d564ce1b7f495efb781d3a78c2a6b47`; content is a payment/refund dispute and must not go through auto-reply |

`same-utterance-new-request-id.json` is intentionally near-identical to
`duplicate-request-id-replay.json`. That is the point of the exercise, not an
accidental duplicate: `deterministic_event_id()` is computed from
`(provider, request_id, bot_id, action_id)`, so identical wording under a new
request id must still produce a new event.
