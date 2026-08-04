"""Restricted Supabase Data API sink for normalized Kakao CS events.

Failure taxonomy
----------------
A write can fail two ways, and conflating them loses events:

- **Availability** (timeout, connection error, HTTP 5xx, 429): the write may
  succeed later, so it raises `TransportError` and the caller fails closed so
  the provider retries.
- **Contract** (HTTP 4xx other than 429 — schema, constraint, authorization):
  the identical retry will fail forever, so it raises `SupabaseWriteRejected`
  and the caller diverts the event to the dead-letter table instead of
  discarding it.

`SupabaseWriteRejected` deliberately does **not** subclass `TransportError`;
transport succeeded and the server answered. Both share `ConnectorError`.

Timeout budget
--------------
Kakao Open Builder resolves a skill call synchronously: a response that arrives
after five seconds is discarded and the customer sees a failure. One request can
make *two* writes — the primary insert, then a dead-letter insert when the
primary is permanently rejected — so the two socket timeouts have to **sum** to
less than that deadline rather than each fit inside it. The timeouts here are
therefore derived from the deadline instead of chosen independently.

The margin is not decoration. It covers the work this module does not measure:
the Kakao-to-endpoint round trip, TLS setup, and the WSGI handler's own body
read, HMAC verification, and JSON encoding. Note also that `urlopen`'s `timeout`
bounds each blocking socket operation, not the call as a whole, so a server that
dribbles bytes can overrun the nominal value. Treat the numbers below as a
budget that keeps the common worst case safe, not as an enforced ceiling.
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from .channel_contracts import ConnectorError, TransportError


_TABLE_NAME = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_APPROVAL_REF = re.compile(r"^APR-[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
UrlOpener = Callable[..., Any]

# 4xx codes that still mean "try again later" rather than "this will never work".
_RETRYABLE_CLIENT_STATUS = frozenset({408, 425, 429})
_SUCCESS_STATUS = frozenset({200, 201, 204})
_USER_AGENT = "signal-to-growth/0.4"

# Kakao discards a skill response that arrives after this many seconds.
KAKAO_RESPONSE_DEADLINE_SECONDS = 5.0
# Reserved for the provider round trip, TLS, and in-process handler work.
KAKAO_RESPONSE_SAFETY_MARGIN_SECONDS = 2.0
# What is left for storage across *both* writes in a single request.
PERSISTENCE_BUDGET_SECONDS = round(
    KAKAO_RESPONSE_DEADLINE_SECONDS - KAKAO_RESPONSE_SAFETY_MARGIN_SECONDS, 3
)
# The primary write is the one that normally has to succeed, so it takes the
# larger share; the dead-letter write only runs after the primary answered.
DEFAULT_EVENT_TIMEOUT_SECONDS = round(PERSISTENCE_BUDGET_SECONDS * 0.6, 3)
DEFAULT_DEAD_LETTER_TIMEOUT_SECONDS = round(
    PERSISTENCE_BUDGET_SECONDS - DEFAULT_EVENT_TIMEOUT_SECONDS, 3
)
# The probe is not on the ingest path; it only has to stay well under a single
# health-check request, so it keeps its own small bound.
DEFAULT_HEALTH_PROBE_TIMEOUT_SECONDS = 1.0


class SupabaseWriteRejected(ConnectorError):
    """Supabase permanently rejected the write; retrying it cannot help."""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


def _validate_connection(
    project_url: str,
    secret_key: str,
    table: str,
    timeout_seconds: float,
    opener: UrlOpener,
) -> None:
    parsed_url = urlparse(project_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ValueError("Supabase project URL must use HTTPS")
    if not isinstance(secret_key, str) or not secret_key.strip():
        raise ValueError("Supabase secret key is required")
    if not _TABLE_NAME.fullmatch(table):
        raise ValueError("Supabase table name is invalid")
    if timeout_seconds <= 0 or timeout_seconds >= KAKAO_RESPONSE_DEADLINE_SECONDS:
        raise ValueError("Supabase timeout must be between 0 and 5 seconds")
    if not callable(opener):
        raise TypeError("opener must be callable")


def _classify_status(status: int, *, action: str) -> ConnectorError:
    """Map an HTTP status onto the availability/contract split."""
    if status >= 500 or status in _RETRYABLE_CLIENT_STATUS:
        return TransportError(f"Supabase {action} was unavailable (HTTP {status})")
    return SupabaseWriteRejected(
        f"Supabase {action} was rejected with HTTP {status}",
        status_code=status,
    )


def _require_approval_ref(approval_ref: str) -> str:
    if (
        not isinstance(approval_ref, str)
        or not _APPROVAL_REF.fullmatch(approval_ref.strip())
    ):
        raise ValueError(
            "approval_ref must be a non-secret reference beginning with APR-"
        )
    return approval_ref.strip()


def _post_json(
    opener: UrlOpener,
    endpoint: str,
    secret_key: str,
    body: bytes,
    timeout_seconds: float,
    *,
    action: str,
) -> None:
    """POST a JSON body and translate any failure into the taxonomy above."""
    request = Request(
        endpoint,
        data=body,
        method="POST",
        headers={
            "apikey": secret_key,
            "Content-Type": "application/json",
            "Prefer": "resolution=ignore-duplicates,return=minimal",
            "User-Agent": _USER_AGENT,
        },
    )
    try:
        response = opener(request, timeout=timeout_seconds)
        with response:
            status = response.getcode()
    except HTTPError as exc:
        raise _classify_status(exc.code, action=action) from exc
    except (TimeoutError, URLError) as exc:
        raise TransportError(f"Supabase {action} was unavailable") from exc

    if status not in _SUCCESS_STATUS:
        raise _classify_status(status, action=action)


class SupabaseEventSink:
    """Insert normalized events with server-only credentials and idempotency."""

    def __init__(
        self,
        project_url: str,
        secret_key: str,
        *,
        table: str = "kakao_cs_events_test",
        timeout_seconds: float = DEFAULT_EVENT_TIMEOUT_SECONDS,
        opener: UrlOpener = urlopen,
    ) -> None:
        _validate_connection(project_url, secret_key, table, timeout_seconds, opener)

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
        approval = _require_approval_ref(approval_ref)

        body = json.dumps(
            {
                "event_id": event_id,
                "provider": provider,
                "provider_event_id": provider_event_id,
                "received_at": received_at,
                "approval_ref": approval,
                "canonical_event": dict(event),
            },
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        _post_json(
            self._opener,
            self._endpoint,
            self._secret_key,
            body,
            self._timeout_seconds,
            action="event persistence",
        )


class SupabaseDeadLetterSink:
    """Persist events that Supabase permanently refused, so none are lost.

    The dead-letter row keeps the same redacted canonical event as the primary
    table plus the reason it could not be stored. It never records the
    exception message, only its class name and the HTTP status.
    """

    def __init__(
        self,
        project_url: str,
        secret_key: str,
        *,
        table: str = "kakao_cs_dead_letters_test",
        timeout_seconds: float = DEFAULT_DEAD_LETTER_TIMEOUT_SECONDS,
        opener: UrlOpener = urlopen,
    ) -> None:
        _validate_connection(project_url, secret_key, table, timeout_seconds, opener)

        query = urlencode({"on_conflict": "event_id"})
        self._endpoint = (
            f"{project_url.rstrip('/')}/rest/v1/{table}?{query}"
        )
        self._secret_key = secret_key.strip()
        self._timeout_seconds = timeout_seconds
        self._opener = opener

    def __call__(
        self,
        event: Mapping[str, Any],
        approval_ref: str,
        *,
        failure_class: str,
        error_type: str,
        status_code: int | None = None,
    ) -> None:
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
        approval = _require_approval_ref(approval_ref)
        if not isinstance(failure_class, str) or not failure_class.strip():
            raise ValueError("failure_class is required")
        if not isinstance(error_type, str) or not error_type.strip():
            raise ValueError("error_type is required")

        body = json.dumps(
            {
                "event_id": event_id,
                "provider": provider,
                "provider_event_id": provider_event_id,
                "received_at": received_at,
                "approval_ref": approval,
                "failure_class": failure_class.strip(),
                "error_type": error_type.strip(),
                "status_code": status_code,
                "canonical_event": dict(event),
            },
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        _post_json(
            self._opener,
            self._endpoint,
            self._secret_key,
            body,
            self._timeout_seconds,
            action="dead-letter persistence",
        )


class SupabaseHealthProbe:
    """Read-only reachability check for the events table, with a TTL cache.

    `configuration_ready()` only proves five environment variables are set.
    This proves the storage dependency actually answers. It issues a bounded
    `select ... limit=0` read — never a write — and caches the verdict for a
    few seconds so a health-check poller cannot amplify into the database.
    """

    def __init__(
        self,
        project_url: str,
        secret_key: str,
        *,
        table: str = "kakao_cs_events_test",
        timeout_seconds: float = DEFAULT_HEALTH_PROBE_TIMEOUT_SECONDS,
        ttl_seconds: float = 15.0,
        opener: UrlOpener = urlopen,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        _validate_connection(project_url, secret_key, table, timeout_seconds, opener)
        if ttl_seconds < 0:
            raise ValueError("ttl_seconds must not be negative")
        if not callable(clock):
            raise TypeError("clock must be callable")

        query = urlencode({"select": "event_id", "limit": "0"})
        self._endpoint = f"{project_url.rstrip('/')}/rest/v1/{table}?{query}"
        self._secret_key = secret_key.strip()
        self._timeout_seconds = timeout_seconds
        self._ttl_seconds = ttl_seconds
        self._opener = opener
        self._clock = clock
        self._cached: bool | None = None
        self._cache_expires_at = 0.0

    def __call__(self) -> bool:
        now = self._clock()
        if self._cached is not None and now < self._cache_expires_at:
            return self._cached

        reachable = self._probe()
        self._cached = reachable
        self._cache_expires_at = now + self._ttl_seconds
        return reachable

    def _probe(self) -> bool:
        request = Request(
            self._endpoint,
            method="GET",
            headers={
                "apikey": self._secret_key,
                "Accept": "application/json",
                "User-Agent": _USER_AGENT,
            },
        )
        try:
            response = self._opener(request, timeout=self._timeout_seconds)
            with response:
                return response.getcode() in {200, 206}
        except (HTTPError, TimeoutError, URLError, OSError):
            return False
