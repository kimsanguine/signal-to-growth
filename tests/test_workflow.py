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
from signal_growth.schema_validation import validate_schema_record
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

    def test_direct_seeding_does_not_require_a_referral_message_draft(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._workspace(Path(directory))
            (path / "referral-message-drafts.md").unlink(missing_ok=True)

            objective = "첫 5명 직접 시딩을 설계한다"
            self.assertEqual(
                "record-growth-decision",
                next_skill(path, objective=objective),
            )
            self.assertNotIn(
                "referral-message-drafts.md",
                next_skill_reason(path, objective=objective),
            )

    def test_introduction_objective_hands_off_after_direct_seeding(self) -> None:
        """A referral loop starts with measurement, not another direct send."""
        with tempfile.TemporaryDirectory() as directory:
            path = self._workspace(Path(directory))
            loop_path = path / "first-user-loop.json"
            payload = json.loads(loop_path.read_text(encoding="utf-8"))
            payload["loop_mode"] = "direct_seeding"
            payload.pop("introduction_loop", None)
            loop_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            (path / "introduction-loop-metric-recipe.md").unlink()
            (path / "introduction-loop-decision.md").unlink()

            objective = "입소문 소개 루프를 다음 단계로 진행한다"
            self.assertEqual(
                "define-growth-metrics",
                next_skill(path, objective=objective),
            )
            self.assertIn(
                "direct-seeding",
                next_skill_reason(path, objective=objective),
            )

    def test_introduction_objective_routes_to_a_decision_after_metric_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self._workspace(Path(directory))
            (path / "introduction-loop-decision.md").unlink()
            (path / "introduction-loop-metric-recipe.md").write_text(
                "Qualified introduction and first-value definition are drafted.\n",
                encoding="utf-8",
            )

            objective = "입소문 소개 루프를 다음 단계로 진행한다"
            self.assertEqual(
                "record-growth-decision",
                next_skill(path, objective=objective),
            )
            self.assertIn(
                "HOLD",
                next_skill_reason(path, objective=objective),
            )

            (path / "introduction-loop-decision.md").write_text(
                "HOLD and resume decision is awaiting human review.\n",
                encoding="utf-8",
            )
            self.assertIsNone(next_skill(path, objective=objective))


class FirstUserIntroductionContractTests(unittest.TestCase):
    """An introduction loop is still draft-only first-user work."""

    def test_introduction_enabled_loop_accepts_reuse_and_hold_conditions(self) -> None:
        payload = json.loads(
            (
                ROOT / "fixtures" / "public-dummy" / "artifacts" / "first-user-loop.json"
            ).read_text(encoding="utf-8")
        )
        payload["loop_mode"] = "introduction_enabled"
        payload["introduction_loop"] = {
            "activation_event": "첫 evidence-backed decision 승인",
            "reuse_window": "첫 가치 경험 뒤 7일 안에 같은 문제를 다시 해결한다.",
            "referral_eligibility": "첫 가치 경험과 재사용을 모두 확인한 뒤에만 요청한다.",
            "recipient_fit": "같은 업무 상황에서 고객 증거를 정리하는 동료 한 명",
            "landing_handoff": {
                "audience": "고객 증거를 수동으로 정리하는 초기 SaaS 팀",
                "trigger": "인터뷰와 CS 메모가 흩어져 다음 결정을 미루는 순간",
                "promise": "근거와 해석을 분리해 다음 결정을 검토할 수 있게 한다.",
                "evidence_ids": ["EV-20260725-001", "EV-20260725-002"],
                "cta": "내 상황이 맞는지 확인을 요청한다.",
            },
            "hold_conditions": [
                "재사용 증거가 없으면 추천 요청을 보류한다.",
                "공개 가능한 근거가 없으면 사회적 증거를 표시하지 않는다.",
            ],
            "external_write": False,
        }

        self.assertEqual(
            [],
            validate_schema_record("first-user-loop.schema.json", payload),
        )

    def test_content_objective_does_not_disturb_other_objectives(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            self.assertEqual(
                "define-growth-metrics",
                next_skill(path, objective="activation 지표 계약을 설계한다"),
            )

    def test_first_experiment_needs_no_prior_evidence_metric_or_decision(self) -> None:
        """The first batch is often how a founder gets evidence, not a consumer of it."""
        payload = {
            "segment": "동네 카페 사장님 5곳",
            "evidence_basis": "first_experiment",
            "evidence_ids": [],
            "channel": "오프라인 방문 아웃리치",
            "offer": "1주일 무료 체험",
            "value_moment": "체험 종료 후 첫 결제",
            "capacity": 5,
            "budget": {"currency": "KRW", "amount": 0},
            "batch_size": 5,
            "review_at": "2026-09-01T00:00:00+09:00",
            "stop_condition": "5명 응답 없으면 채널을 재검토한다.",
            "external_write": False,
            "metric_ids": [],
            "proposed_metrics": [
                {
                    "name": "첫 결제 도달률",
                    "why_this_metric": "유료 전환이 실제 가치를 얻었다는 가장 직접적인 신호다.",
                    "how_to_measure": "체험 종료 시점에 결제 여부를 수동으로 확인한다.",
                }
            ],
            "decision_id": None,
            "loop_mode": "direct_seeding",
        }
        self.assertEqual(
            [],
            validate_schema_record("first-user-loop.schema.json", payload),
        )

    def test_prior_evidence_basis_still_requires_a_real_evidence_id(self) -> None:
        """Claiming prior evidence without naming any record is not honest labeling."""
        payload = {
            "segment": "동네 카페 사장님 5곳",
            "evidence_basis": "prior_evidence",
            "evidence_ids": [],
            "channel": "오프라인 방문 아웃리치",
            "offer": "1주일 무료 체험",
            "value_moment": "체험 종료 후 첫 결제",
            "capacity": 5,
            "budget": {"currency": "KRW", "amount": 0},
            "batch_size": 5,
            "review_at": "2026-09-01T00:00:00+09:00",
            "stop_condition": "5명 응답 없으면 채널을 재검토한다.",
            "external_write": False,
            "metric_ids": [],
            "proposed_metrics": [
                {
                    "name": "첫 결제 도달률",
                    "why_this_metric": "유료 전환이 실제 가치를 얻었다는 신호다.",
                    "how_to_measure": "수동 확인",
                }
            ],
            "decision_id": None,
            "loop_mode": "direct_seeding",
        }
        self.assertNotEqual(
            [],
            validate_schema_record("first-user-loop.schema.json", payload),
        )

    def test_no_real_or_proposed_metric_fails_validation(self) -> None:
        """A first-user experiment must still say what a good result looks like."""
        payload = {
            "segment": "동네 카페 사장님 5곳",
            "evidence_basis": "first_experiment",
            "evidence_ids": [],
            "channel": "오프라인 방문 아웃리치",
            "offer": "1주일 무료 체험",
            "value_moment": "체험 종료 후 첫 결제",
            "capacity": 5,
            "budget": {"currency": "KRW", "amount": 0},
            "batch_size": 5,
            "review_at": "2026-09-01T00:00:00+09:00",
            "stop_condition": "5명 응답 없으면 채널을 재검토한다.",
            "external_write": False,
            "metric_ids": [],
            "proposed_metrics": [],
            "decision_id": None,
            "loop_mode": "direct_seeding",
        }
        self.assertNotEqual(
            [],
            validate_schema_record("first-user-loop.schema.json", payload),
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
