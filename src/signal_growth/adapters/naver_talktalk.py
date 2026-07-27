"""Naver TalkTalk event-only adapter.

The public Chat Bot API documents source IP ranges but no payload-bound
signature or historical backfill endpoint. This adapter therefore records weak
or no assurance and never exposes reply/send behavior.
"""

from __future__ import annotations

import hashlib
import ipaddress
from datetime import datetime
from typing import Any, Mapping

from ..channel_contracts import (
    Capability,
    CanonicalChannelEvent,
    CanonicalEventStatus,
    EventVerificationError,
    PayloadValidationError,
    ProviderCapabilities,
    RequestContext,
    VerificationAssurance,
    VerifiedEvent,
)
from ..connector_validation import (
    deterministic_event_id,
    hmac_customer_reference,
    isoformat_utc,
    opaque_reference,
    parse_json_body,
    raw_payload_ref,
    redact_text_with_metadata,
)
from .base import BaseChannelAdapter


_NAVER_WEBHOOK_NETWORKS = tuple(
    ipaddress.ip_network(value)
    for value in (
        "211.249.40.0/27",
        "211.249.68.0/27",
        "220.230.168.0/27",
        "103.6.173.0/27",
    )
)

_EVENT_TYPES = {
    "open": "conversation_opened",
    "send": "message_received",
    "echo": "message_sent",
    "leave": "conversation_closed",
    "friend": "other",
    "action": "other",
}


class NaverTalkTalkAdapter(BaseChannelAdapter):
    provider = "naver_talktalk"

    def __init__(
        self,
        customer_hmac_key: bytes,
        *,
        processing_basis_ref: str = "POL-PUBLIC-DUMMY",
        allow_unverified_fixture: bool = True,
    ) -> None:
        if not customer_hmac_key:
            raise ValueError("customer_hmac_key is required")
        self._customer_hmac_key = customer_hmac_key
        self._processing_basis_ref = processing_basis_ref
        self._allow_unverified_fixture = allow_unverified_fixture

    def capabilities(
        self,
        context: Mapping[str, Any] | None = None,
    ) -> ProviderCapabilities:
        del context
        return ProviderCapabilities(
            provider=self.provider,
            supported=frozenset(
                {
                    Capability.WEBHOOK_INGEST,
                    Capability.HEALTHCHECK,
                }
            ),
            unsupported_reasons={
                Capability.CONVERSATION_BACKFILL: (
                    "the public Chat Bot API does not document historical backfill"
                ),
                Capability.DELIVERY_STATUS: (
                    "the public event contract does not define final delivery/read state"
                ),
                Capability.RECONCILIATION: (
                    "backfill and delivery reconciliation are not publicly documented"
                ),
                Capability.REPLY_DRAFT: (
                    "reply drafting belongs to the approval workflow, not this adapter"
                ),
                Capability.REPLY_SEND: (
                    "Naver Send API is intentionally disabled in the read-only release"
                ),
            },
            disabled_by_policy=frozenset({Capability.REPLY_SEND}),
            source_refs={
                capability: "https://github.com/navertalk/chatbot-api"
                for capability in Capability
            },
        )

    def verify_event(
        self,
        raw_body: bytes,
        headers: Mapping[str, str],
        received_at: datetime | str,
        *,
        request_context: RequestContext | None = None,
    ) -> VerifiedEvent:
        del headers
        auth_verified = False
        assurance = VerificationAssurance.NONE
        context = request_context or RequestContext()

        if context.source_ip:
            try:
                address = ipaddress.ip_address(context.source_ip)
            except ValueError as exc:
                raise EventVerificationError("source IP is invalid") from exc
            if not any(address in network for network in _NAVER_WEBHOOK_NETWORKS):
                raise EventVerificationError(
                    "source IP is outside the documented Naver webhook ranges"
                )
            auth_verified = True
            assurance = VerificationAssurance.WEAK
        elif not self._allow_unverified_fixture:
            raise EventVerificationError(
                "Naver payload-bound authentication is unavailable; "
                "a trusted source IP is required outside fixture mode"
            )

        payload = parse_json_body(raw_body)
        event_name = payload.get("event")
        if event_name not in _EVENT_TYPES:
            raise PayloadValidationError("unsupported Naver event type")
        if not isinstance(payload.get("user"), str) or not payload["user"]:
            raise PayloadValidationError("Naver event requires a stable user value")

        return VerifiedEvent(
            provider=self.provider,
            raw_body=raw_body,
            payload=payload,
            received_at=isoformat_utc(received_at),
            auth_verified=auth_verified,
            verification_assurance=assurance,
        )

    def normalize_event(
        self,
        verified_event: VerifiedEvent,
    ) -> CanonicalChannelEvent:
        payload = verified_event.payload
        event_name = str(payload["event"])
        user = str(payload["user"])
        body_digest = hashlib.sha256(verified_event.raw_body).hexdigest()
        explicit_id = payload.get("eventId")

        if isinstance(explicit_id, str) and explicit_id:
            stable_fields = {"provider_event_id": explicit_id}
            provider_event_id = explicit_id
        else:
            # The public Naver contract does not expose an event ID. Hash the
            # complete immutable payload so reprocessing is stable. Two
            # genuinely distinct, byte-identical events remain indistinguishable
            # and must be reported as an event-only provider limitation.
            stable_fields = {"payload_sha256": body_digest}
            derived = deterministic_event_id(self.provider, stable_fields)
            provider_event_id = f"derived-{derived[4:20]}"

        event_id = deterministic_event_id(self.provider, stable_fields)
        customer_ref = hmac_customer_reference(
            self._customer_hmac_key,
            self.provider,
            user,
        )
        content = self._content(payload)
        attachments = self._attachments(payload)
        direction = "outbound" if event_name == "echo" else "inbound"
        redacted_content, privacy = redact_text_with_metadata(content)

        return CanonicalChannelEvent(
            event_id=event_id,
            provider=self.provider,
            provider_event_id=provider_event_id,
            channel="naver_talktalk",
            direction=direction,
            event_type=_EVENT_TYPES[event_name],
            occurred_at=verified_event.received_at,
            received_at=verified_event.received_at,
            conversation_ref=customer_ref,
            message_ref=(
                opaque_reference(provider_event_id)
                if event_name in {"send", "echo"}
                else None
            ),
            customer_ref_hmac=customer_ref,
            content_redacted=redacted_content,
            attachment_metadata=attachments,
            raw_payload_ref=raw_payload_ref(
                verified_event.raw_body,
                fixture=not verified_event.auth_verified,
            ),
            privacy=privacy,
            consent_or_processing_basis_ref=self._processing_basis_ref,
            idempotency_key=event_id,
            auth_verified=verified_event.auth_verified,
            verification_assurance=verified_event.verification_assurance,
            provider_status=event_name,
            canonical_status=CanonicalEventStatus.NORMALIZED,
        )

    @staticmethod
    def _content(payload: Mapping[str, Any]) -> str | None:
        text_content = payload.get("textContent")
        if isinstance(text_content, Mapping):
            text = text_content.get("text")
            if isinstance(text, str):
                return text
        return None

    @staticmethod
    def _attachments(
        payload: Mapping[str, Any],
    ) -> tuple[Mapping[str, Any], ...]:
        # The public event contract does not provide reliable byte size and
        # content digest fields required by the canonical attachment contract.
        return ()
