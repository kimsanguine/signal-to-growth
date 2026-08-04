"""Environment-backed Kakao skill application for hosted test endpoints.

Readiness is not liveness
-------------------------
`configuration_ready` answers "are the five server-side variables present?".
That is a *configuration* check: it passes while Supabase is unreachable, the
key is revoked, or the project is paused. `dependency_ready` answers the
separate question "does storage actually respond?" with a bounded read-only
probe. `/api/health` reports both so a green check cannot mean "well-formed
environment, unusable service".
"""

from __future__ import annotations

import os
from collections.abc import Callable

from .adapters import KakaoOpenBuilderAdapter
from .kakao_skill_server import KakaoSkillApplication
from .supabase_sink import (
    SupabaseDeadLetterSink,
    SupabaseEventSink,
    SupabaseHealthProbe,
)


GetEnv = Callable[[str], str | None]
REQUIRED_ENV_NAMES = (
    "KAKAO_SKILL_API_KEY",
    "STG_CUSTOMER_HMAC_KEY",
    "STG_APPROVAL_REF",
    "SUPABASE_URL",
    "SUPABASE_SECRET_KEY",
)
DEFAULT_EVENTS_TABLE = "kakao_cs_events_test"
DEFAULT_DEAD_LETTER_TABLE = "kakao_cs_dead_letters_test"


class RuntimeConfigurationError(ValueError):
    """The hosted endpoint is missing required server-side configuration."""


def configuration_ready(getenv: GetEnv = os.environ.get) -> bool:
    """Return True when every required variable is present and non-empty."""
    return all(bool((getenv(name) or "").strip()) for name in REQUIRED_ENV_NAMES)


def _events_table(getenv: GetEnv) -> str:
    return (getenv("SUPABASE_KAKAO_EVENTS_TABLE") or "").strip() or DEFAULT_EVENTS_TABLE


def _dead_letter_table(getenv: GetEnv) -> str:
    return (
        (getenv("SUPABASE_KAKAO_DEAD_LETTER_TABLE") or "").strip()
        or DEFAULT_DEAD_LETTER_TABLE
    )


def build_supabase_health_probe(
    getenv: GetEnv = os.environ.get,
) -> SupabaseHealthProbe:
    """Build the read-only storage probe used by the health endpoint."""
    if not configuration_ready(getenv):
        raise RuntimeConfigurationError("required runtime configuration is missing")
    try:
        return SupabaseHealthProbe(
            (getenv("SUPABASE_URL") or "").strip(),
            (getenv("SUPABASE_SECRET_KEY") or "").strip(),
            table=_events_table(getenv),
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeConfigurationError("runtime configuration is invalid") from exc


# The probe caches its verdict, so it must outlive a single request to be useful.
_HEALTH_PROBE: SupabaseHealthProbe | None = None


def dependency_ready(getenv: GetEnv = os.environ.get) -> bool:
    """Return True when the storage dependency answers a bounded read."""
    global _HEALTH_PROBE
    if _HEALTH_PROBE is None:
        _HEALTH_PROBE = build_supabase_health_probe(getenv)
    return _HEALTH_PROBE()


def reset_health_probe() -> None:
    """Drop the cached probe. Intended for tests and configuration reloads."""
    global _HEALTH_PROBE
    _HEALTH_PROBE = None


def build_kakao_skill_application(
    getenv: GetEnv = os.environ.get,
) -> KakaoSkillApplication:
    values = {
        name: (getenv(name) or "").strip()
        for name in REQUIRED_ENV_NAMES
    }
    if not all(values.values()):
        raise RuntimeConfigurationError("required runtime configuration is missing")
    if len(values["KAKAO_SKILL_API_KEY"]) < 32:
        raise RuntimeConfigurationError(
            "KAKAO_SKILL_API_KEY must contain at least 32 characters"
        )
    if len(values["STG_CUSTOMER_HMAC_KEY"]) < 32:
        raise RuntimeConfigurationError(
            "STG_CUSTOMER_HMAC_KEY must contain at least 32 characters"
        )

    try:
        adapter = KakaoOpenBuilderAdapter(
            values["STG_CUSTOMER_HMAC_KEY"].encode("utf-8"),
            expected_api_key=values["KAKAO_SKILL_API_KEY"],
            processing_basis_ref=(
                (getenv("STG_PROCESSING_BASIS_REF") or "").strip()
                or "POL-KAKAO-TEST-SYNTHETIC"
            ),
            allow_unverified_fixture=False,
        )
        sink = SupabaseEventSink(
            values["SUPABASE_URL"],
            values["SUPABASE_SECRET_KEY"],
            table=_events_table(getenv),
        )
        dead_letter_sink = SupabaseDeadLetterSink(
            values["SUPABASE_URL"],
            values["SUPABASE_SECRET_KEY"],
            table=_dead_letter_table(getenv),
        )
        return KakaoSkillApplication(
            adapter,
            sink,
            approval_ref=values["STG_APPROVAL_REF"],
            dead_letter_sink=dead_letter_sink,
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeConfigurationError(
            "runtime configuration is invalid"
        ) from exc
