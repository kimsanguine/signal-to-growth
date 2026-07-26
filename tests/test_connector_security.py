import copy
import json
import sys
import tempfile
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
    EventIdentityError,
    EventVerificationError,
    RequestContext,
)
from signal_growth.connector_validation import (  # noqa: E402
    redact_mapping,
    redact_text,
    validate_connector_directory,
)


CHANNEL_FIXTURE = (
    ROOT
    / "fixtures"
    / "public-dummy"
    / "providers"
    / "channel-talk"
    / "message-event.json"
)
KAKAO_FIXTURE = (
    ROOT
    / "fixtures"
    / "public-dummy"
    / "providers"
    / "kakao-openbuilder"
    / "skill-request.json"
)


class ConnectorSecurityTests(unittest.TestCase):
    def test_redaction_removes_supported_contact_and_credential_patterns(self):
        email = "customer" + "@" + "example.invalid"
        phone = "010" + "-1234-5678"
        text = f"연락처 {email} / {phone}; Authorization: Bearer abcdefghijklmnop"

        redacted = redact_text(text)

        self.assertNotIn(email, redacted)
        self.assertNotIn(phone, redacted)
        self.assertNotIn("abcdefghijklmnop", redacted)
        self.assertIn("[REDACTED_EMAIL]", redacted)
        self.assertIn("[REDACTED_PHONE]", redacted)

    def test_redaction_removes_high_risk_korean_identifiers(self):
        resident_id = "900101" + "-1234567"
        card = "4111" + "-1111-1111-1111"
        account = "계좌번호: " + "123-456-789012"
        text = f"성명: 홍길동, {resident_id}, {card}, {account}"

        redacted = redact_text(text)

        self.assertNotIn("홍길동", redacted)
        self.assertNotIn(resident_id, redacted)
        self.assertNotIn(card, redacted)
        self.assertNotIn("123-456-789012", redacted)

    def test_mapping_redaction_never_echoes_direct_identifier_or_secret(self):
        value = {
            "profile": {"email": "synthetic-at-example", "phone": "synthetic-phone"},
            "authorization": "synthetic-credential",
            "content": "safe content",
        }

        redacted = redact_mapping(value)

        self.assertEqual("[REDACTED_IDENTIFIER]", redacted["profile"]["email"])
        self.assertEqual("[REDACTED_IDENTIFIER]", redacted["profile"]["phone"])
        self.assertEqual("[REDACTED_SECRET]", redacted["authorization"])
        self.assertEqual("safe content", redacted["content"])

    def test_channel_talk_rejects_wrong_legacy_webhook_token(self):
        adapter = ChannelTalkAdapter(
            b"public-dummy-hmac",
            expected_webhook_token="expected-fixture-token",
            allow_unverified_fixture=False,
        )

        with self.assertRaises(EventVerificationError):
            adapter.ingest(
                CHANNEL_FIXTURE.read_bytes(),
                received_at="2026-07-26T03:00:00Z",
                request_context=RequestContext(
                    query={"token": "wrong-fixture-token"},
                    environment="test",
                ),
            )

    def test_channel_talk_rejects_unverified_production_ingress(self):
        adapter = ChannelTalkAdapter(
            b"public-dummy-hmac",
            allow_unverified_fixture=True,
        )

        with self.assertRaises(EventVerificationError):
            adapter.ingest(
                CHANNEL_FIXTURE.read_bytes(),
                received_at="2026-07-26T03:00:00Z",
                request_context=RequestContext(environment="production"),
            )

    def test_naver_rejects_source_outside_documented_ranges(self):
        adapter = NaverTalkTalkAdapter(
            b"public-dummy-hmac",
            allow_unverified_fixture=False,
        )
        raw = json.dumps(
            {"event": "send", "user": "public-dummy-user"}
        ).encode("utf-8")

        with self.assertRaises(EventVerificationError):
            adapter.ingest(
                raw,
                received_at="2026-07-26T03:00:00Z",
                request_context=RequestContext(
                    source_ip="192.0.2.1",
                    environment="test",
                ),
            )

    def test_kakao_rejects_wrong_api_key_and_missing_request_id(self):
        adapter = KakaoOpenBuilderAdapter(
            b"public-dummy-hmac",
            expected_api_key="expected-fixture-key",
            allow_unverified_fixture=False,
        )

        with self.assertRaises(EventVerificationError):
            adapter.ingest(
                KAKAO_FIXTURE.read_bytes(),
                headers={
                    "X-Api-Key": "wrong-fixture-key",
                    "X-Request-Id": "request-public-dummy-001",
                },
                received_at="2026-07-26T03:00:00Z",
                request_context=RequestContext(environment="test"),
            )

        with self.assertRaises(EventIdentityError):
            adapter.ingest(
                KAKAO_FIXTURE.read_bytes(),
                headers={"X-Api-Key": "expected-fixture-key"},
                received_at="2026-07-26T03:00:00Z",
                request_context=RequestContext(environment="test"),
            )

    def test_kakao_marks_static_header_auth_as_weak_assurance(self):
        adapter = KakaoOpenBuilderAdapter(
            b"public-dummy-hmac",
            expected_api_key="expected-fixture-key",
            allow_unverified_fixture=False,
        )

        event = adapter.ingest(
            KAKAO_FIXTURE.read_bytes(),
            headers={
                "x-api-key": "expected-fixture-key",
                "x-request-id": "request-public-dummy-001",
            },
            received_at="2026-07-26T03:00:00Z",
            request_context=RequestContext(environment="test"),
        )

        self.assertTrue(event.auth_verified)
        self.assertEqual("weak", event.verification_assurance.value)

    def test_connector_directory_rejects_raw_credential_fields(self):
        source = json.loads(
            (
                ROOT
                / "fixtures"
                / "public-dummy"
                / "connector-artifacts"
                / "channel-connection.json"
            ).read_text(encoding="utf-8")
        )
        unsafe = copy.deepcopy(source)
        unsafe["api_key"] = "synthetic-credential-value"

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "channel-connection.json"
            path.write_text(json.dumps(unsafe), encoding="utf-8")
            issues = validate_connector_directory(Path(temporary))

        self.assertTrue(
            any("raw credential" in issue.message for issue in issues),
            [issue.render() for issue in issues],
        )

    def test_public_negative_connector_fixtures_are_rejected(self):
        negative_root = ROOT / "fixtures" / "negative" / "providers"

        malformed = validate_connector_directory(negative_root / "malformed")
        unsafe = validate_connector_directory(negative_root / "unsafe-connection")

        self.assertTrue(malformed)
        self.assertTrue(unsafe)
        self.assertTrue(
            any("external writes" in issue.message for issue in unsafe),
            [issue.render() for issue in unsafe],
        )


if __name__ == "__main__":
    unittest.main()
