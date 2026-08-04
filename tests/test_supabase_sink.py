import json
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.channel_contracts import TransportError  # noqa: E402
from signal_growth.supabase_sink import (  # noqa: E402
    SupabaseDeadLetterSink,
    SupabaseEventSink,
    SupabaseHealthProbe,
    SupabaseWriteRejected,
)


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
        self.sink(self.event, "APR-KAKAO-TEST-001")

        request, timeout = self.requests[0]
        payload = json.loads(request.data)
        self.assertEqual("CSE-public-dummy-001", payload["event_id"])
        self.assertEqual("APR-KAKAO-TEST-001", payload["approval_ref"])
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

    def _sink_raising_status(self, status):
        def failing_opener(request, *, timeout):
            del request, timeout
            raise HTTPError(
                "https://project-ref.supabase.co/rest/v1/test",
                status,
                "forbidden-private-detail",
                {},
                None,
            )

        return SupabaseEventSink(
            "https://project-ref.supabase.co",
            "sb_secret_public_dummy",
            opener=failing_opener,
        )

    def test_reports_http_status_without_response_body(self):
        # A 403 is permanent: the same request will be refused forever, so it
        # must not be reported as a retryable transport problem.
        sink = self._sink_raising_status(403)

        with self.assertRaisesRegex(SupabaseWriteRejected, "HTTP 403") as caught:
            sink(self.event, "APR-KAKAO-TEST-001")
        self.assertNotIn("forbidden-private-detail", str(caught.exception))
        self.assertEqual(403, caught.exception.status_code)

    def test_server_error_is_an_availability_failure(self):
        # 5xx may succeed on retry, so the caller must be told to fail closed
        # rather than divert a recoverable event to the dead-letter table.
        sink = self._sink_raising_status(503)

        with self.assertRaises(TransportError):
            sink(self.event, "APR-KAKAO-TEST-001")

    def test_rate_limit_is_treated_as_retryable_despite_4xx(self):
        sink = self._sink_raising_status(429)

        error = None
        try:
            sink(self.event, "APR-KAKAO-TEST-001")
        except TransportError as exc:
            error = exc
        self.assertIsInstance(error, TransportError)
        self.assertNotIsInstance(error, SupabaseWriteRejected)

    def test_schema_rejection_is_not_an_availability_failure(self):
        # 422 means the row violates the table contract; retrying is pointless.
        sink = self._sink_raising_status(422)

        with self.assertRaises(SupabaseWriteRejected) as caught:
            sink(self.event, "APR-KAKAO-TEST-001")
        self.assertNotIsInstance(caught.exception, TransportError)

    def test_rejects_invalid_approval_reference_before_transport(self):
        with self.assertRaisesRegex(ValueError, "beginning with APR-"):
            self.sink(self.event, "private free-form approval note")
        self.assertEqual([], self.requests)


class SupabaseDeadLetterSinkTests(unittest.TestCase):
    def setUp(self):
        self.requests = []

        def opener(request, *, timeout):
            self.requests.append((request, timeout))
            return FakeResponse()

        self.sink = SupabaseDeadLetterSink(
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

    def test_preserves_the_event_and_why_it_could_not_be_stored(self):
        self.sink(
            self.event,
            "APR-KAKAO-TEST-001",
            failure_class="contract",
            error_type="SupabaseWriteRejected",
            status_code=422,
        )

        request, _ = self.requests[0]
        payload = json.loads(request.data)
        # The event itself must survive; that is the point of a dead letter.
        self.assertEqual(self.event, payload["canonical_event"])
        self.assertEqual("contract", payload["failure_class"])
        self.assertEqual("SupabaseWriteRejected", payload["error_type"])
        self.assertEqual(422, payload["status_code"])
        self.assertEqual("APR-KAKAO-TEST-001", payload["approval_ref"])
        self.assertIn("dead_letters", request.full_url)

    def test_uses_server_only_credentials_like_the_primary_sink(self):
        self.sink(
            self.event,
            "APR-KAKAO-TEST-001",
            failure_class="contract",
            error_type="ValueError",
        )

        request, timeout = self.requests[0]
        self.assertEqual("sb_secret_public_dummy", request.get_header("Apikey"))
        self.assertIsNone(request.get_header("Authorization"))
        self.assertLess(timeout, 5)

    def test_rejects_invalid_approval_reference_before_transport(self):
        with self.assertRaisesRegex(ValueError, "beginning with APR-"):
            self.sink(
                self.event,
                "free-form note",
                failure_class="contract",
                error_type="ValueError",
            )
        self.assertEqual([], self.requests)


class SupabaseHealthProbeTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.now = 1000.0
        self.status = 200

    def build(self, ttl_seconds=15.0, raises=None):
        def opener(request, *, timeout):
            self.calls.append((request, timeout))
            if raises is not None:
                raise raises
            return FakeResponse(self.status)

        return SupabaseHealthProbe(
            "https://project-ref.supabase.co",
            "sb_secret_public_dummy",
            ttl_seconds=ttl_seconds,
            opener=opener,
            clock=lambda: self.now,
        )

    def test_reports_reachable_storage_with_a_read_only_request(self):
        probe = self.build()

        self.assertTrue(probe())
        request, timeout = self.calls[0]
        # A liveness probe must never mutate the table it is checking.
        self.assertEqual("GET", request.get_method())
        self.assertIn("limit=0", request.full_url)
        self.assertLessEqual(timeout, 1.0)

    def test_reports_unreachable_storage_instead_of_raising(self):
        probe = self.build(raises=URLError("connection refused"))

        self.assertFalse(probe())

    def test_http_error_counts_as_unreachable(self):
        probe = self.build(
            raises=HTTPError(
                "https://project-ref.supabase.co/rest/v1/test",
                401,
                "unauthorized",
                {},
                None,
            )
        )

        self.assertFalse(probe())

    def test_caches_the_verdict_so_polling_cannot_amplify(self):
        probe = self.build(ttl_seconds=15.0)

        self.assertTrue(probe())
        self.assertTrue(probe())
        self.assertEqual(1, len(self.calls))

    def test_rechecks_after_the_cache_expires(self):
        probe = self.build(ttl_seconds=15.0)

        self.assertTrue(probe())
        self.now += 16.0
        self.assertTrue(probe())
        self.assertEqual(2, len(self.calls))


if __name__ == "__main__":
    unittest.main()
