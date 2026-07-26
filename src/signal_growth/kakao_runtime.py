"""Environment-backed Kakao skill application for hosted test endpoints."""

from __future__ import annotations

import os
from collections.abc import Callable

from .adapters import KakaoOpenBuilderAdapter
from .kakao_skill_server import KakaoSkillApplication
from .supabase_sink import SupabaseEventSink


GetEnv = Callable[[str], str | None]
REQUIRED_ENV_NAMES = (
    "KAKAO_SKILL_API_KEY",
    "STG_CUSTOMER_HMAC_KEY",
    "STG_APPROVAL_REF",
    "SUPABASE_URL",
    "SUPABASE_SECRET_KEY",
)


class RuntimeConfigurationError(ValueError):
    """The hosted endpoint is missing required server-side configuration."""


def configuration_ready(getenv: GetEnv = os.environ.get) -> bool:
    return all(bool((getenv(name) or "").strip()) for name in REQUIRED_ENV_NAMES)


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
            table=(
                (getenv("SUPABASE_KAKAO_EVENTS_TABLE") or "").strip()
                or "kakao_cs_events_test"
            ),
        )
        return KakaoSkillApplication(
            adapter,
            sink,
            approval_ref=values["STG_APPROVAL_REF"],
        )
    except (TypeError, ValueError) as exc:
        raise RuntimeConfigurationError(
            "runtime configuration is invalid"
        ) from exc
