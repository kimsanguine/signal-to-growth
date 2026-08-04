"""Structured, privacy-preserving logging for the customer-signal ingest path.

The ingest path touches three things that must never reach a log file: raw
customer utterances, provider-side account identifiers, and server-only
credentials. A log line is the easiest place to leak all three, so this module
refuses free-form content instead of trusting each call site to remember.

Two guarantees make that refusal enforceable rather than aspirational:

1. `safe_event_descriptor` copies an explicit allowlist of non-sensitive event
   fields and drops everything else, including the message body.
2. `StructuredLogger.emit` rejects any field name outside `LOGGABLE_FIELDS`.
   A contributor who adds `content=event["content_redacted"]` gets a loud
   `ValueError` in the test suite instead of a quiet privacy regression.

Exception *messages* are never logged either. Only the exception class name
travels, because a third-party error string may embed a request body or a URL
with an embedded key. Anything an operator needs for recovery is expressed as
a bounded field: `failure_class`, `status_code`, `dead_lettered`.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Mapping

LOGGER_NAME = "signal_growth.ingest"

# Event fields safe to log. `content_redacted` is deliberately excluded: it is
# redacted, not anonymized, so it stays out of operational logs.
SAFE_EVENT_FIELDS = (
    "event_id",
    "provider",
    "provider_event_id",
    "received_at",
)

# Failure classes. The split drives both the HTTP status and the recovery path.
FAILURE_CONTRACT = "contract"
FAILURE_AVAILABILITY = "availability"
FAILURE_UNKNOWN = "unknown"

LOGGABLE_FIELDS = frozenset(
    {
        "approval_ref",
        "dead_lettered",
        "error_type",
        "failure_class",
        "outcome",
        "status_code",
        *SAFE_EVENT_FIELDS,
    }
)


def safe_event_descriptor(event: Mapping[str, Any]) -> dict[str, str]:
    """Return only the allowlisted, non-sensitive identifiers from an event."""
    descriptor: dict[str, str] = {}
    for field in SAFE_EVENT_FIELDS:
        value = event.get(field)
        if isinstance(value, str) and value:
            descriptor[field] = value
    return descriptor


def error_type(error: BaseException) -> str:
    """Return the exception class name, never its message."""
    return type(error).__name__


class StructuredLogger:
    """Emit one JSON object per line through the standard logging module."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger(LOGGER_NAME)

    def emit(
        self,
        event_name: str,
        *,
        level: int = logging.INFO,
        **fields: Any,
    ) -> None:
        unknown = sorted(set(fields) - LOGGABLE_FIELDS)
        if unknown:
            raise ValueError(
                "refusing to log non-allowlisted fields: " + ", ".join(unknown)
            )
        record: dict[str, Any] = {"event": event_name}
        record.update({key: value for key, value in fields.items() if value is not None})
        self._logger.log(
            level,
            json.dumps(
                record,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )

    def ingest_failure(
        self,
        *,
        failure_class: str,
        error: BaseException,
        event: Mapping[str, Any],
        approval_ref: str,
        outcome: str,
        dead_lettered: bool | None = None,
        status_code: int | None = None,
    ) -> None:
        """Record an ingest-path failure with recovery-relevant fields only."""
        self.emit(
            "ingest_failure",
            level=logging.ERROR,
            failure_class=failure_class,
            error_type=error_type(error),
            outcome=outcome,
            approval_ref=approval_ref,
            dead_lettered=dead_lettered,
            status_code=status_code,
            **safe_event_descriptor(event),
        )
