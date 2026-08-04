import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.adapters import (  # noqa: E402
    ChannelTalkAdapter,
    KakaoOpenBuilderAdapter,
    NaverTalkTalkAdapter,
)
from signal_growth.channel_contracts import (  # noqa: E402
    Capability,
    EventIdentityError,
    HttpResponse,
    RequestContext,
    UnsupportedCapability,
)
from signal_growth.connector_validation import dedupe_events  # noqa: E402
from signal_growth.policy import fixture_ingest_policy  # noqa: E402


PROVIDERS = ROOT / "fixtures" / "public-dummy" / "providers"


class FixtureTransport:
    def __init__(self, body: bytes, *, authenticated: bool = True) -> None:
        self.body = body
        self.authenticated = authenticated
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        return HttpResponse(
            status=200,
            body=self.body,
            authenticated=self.authenticated,
        )


class ConnectorWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cs_event_schema = json.loads(
            (ROOT / "contracts" / "cs-event.schema.json").read_text(
                encoding="utf-8"
            )
        )

    def assert_schema_valid(self, event):
        errors = list(
            Draft202012Validator(
                self.cs_event_schema,
                format_checker=FormatChecker(),
            ).iter_errors(event.to_dict())
        )
        self.assertEqual([], errors, [error.message for error in errors])

    def test_naver_fixture_normalizes_deterministically_and_dedupes(self):
        adapter = NaverTalkTalkAdapter(
            b"public-dummy-hmac",
            policy=fixture_ingest_policy(),
        )
        raw = (PROVIDERS / "naver-talktalk" / "send-event.json").read_bytes()

        first = adapter.ingest(
            raw,
            received_at="2026-07-26T03:00:00Z",
            request_context=RequestContext(environment="fixture"),
        )
        replay = adapter.ingest(
            raw,
            received_at="2026-07-26T03:05:00Z",
            request_context=RequestContext(environment="fixture"),
        )

        self.assertEqual(first.event_id, replay.event_id)
        self.assertEqual(first.idempotency_key, replay.idempotency_key)
        self.assertEqual(1, len(dedupe_events([first, replay])))
        self.assertFalse(first.auth_verified)
        self.assert_schema_valid(first)

    def test_conflicting_replay_is_not_silently_deduplicated(self):
        first = {
            "event_id": "CSE-conflict-public-dummy",
            "content_redacted": "첫 번째 내용",
        }
        conflicting = {
            "event_id": "CSE-conflict-public-dummy",
            "content_redacted": "다른 내용",
        }

        with self.assertRaises(EventIdentityError):
            dedupe_events([first, conflicting])

    def test_channel_webhook_and_backfill_share_canonical_identity(self):
        adapter = ChannelTalkAdapter(
            b"public-dummy-hmac",
            credential_ref="secret://channel-talk/test",
            policy=fixture_ingest_policy(),
        )
        webhook = adapter.ingest(
            (PROVIDERS / "channel-talk" / "message-event.json").read_bytes(),
            received_at="2026-07-26T03:00:00Z",
            request_context=RequestContext(environment="fixture"),
        )
        transport = FixtureTransport(
            (PROVIDERS / "channel-talk" / "backfill-response.json").read_bytes()
        )

        page = adapter.backfill(
            transport,
            "chat_public_dummy_001",
            received_at="2026-07-26T03:05:00Z",
        )

        self.assertEqual(1, len(page.events))
        self.assertEqual(webhook.event_id, page.events[0].event_id)
        self.assertEqual(1, len(dedupe_events([webhook, page.events[0]])))
        self.assertEqual("secret://channel-talk/test", page.request.credential_ref)
        self.assertNotIn("Authorization", page.request.headers)
        self.assert_schema_valid(page.events[0])

    def test_kakao_skill_request_normalizes_and_dedupes_by_request_id(self):
        adapter = KakaoOpenBuilderAdapter(
            b"public-dummy-hmac",
            policy=fixture_ingest_policy(),
        )
        raw = (
            PROVIDERS / "kakao-openbuilder" / "skill-request.json"
        ).read_bytes()
        headers = {"X-Request-Id": "request-public-dummy-001"}

        first = adapter.ingest(
            raw,
            headers=headers,
            received_at="2026-07-26T03:00:00Z",
            request_context=RequestContext(environment="fixture"),
        )
        replay = adapter.ingest(
            raw,
            headers=headers,
            received_at="2026-07-26T03:05:00Z",
            request_context=RequestContext(environment="fixture"),
        )
        second_request = adapter.ingest(
            raw,
            headers={"X-Request-Id": "request-public-dummy-002"},
            received_at="2026-07-26T03:06:00Z",
            request_context=RequestContext(environment="fixture"),
        )

        self.assertEqual(first.event_id, replay.event_id)
        self.assertNotEqual(first.event_id, second_request.event_id)
        self.assertEqual("kakao_channel_chatbot", first.channel)
        self.assertEqual("message_received", first.event_type)
        self.assertFalse(first.auth_verified)
        self.assertEqual(1, len(dedupe_events([first, replay])))
        self.assert_schema_valid(first)

    def test_kakao_skill_response_uses_official_simple_text_contract(self):
        response = KakaoOpenBuilderAdapter.build_skill_response(
            "문의가 접수되었습니다."
        )

        self.assertEqual("2.0", response["version"])
        self.assertEqual(
            "문의가 접수되었습니다.",
            response["template"]["outputs"][0]["simpleText"]["text"],
        )

    def test_unsupported_capabilities_fail_loudly(self):
        naver = NaverTalkTalkAdapter(b"public-dummy-hmac")
        channel = ChannelTalkAdapter(b"public-dummy-hmac")
        kakao = KakaoOpenBuilderAdapter(b"public-dummy-hmac")

        with self.assertRaises(UnsupportedCapability):
            naver.build_backfill_request("public-dummy-chat")
        with self.assertRaises(UnsupportedCapability):
            naver.send_approved({})
        with self.assertRaises(UnsupportedCapability):
            channel.send_approved({})
        with self.assertRaises(UnsupportedCapability):
            kakao.build_backfill_request("public-dummy-chat")
        self.assertFalse(naver.capabilities().supports(Capability.REPLY_SEND))
        self.assertFalse(channel.capabilities().supports(Capability.REPLY_SEND))
        self.assertTrue(
            kakao.capabilities().supports(Capability.SKILL_REQUEST_INGEST)
        )
        naver_capabilities = {
            item["name"]: item
            for item in naver.capabilities().to_dict()["capabilities"]
        }
        self.assertEqual(
            "disabled_by_policy",
            naver_capabilities["reply_send"]["support"],
        )
        self.assertEqual(
            "draft_only",
            naver_capabilities["reply_send"]["access_mode"],
        )


if __name__ == "__main__":
    unittest.main()
