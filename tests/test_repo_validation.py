from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.repo_validation import validate_repository


class RepositoryValidationTests(unittest.TestCase):
    def test_repository_structure_is_valid(self) -> None:
        issues = validate_repository(ROOT)
        self.assertEqual([], issues, [issue.render() for issue in issues])


if __name__ == "__main__":
    unittest.main()
