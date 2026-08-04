import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.hosted_app import HostedKakaoApplication  # noqa: E402
from signal_growth.kakao_runtime import RuntimeConfigurationError  # noqa: E402


class HostedKakaoApplicationTests(unittest.TestCase):
    def setUp(self):
        self.app = HostedKakaoApplication()

    def request(self, method, path, body=b"", headers=None):
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "CONTENT_LENGTH": str(len(body)),
            "wsgi.input": io.BytesIO(body),
        }
        for name, value in (headers or {}).items():
            environ[f"HTTP_{name.upper().replace('-', '_')}"] = value
        captured = {}

        def start_response(status, response_headers):
            captured["status"] = status
            captured["headers"] = dict(response_headers)

        response = b"".join(self.app(environ, start_response))
        return captured, json.loads(response)

    def test_health_fails_closed_without_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            captured, response = self.request("GET", "/api/health")

        self.assertEqual("503 Service Unavailable", captured["status"])
        self.assertEqual("configuration_required", response["status"])
        self.assertFalse(response["external_write"])

    def test_root_exposes_safe_service_metadata(self):
        captured, response = self.request("GET", "/")

        self.assertEqual("200 OK", captured["status"])
        self.assertEqual("Signal to Growth", response["name"])
        self.assertEqual("/api/health", response["health"])
        self.assertFalse(response["external_write"])
        self.assertNotIn("configuration", response)

    def test_unknown_route_is_not_exposed(self):
        captured, response = self.request("GET", "/unknown")

        self.assertEqual("404 Not Found", captured["status"])
        self.assertEqual({"error": "not_found"}, response)

    def test_kakao_endpoint_fails_closed_without_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            captured, response = self.request("POST", "/api/kakao/skill")

        self.assertEqual("503 Service Unavailable", captured["status"])
        self.assertEqual({"error": "service_not_configured"}, response)


class HealthCheckLayeringTests(unittest.TestCase):
    """Configuration readiness and dependency liveness are separate questions."""

    def setUp(self):
        self.probe_calls = 0

    def build(self, *, configured=True, reachable=True, probe_raises=None):
        def configuration_check():
            return configured

        def dependency_check():
            self.probe_calls += 1
            if probe_raises is not None:
                raise probe_raises
            return reachable

        return HostedKakaoApplication(
            configuration_check=configuration_check,
            dependency_check=dependency_check,
        )

    def health(self, app):
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/api/health",
            "CONTENT_LENGTH": "0",
            "wsgi.input": io.BytesIO(b""),
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = dict(headers)

        body = b"".join(app(environ, start_response))
        return captured, json.loads(body)

    def test_reports_configured_only_when_storage_also_answers(self):
        captured, response = self.health(self.build())

        self.assertEqual("200 OK", captured["status"])
        self.assertEqual("configured", response["status"])
        self.assertEqual("ready", response["checks"]["configuration"])
        self.assertEqual("reachable", response["checks"]["storage"])

    def test_present_variables_with_unreachable_storage_report_degraded(self):
        # This is the case the old check could not see: five variables are set,
        # so it answered "configured" while every write would have failed.
        captured, response = self.health(self.build(reachable=False))

        self.assertEqual("503 Service Unavailable", captured["status"])
        self.assertEqual("degraded", response["status"])
        self.assertEqual("ready", response["checks"]["configuration"])
        self.assertEqual("unreachable", response["checks"]["storage"])

    def test_missing_configuration_is_reported_without_probing_storage(self):
        # Probing without configuration would only produce a misleading
        # connection error in place of the real cause.
        captured, response = self.health(self.build(configured=False))

        self.assertEqual("503 Service Unavailable", captured["status"])
        self.assertEqual("configuration_required", response["status"])
        self.assertEqual("skipped", response["checks"]["storage"])
        self.assertEqual(0, self.probe_calls)

    def test_invalid_configuration_does_not_surface_as_a_crash(self):
        app = self.build(
            probe_raises=RuntimeConfigurationError("runtime configuration is invalid")
        )

        captured, response = self.health(app)

        self.assertEqual("503 Service Unavailable", captured["status"])
        self.assertEqual("configuration_required", response["status"])
        self.assertEqual("invalid", response["checks"]["configuration"])

    def test_health_never_advertises_external_writes(self):
        for app in (self.build(), self.build(reachable=False)):
            _, response = self.health(app)
            self.assertFalse(response["external_write"])


if __name__ == "__main__":
    unittest.main()
