"""Read-only Channel Talk legacy webhook and backfill adapter."""

from __future__ import annotations

import hmac
import json
import re
from datetime import datetime
from typing import Any, Mapping
from urllib.parse import quote, urlencode

from ..channel_contracts import (
    BackfillPage,
    Capability,
    CanonicalChannelEvent,
    CanonicalEventStatus,
    EventVerificationError,
    HttpRequest,
    PayloadValidationError,
    ProviderCapabilities,
    RequestContext,
    TransportError,
    VerificationAssurance,
    VerifiedEvent,
)
from ..connector_validation import (
    deterministic_event_id,
    epoch_millis_to_iso,
    hmac_customer_reference,
    isoformat_utc,
    opaque_reference,
    parse_json_body,
    raw_payload_ref,
    redact_text_with_metadata,
)
from .base import BaseChannelAdapter, InjectedTransport, send_with_injected_transport


_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:-]+$")


class ChannelTalkAdapter(BaseChannelAdapter):
    provider = "channel_talk"
    _base_url = "https://api.channel.io/open/v5"

    def __init__(
        self,
        customer_hmac_key: bytes,
        *,
        expected_webhook_token: str | None = None,
        credential_ref: str | None = None,
        processing_basis_ref: str = "POL-PUBLIC-DUMMY",
        allow_unverified_fixture: bool = True,
    ) -> None:
        if not customer_hmac_key:
            raise ValueError("customer_hmac_key is required")
        if credential_ref is not None and not credential_ref.startswith("secret://"):
            raise ValueError("credential_ref must be a secret:// reference")
        self._customer_hmac_key = customer_hmac_key
        self._expected_webhook_token = expected_webhook_token
        self._credential_ref = credential_ref
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
                    Capability.CONVERSATION_BACKFILL,
                    Capability.RECONCILIATION,
                    Capability.HEALTHCHECK,
                }
            ),
            unsupported_reasons={
                Capability.DELIVERY_STATUS: (
                    "message read APIs do not establish final transport delivery semantics"
                ),
                Capability.REPLY_DRAFT: (
                    "reply drafting belongs to the approval workflow, not this adapter"
                ),
                Capability.REPLY_SEND: (
                    "write APIs are intentionally disabled in the read-only release"
                ),
            },
            disabled_by_policy=frozenset({Capability.REPLY_SEND}),
            source_refs={
                capability: (
                    "https://developers.channel.io/en/articles/"
                    "What-is-Open-API-c8c76fba"
                )
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
        context = request_context or RequestContext()

        if self._expected_webhook_token is not None:
            supplied = context.query.get("token")
            if not isinstance(supplied, str) or not hmac.compare_digest(
                supplied,
                self._expected_webhook_token,
            ):
                raise EventVerificationError("Channel Talk webhook token mismatch")
            auth_verified = True
            assurance = VerificationAssurance.WEAK
        elif context.environment == "fixture" and self._allow_unverified_fixture:
            auth_verified = False
            assurance = VerificationAssurance.NONE
        else:
            raise EventVerificationError(
                "legacy Channel Talk webhook requires the configured URL token"
            )

        payload = parse_json_body(raw_body)
        if payload.get("event") != "push":
            raise PayloadValidationError("only Channel Talk push events are supported")
        if payload.get("type") not in {"message", "userChat"}:
            raise PayloadValidationError(
                "only Channel Talk message and userChat events are supported"
            )

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
        entity_type = payload["type"]
        entity = payload.get("entity")
        if not isinstance(entity, Mapping):
            raise PayloadValidationError("Channel Talk event requires entity")

        if entity_type == "message":
            return self._normalize_message(
                entity,
                raw_body=verified_event.raw_body,
                received_at=verified_event.received_at,
                auth_verified=verified_event.auth_verified,
                assurance=verified_event.verification_assurance,
            )

        refers = payload.get("refers")
        message = refers.get("message") if isinstance(refers, Mapping) else None
        if not isinstance(message, Mapping):
            raise PayloadValidationError(
                "Channel Talk userChat event requires refers.message"
            )
        return self._normalize_message(
            message,
            raw_body=verified_event.raw_body,
            received_at=verified_event.received_at,
            auth_verified=verified_event.auth_verified,
            assurance=verified_event.verification_assurance,
            conversation_override=entity.get("id"),
        )

    def _normalize_message(
        self,
        message: Mapping[str, Any],
        *,
        raw_body: bytes,
        received_at: str,
        auth_verified: bool,
        assurance: VerificationAssurance,
        conversation_override: Any = None,
    ) -> CanonicalChannelEvent:
        provider_event_id = message.get("id")
        conversation_ref = conversation_override or message.get("chatId")
        created_at = message.get("createdAt")
        if not isinstance(provider_event_id, str) or not provider_event_id:
            raise PayloadValidationError("Channel Talk message requires id")
        if not isinstance(conversation_ref, str) or not conversation_ref:
            raise PayloadValidationError("Channel Talk message requires chatId")
        if message.get("chatType") != "userChat":
            raise PayloadValidationError("group chat is outside the CS connector scope")

        occurred_at = epoch_millis_to_iso(created_at)
        event_id = deterministic_event_id(
            self.provider,
            {
                "provider_event_id": provider_event_id,
                "version": message.get("version", 0),
            },
        )
        customer_basis = conversation_ref
        customer_ref = hmac_customer_reference(
            self._customer_hmac_key,
            self.provider,
            customer_basis,
        )
        person_type = message.get("personType")
        direction = "inbound" if person_type == "user" else "outbound"
        redacted_content, privacy = redact_text_with_metadata(
            message.get("plainText")
            if isinstance(message.get("plainText"), str)
            else None
        )

        return CanonicalChannelEvent(
            event_id=event_id,
            provider=self.provider,
            provider_event_id=provider_event_id,
            channel="channel_talk",
            direction=direction,
            event_type=(
                "message_received" if direction == "inbound" else "message_sent"
            ),
            occurred_at=occurred_at,
            received_at=received_at,
            conversation_ref=opaque_reference(conversation_ref),
            message_ref=opaque_reference(provider_event_id),
            customer_ref_hmac=customer_ref,
            content_redacted=redacted_content,
            attachment_metadata=self._attachment_metadata(message),
            raw_payload_ref=raw_payload_ref(
                raw_body,
                fixture=not auth_verified,
            ),
            privacy=privacy,
            consent_or_processing_basis_ref=self._processing_basis_ref,
            idempotency_key=event_id,
            auth_verified=auth_verified,
            verification_assurance=assurance,
            provider_status=str(message.get("state", "created")),
            canonical_status=CanonicalEventStatus.NORMALIZED,
        )

    @staticmethod
    def _attachment_metadata(
        message: Mapping[str, Any],
    ) -> tuple[Mapping[str, Any], ...]:
        # Provider file descriptors do not guarantee the byte hash and size
        # required by the canonical contract. Do not invent those values.
        return ()

    def build_backfill_request(
        self,
        user_chat_id: str,
        *,
        cursor: str | None = None,
        limit: int = 100,
        sort_order: str = "asc",
    ) -> HttpRequest:
        self.require_capability(Capability.CONVERSATION_BACKFILL)
        if not _SAFE_IDENTIFIER.fullmatch(user_chat_id):
            raise PayloadValidationError("user_chat_id contains unsafe characters")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
            raise PayloadValidationError("limit must be an integer from 1 to 500")
        if sort_order not in {"asc", "desc"}:
            raise PayloadValidationError("sort_order must be asc or desc")
        query: dict[str, str | int] = {
            "limit": limit,
            "sortOrder": sort_order,
        }
        if cursor is not None:
            if not isinstance(cursor, str) or not cursor:
                raise PayloadValidationError("cursor must be a non-empty opaque string")
            query["since"] = cursor

        url = (
            f"{self._base_url}/user-chats/{quote(user_chat_id, safe='')}/messages?"
            f"{urlencode(query)}"
        )
        return HttpRequest(
            method="GET",
            url=url,
            headers={"Accept": "application/json"},
            credential_ref=self._credential_ref,
        )

    def backfill(
        self,
        transport: InjectedTransport,
        user_chat_id: str,
        *,
        received_at: datetime | str,
        cursor: str | None = None,
        limit: int = 100,
        sort_order: str = "asc",
    ) -> BackfillPage:
        request = self.build_backfill_request(
            user_chat_id,
            cursor=cursor,
            limit=limit,
            sort_order=sort_order,
        )
        response = send_with_injected_transport(transport, request)
        if response.status != 200:
            raise TransportError(
                f"Channel Talk backfill returned HTTP {response.status}"
            )
        try:
            payload = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TransportError("Channel Talk backfill returned invalid JSON") from exc
        if not isinstance(payload, Mapping) or not isinstance(
            payload.get("messages"),
            list,
        ):
            raise TransportError("Channel Talk backfill response requires messages")

        normalized_received_at = isoformat_utc(received_at)
        events: list[CanonicalChannelEvent] = []
        for message in payload["messages"]:
            if not isinstance(message, Mapping):
                raise TransportError("Channel Talk backfill messages must be objects")
            raw_message = json.dumps(
                message,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            events.append(
                self._normalize_message(
                    message,
                    raw_body=raw_message,
                    received_at=normalized_received_at,
                    auth_verified=response.authenticated,
                    assurance=(
                        VerificationAssurance.MEDIUM
                        if response.authenticated
                        else VerificationAssurance.NONE
                    ),
                )
            )

        next_cursor = payload.get("next")
        if next_cursor is not None and not isinstance(next_cursor, str):
            raise TransportError("Channel Talk next cursor must be a string or null")
        return BackfillPage(
            request=request,
            events=tuple(events),
            next_cursor=next_cursor,
        )
