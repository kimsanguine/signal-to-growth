"""Base interfaces for provider adapters.

This module performs no network I/O. Any read operation that needs a provider
response must receive an ``InjectedTransport`` from the caller.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Mapping, Protocol, runtime_checkable

from ..channel_contracts import (
    Capability,
    CanonicalChannelEvent,
    HttpRequest,
    HttpResponse,
    ProviderCapabilities,
    RequestContext,
    UnsupportedCapability,
    VerifiedEvent,
)


@runtime_checkable
class InjectedTransport(Protocol):
    def send(self, request: HttpRequest) -> HttpResponse:
        """Return a deterministic response without adapter-owned network access."""


class ChannelAdapter(Protocol):
    provider: str

    def capabilities(
        self,
        context: Mapping[str, Any] | None = None,
    ) -> ProviderCapabilities: ...

    def verify_event(
        self,
        raw_body: bytes,
        headers: Mapping[str, str],
        received_at: datetime | str,
        *,
        request_context: RequestContext | None = None,
    ) -> VerifiedEvent: ...

    def normalize_event(
        self,
        verified_event: VerifiedEvent,
    ) -> CanonicalChannelEvent: ...

    def ingest(
        self,
        raw_body: bytes,
        *,
        headers: Mapping[str, str] | None = None,
        received_at: datetime | str,
        request_context: RequestContext | None = None,
    ) -> CanonicalChannelEvent: ...


class BaseChannelAdapter(ABC):
    provider = "base"

    @abstractmethod
    def capabilities(
        self,
        context: Mapping[str, Any] | None = None,
    ) -> ProviderCapabilities:
        raise NotImplementedError

    @abstractmethod
    def verify_event(
        self,
        raw_body: bytes,
        headers: Mapping[str, str],
        received_at: datetime | str,
        *,
        request_context: RequestContext | None = None,
    ) -> VerifiedEvent:
        raise NotImplementedError

    @abstractmethod
    def normalize_event(
        self,
        verified_event: VerifiedEvent,
    ) -> CanonicalChannelEvent:
        raise NotImplementedError

    def ingest(
        self,
        raw_body: bytes,
        *,
        headers: Mapping[str, str] | None = None,
        received_at: datetime | str,
        request_context: RequestContext | None = None,
    ) -> CanonicalChannelEvent:
        verified = self.verify_event(
            raw_body,
            headers or {},
            received_at,
            request_context=request_context,
        )
        return self.normalize_event(verified)

    def require_capability(self, capability: Capability | str) -> None:
        self.capabilities().require(capability)

    def build_backfill_request(self, *args: Any, **kwargs: Any) -> HttpRequest:
        self.require_capability(Capability.CONVERSATION_BACKFILL)
        raise UnsupportedCapability(
            self.provider,
            Capability.CONVERSATION_BACKFILL,
            "adapter did not implement request construction",
        )

    def create_reply_draft(self, *args: Any, **kwargs: Any) -> Any:
        self.require_capability(Capability.REPLY_DRAFT)
        raise UnsupportedCapability(
            self.provider,
            Capability.REPLY_DRAFT,
            "adapter did not implement draft creation",
        )

    def send_approved(self, *args: Any, **kwargs: Any) -> Any:
        raise UnsupportedCapability(
            self.provider,
            Capability.REPLY_SEND,
            "this release is read-only and performs no external writes",
        )

    def fetch_status(self, *args: Any, **kwargs: Any) -> Any:
        self.require_capability(Capability.DELIVERY_STATUS)
        raise UnsupportedCapability(
            self.provider,
            Capability.DELIVERY_STATUS,
            "adapter did not implement delivery status",
        )

    def reconcile(self, *args: Any, **kwargs: Any) -> Any:
        self.require_capability(Capability.RECONCILIATION)
        raise UnsupportedCapability(
            self.provider,
            Capability.RECONCILIATION,
            "adapter did not implement reconciliation",
        )

    def healthcheck(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "health": "configuration_only",
            "network_checked": False,
        }


def send_with_injected_transport(
    transport: InjectedTransport,
    request: HttpRequest,
) -> HttpResponse:
    """Invoke only a caller-provided transport and validate its return type."""
    response = transport.send(request)
    if not isinstance(response, HttpResponse):
        raise TypeError("injected transport must return HttpResponse")
    return response
