"""In-memory connector state, dedupe, and non-regressing delivery projection."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from .channel_contracts import (
    CanonicalChannelEvent,
    CanonicalDeliveryEvent,
    CanonicalStatus,
)
from .connector_validation import isoformat_utc


_ALLOWED_TRANSITIONS: dict[CanonicalStatus, frozenset[CanonicalStatus]] = {
    CanonicalStatus.DRAFT: frozenset(
        {
            CanonicalStatus.VALIDATED,
            CanonicalStatus.CANCELLED,
            CanonicalStatus.EXPIRED,
        }
    ),
    CanonicalStatus.VALIDATED: frozenset(
        {
            CanonicalStatus.APPROVED,
            CanonicalStatus.SUBMITTED,
            CanonicalStatus.CANCELLED,
            CanonicalStatus.EXPIRED,
        }
    ),
    CanonicalStatus.APPROVED: frozenset(
        {
            CanonicalStatus.SUBMITTED,
            CanonicalStatus.CANCELLED,
            CanonicalStatus.EXPIRED,
        }
    ),
    CanonicalStatus.SUBMITTED: frozenset(
        {
            CanonicalStatus.ACCEPTED,
            CanonicalStatus.QUEUED,
            CanonicalStatus.SENT,
            CanonicalStatus.DELIVERED,
            CanonicalStatus.FAILED,
            CanonicalStatus.CANCELLED,
            CanonicalStatus.EXPIRED,
        }
    ),
    CanonicalStatus.ACCEPTED: frozenset(
        {
            CanonicalStatus.QUEUED,
            CanonicalStatus.SENT,
            CanonicalStatus.DELIVERED,
            CanonicalStatus.FAILED,
            CanonicalStatus.CANCELLED,
            CanonicalStatus.EXPIRED,
        }
    ),
    CanonicalStatus.QUEUED: frozenset(
        {
            CanonicalStatus.SENT,
            CanonicalStatus.DELIVERED,
            CanonicalStatus.FAILED,
            CanonicalStatus.CANCELLED,
            CanonicalStatus.EXPIRED,
        }
    ),
    CanonicalStatus.SENT: frozenset(
        {
            CanonicalStatus.DELIVERED,
            CanonicalStatus.FAILED,
            CanonicalStatus.EXPIRED,
        }
    ),
    CanonicalStatus.DELIVERED: frozenset({CanonicalStatus.READ}),
    CanonicalStatus.READ: frozenset(),
    CanonicalStatus.FAILED: frozenset(),
    CanonicalStatus.CANCELLED: frozenset(),
    CanonicalStatus.EXPIRED: frozenset(),
    CanonicalStatus.UNKNOWN: frozenset(
        status for status in CanonicalStatus if status is not CanonicalStatus.UNKNOWN
    ),
}


@dataclass
class ConnectorState:
    connection_id: str
    provider: str
    mode: str
    external_write_enabled: bool = False
    cursor: str | None = None
    last_webhook_at: str | None = None
    last_backfill_at: str | None = None
    last_reconciled_at: str | None = None
    ingested_count: int = 0
    duplicate_count: int = 0
    dead_letter_count: int = 0
    blocked_reasons: list[str] = field(default_factory=list)
    health: str = "unknown"
    verification_level: str = "none"
    _seen_event_ids: set[str] = field(default_factory=set, repr=False)

    def __post_init__(self) -> None:
        if self.mode in {"read_only", "draft_only"} and self.external_write_enabled:
            raise ValueError(f"{self.mode} connector state cannot enable external writes")
        if self.mode == "approved_write" and not self.external_write_enabled:
            raise ValueError("approved_write connector state must enable external writes")

    def record_event(self, event: CanonicalChannelEvent) -> bool:
        """Return ``True`` only for the first occurrence of an event ID."""
        if event.event_id in self._seen_event_ids:
            self.duplicate_count += 1
            return False
        self._seen_event_ids.add(event.event_id)
        self.ingested_count += 1
        self.last_webhook_at = event.received_at
        return True

    def record_dead_letter(self, reason: str) -> None:
        self.dead_letter_count += 1
        if reason not in self.blocked_reasons:
            self.blocked_reasons.append(reason)

    def record_backfill(self, cursor: str | None, observed_at: datetime | str) -> None:
        self.cursor = cursor
        self.last_backfill_at = isoformat_utc(observed_at)

    def record_reconciliation(self, observed_at: datetime | str) -> None:
        self.last_reconciled_at = isoformat_utc(observed_at)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("_seen_event_ids", None)
        return value


@dataclass(frozen=True)
class DeliveryAttemptKey:
    attempt_id: str
    transport: str


@dataclass
class DeliveryAttemptState:
    key: DeliveryAttemptKey
    current_status: CanonicalStatus
    status_at: str
    provider: str
    provider_message_refs: list[str] = field(default_factory=list)
    applied_delivery_event_ids: list[str] = field(default_factory=list)
    ignored_delivery_event_ids: list[str] = field(default_factory=list)
    parent_attempt_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_id": self.key.attempt_id,
            "transport": self.key.transport,
            "current_status": self.current_status.value,
            "status_at": self.status_at,
            "provider": self.provider,
            "provider_message_refs": list(self.provider_message_refs),
            "applied_delivery_event_ids": list(self.applied_delivery_event_ids),
            "ignored_delivery_event_ids": list(self.ignored_delivery_event_ids),
            "parent_attempt_ref": self.parent_attempt_ref,
        }


@dataclass(frozen=True)
class TransitionResult:
    applied: bool
    reason: str
    state: DeliveryAttemptState


class DeliveryStateProjector:
    """Project delivery events without merging fallback attempts or regressing."""

    def __init__(self) -> None:
        self._attempts: dict[DeliveryAttemptKey, DeliveryAttemptState] = {}
        self._seen_event_ids: set[str] = set()

    def project(self, event: CanonicalDeliveryEvent) -> TransitionResult:
        observed_at = isoformat_utc(event.status_observed_at)
        key = DeliveryAttemptKey(
            attempt_id=event.attempt_id,
            transport=event.transport,
        )

        existing = self._attempts.get(key)
        if event.delivery_event_id in self._seen_event_ids:
            if existing is None:
                raise RuntimeError("dedupe state is inconsistent")
            return TransitionResult(False, "duplicate_event", existing)

        self._seen_event_ids.add(event.delivery_event_id)
        if existing is None:
            state = DeliveryAttemptState(
                key=key,
                current_status=event.canonical_status,
                status_at=observed_at,
                provider=event.provider,
                provider_message_refs=(
                    [event.provider_message_ref]
                    if event.provider_message_ref is not None
                    else []
                ),
                applied_delivery_event_ids=[event.delivery_event_id],
                parent_attempt_ref=event.parent_attempt_ref,
            )
            self._attempts[key] = state
            return TransitionResult(True, "initial_state", state)

        if (
            event.provider_message_ref is not None
            and event.provider_message_ref not in existing.provider_message_refs
        ):
            existing.provider_message_refs.append(event.provider_message_ref)

        if event.canonical_status == existing.current_status:
            existing.ignored_delivery_event_ids.append(event.delivery_event_id)
            return TransitionResult(False, "same_status", existing)

        if _as_datetime(observed_at) < _as_datetime(existing.status_at):
            existing.ignored_delivery_event_ids.append(event.delivery_event_id)
            return TransitionResult(False, "stale_event", existing)

        allowed = _ALLOWED_TRANSITIONS[existing.current_status]
        if event.canonical_status not in allowed:
            existing.ignored_delivery_event_ids.append(event.delivery_event_id)
            return TransitionResult(False, "non_regressing_transition", existing)

        existing.current_status = event.canonical_status
        existing.status_at = observed_at
        existing.applied_delivery_event_ids.append(event.delivery_event_id)
        return TransitionResult(True, "advanced", existing)

    def get(
        self,
        attempt_id: str,
        transport: str,
    ) -> DeliveryAttemptState | None:
        return self._attempts.get(
            DeliveryAttemptKey(
                attempt_id=attempt_id,
                transport=transport,
            )
        )

    def attempts(self) -> tuple[DeliveryAttemptState, ...]:
        return tuple(
            self._attempts[key]
            for key in sorted(
                self._attempts,
                key=lambda item: (
                    item.attempt_id,
                    item.transport,
                ),
            )
        )


def _as_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def is_allowed_delivery_transition(
    current: CanonicalStatus | str,
    candidate: CanonicalStatus | str,
) -> bool:
    current_status = (
        current if isinstance(current, CanonicalStatus) else CanonicalStatus(current)
    )
    candidate_status = (
        candidate
        if isinstance(candidate, CanonicalStatus)
        else CanonicalStatus(candidate)
    )
    return (
        current_status == candidate_status
        or candidate_status in _ALLOWED_TRANSITIONS[current_status]
    )
