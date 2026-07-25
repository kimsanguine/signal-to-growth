from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.workflow import completed_skills, next_skill


class WorkflowTests(unittest.TestCase):
    def test_empty_workspace_starts_with_reach(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            self.assertEqual("plan-customer-reach", next_skill(path))
            self.assertEqual([], completed_skills(path))

    def test_completed_fixture_has_no_missing_specialist_skill(self) -> None:
        path = ROOT / "fixtures" / "public-dummy" / "artifacts"
        self.assertIsNone(next_skill(path))
        self.assertEqual(9, len(completed_skills(path)))


if __name__ == "__main__":
    unittest.main()
