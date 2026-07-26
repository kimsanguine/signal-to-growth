"""Deployment-neutral WSGI application for a Kakao chatbot skill endpoint."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Callable, Iterable, Mapping

from .adapters import KakaoOpenBuilderAdapter
from .channel_contracts import (
    EventIdentityError,
    EventVerificationError,
    PayloadValidationError,
)


EventSink = Callable[[Mapping[str, Any]], None]
StartResponse = Callable[[str, list[tuple[str, str]]], Any]


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
    ) -> None:
        if not callable(event_sink):
            raise TypeError("event_sink must be callable")
        if not isinstance(approval_ref, str) or not approval_ref.strip():
            raise ValueError("approval_ref is required for the test response")
        if not isinstance(max_body_bytes, int) or max_body_bytes < 1:
            raise ValueError("max_body_bytes must be a positive integer")
        self._adapter = adapter
        self._event_sink = event_sink
        self._approval_ref = approval_ref.strip()
        self._response = adapter.build_skill_response(response_text)
        self._path = path
        self._max_body_bytes = max_body_bytes

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

        try:
            self._event_sink(event.to_dict())
        except Exception:
            return self._json_response(
                start_response,
                "503 Service Unavailable",
                {"error": "event_persistence_failed"},
            )

        return self._json_response(
            start_response,
            "200 OK",
            self._response,
        )

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
