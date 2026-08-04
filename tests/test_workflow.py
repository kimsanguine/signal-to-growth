from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from shutil import copy2, copytree
import json


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.append_only import chain_records
from signal_growth.workflow import completed_skills, next_skill, next_skill_reason


def _write_chained(path: Path, records: list[dict]) -> None:
    """Write a mutated artifact back as a valid append chain.

    These tests simulate a workspace that legitimately reached a different
    state, not one whose history was rewritten. Writing the edited records back
    without relinking them would trip the tamper-evidence check instead of the
    routing behavior under test.
    """
    path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False) + "\n"
            for record in chain_records(records)
        ),
        encoding="utf-8",
    )


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
            _write_chained(evidence_path, records)

            self.assertEqual("synthesize-interviews", next_skill(path))
            self.assertIn("awaiting human strength approval", next_skill_reason(path))
            self.assertNotIn("synthesize-interviews", completed_skills(path))


class VisibilityBranchRoutingTests(unittest.TestCase):
    """run-growth-loop declares this skill as a routing node, so it must route.

    While it was absent from OBJECTIVE_ROUTES and SKILL_OUTPUT_FILES, a
    visibility objective silently fell through to the core sequence and the
    three-way output-contract drift check degraded to a two-way one.
    """

    def test_a_visibility_objective_routes_to_the_visibility_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for objective in (
                "AI 검색 가시성 점검",
                "run an answer engine visibility audit",
                "우리 제품 인용 현황 확인",
            ):
                self.assertEqual(
                    "audit-answer-visibility",
                    next_skill(path, objective=objective),
                    objective,
                )

    def test_an_incomplete_visibility_audit_names_its_missing_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifacts"
            copytree(ROOT / "fixtures" / "public-dummy" / "artifacts", path)
            (path / "citation-gaps.md").unlink()

            objective = "가시성 감사"
            self.assertEqual("audit-answer-visibility", next_skill(path, objective=objective))
            self.assertIn("citation-gaps.md", next_skill_reason(path, objective=objective))

    def test_a_complete_visibility_audit_does_not_re_route_to_itself(self) -> None:
        path = ROOT / "fixtures" / "public-dummy" / "artifacts"
        self.assertNotEqual(
            "audit-answer-visibility",
            next_skill(path, objective="가시성 감사"),
        )


class ContentBranchRoutingTests(unittest.TestCase):
    """A product introduction page must describe a validated first-user loop."""

    def _workspace(self, root: Path) -> Path:
        path = root / "artifacts"
        copytree(ROOT / "fixtures" / "public-dummy" / "artifacts", path)
        copytree(ROOT / "fixtures" / "public-dummy" / "interviews", root / "interviews")
        return path

    def test_content_objective_routes_to_content_when_the_loop_is_complete(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._workspace(Path(directory))

            for objective in ("제품 소개 페이지 초안", "write a landing page draft"):
                self.assertEqual(
                    "draft-evidence-content",
                    next_skill(path, objective=objective),
                    objective,
                )

    def test_content_objective_falls_back_to_the_first_user_loop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._workspace(Path(directory))
            (path / "experiment-cards.md").unlink()

            objective = "제품 소개 페이지 초안"
            self.assertEqual(
                "design-first-user-loop", next_skill(path, objective=objective)
            )
            reason = next_skill_reason(path, objective=objective)
            self.assertIn("draft-evidence-content", reason)
            self.assertIn("experiment-cards.md", reason)

    def test_content_objective_does_not_disturb_other_objectives(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            self.assertEqual(
                "define-growth-metrics",
                next_skill(path, objective="activation 지표 계약을 설계한다"),
            )


class ApprovalWaitReasonTests(unittest.TestCase):
    """Waiting for a person is not the same as a forgotten output artifact."""

    def _awaiting_approval_workspace(self, root: Path) -> Path:
        """Build the state a learner actually reaches: drafted, not yet approved."""
        path = root / "artifacts"
        copytree(ROOT / "fixtures" / "public-dummy" / "artifacts", path)
        copytree(ROOT / "fixtures" / "public-dummy" / "interviews", root / "interviews")

        for filename, pending_status in (
            ("decisions.jsonl", "awaiting_human_review"),
            ("actions.jsonl", "draft"),
        ):
            target = path / filename
            records = [
                json.loads(line)
                for line in target.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            for record in records:
                if str(record.get("approved_by", "")).startswith("APR-"):
                    record["status"] = pending_status
                    record["approved_by"] = None
            _write_chained(target, records)
        (path / "approvals.jsonl").unlink()
        return path

    def test_missing_approval_reads_as_awaiting_human_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._awaiting_approval_workspace(Path(directory))

            self.assertEqual("record-growth-decision", next_skill(path))
            reason = next_skill_reason(path)
            self.assertIn("awaiting human approval in a later user turn", reason)
            self.assertNotIn("missing required output-contract artifacts", reason)

    def test_other_missing_outputs_are_still_reported_separately(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._awaiting_approval_workspace(Path(directory))
            (path / "review-queue.md").unlink()

            reason = next_skill_reason(path)
            self.assertIn("missing required output-contract artifacts", reason)
            self.assertIn("review-queue.md", reason)
            self.assertIn("awaiting human approval in a later user turn", reason)


class ConnectorObjectiveTests(unittest.TestCase):
    """A connector objective must route, not crash.

    `connect-customer-channels` is deliberately absent from SKILL_OUTPUT_FILES
    because its artifacts are governed by the connector contract rather than by
    a routed output contract. The objective branch forgot that and indexed the
    table directly, so every connector hint raised KeyError before any user saw
    a routing answer.
    """

    def test_every_connector_objective_hint_routes_without_raising(self) -> None:
        path = ROOT / "fixtures" / "public-dummy" / "artifacts"
        for objective in ("카카오 연결", "connector 설정", "webhook", "channel talk"):
            with self.subTest(objective=objective):
                self.assertEqual(
                    "connect-customer-channels",
                    next_skill(path, objective=objective),
                )
                self.assertIn(
                    "connect-customer-channels",
                    next_skill_reason(path, objective=objective),
                )

    def test_an_unconfigured_connector_is_named_as_the_reason(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            reason = next_skill_reason(path, objective="카카오 연결")
            self.assertIn("not-configured", reason)

    def test_a_valid_connector_objective_hands_off_instead_of_looping(self) -> None:
        """Asking to connect what is already connected must not re-route there."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            source = ROOT / "fixtures" / "public-dummy" / "connector-artifacts"
            for item in source.iterdir():
                copy2(item, path / item.name)

            self.assertNotEqual(
                "connect-customer-channels",
                next_skill(path, objective="카카오 연결"),
            )

    def test_every_routable_objective_target_can_be_judged_complete(self) -> None:
        """The KeyError came from a routing target with no completion rule.

        Asserting the table agreement here means adding a future objective
        route without a completion rule fails a test instead of a user's run.
        """
        from signal_growth.workflow import (
            CONNECTOR_SKILL,
            OBJECTIVE_ROUTES,
            SKILL_OUTPUT_FILES,
        )

        for _, skill in OBJECTIVE_ROUTES:
            with self.subTest(skill=skill):
                self.assertTrue(skill == CONNECTOR_SKILL or skill in SKILL_OUTPUT_FILES)


if __name__ == "__main__":
    unittest.main()
