import json
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.channel_contracts import TransportError  # noqa: E402
from signal_growth.supabase_sink import SupabaseEventSink  # noqa: E402


class FakeResponse:
    def __init__(self, status=201):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def getcode(self):
        return self.status


class SupabaseEventSinkTests(unittest.TestCase):
    def setUp(self):
        self.requests = []

        def opener(request, *, timeout):
            self.requests.append((request, timeout))
            return FakeResponse()

        self.sink = SupabaseEventSink(
            "https://project-ref.supabase.co",
            "sb_secret_public_dummy",
            opener=opener,
        )
        self.event = {
            "event_id": "CSE-public-dummy-001",
            "provider": "kakao_openbuilder",
            "provider_event_id": "request-public-dummy-001",
            "received_at": "2026-07-26T00:00:00Z",
            "content_redacted": "[REDACTED_PHONE]",
        }

    def test_posts_normalized_event_with_server_only_key(self):
        self.sink(self.event)

        request, timeout = self.requests[0]
        payload = json.loads(request.data)
        self.assertEqual("CSE-public-dummy-001", payload["event_id"])
        self.assertEqual(self.event, payload["canonical_event"])
        self.assertEqual("sb_secret_public_dummy", request.get_header("Apikey"))
        self.assertIsNone(request.get_header("Authorization"))
        self.assertEqual(
            "resolution=ignore-duplicates,return=minimal",
            request.get_header("Prefer"),
        )
        self.assertIn("on_conflict=event_id", request.full_url)
        self.assertLess(timeout, 5)

    def test_rejects_non_https_project_url(self):
        with self.assertRaises(ValueError):
            SupabaseEventSink(
                "http://project-ref.supabase.co",
                "sb_secret_public_dummy",
            )

    def test_reports_http_status_without_response_body(self):
        def failing_opener(request, *, timeout):
            del request, timeout
            raise HTTPError(
                "https://project-ref.supabase.co/rest/v1/test",
                403,
                "forbidden-private-detail",
                {},
                None,
            )

        sink = SupabaseEventSink(
            "https://project-ref.supabase.co",
            "sb_secret_public_dummy",
            opener=failing_opener,
        )

        with self.assertRaisesRegex(TransportError, "HTTP 403") as caught:
            sink(self.event)
        self.assertNotIn("forbidden-private-detail", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
