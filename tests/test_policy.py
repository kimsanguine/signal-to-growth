"""The repository policy file must decide runtime behavior, not describe it.

These tests fail if `policies/default-policy.json` becomes decorative again:
one asserts the file is actually read, and one asserts that changing the
blocked list changes what the Kakao adapter accepts.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.adapters import (  # noqa: E402
    ChannelTalkAdapter,
    KakaoOpenBuilderAdapter,
    NaverTalkTalkAdapter,
)
from signal_growth.channel_contracts import (  # noqa: E402
    EventVerificationError,
    HttpResponse,
    RequestContext,
    VerificationAssurance,
)
from signal_growth.policy import (  # noqa: E402
    ConnectorPolicy,
    PolicyLoadError,
    PolicyViolation,
    default_connector_policy,
    fixture_ingest_policy,
    load_policy_document,
    policy_directory,
)


PROVIDERS = ROOT / "fixtures" / "public-dummy" / "providers"
KAKAO_FIXTURE = PROVIDERS / "kakao-openbuilder" / "skill-request.json"
CHANNEL_FIXTURE = PROVIDERS / "channel-talk" / "message-event.json"
NAVER_FIXTURE = PROVIDERS / "naver-talktalk" / "send-event.json"
HEADERS = {"X-Request-Id": "request-public-dummy-001"}


class PolicyLoaderTests(unittest.TestCase):
    def test_default_policy_is_loaded_from_the_repository_file(self):
        document = load_policy_document()
        policy = default_connector_policy()

        self.assertEqual(
            ROOT / "policies",
            policy_directory(),
        )
        self.assertEqual(
            frozenset(document["connectors"]["blocked_verification_assurance"]),
            policy.blocked_verification_assurance,
        )
        self.assertEqual(
            document["connectors"]["default_mode"],
            policy.default_mode,
        )
        # The shipped policy must keep unverified events out of the ingest path.
        self.assertIn("none", policy.blocked_verification_assurance)

    def test_unknown_assurance_value_fails_loudly_at_load_time(self):
        document = json.loads(
            (ROOT / "policies" / "default-policy.json").read_text(encoding="utf-8")
        )
        document["connectors"]["blocked_verification_assurance"] = ["nome"]

        with self.assertRaisesRegex(PolicyLoadError, "unknown verification assurance"):
            ConnectorPolicy.from_document(document, source="test-policy")

    def test_missing_connectors_section_fails_loudly(self):
        with self.assertRaisesRegex(PolicyLoadError, "connectors section"):
            ConnectorPolicy.from_document({}, source="test-policy")


class KakaoAssuranceEnforcementTests(unittest.TestCase):
    """The block must come from the policy, not from a constructor default."""

    def test_default_policy_blocks_unverified_fixture_ingest(self):
        adapter = KakaoOpenBuilderAdapter(b"public-dummy-hmac")

        with self.assertRaises(PolicyViolation) as captured:
            adapter.ingest(
                KAKAO_FIXTURE.read_bytes(),
                headers=HEADERS,
                received_at="2026-08-04T03:00:00Z",
                request_context=RequestContext(environment="fixture"),
            )

        self.assertIn("blocked_verification_assurance", str(captured.exception))
        # An existing ingress already answers this exception type.
        self.assertIsInstance(captured.exception, EventVerificationError)

    def test_fixture_policy_permits_normalizing_public_dummy_fixtures(self):
        adapter = KakaoOpenBuilderAdapter(
            b"public-dummy-hmac",
            policy=fixture_ingest_policy(),
        )

        event = adapter.ingest(
            KAKAO_FIXTURE.read_bytes(),
            headers=HEADERS,
            received_at="2026-08-04T03:00:00Z",
            request_context=RequestContext(environment="fixture"),
        )

        self.assertFalse(event.auth_verified)
        self.assertEqual("none", event.verification_assurance.value)

    def test_blocking_weak_in_the_policy_rejects_api_key_verified_events(self):
        """Proves the policy value drives the check instead of a hardcoded one."""
        stricter = ConnectorPolicy(
            source="test-policy",
            blocked_verification_assurance=frozenset({"none", "weak"}),
            default_mode="read_only",
        )
        adapter = KakaoOpenBuilderAdapter(
            b"public-dummy-hmac",
            expected_api_key="expected-fixture-key",
            policy=stricter,
        )
        headers = {**HEADERS, "X-Api-Key": "expected-fixture-key"}

        with self.assertRaises(PolicyViolation):
            adapter.ingest(
                KAKAO_FIXTURE.read_bytes(),
                headers=headers,
                received_at="2026-08-04T03:00:00Z",
                request_context=RequestContext(environment="test"),
            )

        # The same request passes under the shipped policy, which allows weak.
        permitted = KakaoOpenBuilderAdapter(
            b"public-dummy-hmac",
            expected_api_key="expected-fixture-key",
        )
        event = permitted.ingest(
            KAKAO_FIXTURE.read_bytes(),
            headers=headers,
            received_at="2026-08-04T03:00:00Z",
            request_context=RequestContext(environment="test"),
        )
        self.assertEqual(VerificationAssurance.WEAK, event.verification_assurance)


class UnauthenticatedTransport:
    """A transport whose response carries no provider authentication."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def send(self, request):
        del request
        return HttpResponse(status=200, body=self._body, authenticated=False)


