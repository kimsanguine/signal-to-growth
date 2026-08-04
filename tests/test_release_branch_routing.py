"""Route a release announcement behind the decision log that justifies it.

`announce-release-to-customers` is an optional branch: nothing downstream needs
it, so it is reachable only from a stated objective. That makes two things worth
pinning. A release objective must actually reach the skill — the visibility
audit spent a round silently falling through to the core sequence because it was
missing from `OBJECTIVE_ROUTES`. And it must not be reachable early: a note
written before `record-growth-decision` is complete has no decision log to
describe shipped changes against, so the router sends the run there first.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from shutil import copytree


ROOT = Path(__file__).resolve().parents[1]
import sys  # noqa: E402

sys.path.insert(0, str(ROOT / "src"))

from signal_growth.workflow import (  # noqa: E402
    BRANCH_PREREQUISITES,
    RELEASE_PREREQUISITE,
    RELEASE_SKILL,
    SKILL_OUTPUT_FILES,
    next_skill,
    next_skill_reason,
)


OBJECTIVES = (
    "릴리스 노트 초안",
    "이번 출시 안내 문구 작성",
    "변경 안내 초안",
    "write a release note for v0.4.1",
    "draft a changelog announcement",
)


class ReleaseBranchRoutingTests(unittest.TestCase):
    def _workspace(self, root: Path) -> Path:
        path = root / "artifacts"
        copytree(ROOT / "fixtures" / "public-dummy" / "artifacts", path)
        copytree(ROOT / "fixtures" / "public-dummy" / "interviews", root / "interviews")
        return path

    def test_a_release_objective_reaches_the_release_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._workspace(Path(directory))
            for objective in OBJECTIVES:
                with self.subTest(objective=objective):
                    self.assertEqual(
                        RELEASE_SKILL, next_skill(path, objective=objective)
                    )

    def test_a_release_objective_waits_for_the_decision_log(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._workspace(Path(directory))
            (path / "review-queue.md").unlink()

            objective = "릴리스 노트 초안"
            self.assertEqual(
                RELEASE_PREREQUISITE, next_skill(path, objective=objective)
            )
            reason = next_skill_reason(path, objective=objective)
            self.assertIn(RELEASE_SKILL, reason)
            self.assertIn("review-queue.md", reason)

    def test_an_empty_workspace_does_not_start_with_an_announcement(self) -> None:
        """With no run at all, there is no release to describe."""
        with tempfile.TemporaryDirectory() as directory:
            self.assertNotEqual(
                RELEASE_SKILL,
                next_skill(Path(directory), objective="릴리스 노트 초안"),
            )

    def test_the_release_branch_does_not_capture_other_objectives(self) -> None:
        """A new hint list must not shadow an existing route."""
        with tempfile.TemporaryDirectory() as directory:
            path = self._workspace(Path(directory))
            self.assertEqual(
                "draft-evidence-content",
                next_skill(path, objective="제품 소개 페이지 초안"),
            )
            self.assertEqual(
                "connect-customer-channels",
                next_skill(path, objective="카카오 연결"),
            )
            for objective in (
                "제품 소개 페이지 초안",
                "AI 검색 가시성 점검",
                "카카오 연결",
                "activation 지표 계약을 설계한다",
            ):
                with self.subTest(objective=objective):
                    self.assertNotEqual(
                        RELEASE_SKILL, next_skill(path, objective=objective)
                    )

    def test_every_branch_prerequisite_has_a_completion_rule(self) -> None:
        """A prerequisite absent from SKILL_OUTPUT_FILES cannot be judged done."""
        for branch, prerequisite in BRANCH_PREREQUISITES.items():
            with self.subTest(branch=branch):
                self.assertIn(branch, SKILL_OUTPUT_FILES)
                self.assertIn(prerequisite, SKILL_OUTPUT_FILES)


if __name__ == "__main__":
    unittest.main()
