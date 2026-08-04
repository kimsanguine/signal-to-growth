"""Deployment-neutral WSGI application for a Kakao chatbot skill endpoint.

Durability of the ingest path
-----------------------------
A single `except Exception` around persistence answers every failure the same
way, which is wrong in both directions: it makes a permanently-rejected event
look retryable (the provider re-sends forever and the event is still lost), and
it hides which dependency broke. Persistence failures are therefore split:

- **Availability** (`TransportError`): the write may succeed later, so fail
  closed with 503 rather than acknowledging. The design intends the provider to
  re-send and no event to be lost — but that outcome depends on Kakao's retry
  behavior, which this repository has not observed against a live channel
  (`docs/PROGRESS.md`). Treat it as the intent, not a verified guarantee. No
  dead-letter row is written on this path.
- **Contract** (`ValueError` family, including `SupabaseWriteRejected`): an
  identical retry can never succeed. Divert the event to the dead-letter sink
  and acknowledge with 200 — the event *is* durably stored, just not in the
  primary table. Without a dead-letter sink configured, fall back to 503 so the
  event is never silently dropped.
- **Unknown**: treat as availability and fail closed. An unrecognized error is
  not evidence that a retry is pointless.
"""

from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime
from typing import Any, Callable, Iterable, Mapping

from .adapters import KakaoOpenBuilderAdapter
from .channel_contracts import (
    EventIdentityError,
    EventVerificationError,
    PayloadValidationError,
    TransportError,
)
from .observability import (
    FAILURE_AVAILABILITY,
    FAILURE_CONTRACT,
    FAILURE_UNKNOWN,
    StructuredLogger,
    error_type,
)


EventSink = Callable[[Mapping[str, Any], str], None]
DeadLetterSink = Callable[..., None]
StartResponse = Callable[[str, list[tuple[str, str]]], Any]
_APPROVAL_REF = re.compile(r"^APR-[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")


