"""Restricted Supabase Data API sink for normalized Kakao CS events."""

from __future__ import annotations

import json
import re
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from .channel_contracts import TransportError


_TABLE_NAME = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_APPROVAL_REF = re.compile(r"^APR-[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
UrlOpener = Callable[..., Any]


class SupabaseEventSink:
    """Insert normalized events with server-only credentials and idempotency."""

    def __init__(
        self,
        project_url: str,
        secret_key: str,
        *,
        table: str = "kakao_cs_events_test",
        timeout_seconds: float = 2.0,
        opener: UrlOpener = urlopen,
    ) -> None:
        parsed_url = urlparse(project_url)
        if parsed_url.scheme != "https" or not parsed_url.netloc:
            raise ValueError("Supabase project URL must use HTTPS")
        if not isinstance(secret_key, str) or not secret_key.strip():
            raise ValueError("Supabase secret key is required")
        if not _TABLE_NAME.fullmatch(table):
            raise ValueError("Supabase table name is invalid")
        if timeout_seconds <= 0 or timeout_seconds >= 5:
            raise ValueError("Supabase timeout must be between 0 and 5 seconds")
        if not callable(opener):
            raise TypeError("opener must be callable")

        query = urlencode({"on_conflict": "event_id"})
        self._endpoint = (
            f"{project_url.rstrip('/')}/rest/v1/{table}?{query}"
        )
        self._secret_key = secret_key.strip()
        self._timeout_seconds = timeout_seconds
        self._opener = opener

    def __call__(self, event: Mapping[str, Any], approval_ref: str) -> None:
        event_id = event.get("event_id")
        provider = event.get("provider")
        provider_event_id = event.get("provider_event_id")
        received_at = event.get("received_at")
        if not all(
            isinstance(value, str) and value
            for value in (event_id, provider, provider_event_id, received_at)
        ):
            raise ValueError(
                "event_id, provider, provider_event_id, and received_at are required"
            )
        if (
            not isinstance(approval_ref, str)
            or not _APPROVAL_REF.fullmatch(approval_ref.strip())
        ):
            raise ValueError(
                "approval_ref must be a non-secret reference beginning with APR-"
            )

        body = json.dumps(
            {
                "event_id": event_id,
                "provider": provider,
                "provider_event_id": provider_event_id,
                "received_at": received_at,
                "approval_ref": approval_ref.strip(),
                "canonical_event": dict(event),
            },
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        request = Request(
            self._endpoint,
            data=body,
            method="POST",
            headers={
                "apikey": self._secret_key,
                "Content-Type": "application/json",
                "Prefer": "resolution=ignore-duplicates,return=minimal",
                "User-Agent": "signal-to-growth/0.2",
            },
        )

        try:
            response = self._opener(
                request,
                timeout=self._timeout_seconds,
            )
            with response:
                status = response.getcode()
        except HTTPError as exc:
            raise TransportError(
                f"Supabase event persistence failed with HTTP {exc.code}"
            ) from exc
        except (TimeoutError, URLError) as exc:
            raise TransportError("Supabase event persistence was unavailable") from exc

        if status not in {200, 201, 204}:
            raise TransportError(
                f"Supabase event persistence returned HTTP {status}"
            )