class ChannelTalkAssuranceEnforcementTests(unittest.TestCase):
    """The same policy must govern Channel Talk, not a constructor default."""

    def test_default_policy_blocks_unverified_fixture_ingest(self):
        adapter = ChannelTalkAdapter(b"public-dummy-hmac")

        with self.assertRaises(PolicyViolation) as captured:
            adapter.ingest(
                CHANNEL_FIXTURE.read_bytes(),
                received_at="2026-08-04T03:00:00Z",
                request_context=RequestContext(environment="fixture"),
            )

        self.assertIn("blocked_verification_assurance", str(captured.exception))
        self.assertIsInstance(captured.exception, EventVerificationError)

    def test_fixture_policy_permits_normalizing_public_dummy_fixtures(self):
        adapter = ChannelTalkAdapter(
            b"public-dummy-hmac",
            policy=fixture_ingest_policy(),
        )

        event = adapter.ingest(
            CHANNEL_FIXTURE.read_bytes(),
            received_at="2026-08-04T03:00:00Z",
            request_context=RequestContext(environment="fixture"),
        )

        self.assertFalse(event.auth_verified)
        self.assertEqual("none", event.verification_assurance.value)

    def test_backfill_from_an_unauthenticated_transport_is_blocked(self):
        """Backfill is a second ingress, so the policy has to cover it too."""
        adapter = ChannelTalkAdapter(
            b"public-dummy-hmac",
            credential_ref="secret://channel-talk/test",
        )
        transport = UnauthenticatedTransport(
            (PROVIDERS / "channel-talk" / "backfill-response.json").read_bytes()
        )

        with self.assertRaises(PolicyViolation):
            adapter.backfill(
                transport,
                "chat_public_dummy_001",
                received_at="2026-08-04T03:00:00Z",
            )

    def test_blocking_weak_in_the_policy_rejects_token_verified_events(self):
        stricter = ConnectorPolicy(
            source="test-policy",
            blocked_verification_assurance=frozenset({"none", "weak"}),
            default_mode="read_only",
        )
        adapter = ChannelTalkAdapter(
            b"public-dummy-hmac",
            expected_webhook_token="expected-fixture-token",
            policy=stricter,
        )

        with self.assertRaises(PolicyViolation):
            adapter.ingest(
                CHANNEL_FIXTURE.read_bytes(),
                received_at="2026-08-04T03:00:00Z",
                request_context=RequestContext(
                    query={"token": "expected-fixture-token"},
                    environment="test",
                ),
            )


class NaverAssuranceEnforcementTests(unittest.TestCase):
    """The same policy must govern Naver TalkTalk, not a constructor default."""

    def test_default_policy_blocks_ingest_without_a_trusted_source_ip(self):
        adapter = NaverTalkTalkAdapter(b"public-dummy-hmac")

        with self.assertRaises(PolicyViolation) as captured:
            adapter.ingest(
                NAVER_FIXTURE.read_bytes(),
                received_at="2026-08-04T03:00:00Z",
                request_context=RequestContext(environment="fixture"),
            )

        self.assertIn("blocked_verification_assurance", str(captured.exception))
        self.assertIsInstance(captured.exception, EventVerificationError)

    def test_fixture_policy_permits_normalizing_public_dummy_fixtures(self):
        adapter = NaverTalkTalkAdapter(
            b"public-dummy-hmac",
            policy=fixture_ingest_policy(),
        )

        event = adapter.ingest(
            NAVER_FIXTURE.read_bytes(),
            received_at="2026-08-04T03:00:00Z",
            request_context=RequestContext(environment="fixture"),
        )

        self.assertFalse(event.auth_verified)
        self.assertEqual("none", event.verification_assurance.value)

    def test_blocking_weak_in_the_policy_rejects_source_ip_verified_events(self):
        stricter = ConnectorPolicy(
            source="test-policy",
            blocked_verification_assurance=frozenset({"none", "weak"}),
            default_mode="read_only",
        )
        adapter = NaverTalkTalkAdapter(b"public-dummy-hmac", policy=stricter)

        with self.assertRaises(PolicyViolation):
            adapter.ingest(
                NAVER_FIXTURE.read_bytes(),
                received_at="2026-08-04T03:00:00Z",
                request_context=RequestContext(
                    source_ip="211.249.40.1",
                    environment="test",
                ),
            )

        # The same request passes under the shipped policy, which allows weak.
        permitted = NaverTalkTalkAdapter(b"public-dummy-hmac")
        event = permitted.ingest(
            NAVER_FIXTURE.read_bytes(),
            received_at="2026-08-04T03:00:00Z",
            request_context=RequestContext(
                source_ip="211.249.40.1",
                environment="test",
            ),
        )
        self.assertEqual(VerificationAssurance.WEAK, event.verification_assurance)


if __name__ == "__main__":
    unittest.main()
