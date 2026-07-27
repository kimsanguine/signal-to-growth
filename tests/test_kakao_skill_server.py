import io
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.adapters import KakaoOpenBuilderAdapter  # noqa: E402
from signal_growth.kakao_skill_server import KakaoSkillApplication  # noqa: E402


FIXTURE = (
    ROOT
    / "fixtures"
    / "public-dummy"
    / "providers"
    / "kakao-openbuilder"
    / "skill-request.json"
)


class KakaoSkillServerTests(unittest.TestCase):
    def setUp(self):
        self.events = []

        def event_sink(event, approval_ref):
            self.events.append((event, approval_ref))

        adapter = KakaoOpenBuilderAdapter(
            b"public-dummy-hmac",
            expected_api_key="expected-fixture-key",
            allow_unverified_fixture=False,
        )
        self.app = KakaoSkillApplication(
            adapter,
            event_sink,
            approval_ref="APR-KAKAO-TEST-001",
        )

    def request(self, *, api_key="expected-fixture-key", request_id="request-001"):
        raw = FIXTURE.read_bytes()
        environ = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/api/kakao/skill",
            "CONTENT_LENGTH": str(len(raw)),
            "CONTENT_TYPE": "application/json",
            "HTTP_X_API_KEY": api_key,
            "HTTP_X_REQUEST_ID": request_id,
            "wsgi.input": io.BytesIO(raw),
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = dict(headers)

        body = b"".join(self.app(environ, start_response))
        return captured, json.loads(body)

    def test_persists_sanitized_event_before_fixed_response(self):
        captured, response = self.request()

        self.assertEqual("200 OK", captured["status"])
        self.assertEqual("2.0", response["version"])
        self.assertEqual(1, len(self.events))
        event, approval_ref = self.events[0]
        self.assertEqual("kakao_openbuilder", event["provider"])
        self.assertEqual("APR-KAKAO-TEST-001", approval_ref)
        self.assertNotIn("bot-user-public-dummy-001", json.dumps(event))

    def test_rejects_wrong_api_key_without_persisting(self):
        captured, response = self.request(api_key="wrong-fixture-key")

        self.assertEqual("401 Unauthorized", captured["status"])
        self.assertEqual({"error": "request_verification_failed"}, response)
        self.assertEqual([], self.events)

    def test_persistence_failure_prevents_acknowledgement(self):
        def failing_sink(event, approval_ref):
            del event, approval_ref
            raise RuntimeError("synthetic persistence failure")

        adapter = KakaoOpenBuilderAdapter(
            b"public-dummy-hmac",
            expected_api_key="expected-fixture-key",
            allow_unverified_fixture=False,
        )
        self.app = KakaoSkillApplication(
            adapter,
            failing_sink,
            approval_ref="APR-KAKAO-TEST-001",
        )

        captured, response = self.request()

        self.assertEqual("503 Service Unavailable", captured["status"])
        self.assertEqual({"error": "event_persistence_failed"}, response)

    def test_rejects_invalid_approval_reference(self):
        adapter = KakaoOpenBuilderAdapter(
            b"public-dummy-hmac",
            expected_api_key="expected-fixture-key",
            allow_unverified_fixture=False,
        )

        with self.assertRaisesRegex(ValueError, "beginning with APR-"):
            KakaoSkillApplication(
                adapter,
                lambda event, approval_ref: None,
                approval_ref="raw approval note",
            )


if __name__ == "__main__":
    unittest.main()
