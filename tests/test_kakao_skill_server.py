import io
import json
import logging
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.adapters import KakaoOpenBuilderAdapter  # noqa: E402
from signal_growth.channel_contracts import TransportError  # noqa: E402
from signal_growth.kakao_skill_server import KakaoSkillApplication  # noqa: E402
from signal_growth.observability import StructuredLogger  # noqa: E402
from signal_growth.supabase_sink import (  # noqa: E402
    KAKAO_RESPONSE_DEADLINE_SECONDS,
    KAKAO_RESPONSE_SAFETY_MARGIN_SECONDS,
    PERSISTENCE_BUDGET_SECONDS,
    SupabaseDeadLetterSink,
    SupabaseEventSink,
    SupabaseWriteRejected,
)


UTTERANCE = "초기 설정 중 연결 단계에서 계속 멈춰요."


class CapturingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


def _quiet_logger() -> StructuredLogger:
    """A logger that keeps expected failure output out of the test report."""
    logger = logging.getLogger("signal_growth.test.quiet")
    logger.handlers = [logging.NullHandler()]
    logger.propagate = False
    return StructuredLogger(logger)


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
        )
        self.app = KakaoSkillApplication(
            adapter,
            failing_sink,
            approval_ref="APR-KAKAO-TEST-001",
            logger=_quiet_logger(),
        )

        captured, response = self.request()

        self.assertEqual("503 Service Unavailable", captured["status"])
        self.assertEqual({"error": "event_persistence_failed"}, response)

    def test_rejects_invalid_approval_reference(self):
        adapter = KakaoOpenBuilderAdapter(
            b"public-dummy-hmac",
            expected_api_key="expected-fixture-key",
        )

        with self.assertRaisesRegex(ValueError, "beginning with APR-"):
            KakaoSkillApplication(
                adapter,
                lambda event, approval_ref: None,
                approval_ref="raw approval note",
            )


