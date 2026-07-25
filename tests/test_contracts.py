from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.contracts import validate_artifact_directory


class ContractValidationTests(unittest.TestCase):
    def test_public_dummy_artifacts_are_complete_and_valid(self) -> None:
        issues = validate_artifact_directory(
            ROOT / "fixtures" / "public-dummy" / "artifacts",
            require_complete=True,
        )
        self.assertEqual([], issues, [issue.render() for issue in issues])

    def test_unknown_evidence_reference_fails(self) -> None:
        issues = validate_artifact_directory(ROOT / "fixtures" / "negative")
        messages = [issue.render() for issue in issues]
        self.assertTrue(
            any("unknown evidence ID" in message for message in messages),
            messages,
        )


if __name__ == "__main__":
    unittest.main()