class KakaoSkillApplication:
    """Persist a sanitized event before returning a fixed Kakao skill response."""

    def __init__(
        self,
        adapter: KakaoOpenBuilderAdapter,
        event_sink: EventSink,
        *,
        approval_ref: str,
        response_text: str = "문의가 접수되었습니다. 확인 후 안내드리겠습니다.",
        path: str = "/api/kakao/skill",
        max_body_bytes: int = 1_048_576,
        dead_letter_sink: DeadLetterSink | None = None,
        logger: StructuredLogger | None = None,
    ) -> None:
        if not callable(event_sink):
            raise TypeError("event_sink must be callable")
        if dead_letter_sink is not None and not callable(dead_letter_sink):
            raise TypeError("dead_letter_sink must be callable")
        if (
            not isinstance(approval_ref, str)
            or not _APPROVAL_REF.fullmatch(approval_ref.strip())
        ):
            raise ValueError(
                "approval_ref must be a non-secret reference beginning with APR-"
            )
        if not isinstance(max_body_bytes, int) or max_body_bytes < 1:
            raise ValueError("max_body_bytes must be a positive integer")
        self._adapter = adapter
        self._event_sink = event_sink
        self._approval_ref = approval_ref.strip()
        self._response = adapter.build_skill_response(response_text)
        self._path = path
        self._max_body_bytes = max_body_bytes
        self._dead_letter_sink = dead_letter_sink
        self._logger = logger or StructuredLogger()

    def __call__(
        self,
        environ: Mapping[str, Any],
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        if environ.get("REQUEST_METHOD") != "POST":
            return self._json_response(
                start_response,
                "405 Method Not Allowed",
                {"error": "method_not_allowed"},
            )
        if environ.get("PATH_INFO") != self._path:
            return self._json_response(
                start_response,
                "404 Not Found",
                {"error": "not_found"},
            )

        started_at = time.perf_counter()
        try:
            raw_body = self._read_body(environ)
            event = self._adapter.ingest(
                raw_body,
                headers=self._headers(environ),
                received_at=datetime.now(UTC),
            )
        except EventVerificationError:
            return self._json_response(
                start_response,
                "401 Unauthorized",
                {"error": "request_verification_failed"},
            )
        except (EventIdentityError, PayloadValidationError, ValueError):
            return self._json_response(
                start_response,
                "400 Bad Request",
                {"error": "invalid_skill_request"},
            )

        payload = event.to_dict()
        try:
            self._event_sink(payload, self._approval_ref)
        except TransportError as exc:
            # Availability: the same write may succeed later, so let Kakao retry.
            self._logger.ingest_failure(
                failure_class=FAILURE_AVAILABILITY,
                error=exc,
                event=payload,
                approval_ref=self._approval_ref,
                outcome="retry_expected",
                dead_lettered=False,
            )
            return self._json_response(
                start_response,
                "503 Service Unavailable",
                {"error": "event_persistence_unavailable"},
            )
        except ValueError as exc:
            # Contract: retrying is pointless, so preserve the event elsewhere.
            return self._handle_contract_failure(start_response, payload, exc)
        except Exception as exc:  # noqa: BLE001 - unknown failures fail closed
            self._logger.ingest_failure(
                failure_class=FAILURE_UNKNOWN,
                error=exc,
                event=payload,
                approval_ref=self._approval_ref,
                outcome="retry_expected",
                dead_lettered=False,
            )
            return self._json_response(
                start_response,
                "503 Service Unavailable",
                {"error": "event_persistence_failed"},
            )

        # Success is logged too. With failure-only logging, a healthy endpoint
        # and a webhook that stopped delivering look identical: both are silent.
        self._logger.ingest_accepted(
            event=payload,
            approval_ref=self._approval_ref,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 3),
        )
        return self._json_response(
            start_response,
            "200 OK",
            self._response,
        )

    def _handle_contract_failure(
        self,
        start_response: StartResponse,
        payload: Mapping[str, Any],
        error: ValueError,
    ) -> list[bytes]:
        """Dead-letter a permanently-rejected event, or fail closed if it cannot."""
        status_code = getattr(error, "status_code", None)
        dead_lettered = self._dead_letter(payload, error, status_code)
        self._logger.ingest_failure(
            failure_class=FAILURE_CONTRACT,
            error=error,
            event=payload,
            approval_ref=self._approval_ref,
            outcome="dead_lettered" if dead_lettered else "dropped_without_storage",
            dead_lettered=dead_lettered,
            status_code=status_code if isinstance(status_code, int) else None,
        )
        if not dead_lettered:
            return self._json_response(
                start_response,
                "503 Service Unavailable",
                {"error": "event_persistence_failed"},
            )
        # The event is durably stored in the dead-letter table, so an
        # acknowledgement is honest and stops a retry loop that cannot succeed.
        return self._json_response(start_response, "200 OK", self._response)

    def _dead_letter(
        self,
        payload: Mapping[str, Any],
        error: ValueError,
        status_code: Any,
    ) -> bool:
        if self._dead_letter_sink is None:
            return False
        try:
            self._dead_letter_sink(
                payload,
                self._approval_ref,
                failure_class=FAILURE_CONTRACT,
                error_type=error_type(error),
                status_code=status_code if isinstance(status_code, int) else None,
            )
        except Exception as exc:  # noqa: BLE001 - the caller then fails closed
            self._logger.ingest_failure(
                failure_class=FAILURE_AVAILABILITY,
                error=exc,
                event=payload,
                approval_ref=self._approval_ref,
                outcome="dead_letter_failed",
                dead_lettered=False,
            )
            return False
        return True

    def _read_body(self, environ: Mapping[str, Any]) -> bytes:
        value = environ.get("CONTENT_LENGTH", "")
        try:
            length = int(value)
        except (TypeError, ValueError) as exc:
            raise PayloadValidationError("Content-Length is required") from exc
        if length < 1 or length > self._max_body_bytes:
            raise PayloadValidationError("request body size is outside the limit")
        stream = environ.get("wsgi.input")
        if stream is None or not hasattr(stream, "read"):
            raise PayloadValidationError("wsgi.input is required")
        body = stream.read(length)
        if not isinstance(body, bytes) or len(body) != length:
            raise PayloadValidationError("request body is incomplete")
        return body

    @staticmethod
    def _headers(environ: Mapping[str, Any]) -> dict[str, str]:
        headers: dict[str, str] = {}
        for key, value in environ.items():
            if not key.startswith("HTTP_") or not isinstance(value, str):
                continue
            name = key[5:].replace("_", "-")
            headers[name] = value
        return headers

    @staticmethod
    def _json_response(
        start_response: StartResponse,
        status: str,
        payload: Mapping[str, Any],
    ) -> list[bytes]:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        start_response(
            status,
            [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
            ],
        )
        return [body]
