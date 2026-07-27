"""Provider-neutral contracts for customer-channel connectors.

The contracts deliberately contain no provider credentials and make unsupported
capabilities explicit. Provider adapters may return these dataclasses or their
``to_dict`` representations to schema-facing code.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping


class ConnectorMode(str, Enum):
    READ_ONLY = "read_only"
    DRAFT_ONLY = "draft_only"
    APPROVED_WRITE = "approved_write"


class Capability(str, Enum):
    WEBHOOK_INGEST = "webhook_ingest"
    SKILL_REQUEST_INGEST = "skill_request_ingest"
    CONVERSATION_BACKFILL = "conversation_backfill"
    DELIVERY_STATUS = "delivery_status"
    RECONCILIATION = "reconciliation"
    REPLY_DRAFT = "reply_draft"
    REPLY_SEND = "reply_send"
    HEALTHCHECK = "healthcheck"


class VerificationAssurance(str, Enum):
    STRONG = "strong"
    MEDIUM = "medium"
    WEAK = "weak"
    NONE = "none"


class CanonicalStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    APPROVED = "approved"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class CanonicalEventStatus(str, Enum):
    RECEIVED = "received"
    NORMALIZED = "normalized"
    IGNORED = "ignored"
    DEAD_LETTER = "dead_letter"
    UNKNOWN = "unknown"


class ConnectorError(ValueError):
    """Base class for deterministic connector failures."""


class PayloadValidationError(ConnectorError):
    """The provider payload cannot be normalized safely."""


class EventIdentityError(ConnectorError):
    """The event does not have sufficient stable identity fields."""


class EventVerificationError(ConnectorError):
    """The inbound request did not pass the configured verification policy."""


class TransportError(ConnectorError):
    """An injected transport returned an unusable response."""


class UnsupportedCapability(ConnectorError):
    """Raised instead of silently returning an empty success."""

    def __init__(self, provider: str, capability: Capability | str, reason: str) -> None:
        self.provider = provider
        self.capability = (
            capability.value if isinstance(capability, Capability) else str(capability)
        )
        self.reason = reason
        super().__init__(
            f"{provider} does not support {self.capability}: {reason}"
        )


@dataclass(frozen=True)
class RequestContext:
    """Trusted ingress metadata supplied by the hosting layer.

    ``source_ip`` must be the socket peer or a value produced by a configured
    trusted proxy. Adapters never infer it from ``X-Forwarded-For``.
    """

    source_ip: str | None = None
    query: Mapping[str, str] = field(default_factory=dict)
    environment: str = "fixture"


@dataclass(frozen=True)
class ProviderCapabilities:
    provider: str
    supported: frozenset[Capability]
    unsupported_reasons: Mapping[Capability, str] = field(default_factory=dict)
    disabled_by_policy: frozenset[Capability] = field(default_factory=frozenset)
    source_refs: Mapping[Capability, str] = field(default_factory=dict)

    def supports(self, capability: Capability | str) -> bool:
        requested = (
            capability
            if isinstance(capability, Capability)
            else Capability(capability)
        )
        return requested in self.supported

    def require(self, capability: Capability | str) -> None:
        requested = (
            capability
            if isinstance(capability, Capability)
            else Capability(capability)
        )
        if requested in self.supported:
            return
        reason = self.unsupported_reasons.get(
            requested,
            "capability is not implemented by this adapter",
        )
        raise UnsupportedCapability(self.provider, requested, reason)

    def to_dict(self) -> dict[str, Any]:
        all_capabilities = (
            set(self.supported)
            | set(self.unsupported_reasons)
            | set(self.disabled_by_policy)
        )
        return {
            "provider": self.provider,
            "capabilities": [
                {
                    "name": capability.value,
                    "support": (
                        "supported"
                        if capability in self.supported
                        else (
                            "disabled_by_policy"
                            if capability in self.disabled_by_policy
                            else "unsupported"
                        )
                    ),
                    "access_mode": (
                        "draft_only"
                        if capability
                        in {Capability.REPLY_DRAFT, Capability.REPLY_SEND}
                        else "read_only"
                    ),
                    "source_ref": self.source_refs.get(
                        capability,
                        f"adapter://{self.provider}/{capability.value}",
                    ),
                }
                for capability in sorted(
                    all_capabilities,
                    key=lambda item: item.value,
                )
            ],
        }


@dataclass(frozen=True)
class VerifiedEvent:
    provider: str
    raw_body: bytes
    payload: Mapping[str, Any]
    received_at: str
    auth_verified: bool
    verification_assurance: VerificationAssurance
    request_id: str | None = None


@dataclass(frozen=True)
class CanonicalChannelEvent:
    event_id: str
    provider: str
    provider_event_id: str
    channel: str
    direction: str
    event_type: str
    occurred_at: str
    received_at: str
    conversation_ref: str
    message_ref: str | None
    customer_ref_hmac: str
    content_redacted: str
    attachment_metadata: tuple[Mapping[str, Any], ...]
    raw_payload_ref: str | None
    privacy: Mapping[str, Any]
    consent_or_processing_basis_ref: str
    idempotency_key: str
    auth_verified: bool
    verification_assurance: VerificationAssurance
    provider_status: str
    canonical_status: CanonicalEventStatus
    source_evidence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["verification_assurance"] = self.verification_assurance.value
        value["canonical_status"] = self.canonical_status.value
        value["attachment_metadata"] = [
            dict(item) for item in self.attachment_metadata
        ]
        value["source_evidence_ids"] = list(self.source_evidence_ids)
        return value


@dataclass(frozen=True)
class CanonicalDeliveryEvent:
    delivery_event_id: str
    attempt_id: str
    provider: str
    product: str
    channel: str
    occurred_at: str
    received_at: str
    status_observed_at: str
    provider_message_ref: str | None
    provider_status: str | None
    canonical_status: CanonicalStatus
    attempt_kind: str
    parent_attempt_ref: str | None
    transport: str
    fallback_applied: bool
    idempotency_key: str
    raw_payload_ref: str | None
    auth_verified: bool
    verification_assurance: VerificationAssurance
    source_evidence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["canonical_status"] = self.canonical_status.value
        value["verification_assurance"] = self.verification_assurance.value
        value["source_evidence_ids"] = list(self.source_evidence_ids)
        return value


@dataclass(frozen=True)
class HttpRequest:
    """A credential-free request description for an injected transport."""

    method: str
    url: str
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes | None = None
    credential_ref: str | None = None


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)
    authenticated: bool = False


@dataclass(frozen=True)
class BackfillPage:
    request: HttpRequest
    events: tuple[CanonicalChannelEvent, ...]
    next_cursor: str | None
