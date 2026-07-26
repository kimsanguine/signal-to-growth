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

    def test_unknown_route_is_not_exposed(self):
        captured, response = self.request("GET", "/")

        self.assertEqual("404 Not Found", captured["status"])
        self.assertEqual({"error": "not_found"}, response)

    def test_kakao_endpoint_fails_closed_without_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            captured, response = self.request("POST", "/api/kakao/skill")

        self.assertEqual("503 Service Unavailable", captured["status"])
        self.assertEqual({"error": "service_not_configured"}, response)


if __name__ == "__main__":
    unittest.main()
