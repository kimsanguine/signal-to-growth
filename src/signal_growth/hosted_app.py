"""Hosted WSGI router for health and Kakao Open Builder test requests.

`/api/health` reports two independent checks. `configuration` is readiness —
the required variables exist. `storage` is liveness — Supabase answered a
bounded read-only probe. A configured-but-unreachable service reports
`degraded` with 503 rather than `configured` with 200, because the ingest path
would fail closed in exactly that state.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Iterable, Mapping

from .kakao_runtime import (
    RuntimeConfigurationError,
    build_kakao_skill_application,
    configuration_ready,
    dependency_ready,
)
from .kakao_skill_server import StartResponse


class HostedKakaoApplication:
    """Expose a layered health check and the fail-closed Kakao endpoint."""

    def __init__(
        self,
        *,
        configuration_check: Callable[[], bool] = configuration_ready,
        dependency_check: Callable[[], bool] = dependency_ready,
    ) -> None:
        self._configuration_check = configuration_check
        self._dependency_check = dependency_check

    def __call__(
        self,
        environ: Mapping[str, Any],
        start_response: StartResponse,
    ) -> Iterable[bytes]:
        method = environ.get("REQUEST_METHOD")
        path = environ.get("PATH_INFO")

        if path == "/":
            if method != "GET":
                return self._json_response(
                    start_response,
                    "405 Method Not Allowed",
                    {"error": "method_not_allowed"},
                )
            return self._json_response(
                start_response,
                "200 OK",
                {
                    "name": "Signal to Growth",
                    "status": "alpha",
                    "documentation": (
                        "https://github.com/kimsanguine/signal-to-growth"
                    ),
                    "health": "/api/health",
                    "kakao_skill": "/api/kakao/skill",
                    "external_write": False,
                },
            )

        if path == "/api/health":
            if method != "GET":
                return self._json_response(
                    start_response,
                    "405 Method Not Allowed",
                    {"error": "method_not_allowed"},
                )
            return self._health_response(start_response)

        if path != "/api/kakao/skill":
            return self._json_response(
                start_response,
                "404 Not Found",
                {"error": "not_found"},
            )

        try:
            application = build_kakao_skill_application()
        except RuntimeConfigurationError:
            return self._json_response(
                start_response,
                "503 Service Unavailable",
                {"error": "service_not_configured"},
            )
        return application(environ, start_response)

    def _health_response(self, start_response: StartResponse) -> list[bytes]:
        if not self._configuration_check():
            # Never probe storage without configuration; there is nothing to
            # probe with, and a connection attempt would only mask the cause.
            return self._json_response(
                start_response,
                "503 Service Unavailable",
                self._health_payload(
                    "configuration_required",
                    configuration="missing",
                    storage="skipped",
                ),
            )

        try:
            reachable = self._dependency_check()
        except RuntimeConfigurationError:
            return self._json_response(
                start_response,
                "503 Service Unavailable",
                self._health_payload(
                    "configuration_required",
                    configuration="invalid",
                    storage="skipped",
                ),
            )

        if not reachable:
            return self._json_response(
                start_response,
                "503 Service Unavailable",
                self._health_payload(
                    "degraded",
                    configuration="ready",
                    storage="unreachable",
                ),
            )
        return self._json_response(
            start_response,
            "200 OK",
            self._health_payload(
                "configured",
                configuration="ready",
                storage="reachable",
            ),
        )

    @staticmethod
    def _health_payload(
        status: str,
        *,
        configuration: str,
        storage: str,
    ) -> dict[str, Any]:
        return {
            "status": status,
            "provider": "kakao_openbuilder",
            "storage": "supabase",
            "external_write": False,
            "checks": {
                "configuration": configuration,
                "storage": storage,
            },
        }

    @staticmethod
    def _json_response(
        start_response: StartResponse,
        status: str,
        payload: Mapping[str, Any],
    ) -> list[bytes]:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        start_response(
            status,
            [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Content-Length", str(len(body))),
                ("Cache-Control", "no-store"),
            ],
        )
        return [body]
