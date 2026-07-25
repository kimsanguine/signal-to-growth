from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.questions import lint_questions


class QuestionLintTests(unittest.TestCase):
    def test_behavior_questions_pass(self) -> None:
        text = (ROOT / "fixtures" / "public-dummy" / "questions-good.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual([], lint_questions(text))

    def test_leading_and_hypothetical_questions_fail(self) -> None:
        text = (ROOT / "fixtures" / "negative" / "questions-leading.md").read_text(
            encoding="utf-8"
        )
        rules = {issue.rule for issue in lint_questions(text)}
        self.assertIn("leading", rules)
        self.assertIn("hypothetical", rules)
        self.assertIn("solution-first", rules)


if __name__ == "__main__":
    unittest.main()