class IngestOutcomeLoggingTests(unittest.TestCase):
    """Every ingest outcome must be logged, because the recovery paths differ.

    Failures are classified so an operator knows whether a retry can help.
    Success is logged too, so silence in this log means "nothing arrived"
    rather than "everything worked".
    """

    def setUp(self):
        self.dead_letters = []
        self.handler = CapturingHandler()
        logger = logging.getLogger("signal_growth.test.skill_server")
        logger.handlers = [self.handler]
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        self.logger = StructuredLogger(logger)

    def dead_letter_sink(self, event, approval_ref, **metadata):
        self.dead_letters.append((event, approval_ref, metadata))

    def build(self, sink, *, dead_letter_sink=None):
        adapter = KakaoOpenBuilderAdapter(
            b"public-dummy-hmac",
            expected_api_key="expected-fixture-key",
        )
        return KakaoSkillApplication(
            adapter,
            sink,
            approval_ref="APR-KAKAO-TEST-001",
            dead_letter_sink=dead_letter_sink,
            logger=self.logger,
        )

    def request(self, app):
        raw = FIXTURE.read_bytes()
        environ = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/api/kakao/skill",
            "CONTENT_LENGTH": str(len(raw)),
            "CONTENT_TYPE": "application/json",
            "HTTP_X_API_KEY": "expected-fixture-key",
            "HTTP_X_REQUEST_ID": "request-001",
            "wsgi.input": io.BytesIO(raw),
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = dict(headers)

        body = b"".join(app(environ, start_response))
        return captured, json.loads(body)

    def log_records(self):
        return [json.loads(line) for line in self.handler.lines]

    def test_successful_ingest_is_logged_so_silence_means_no_traffic(self):
        captured, _ = self.request(self.build(lambda event, approval_ref: None))

        self.assertEqual("200 OK", captured["status"])
        record = self.log_records()[0]
        self.assertEqual("ingest_accepted", record["event"])
        self.assertEqual("persisted", record["outcome"])
        self.assertEqual("kakao_openbuilder", record["provider"])
        self.assertEqual("APR-KAKAO-TEST-001", record["approval_ref"])
        self.assertIn("event_id", record)
        self.assertGreaterEqual(record["duration_ms"], 0)
        # The redact contract still holds on the success path.
        self.assertNotIn("content_redacted", record)
        self.assertNotIn(UTTERANCE, self.handler.lines[0])

    def test_a_rejected_request_emits_no_success_line(self):
        raw = FIXTURE.read_bytes()
        environ = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/api/kakao/skill",
            "CONTENT_LENGTH": str(len(raw)),
            "HTTP_X_API_KEY": "wrong-fixture-key",
            "HTTP_X_REQUEST_ID": "request-001",
            "wsgi.input": io.BytesIO(raw),
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = status

        app = self.build(lambda event, approval_ref: None)
        b"".join(app(environ, start_response))

        self.assertEqual("401 Unauthorized", captured["status"])
        self.assertEqual([], self.log_records())

    def test_availability_failure_fails_closed_without_dead_lettering(self):
        # Supabase may accept this same write in a minute, so the event must
        # stay in Kakao's retry queue rather than be filed as undeliverable.
        def unavailable(event, approval_ref):
            del event, approval_ref
            raise TransportError("Supabase event persistence was unavailable")

        captured, response = self.request(
            self.build(unavailable, dead_letter_sink=self.dead_letter_sink)
        )

        self.assertEqual("503 Service Unavailable", captured["status"])
        self.assertEqual({"error": "event_persistence_unavailable"}, response)
        self.assertEqual([], self.dead_letters)
        record = self.log_records()[0]
        self.assertEqual("availability", record["failure_class"])
        self.assertEqual("retry_expected", record["outcome"])

    def test_contract_failure_is_dead_lettered_and_acknowledged(self):
        # A retry of this exact event can never succeed, so an endless 503 loop
        # would lose it. Storing it elsewhere makes the acknowledgement honest.
        def rejected(event, approval_ref):
            del event, approval_ref
            raise SupabaseWriteRejected("rejected with HTTP 422", status_code=422)

        captured, response = self.request(
            self.build(rejected, dead_letter_sink=self.dead_letter_sink)
        )

        self.assertEqual("200 OK", captured["status"])
        self.assertEqual("2.0", response["version"])
        self.assertEqual(1, len(self.dead_letters))
        event, approval_ref, metadata = self.dead_letters[0]
        self.assertEqual("kakao_openbuilder", event["provider"])
        self.assertEqual("APR-KAKAO-TEST-001", approval_ref)
        self.assertEqual("contract", metadata["failure_class"])
        self.assertEqual("SupabaseWriteRejected", metadata["error_type"])
        self.assertEqual(422, metadata["status_code"])
        record = self.log_records()[0]
        self.assertEqual("contract", record["failure_class"])
        self.assertTrue(record["dead_lettered"])

    def test_contract_failure_without_dead_letter_sink_fails_closed(self):
        # No dead-letter destination means the only safe answer is to refuse
        # the acknowledgement; dropping the event silently would be worse.
        def rejected(event, approval_ref):
            del event, approval_ref
            raise SupabaseWriteRejected("rejected with HTTP 400", status_code=400)

        captured, response = self.request(self.build(rejected))

        self.assertEqual("503 Service Unavailable", captured["status"])
        self.assertEqual({"error": "event_persistence_failed"}, response)
        record = self.log_records()[0]
        self.assertEqual("dropped_without_storage", record["outcome"])
        self.assertFalse(record["dead_lettered"])

    def test_failing_dead_letter_sink_still_fails_closed(self):
        def rejected(event, approval_ref):
            del event, approval_ref
            raise SupabaseWriteRejected("rejected with HTTP 409", status_code=409)

        def broken_dead_letter(event, approval_ref, **metadata):
            del event, approval_ref, metadata
            raise TransportError("dead-letter persistence was unavailable")

        captured, response = self.request(
            self.build(rejected, dead_letter_sink=broken_dead_letter)
        )

        self.assertEqual("503 Service Unavailable", captured["status"])
        outcomes = [record["outcome"] for record in self.log_records()]
        self.assertIn("dead_letter_failed", outcomes)
        self.assertIn("dropped_without_storage", outcomes)

    def test_unknown_failure_is_not_assumed_to_be_permanent(self):
        # An unrecognized error is not evidence that a retry is pointless, so
        # it must not be dead-lettered as if it were a contract violation.
        def broken(event, approval_ref):
            del event, approval_ref
            raise RuntimeError("synthetic persistence failure")

        captured, _ = self.request(
            self.build(broken, dead_letter_sink=self.dead_letter_sink)
        )

        self.assertEqual("503 Service Unavailable", captured["status"])
        self.assertEqual([], self.dead_letters)
        self.assertEqual("unknown", self.log_records()[0]["failure_class"])

    def test_failure_logs_never_contain_the_customer_utterance(self):
        def rejected(event, approval_ref):
            del event, approval_ref
            raise SupabaseWriteRejected("rejected with HTTP 422", status_code=422)

        self.request(self.build(rejected, dead_letter_sink=self.dead_letter_sink))

        joined = "\n".join(self.handler.lines)
        self.assertNotIn(UTTERANCE, joined)
        self.assertNotIn("bot-user-public-dummy-001", joined)
        self.assertNotIn("hmac:", joined)
        # The identifiers an operator actually needs are still present.
        self.assertIn("request-001", joined)


