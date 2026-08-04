from __future__ import annotations

import json
import logging
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.observability import (
    FAILURE_CONTRACT,
    StructuredLogger,
    error_type,
    safe_event_descriptor,
)


UTTERANCE = "초기 설정 중 연결 단계에서 계속 멈춰요."
EVENT = {
    "event_id": "CSE-public-dummy-001",
    "provider": "kakao_openbuilder",
    "provider_event_id": "request-public-dummy-001",
    "received_at": "2026-07-26T00:00:00Z",
    "content_redacted": UTTERANCE,
    "customer_ref_hmac": "hmac:0123456789abcdef",
    "conversation_ref": "ref:0123456789abcdef",
}


class CapturingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


class SafeEventDescriptorTests(unittest.TestCase):
    def test_keeps_only_non_sensitive_identifiers(self) -> None:
        descriptor = safe_event_descriptor(EVENT)

        self.assertEqual(
            {
                "event_id": "CSE-public-dummy-001",
                "provider": "kakao_openbuilder",
                "provider_event_id": "request-public-dummy-001",
                "received_at": "2026-07-26T00:00:00Z",
            },
            descriptor,
        )

    def test_drops_message_content_and_customer_references(self) -> None:
        # The redacted body is still customer speech, and the hmac is still a
        # stable per-customer identifier. Neither belongs in an operations log.
        descriptor = safe_event_descriptor(EVENT)

        self.assertNotIn("content_redacted", descriptor)
        self.assertNotIn("customer_ref_hmac", descriptor)
        self.assertNotIn("conversation_ref", descriptor)

    def test_tolerates_a_partial_event(self) -> None:
        self.assertEqual(
            {"provider": "kakao_openbuilder"},
            safe_event_descriptor({"provider": "kakao_openbuilder"}),
        )


class StructuredLoggerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.handler = CapturingHandler()
        self.logger = logging.getLogger("signal_growth.test.ingest")
        self.logger.handlers = [self.handler]
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        self.structured = StructuredLogger(self.logger)

    def test_emits_one_json_object_per_line(self) -> None:
        self.structured.emit("ingest_failure", outcome="retry_expected")

        record = json.loads(self.handler.lines[0])
        self.assertEqual("ingest_failure", record["event"])
        self.assertEqual("retry_expected", record["outcome"])

    def test_refuses_field_names_outside_the_allowlist(self) -> None:
        # This is the guarantee: a contributor cannot casually log the body,
        # because the logger rejects the field name rather than trusting them.
        with self.assertRaisesRegex(ValueError, "content_redacted"):
            self.structured.emit("ingest_failure", content_redacted=UTTERANCE)

        self.assertEqual([], self.handler.lines)

    def test_ingest_failure_never_writes_customer_content(self) -> None:
        self.structured.ingest_failure(
            failure_class=FAILURE_CONTRACT,
            error=ValueError("row violates check constraint on 010-1234-5678"),
            event=EVENT,
            approval_ref="APR-KAKAO-TEST-001",
            outcome="dead_lettered",
            dead_lettered=True,
            status_code=422,
        )

        line = self.handler.lines[0]
        self.assertNotIn(UTTERANCE, line)
        self.assertNotIn("hmac:0123456789abcdef", line)
        # Exception messages are withheld too: a driver may embed a payload.
        self.assertNotIn("010-1234-5678", line)

        record = json.loads(line)
        self.assertEqual("contract", record["failure_class"])
        self.assertEqual("ValueError", record["error_type"])
        self.assertEqual("dead_lettered", record["outcome"])
        self.assertTrue(record["dead_lettered"])
        self.assertEqual(422, record["status_code"])
        self.assertEqual("CSE-public-dummy-001", record["event_id"])

    def test_ingest_accepted_records_the_success_path(self) -> None:
        # Without a success line, "healthy" and "webhook disconnected" both
        # produce an empty log, so this line is what makes them distinguishable.
        self.structured.ingest_accepted(
            event=EVENT,
            approval_ref="APR-KAKAO-TEST-001",
            duration_ms=12.5,
        )

        record = json.loads(self.handler.lines[0])
        self.assertEqual("ingest_accepted", record["event"])
        self.assertEqual("persisted", record["outcome"])
        self.assertEqual("CSE-public-dummy-001", record["event_id"])
        self.assertEqual("kakao_openbuilder", record["provider"])
        self.assertEqual(12.5, record["duration_ms"])

    def test_ingest_accepted_never_writes_customer_content(self) -> None:
        self.structured.ingest_accepted(
            event=EVENT,
            approval_ref="APR-KAKAO-TEST-001",
            duration_ms=1.0,
        )

        line = self.handler.lines[0]
        self.assertNotIn(UTTERANCE, line)
        self.assertNotIn("hmac:0123456789abcdef", line)
        self.assertNotIn("ref:0123456789abcdef", line)

    def test_error_type_reports_the_class_not_the_message(self) -> None:
        self.assertEqual("KeyError", error_type(KeyError("secret-detail")))


if __name__ == "__main__":
    unittest.main()
