"""Kakao Channel chatbot skill-request adapter.

This adapter targets Kakao i Open Builder skill requests. It is not a
ConsultTalk, AlimTalk, or native Channel 1:1 chat adapter.
"""

from __future__ import annotations

import hmac
from datetime import datetime
from typing import Any, Mapping

from ..channel_contracts import (
    Capability,
    CanonicalChannelEvent,
    CanonicalEventStatus,
    EventIdentityError,
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
from ..policy import ConnectorPolicy, default_connector_policy
from .base import BaseChannelAdapter


_SOURCE_URL = (
    "https://kakaobusiness.gitbook.io/main/tool/chatbot/skill_guide/make_skill"
)


def _header_value(headers: Mapping[str, str], name: str) -> str | None:
    expected = name.casefold()
    for key, value in headers.items():
        if key.casefold() == expected:
            return value
    return None


class KakaoOpenBuilderAdapter(BaseChannelAdapter):
    """Normalize synchronous Kakao Channel chatbot skill requests."""

    provider = "kakao_openbuilder"

    def __init__(
        self,
        customer_hmac_key: bytes,
        *,
        expected_api_key: str | None = None,
        processing_basis_ref: str = "POL-PUBLIC-DUMMY",
        policy: ConnectorPolicy | None = None,
    ) -> None:
        if not customer_hmac_key:
            raise ValueError("customer_hmac_key is required")
        self._customer_hmac_key = customer_hmac_key
        self._expected_api_key = expected_api_key
        self._processing_basis_ref = processing_basis_ref
        # The repository policy decides which assurance levels may be ingested.
        # Callers normalizing public dummy fixtures pass fixture_ingest_policy().
        self._policy = policy or default_connector_policy()

    def capabilities(
        self,
        context: Mapping[str, Any] | None = None,
    ) -> ProviderCapabilities:
        del context
        return ProviderCapabilities(
            provider=self.provider,
            supported=frozenset(
                {
                    Capability.SKILL_REQUEST_INGEST,
                    Capability.HEALTHCHECK,
                }
            ),
            unsupported_reasons={
                Capability.WEBHOOK_INGEST: (
                    "Open Builder invokes a synchronous skill server; this is not "
                    "a native Kakao Channel 1:1 chat webhook"
                ),
                Capability.CONVERSATION_BACKFILL: (
                    "the reviewed Open Builder contract does not expose chat-history "
                    "backfill"
                ),
                Capability.DELIVERY_STATUS: (
                    "a successful skill response is not a delivery or read receipt"
                ),
                Capability.RECONCILIATION: (
                    "the reviewed Open Builder contract has no history API to reconcile"
                ),
                Capability.REPLY_DRAFT: (
                    "reply drafting belongs to the approval workflow"
                ),
                Capability.REPLY_SEND: (
                    "the adapter does not call an outbound Send API"
                ),
            },
            disabled_by_policy=frozenset({Capability.REPLY_SEND}),
            source_refs={capability: _SOURCE_URL for capability in Capability},
        )

    def verify_event(
        self,
        raw_body: bytes,
        headers: Mapping[str, str],
        received_at: datetime | str,
        *,
        request_context: RequestContext | None = None,
    ) -> VerifiedEvent:
        context = request_context or RequestContext()
        supplied_api_key = _header_value(headers, "x-api-key")

        if self._expected_api_key is not None:
            if not isinstance(supplied_api_key, str) or not hmac.compare_digest(
                supplied_api_key,
                self._expected_api_key,
            ):
                raise EventVerificationError("Kakao skill x-api-key mismatch")
            auth_verified = True
            assurance = VerificationAssurance.WEAK
        elif context.environment == "fixture":
            auth_verified = False
            assurance = VerificationAssurance.NONE
        else:
            raise EventVerificationError(
                "Kakao skill requests require a configured x-api-key"
            )

        # Enforced against policies/default-policy.json, not a constructor
        # default: editing that file changes what this endpoint accepts.
        self._policy.require_allowed_assurance(self.provider, assurance)

        request_id = _header_value(headers, "x-request-id")
        if not isinstance(request_id, str) or not request_id.strip():
            raise EventIdentityError("Kakao skill request requires X-Request-Id")

        payload = parse_json_body(raw_body)
        self._validate_payload(payload)

        return VerifiedEvent(
            provider=self.provider,
            raw_body=raw_body,
            payload=payload,
            received_at=isoformat_utc(received_at),
            auth_verified=auth_verified,
            verification_assurance=assurance,
            request_id=request_id.strip(),
        )

    @staticmethod
    def _validate_payload(payload: Mapping[str, Any]) -> None:
        user_request = payload.get("userRequest")
        bot = payload.get("bot")
        action = payload.get("action")
        if not isinstance(user_request, Mapping):
            raise PayloadValidationError("Kakao skill payload requires userRequest")
        if not isinstance(bot, Mapping) or not isinstance(bot.get("id"), str):
            raise PayloadValidationError("Kakao skill payload requires bot.id")
        if not isinstance(action, Mapping) or not isinstance(action.get("id"), str):
            raise PayloadValidationError("Kakao skill payload requires action.id")
        user = user_request.get("user")
        if not isinstance(user, Mapping) or not isinstance(user.get("id"), str):
            raise PayloadValidationError(
                "Kakao skill payload requires userRequest.user.id"
            )
        if not isinstance(user_request.get("utterance"), str):
            raise PayloadValidationError(
                "Kakao skill payload requires userRequest.utterance"
            )

    def normalize_event(
        self,
        verified_event: VerifiedEvent,
    ) -> CanonicalChannelEvent:
        if verified_event.request_id is None:
            raise EventIdentityError("verified Kakao event requires request_id")

        payload = verified_event.payload
        user_request = payload["userRequest"]
        bot = payload["bot"]
        action = payload["action"]
        user = user_request["user"]
        request_id = verified_event.request_id
        bot_id = bot["id"]
        user_id = user["id"]
        action_id = action["id"]

        event_id = deterministic_event_id(
            self.provider,
            {
                "request_id": request_id,
                "bot_id": bot_id,
                "action_id": action_id,
            },
        )
        redacted_content, privacy = redact_text_with_metadata(
            user_request["utterance"]
        )

        return CanonicalChannelEvent(
            event_id=event_id,
            provider=self.provider,
            provider_event_id=request_id,
            channel="kakao_channel_chatbot",
            direction="inbound",
            event_type="message_received",
            occurred_at=verified_event.received_at,
            received_at=verified_event.received_at,
            conversation_ref=opaque_reference(f"{bot_id}:{user_id}"),
            message_ref=opaque_reference(request_id),
            customer_ref_hmac=hmac_customer_reference(
                self._customer_hmac_key,
                self.provider,
                f"{bot_id}:{user_id}",
            ),
            content_redacted=redacted_content,
            attachment_metadata=(),
            raw_payload_ref=raw_payload_ref(
                verified_event.raw_body,
                fixture=not verified_event.auth_verified,
            ),
            privacy=privacy,
            consent_or_processing_basis_ref=self._processing_basis_ref,
            idempotency_key=event_id,
            auth_verified=verified_event.auth_verified,
            verification_assurance=verified_event.verification_assurance,
            provider_status="skill_request_received",
            canonical_status=CanonicalEventStatus.NORMALIZED,
            bot_ref=bot_id,
        )

    @staticmethod
    def build_skill_response(text: str) -> dict[str, Any]:
        if not isinstance(text, str) or not text.strip():
            raise PayloadValidationError("Kakao skill response text is required")
        if len(text) > 1000:
            raise PayloadValidationError(
                "Kakao simpleText response must not exceed 1000 characters"
            )
        return {
            "version": "2.0",
            "template": {
                "outputs": [
                    {
                        "simpleText": {
                            "text": text,
                        }
                    }
                ]
            },
        }
