from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from shutil import copytree


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.contracts import validate_artifact_directory
from signal_growth.workflow import next_skill, next_skill_reason

FIXTURE_ARTIFACTS = ROOT / "fixtures" / "public-dummy" / "artifacts"
FANOUT_OUTPUTS = ("visual-prompts.md", "video-script.md", "fanout-coverage.md")


def _workspace(directory: Path) -> Path:
    """Copy the public fixture so evidence locators still resolve."""
    artifacts = directory / "artifacts"
    copytree(FIXTURE_ARTIFACTS, artifacts)
    copytree(ROOT / "fixtures" / "public-dummy" / "interviews", directory / "interviews")
    return artifacts


def _brief(artifacts: Path) -> dict:
    return json.loads((artifacts / "content-brief.json").read_text(encoding="utf-8"))


def _write_brief(artifacts: Path, payload: dict) -> None:
    (artifacts / "content-brief.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


class ContentBriefContractTests(unittest.TestCase):
    """A brief decides what gets published, so its sources must be real."""

    def _messages(self, artifacts: Path) -> list[str]:
        return [issue.render() for issue in validate_artifact_directory(artifacts)]

    def test_a_brief_cannot_cite_a_signal_that_does_not_exist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = _workspace(Path(directory))
            payload = _brief(artifacts)
            payload["source_signal_ids"] = ["SIG-20260725-404"]
            _write_brief(artifacts, payload)

            self.assertTrue(
                any(
                    "source_signal_ids references unknown signal ID" in message
                    for message in self._messages(artifacts)
                ),
                self._messages(artifacts),
            )

    def test_a_brief_cannot_cite_an_unapproved_or_restricted_signal(self) -> None:
        """SIG-20260725-002 is a restricted billing dispute awaiting review.

        Existence is not the gate here. A signal a person has not cleared must
        not become the stated reason a public page was written.
        """
        with tempfile.TemporaryDirectory() as directory:
            artifacts = _workspace(Path(directory))
            payload = _brief(artifacts)
            payload["source_signal_ids"] = ["SIG-20260725-002"]
            _write_brief(artifacts, payload)

            self.assertTrue(
                any(
                    "cannot justify public content" in message
                    for message in self._messages(artifacts)
                ),
                self._messages(artifacts),
            )

    def test_a_topic_with_no_recorded_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = _workspace(Path(directory))
            payload = _brief(artifacts)
            payload["source_signal_ids"] = []
            payload["source_observation_ids"] = []
            _write_brief(artifacts, payload)

            self.assertNotEqual([], self._messages(artifacts))

    def test_a_planned_blog_draft_must_name_its_evidence_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = _workspace(Path(directory))
            payload = _brief(artifacts)
            payload["evidence_ids"] = []
            _write_brief(artifacts, payload)

            self.assertNotEqual([], self._messages(artifacts))


class FanoutRoutingTests(unittest.TestCase):
    """The fanout branch reuses a finished draft; it never starts one."""

    def test_a_fanout_objective_routes_to_the_fanout_skill(self) -> None:
        for objective in (
            "OSMU로 콘텐츠 재사용",
            "이미지 프롬프트 만들어줘",
            "run a content fanout",
        ):
            with self.subTest(objective=objective):
                self.assertEqual(
                    "osmu-fanout",
                    next_skill(FIXTURE_ARTIFACTS, objective=objective),
                )

    def test_an_incomplete_draft_routes_back_to_the_draft_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = _workspace(Path(directory))
            (artifacts / "draft.md").unlink()

            objective = "영상 스크립트"
            self.assertEqual(
                "draft-evidence-content",
                next_skill(artifacts, objective=objective),
            )
            self.assertIn("draft.md", next_skill_reason(artifacts, objective=objective))

    def test_a_missing_brief_is_named_as_the_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = _workspace(Path(directory))
            (artifacts / "content-brief.json").unlink()

            objective = "카드뉴스 개요"
            self.assertEqual("osmu-fanout", next_skill(artifacts, objective=objective))
            reason = next_skill_reason(artifacts, objective=objective)
            self.assertIn("content-brief.json", reason)
            self.assertNotIn("visual-prompts.md", reason)

    def test_an_invalid_brief_is_reported_before_missing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = _workspace(Path(directory))
            payload = _brief(artifacts)
            payload["intent"] = "growth-hack"
            _write_brief(artifacts, payload)

            reason = next_skill_reason(artifacts, objective="osmu")
            self.assertIn("fails contract validation", reason)

    def test_a_complete_fanout_does_not_re_route_to_itself(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = _workspace(Path(directory))
            for filename in FANOUT_OUTPUTS:
                (artifacts / filename).write_text("CLM-20260725-002\n", encoding="utf-8")

            self.assertNotEqual(
                "osmu-fanout",
                next_skill(artifacts, objective="osmu 팬아웃"),
            )

    def test_a_fanout_objective_does_not_disturb_other_objectives(self) -> None:
        self.assertEqual(
            "audit-answer-visibility",
            next_skill(Path("/nonexistent"), objective="가시성 감사"),
        )


if __name__ == "__main__":
    unittest.main()
