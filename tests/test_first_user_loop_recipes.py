from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FirstUserLoopRecipeTests(unittest.TestCase):
    """The reusable skill text must keep the direct-seed and referral stages distinct."""

    def test_metric_recipe_names_the_introduction_value_events(self) -> None:
        text = (ROOT / "skills" / "define-growth-metrics" / "SKILL.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("Introduction-loop metric recipe", text)
        for event in (
            "qualified introduction",
            "referred user's first value",
            "referred user's reuse",
            "activation-based loop coefficient",
        ):
            self.assertIn(event, text)

    def test_decision_skill_requires_loop_hold_resume_and_reward_choice(self) -> None:
        text = (ROOT / "skills" / "record-growth-decision" / "SKILL.md").read_text(
            encoding="utf-8"
        ).casefold()

        for field in (
            "loop coefficient",
            "hold condition",
            "resume condition",
            "reward experiment",
        ):
            self.assertIn(field, text)


if __name__ == "__main__":
    unittest.main()
