from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.privacy import scan_path, scan_text


class PrivacyTests(unittest.TestCase):
    def test_public_fixture_has_no_supported_private_pattern(self) -> None:
        findings = scan_path(
            ROOT
            / "fixtures"
            / "public-dummy"
            / "interviews"
            / "P-20260725-001.md"
        )
        self.assertEqual([], findings)

    def test_findings_report_type_and_line_without_value(self) -> None:
        findings = scan_text("first line\nperson@example.com\n010-1234-5678")
        self.assertEqual(["email", "korean-mobile"], [item.kind for item in findings])
        rendered = "\n".join(item.render(Path("sample.txt")) for item in findings)
        self.assertNotIn("person@example.com", rendered)
        self.assertNotIn("010-1234-5678", rendered)


if __name__ == "__main__":
    unittest.main()
