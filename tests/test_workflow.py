from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from shutil import copy2, copytree
import json


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.workflow import completed_skills, next_skill, next_skill_reason


class WorkflowTests(unittest.TestCase):
    def test_empty_workspace_starts_with_reach(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            self.assertEqual("plan-customer-reach", next_skill(path))
            self.assertEqual([], completed_skills(path))

    def test_outcome_review_fixture_routes_to_follow_up_decision(self) -> None:
        path = ROOT / "fixtures" / "public-dummy" / "artifacts"
        self.assertEqual("record-growth-decision", next_skill(path))
        self.assertEqual(7, len(completed_skills(path)))

    def test_partial_connector_routes_to_connector_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for filename in ("reach-plan.json", "interview-guide.md", "evidence.jsonl"):
                (path / filename).touch()
            (path / "channel-connection.json").touch()

            self.assertEqual("connect-customer-channels", next_skill(path))
            self.assertEqual(0, len(completed_skills(path)))

    def test_complete_connector_hands_off_to_signal_triage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            source = ROOT / "fixtures" / "public-dummy" / "connector-artifacts"
            for filename in (
                "channel-connection.json",
                "cs-events.jsonl",
                "connector-state.json",
            ):
                copy2(source / filename, path / filename)

            self.assertEqual("triage-customer-signals", next_skill(path))
            self.assertEqual(["connect-customer-channels"], completed_skills(path))

    def test_objective_can_route_directly_to_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            self.assertEqual(
                "define-growth-metrics",
                next_skill(path, objective="activation 지표 계약을 설계한다"),
            )

    def test_reason_matches_empty_workspace_routing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            reason = next_skill_reason(path)
            self.assertIn("reach-plan.json", reason)

    def test_reason_explains_why_outcome_review_needs_a_decision(self) -> None:
        path = ROOT / "fixtures" / "public-dummy" / "artifacts"
        reason = next_skill_reason(path)
        self.assertIn("not mature", reason)
        self.assertIn("follow-up decision", reason)

    def test_active_complete_artifacts_without_an_outcome_review_have_no_next_skill(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "artifacts"
            copytree(ROOT / "fixtures" / "public-dummy" / "artifacts", path)
            copytree(ROOT / "fixtures" / "public-dummy" / "interviews", root / "interviews")
            (path / "outcomes.jsonl").unlink()
            (path / "run-state.json").unlink()

            self.assertIsNone(next_skill(path))
            self.assertIn("no required next skill", next_skill_reason(path))

    def test_reason_explains_partial_connector_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for filename in ("reach-plan.json", "interview-guide.md", "evidence.jsonl"):
                (path / filename).touch()
            (path / "channel-connection.json").touch()

            reason = next_skill_reason(path)
            self.assertIn("partial", reason)

    def test_missing_companion_output_keeps_the_specialist_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "artifacts"
            copytree(ROOT / "fixtures" / "public-dummy" / "artifacts", path)
            copytree(ROOT / "fixtures" / "public-dummy" / "interviews", root / "interviews")
            (path / "theme-cards.md").unlink()

            self.assertEqual("synthesize-interviews", next_skill(path))
            self.assertIn("theme-cards.md", next_skill_reason(path))
            self.assertNotIn("synthesize-interviews", completed_skills(path))

    def test_awaiting_human_evidence_routes_back_to_synthesis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "artifacts"
            copytree(ROOT / "fixtures" / "public-dummy" / "artifacts", path)
            copytree(ROOT / "fixtures" / "public-dummy" / "interviews", root / "interviews")
            evidence_path = path / "evidence.jsonl"
            records = [json.loads(line) for line in evidence_path.read_text(encoding="utf-8").splitlines()]
            records[0]["strength"] = "awaiting_human_tag"
            records[0]["approved_by"] = None
            evidence_path.write_text(
                "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
                encoding="utf-8",
            )

            self.assertEqual("synthesize-interviews", next_skill(path))
            self.assertIn("awaiting human strength approval", next_skill_reason(path))
            self.assertNotIn("synthesize-interviews", completed_skills(path))


if __name__ == "__main__":
    unittest.main()
