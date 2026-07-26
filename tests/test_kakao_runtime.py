import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.kakao_runtime import (  # noqa: E402
    RuntimeConfigurationError,
    build_kakao_skill_application,
    configuration_ready,
)
from signal_growth.kakao_skill_server import KakaoSkillApplication  # noqa: E402


class KakaoRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.values = {
            "KAKAO_SKILL_API_KEY": "k" * 32,
            "STG_CUSTOMER_HMAC_KEY": "h" * 32,
            "STG_APPROVAL_REF": "APR-KAKAO-TEST-001",
            "SUPABASE_URL": "https://project-ref.supabase.co",
            "SUPABASE_SECRET_KEY": "sb_secret_public_dummy",
        }

    def getenv(self, name):
        return self.values.get(name)

    def test_builds_application_only_when_required_configuration_exists(self):
        self.assertTrue(configuration_ready(self.getenv))
        self.assertIsInstance(
            build_kakao_skill_application(self.getenv),
            KakaoSkillApplication,
        )

    def test_missing_configuration_fails_closed(self):
        del self.values["SUPABASE_SECRET_KEY"]

        self.assertFalse(configuration_ready(self.getenv))
        with self.assertRaises(RuntimeConfigurationError):
            build_kakao_skill_application(self.getenv)

    def test_short_shared_key_fails_closed(self):
        self.values["KAKAO_SKILL_API_KEY"] = "too-short"

        with self.assertRaises(RuntimeConfigurationError):
            build_kakao_skill_application(self.getenv)

    def test_invalid_supabase_url_fails_as_configuration_error(self):
        self.values["SUPABASE_URL"] = "http://project-ref.supabase.co"

        with self.assertRaises(RuntimeConfigurationError):
            build_kakao_skill_application(self.getenv)

    def test_invalid_approval_reference_fails_as_configuration_error(self):
        self.values["STG_APPROVAL_REF"] = "approval-without-prefix"

        with self.assertRaises(RuntimeConfigurationError):
            build_kakao_skill_application(self.getenv)


if __name__ == "__main__":
    unittest.main()