class _FakeResponse:
    def __init__(self, status=201):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def getcode(self):
        return self.status


class KakaoResponseDeadlineTests(unittest.TestCase):
    """One request can make two writes, and they share a single 5s deadline.

    Kakao resolves a skill call synchronously and discards a response that
    arrives late, so the case worth measuring is the worst one: the primary
    write burns its entire timeout before Supabase permanently rejects it, and
    the dead-letter write then burns its own. The two timeouts have to fit
    inside the deadline *together*, with room left over for the provider round
    trip and the handler's own work.

    The delay is simulated rather than slept. A test that really waited three
    seconds would measure the machine instead of the configuration, and would
    be the first one someone skips.
    """

    def setUp(self):
        self.spent_seconds = 0.0

    def _exhausting_opener(self, outcome):
        """An opener that consumes the whole socket timeout it was handed."""

        def opener(request, *, timeout):
            del request
            self.spent_seconds += timeout
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        return opener

    def _post_fixture(self, app):
        raw = FIXTURE.read_bytes()
        environ = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": "/api/kakao/skill",
            "CONTENT_LENGTH": str(len(raw)),
            "CONTENT_TYPE": "application/json",
            "HTTP_X_API_KEY": "expected-fixture-key",
            "HTTP_X_REQUEST_ID": "request-001",
            "wsgi.input": io.BytesIO(raw),
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = status

        body = b"".join(app(environ, start_response))
        return captured, json.loads(body)

    def test_worst_case_double_write_stays_inside_the_response_deadline(self):
        # 422 is a contract failure, which is the only path that makes a second
        # write. Both sinks are built with their production defaults, so this
        # measures the shipped configuration, not test-local numbers.
        rejected = HTTPError(
            "https://project-ref.supabase.co/rest/v1/kakao_cs_events_test",
            422,
            "unprocessable",
            {},
            None,
        )
        sink = SupabaseEventSink(
            "https://project-ref.supabase.co",
            "sb_secret_public_dummy",
            opener=self._exhausting_opener(rejected),
        )
        dead_letter_sink = SupabaseDeadLetterSink(
            "https://project-ref.supabase.co",
            "sb_secret_public_dummy",
            opener=self._exhausting_opener(_FakeResponse(201)),
        )
        app = KakaoSkillApplication(
            KakaoOpenBuilderAdapter(
                b"public-dummy-hmac",
                expected_api_key="expected-fixture-key",
            ),
            sink,
            approval_ref="APR-KAKAO-TEST-001",
            dead_letter_sink=dead_letter_sink,
            logger=_quiet_logger(),
        )

        captured, response = self._post_fixture(app)

        # Both writes ran: the event reached the dead-letter table, so the
        # acknowledgement is honest and the deadline still has to hold.
        self.assertEqual("200 OK", captured["status"])
        self.assertEqual("2.0", response["version"])
        self.assertEqual(PERSISTENCE_BUDGET_SECONDS, round(self.spent_seconds, 3))
        # Asserted against Kakao's deadline directly, not against the margin
        # constant. `budget + margin == deadline` is true by construction and
        # would still hold if someone shrank the margin to nothing; this
        # catches that, because storage may never claim more than 60% of the
        # deadline no matter how the constants are split.
        self.assertLessEqual(
            round(self.spent_seconds, 3),
            0.6 * KAKAO_RESPONSE_DEADLINE_SECONDS,
        )
        self.assertGreaterEqual(KAKAO_RESPONSE_SAFETY_MARGIN_SECONDS, 2.0)

    def test_availability_failure_answers_well_inside_the_deadline(self):
        # A timing-out primary write fails closed with one write, not two, so
        # it must leave even more headroom than the dead-letter path.
        sink = SupabaseEventSink(
            "https://project-ref.supabase.co",
            "sb_secret_public_dummy",
            opener=self._exhausting_opener(TimeoutError("socket timed out")),
        )
        app = KakaoSkillApplication(
            KakaoOpenBuilderAdapter(
                b"public-dummy-hmac",
                expected_api_key="expected-fixture-key",
            ),
            sink,
            approval_ref="APR-KAKAO-TEST-001",
            logger=_quiet_logger(),
        )

        captured, response = self._post_fixture(app)

        self.assertEqual("503 Service Unavailable", captured["status"])
        self.assertEqual({"error": "event_persistence_unavailable"}, response)
        self.assertLess(self.spent_seconds, PERSISTENCE_BUDGET_SECONDS)


if __name__ == "__main__":
    unittest.main()
