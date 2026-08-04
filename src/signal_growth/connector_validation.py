"""Deterministic validation, redaction, and identity helpers for connectors."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from .append_only import APPEND_ONLY_FILES, verify_append_chain
from .channel_contracts import (
    EventIdentityError,
    PayloadValidationError,
)
from .schema_validation import validate_schema_record


_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_KOREAN_MOBILE = re.compile(
    r"(?<!\d)01[016789][-\s]?\d{3,4}[-\s]?\d{4}(?!\d)"
)
_INTERNATIONAL_PHONE = re.compile(
    r"(?<!\d)\+\d{1,3}[-\s]?\d{2,4}[-\s]?\d{3,4}[-\s]?\d{4}(?!\d)"
)
_RESIDENT_ID = re.compile(r"(?<!\d)\d{6}[-\s]?[1-8]\d{6}(?!\d)")
_BUSINESS_ID = re.compile(r"(?<!\d)\d{3}[-\s]?\d{2}[-\s]?\d{5}(?!\d)")
_PAYMENT_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
_BANK_ACCOUNT = re.compile(
    r"(?:계좌(?:번호)?|account)\s*[:=]?\s*(?:\d[-\s]?){8,20}",
    re.I,
)
_LABELED_NAME = re.compile(r"(?:이름|성명)\s*[:=]?\s*[가-힣]{2,4}")
_LABELED_ADDRESS = re.compile(
    r"(?:주소|address)\s*[:=]?\s*[^\n,;]{6,120}",
    re.I,
)
_JWT = re.compile(
    r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
)
_API_KEY = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[opusr]_[A-Za-z0-9]{16,})\b")
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*\b")
_URL_SECRET = re.compile(
    r"(?i)([?&](?:token|secret|api[_-]?key|access[_-]?key)=)[^&#\s]+"
)

_DIRECT_IDENTIFIER_KEYS = {
    "email",
    "emailaddress",
    "mobile",
    "mobilenumber",
    "phone",
    "phonenumber",
    "name",
    "username",
}
_PROHIBITED_ARTIFACT_IDENTIFIER_KEYS = {
    "accountnumber",
    "address",
    "cardnumber",
    "email",
    "emailaddress",
    "mobile",
    "mobilenumber",
    "phone",
    "phonenumber",
    "recipientno",
    "residentid",
    "username",
}
_CREDENTIAL_KEYS = {
    "authorization",
    "token",
    "secret",
    "apikey",
    "apisecret",
    "accesskey",
    "accesssecret",
    "password",
}

_CONNECTOR_FILES = {
    "channel-connection.json",
    "cs-events.jsonl",
    "reply-drafts.jsonl",
    "delivery-events.jsonl",
    "connector-state.json",
}
_REQUIRED_CONNECTOR_FILES = {
    "channel-connection.json",
    "cs-events.jsonl",
    "connector-state.json",
}
# Connector artifacts that are append-only ledgers, so their chain is verified
# here the same way contracts.py verifies the evidence-side ledgers.
_CHAINED_CONNECTOR_FILES = tuple(
    sorted(_CONNECTOR_FILES & APPEND_ONLY_FILES)
)
_EVENT_STATUSES = {"received", "normalized", "ignored", "dead_letter", "unknown"}
_DELIVERY_STATUSES = {
    "draft",
    "validated",
    "approved",
    "submitted",
    "accepted",
    "queued",
    "sent",
    "delivered",
    "read",
    "failed",
    "cancelled",
    "expired",
    "unknown",
}
_CONNECTOR_SCHEMA_FILES = {
    "channel-connection.json": "channel-connection.schema.json",
    "cs-events.jsonl": "cs-event.schema.json",
    "reply-drafts.jsonl": "reply-draft.schema.json",
    "delivery-events.jsonl": "delivery-event.schema.json",
    "connector-state.json": "connector-state.schema.json",
}
_PROVIDER_CHANNELS = {
    "kakao_openbuilder": {"kakao_channel_chatbot"},
    "channel_talk": {"channel_talk"},
    "naver_talktalk": {"naver_talktalk"},
}
_PROVIDER_STATUS_CANONICAL = {
    "REQUEST_ACCEPTED": "accepted",
    "ACCEPTED": "accepted",
    "DELIVERED": "delivered",
    "READ": "read",
}


@dataclass(frozen=True)
class ConnectorValidationIssue:
    path: str
    message: str

    def render(self) -> str:
        return f"{self.path}: {self.message}"


def canonical_json(value: Any) -> bytes:
    """Serialize supported JSON values with stable key ordering."""
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EventIdentityError("stable identity fields must be JSON values") from exc


def deterministic_event_id(
    provider: str,
    stable_fields: Mapping[str, Any],
) -> str:
    """Return the same ID for the same provider and stable event fields."""
    if not provider.strip():
        raise EventIdentityError("provider is required for event identity")
    if not stable_fields:
        raise EventIdentityError("stable event identity fields are required")
    if any(value is None or value == "" for value in stable_fields.values()):
        raise EventIdentityError("stable event identity fields cannot be empty")
    digest = hashlib.sha256(
        provider.encode("utf-8") + b"\0" + canonical_json(dict(stable_fields))
    ).hexdigest()
    return f"CSE-{digest[:32]}"


def raw_payload_ref(raw_body: bytes, *, fixture: bool) -> str | None:
    """Return a content-addressed fixture reference.

    A real restricted pointer must be created by the hosting inbox after durable
    storage. The offline adapter cannot honestly claim that storage occurred.
    """
    if not fixture:
        return None
    return f"fixture+sha256://{hashlib.sha256(raw_body).hexdigest()}"


def hmac_customer_reference(
    key: bytes,
    provider: str,
    provider_customer_id: str,
) -> str:
    if not key:
        raise ValueError("a non-empty tenant HMAC key is required")
    if not provider_customer_id:
        raise PayloadValidationError("provider customer identity is required")
    digest = hmac.new(
        key,
        f"{provider}\0{provider_customer_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"hmac:{digest}"


def opaque_reference(value: str, *, kind: str = "ref") -> str:
    if kind not in {"ref", "hmac"}:
        raise ValueError("opaque reference kind must be ref or hmac")
    if not value:
        raise PayloadValidationError("opaque reference source is required")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"{kind}:{digest[:32]}"


def redact_text(text: str | None) -> str | None:
    if text is None:
        return None
    redacted = _EMAIL.sub("[REDACTED_EMAIL]", text)
    redacted = _KOREAN_MOBILE.sub("[REDACTED_PHONE]", redacted)
    redacted = _INTERNATIONAL_PHONE.sub("[REDACTED_PHONE]", redacted)
    redacted = _RESIDENT_ID.sub("[REDACTED_RESIDENT_ID]", redacted)
    redacted = _BUSINESS_ID.sub("[REDACTED_BUSINESS_ID]", redacted)
    redacted = _PAYMENT_CARD.sub("[REDACTED_PAYMENT_CARD]", redacted)
    redacted = _BANK_ACCOUNT.sub("[REDACTED_ACCOUNT]", redacted)
    redacted = _LABELED_NAME.sub("이름: [REDACTED_NAME]", redacted)
    redacted = _LABELED_ADDRESS.sub("주소: [REDACTED_ADDRESS]", redacted)
    redacted = _JWT.sub("[REDACTED_SECRET]", redacted)
    redacted = _API_KEY.sub("[REDACTED_SECRET]", redacted)
    redacted = _BEARER.sub("[REDACTED_SECRET]", redacted)
    return _URL_SECRET.sub(r"\1[REDACTED_SECRET]", redacted)


def redact_text_with_metadata(text: str | None) -> tuple[str, dict[str, Any]]:
    original = text or ""
    pii_types: list[str] = []
    if _EMAIL.search(original):
        pii_types.append("email")
    if _KOREAN_MOBILE.search(original) or _INTERNATIONAL_PHONE.search(original):
        pii_types.append("phone")
    if _LABELED_NAME.search(original):
        pii_types.append("name")
    if _LABELED_ADDRESS.search(original):
        pii_types.append("address")
    if _PAYMENT_CARD.search(original) or _BANK_ACCOUNT.search(original):
        pii_types.append("account_identifier")
    if _RESIDENT_ID.search(original) or _BUSINESS_ID.search(original):
        pii_types.append("other")
    if _JWT.search(original) or _API_KEY.search(original) or _BEARER.search(original):
        pii_types.append("other")
    redacted = redact_text(original) or ""
    return redacted, {
        "classification": "restricted",
        "redaction_status": "redacted" if redacted != original else "not_required",
        "pii_types_removed": pii_types,
    }


def redact_mapping(value: Any) -> Any:
    """Recursively redact direct identifiers and credential-looking fields."""
    if isinstance(value, Mapping):
        output: dict[str, Any] = {}
        for key, child in value.items():
            normalized_key = re.sub(r"[^a-z]", "", str(key).lower())
            if normalized_key in _DIRECT_IDENTIFIER_KEYS:
                output[str(key)] = "[REDACTED_IDENTIFIER]"
            elif normalized_key in _CREDENTIAL_KEYS:
                output[str(key)] = "[REDACTED_SECRET]"
            else:
                output[str(key)] = redact_mapping(child)
        return output
    if isinstance(value, list):
        return [redact_mapping(child) for child in value]
    if isinstance(value, tuple):
        return tuple(redact_mapping(child) for child in value)
    if isinstance(value, str):
        return redact_text(value)
    return value


def parse_json_body(raw_body: bytes, *, max_bytes: int | None = None) -> dict[str, Any]:
    if max_bytes is not None and len(raw_body) > max_bytes:
        raise PayloadValidationError("payload exceeds the configured size limit")
    try:
        value = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PayloadValidationError("payload must be a UTF-8 JSON object") from exc
    if not isinstance(value, dict):
        raise PayloadValidationError("payload must be a JSON object")
    return value


def isoformat_utc(value: datetime | str) -> str:
    if isinstance(value, str):
        candidate = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError as exc:
            raise PayloadValidationError("timestamp must be ISO 8601") from exc
    else:
        parsed = value
    if parsed.tzinfo is None:
        raise PayloadValidationError("timestamp must include a timezone")
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def epoch_millis_to_iso(value: Any) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise PayloadValidationError("provider timestamp must be epoch milliseconds")
    try:
        parsed = datetime.fromtimestamp(value / 1000, tz=UTC)
    except (OverflowError, OSError, ValueError) as exc:
        raise PayloadValidationError("provider timestamp is out of range") from exc
    return parsed.isoformat().replace("+00:00", "Z")


def dedupe_events(events: Iterable[Any]) -> list[Any]:
    """Deduplicate exact retries and reject conflicting event identities."""
    seen: dict[str, bytes] = {}
    output: list[Any] = []
    for event in events:
        if isinstance(event, Mapping):
            event_id = event.get("event_id")
            comparable = dict(event)
        else:
            event_id = getattr(event, "event_id", None)
            to_dict = getattr(event, "to_dict", None)
            comparable = to_dict() if callable(to_dict) else vars(event)
        if not isinstance(event_id, str) or not event_id:
            raise EventIdentityError("every event must expose a non-empty event_id")
        stable_fields = {
            key: comparable[key]
            for key in (
                "provider",
                "provider_event_id",
                "channel",
                "direction",
                "event_type",
                "conversation_ref",
                "message_ref",
                "customer_ref_hmac",
                "content_redacted",
                "attachment_metadata",
            )
            if key in comparable
        }
        if not stable_fields:
            stable_fields = {
                key: value
                for key, value in comparable.items()
                if key not in {"event_id", "idempotency_key", "received_at"}
            }
        fingerprint = hashlib.sha256(canonical_json(stable_fields)).digest()
        if event_id in seen:
            if seen[event_id] != fingerprint:
                raise EventIdentityError(
                    "the same event_id was observed with conflicting content"
                )
            continue
        seen[event_id] = fingerprint
        output.append(event)
    return output


def validate_connection(connection: Mapping[str, Any]) -> list[ConnectorValidationIssue]:
    """Validate the credential-free portion of a channel connection."""
    issues: list[ConnectorValidationIssue] = []
    required = {
        "connection_id",
        "provider",
        "region",
        "environment",
        "mode",
        "credential_ref",
        "capabilities",
        "retention_policy_ref",
        "approved_by",
        "verified_at",
        "external_write_enabled",
    }
    missing = sorted(required - set(connection))
    if missing:
        issues.append(
            ConnectorValidationIssue(
                "connection",
                f"missing fields: {', '.join(missing)}",
            )
        )
        return issues

    if connection.get("mode") not in {
        "read_only",
        "draft_only",
        "approved_write",
    }:
        issues.append(
            ConnectorValidationIssue(
                "connection.mode",
                "mode must be read_only, draft_only, or approved_write",
            )
        )

    credential_ref = connection.get("credential_ref")
    if credential_ref is not None and (
        not isinstance(credential_ref, str)
        or not credential_ref.startswith("secret://")
    ):
        issues.append(
            ConnectorValidationIssue(
                "connection.credential_ref",
                "credential_ref must be a secret:// reference, never a credential value",
            )
        )

    capabilities = connection.get("capabilities")
    if not isinstance(capabilities, list) or not all(
        isinstance(item, Mapping)
        and {"name", "support", "access_mode", "source_ref"} <= set(item)
        for item in capabilities
    ):
        issues.append(
            ConnectorValidationIssue(
                "connection.capabilities",
                "capabilities must be an array of capability objects",
            )
        )
    else:
        for index, item in enumerate(capabilities):
            if item.get("support") not in {
                "supported",
                "unsupported",
                "unconfirmed",
                "disabled_by_policy",
            }:
                issues.append(
                    ConnectorValidationIssue(
                        f"connection.capabilities[{index}].support",
                        "support must be supported, unsupported, unconfirmed, "
                        "or disabled_by_policy",
                    )
                )
            if item.get("access_mode") not in {
                "read_only",
                "draft_only",
                "approved_write",
            }:
                issues.append(
                    ConnectorValidationIssue(
                        f"connection.capabilities[{index}].access_mode",
                        "invalid access mode",
                    )
                )

    if connection.get("mode") in {"read_only", "draft_only"} and connection.get(
        "external_write_enabled"
    ) is not False:
        issues.append(
            ConnectorValidationIssue(
                "connection.external_write_enabled",
                "read_only and draft_only connections must disable external writes",
            )
        )
    if connection.get("mode") == "approved_write":
        if connection.get("external_write_enabled") is not True:
            issues.append(
                ConnectorValidationIssue(
                    "connection.external_write_enabled",
                    "approved_write connections must enable external writes",
                )
            )
        approved_by = connection.get("approved_by")
        if not isinstance(approved_by, str) or not approved_by.startswith("APR-"):
            issues.append(
                ConnectorValidationIssue(
                    "connection.approved_by",
                    "approved_write connections require an APR- approval reference",
                )
            )

    for key in connection:
        normalized_key = re.sub(r"[^a-z]", "", str(key).lower())
        if normalized_key in _CREDENTIAL_KEYS and key != "credential_ref":
            issues.append(
                ConnectorValidationIssue(
                    f"connection.{key}",
                    "raw credential fields are forbidden",
                )
            )
    return issues


validate_connector_connection = validate_connection


def _load_connector_records(path: Path) -> list[dict[str, Any]]:
    if path.suffix == ".jsonl":
        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            1,
        ):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"line {line_number}: record must be an object")
            records.append(value)
        return records
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON artifact must be an object")
    return [value]


def _prohibited_paths(value: Any, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            normalized = re.sub(r"[^a-z]", "", str(key).lower())
            if (
                normalized in _CREDENTIAL_KEYS
                or normalized in _PROHIBITED_ARTIFACT_IDENTIFIER_KEYS
            ):
                paths.append(path)
            paths.extend(_prohibited_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(_prohibited_paths(child, f"{prefix}[{index}]"))
    return paths


def _missing(record: Mapping[str, Any], required: set[str]) -> list[str]:
    return sorted(required - set(record))


def _validate_cs_event(
    record: Mapping[str, Any],
    location: str,
) -> list[ConnectorValidationIssue]:
    required = {
        "event_id",
        "provider",
        "provider_event_id",
        "channel",
        "direction",
        "event_type",
        "occurred_at",
        "received_at",
        "conversation_ref",
        "message_ref",
        "customer_ref_hmac",
        "content_redacted",
        "attachment_metadata",
        "raw_payload_ref",
        "privacy",
        "consent_or_processing_basis_ref",
        "idempotency_key",
        "auth_verified",
        "verification_assurance",
        "provider_status",
        "canonical_status",
        "source_evidence_ids",
    }
    issues: list[ConnectorValidationIssue] = []
    missing = _missing(record, required)
    if missing:
        return [ConnectorValidationIssue(location, f"missing fields: {', '.join(missing)}")]
    if record.get("canonical_status") not in _EVENT_STATUSES:
        issues.append(ConnectorValidationIssue(location, "invalid canonical event status"))
    if (
        record.get("verification_assurance") == "none"
        and record.get("auth_verified") is True
    ):
        issues.append(
            ConnectorValidationIssue(
                location,
                "auth_verified cannot be true when verification assurance is none",
            )
        )
    provider = record.get("provider")
    expected_channels = _PROVIDER_CHANNELS.get(provider)
    if expected_channels is not None and record.get("channel") not in expected_channels:
        issues.append(
            ConnectorValidationIssue(
                location,
                f"{provider} cannot produce channel={record.get('channel')}",
            )
        )
    content = record.get("content_redacted")
    if not isinstance(content, str) or redact_text(content) != content:
        issues.append(
            ConnectorValidationIssue(
                location,
                "content_redacted still contains a supported private-data pattern",
            )
        )
    return issues


def validate_cs_event_record(
    record: Mapping[str, Any],
    location: str = "cs-event",
) -> list[ConnectorValidationIssue]:
    """Validate one canonical event with schema, privacy, and product invariants."""
    issues = [
        ConnectorValidationIssue(location, message)
        for message in validate_schema_record("cs-event.schema.json", record)
    ]
    prohibited = _prohibited_paths(record)
    if prohibited:
        issues.append(
            ConnectorValidationIssue(
                location,
                f"raw credential or identifier fields are forbidden: {', '.join(prohibited)}",
            )
        )
    issues.extend(_validate_cs_event(record, location))
    return issues


def _validate_reply_draft(
    record: Mapping[str, Any],
    location: str,
) -> list[ConnectorValidationIssue]:
    required = {
        "draft_id",
        "source_event_ids",
        "conversation_ref",
        "provider",
        "product",
        "session_state",
        "content",
        "template_ref",
        "template_variables",
        "risk_class",
        "status",
        "approval_id",
        "expires_at",
        "external_write",
    }
    missing = _missing(record, required)
    if missing:
        return [ConnectorValidationIssue(location, f"missing fields: {', '.join(missing)}")]
    issues: list[ConnectorValidationIssue] = []
    if record.get("external_write") is not False:
        issues.append(
            ConnectorValidationIssue(
                location,
                "reply drafts must keep external_write=false",
            )
        )
    if record.get("status") == "approved" and not record.get("approval_id"):
        issues.append(
            ConnectorValidationIssue(location, "approved draft requires approval_id")
        )
    if (
        record.get("product") == "consulttalk"
        and record.get("status") == "approved"
        and record.get("session_state") != "active"
    ):
        issues.append(
            ConnectorValidationIssue(
                location,
                "approved ConsultTalk draft requires an active session",
            )
        )
    return issues


def _validate_delivery_event(
    record: Mapping[str, Any],
    location: str,
) -> list[ConnectorValidationIssue]:
    required = {
        "delivery_event_id",
        "attempt_id",
        "provider",
        "product",
        "channel",
        "occurred_at",
        "received_at",
        "status_observed_at",
        "provider_message_ref",
        "provider_status",
        "canonical_status",
        "attempt_kind",
        "parent_attempt_ref",
        "transport",
        "fallback_applied",
        "idempotency_key",
        "raw_payload_ref",
        "auth_verified",
        "verification_assurance",
        "source_evidence_ids",
    }
    missing = _missing(record, required)
    if missing:
        return [ConnectorValidationIssue(location, f"missing fields: {', '.join(missing)}")]
    issues: list[ConnectorValidationIssue] = []
    if record.get("canonical_status") not in _DELIVERY_STATUSES:
        issues.append(ConnectorValidationIssue(location, "invalid delivery status"))
    provider_status = record.get("provider_status")
    expected_status = (
        _PROVIDER_STATUS_CANONICAL.get(provider_status.upper())
        if isinstance(provider_status, str)
        else None
    )
    if expected_status is not None and record.get("canonical_status") != expected_status:
        issues.append(
            ConnectorValidationIssue(
                location,
                f"provider_status={provider_status} requires canonical_status={expected_status}",
            )
        )
    if record.get("attempt_kind") == "fallback":
        if not record.get("parent_attempt_ref") or record.get("fallback_applied") is not True:
            issues.append(
                ConnectorValidationIssue(
                    location,
                    "fallback must be a separate linked attempt",
                )
            )
    elif record.get("parent_attempt_ref") is not None or record.get(
        "fallback_applied"
    ) is not False:
        issues.append(
            ConnectorValidationIssue(
                location,
                "primary attempt cannot claim fallback state",
            )
        )
    return issues


def _validate_connector_state(
    record: Mapping[str, Any],
    location: str,
) -> list[ConnectorValidationIssue]:
    required = {
        "connection_id",
        "provider",
        "mode",
        "external_write_enabled",
        "cursor",
        "last_webhook_at",
        "last_backfill_at",
        "last_reconciled_at",
        "ingested_count",
        "duplicate_count",
        "dead_letter_count",
        "blocked_reasons",
        "health",
        "verification_level",
    }
    missing = _missing(record, required)
    if missing:
        return [ConnectorValidationIssue(location, f"missing fields: {', '.join(missing)}")]
    if record.get("mode") in {"read_only", "draft_only"} and record.get(
        "external_write_enabled"
    ) is not False:
        return [
            ConnectorValidationIssue(
                location,
                "read-only connector state must disable external writes",
            )
        ]
    return []


def validate_connector_directory(
    directory: Path,
    *,
    require_complete: bool = False,
) -> list[ConnectorValidationIssue]:
    """Validate credential-free connector artifacts without network access."""
    issues: list[ConnectorValidationIssue] = []
    if not directory.exists() or not directory.is_dir():
        return [ConnectorValidationIssue(str(directory), "directory does not exist")]

    if require_complete:
        for filename in sorted(_REQUIRED_CONNECTOR_FILES):
            if not (directory / filename).exists():
                issues.append(
                    ConnectorValidationIssue(filename, "required connector artifact is missing")
                )

    validators = {
        "cs-events.jsonl": _validate_cs_event,
        "reply-drafts.jsonl": _validate_reply_draft,
        "delivery-events.jsonl": _validate_delivery_event,
        "connector-state.json": _validate_connector_state,
    }
    loaded_records: dict[str, list[dict[str, Any]]] = {}
    for filename in sorted(_CONNECTOR_FILES):
        path = directory / filename
        if not path.exists():
            continue
        try:
            records = _load_connector_records(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            issues.append(ConnectorValidationIssue(filename, str(exc)))
            continue
        loaded_records[filename] = records
        for index, record in enumerate(records, 1):
            location = f"{filename}[{index}]"
            issues.extend(
                ConnectorValidationIssue(location, message)
                for message in validate_schema_record(
                    _CONNECTOR_SCHEMA_FILES[filename],
                    record,
                )
            )
            prohibited = _prohibited_paths(record)
            if prohibited:
                issues.append(
                    ConnectorValidationIssue(
                        location,
                        f"raw credential or identifier fields are forbidden: {', '.join(prohibited)}",
                    )
                )
            if filename == "channel-connection.json":
                issues.extend(
                    ConnectorValidationIssue(
                        f"{location}.{issue.path}",
                        issue.message,
                    )
                    for issue in validate_connection(record)
                )
            else:
                issues.extend(validators[filename](record, location))

    for filename in _CHAINED_CONNECTOR_FILES:
        issues.extend(
            ConnectorValidationIssue(location, message)
            for location, message in verify_append_chain(
                loaded_records.get(filename, []),
                filename,
            )
        )

    connections = loaded_records.get("channel-connection.json", [])
    states = loaded_records.get("connector-state.json", [])
    events = loaded_records.get("cs-events.jsonl", [])
    if connections:
        connection = connections[0]
        connection_id = connection.get("connection_id")
        provider = connection.get("provider")
        for index, state in enumerate(states, 1):
            if state.get("connection_id") != connection_id:
                issues.append(
                    ConnectorValidationIssue(
                        f"connector-state.json[{index}]",
                        "connection_id does not match channel-connection.json",
                    )
                )
            if state.get("provider") != provider:
                issues.append(
                    ConnectorValidationIssue(
                        f"connector-state.json[{index}]",
                        "provider does not match channel-connection.json",
                    )
                )
        for index, event in enumerate(events, 1):
            if event.get("provider") != provider:
                issues.append(
                    ConnectorValidationIssue(
                        f"cs-events.jsonl[{index}]",
                        "provider does not match channel-connection.json",
                    )
                )
    return issues
