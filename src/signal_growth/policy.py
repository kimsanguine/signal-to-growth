"""Load `policies/default-policy.json` and enforce it at runtime.

A policy file that no code reads is documentation, not a control. Before this
module existed, `connectors.blocked_verification_assurance` was a claim in JSON
while the actual block lived in a per-adapter constructor argument
(`allow_unverified_fixture`). Two failure modes followed from that split:

1. Editing the policy file changed nothing at runtime.
2. A caller could construct an adapter with the permissive default and ingest
   an unverified event, because no shared check ever consulted the policy.

This module makes the file the authority. `ConnectorPolicy` is the typed view a
connector needs, `default_connector_policy()` reads the repository policy, and
`require_allowed_assurance` refuses an event whose verification assurance the
policy blocks. The refusal is an `EventVerificationError` subclass so an
existing ingress path answers it the same way it answers any other failed
verification, rather than surfacing a new unhandled error class.

Fixture ingest is the one sanctioned exemption and it is explicit: a caller
that deliberately normalizes public dummy fixtures passes
`fixture_ingest_policy()`. That call site is greppable; a permissive default
was not.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from .channel_contracts import EventVerificationError, VerificationAssurance


DEFAULT_POLICY_FILENAME = "default-policy.json"

_KNOWN_ASSURANCE_VALUES = frozenset(item.value for item in VerificationAssurance)


class PolicyLoadError(ValueError):
    """The policy file is missing, unreadable, or internally inconsistent."""


class PolicyViolation(EventVerificationError):
    """A policy in `policies/` forbids continuing with this event."""


def policy_directory() -> Path:
    """Return the repository `policies/` directory."""
    configured_root = os.environ.get("SIGNAL_TO_GROWTH_ROOT")
    candidates: list[Path] = []
    if configured_root:
        candidates.append(Path(configured_root).expanduser().resolve() / "policies")
    candidates.extend(
        (
            Path(__file__).resolve().parents[2] / "policies",
            Path.cwd().resolve() / "policies",
        )
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise PolicyLoadError(
        "Signal to Growth policies directory was not found; "
        "set SIGNAL_TO_GROWTH_ROOT to the repository root"
    )


def load_policy_document(filename: str = DEFAULT_POLICY_FILENAME) -> dict[str, Any]:
    """Return a policy file as a plain document, without interpreting it."""
    path = policy_directory() / filename
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PolicyLoadError(f"policy file is unreadable: {path}") from exc
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PolicyLoadError(f"policy file is not valid JSON: {path}") from exc
    if not isinstance(document, dict):
        raise PolicyLoadError(f"policy file must contain an object: {path}")
    return document


@dataclass(frozen=True)
class ConnectorPolicy:
    """The connector-facing subset of a policy document."""

    source: str
    blocked_verification_assurance: frozenset[str]
    # RESERVED, NOT ENFORCED. `default_mode` is parsed and validated so the
    # file stays well-formed, but no runtime check consults it today: the
    # read-only stance is structural instead. `BaseChannelAdapter.send_approved`
    # raises `UnsupportedCapability` unconditionally and every adapter lists
    # `REPLY_SEND` in `disabled_by_policy`, so there is no write attempt for a
    # mode check to gate. When an outbound path is added, gate it here rather
    # than leaving this field decorative.
    default_mode: str

    @classmethod
    def from_document(
        cls,
        document: Mapping[str, Any],
        *,
        source: str,
    ) -> "ConnectorPolicy":
        connectors = document.get("connectors")
        if not isinstance(connectors, Mapping):
            raise PolicyLoadError(f"{source} is missing the connectors section")

        blocked = connectors.get("blocked_verification_assurance")
        if not isinstance(blocked, list) or not all(
            isinstance(item, str) for item in blocked
        ):
            raise PolicyLoadError(
                f"{source}: connectors.blocked_verification_assurance "
                "must be a list of strings"
            )
        unknown = sorted(set(blocked) - _KNOWN_ASSURANCE_VALUES)
        if unknown:
            # A typo here would silently block nothing, so fail at load time.
            raise PolicyLoadError(
                f"{source}: unknown verification assurance value(s): "
                f"{', '.join(unknown)}"
            )

        default_mode = connectors.get("default_mode")
        if not isinstance(default_mode, str) or not default_mode.strip():
            raise PolicyLoadError(f"{source}: connectors.default_mode is required")

        return cls(
            source=source,
            blocked_verification_assurance=frozenset(blocked),
            default_mode=default_mode.strip(),
        )

    def allows_assurance(self, assurance: VerificationAssurance | str) -> bool:
        value = (
            assurance.value
            if isinstance(assurance, VerificationAssurance)
            else str(assurance)
        )
        return value not in self.blocked_verification_assurance

    def require_allowed_assurance(
        self,
        provider: str,
        assurance: VerificationAssurance | str,
    ) -> None:
        """Raise when the policy blocks this verification assurance level."""
        if self.allows_assurance(assurance):
            return
        value = (
            assurance.value
            if isinstance(assurance, VerificationAssurance)
            else str(assurance)
        )
        raise PolicyViolation(
            f"{provider} event with verification assurance '{value}' is blocked by "
            f"{self.source} (connectors.blocked_verification_assurance)"
        )


@lru_cache(maxsize=None)
def default_connector_policy() -> ConnectorPolicy:
    """Return the connector policy declared in `policies/default-policy.json`."""
    return ConnectorPolicy.from_document(
        load_policy_document(),
        source=f"policies/{DEFAULT_POLICY_FILENAME}",
    )


def fixture_ingest_policy() -> ConnectorPolicy:
    """Return the fixture-only relaxation used to normalize public dummy data.

    This permits every assurance level, including `none`, because a repository
    fixture carries no provider authentication to verify. It must never be used
    for an endpoint that receives provider traffic.
    """
    return ConnectorPolicy(
        source="fixture-ingest-policy (public dummy fixtures only)",
        blocked_verification_assurance=frozenset(),
        default_mode="read_only",
    )


def reset_policy_cache() -> None:
    """Drop the cached default policy. Intended for tests and reloads."""
    default_connector_policy.cache_clear()
