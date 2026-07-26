"""Hosted WSGI router for health and Kakao Open Builder test requests."""

from __future__ import annotations

import json
from typing import Any, Iterable, Mapping

from .kakao_runtime import (
    RuntimeConfigurationError,
    build_kakao_skill_application,
    configuration_ready,
)
from .kakao_skill_server import StartResponse


class HostedKakaoApplication:
    """Expose a configuration health check and the fail-closed Kakao endpoint."""

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
            ready = configuration_ready()
            return self._json_response(
                start_response,
                "200 OK" if ready else "503 Service Unavailable",
                {
                    "status": (
                        "configured" if ready else "configuration_required"
                    ),
                    "provider": "kakao_openbuilder",
                    "storage": "supabase",
                    "external_write": False,
                },
            )

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
