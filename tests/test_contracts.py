from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from shutil import copytree


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.contracts import validate_artifact_directory, validate_record


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

    def test_schema_rejects_unknown_evidence_fields(self) -> None:
        record = json.loads(
            (
                ROOT
                / "fixtures"
                / "public-dummy"
                / "artifacts"
                / "evidence.jsonl"
            )
            .read_text(encoding="utf-8")
            .splitlines()[0]
        )
        record["unexpected"] = "not allowed"
        issues = validate_record("evidence", record, "evidence[1]")
        self.assertTrue(
            any("Additional properties" in issue.message for issue in issues),
            [issue.render() for issue in issues],
        )

    def test_evidence_locator_must_match_source_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_dir = root / "artifacts"
            source_dir = root / "interviews"
            artifact_dir.mkdir()
            source_dir.mkdir()
            (source_dir / "source.md").write_text(
                "첫 줄\n실제 고객 발화\n",
                encoding="utf-8",
            )
            record = {
                "evidence_id": "EV-20260726-001",
                "source_id": "SRC-001",
                "participant_id": "P-001",
                "source_type": "interview",
                "observed_at": "2026-07-26T00:00:00Z",
                "excerpt": "실제 고객 발화",
                "locator": {"file": "../interviews/source.md", "line": 1},
                "interpretation": "테스트",
                "strength": "awaiting_human_tag",
                "privacy": "internal",
                "created_by": "human",
                "approved_by": None,
            }
            (artifact_dir / "evidence.jsonl").write_text(
                json.dumps(record, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            issues = validate_artifact_directory(artifact_dir)
            self.assertTrue(
                any("does not match" in issue.message for issue in issues),
                [issue.render() for issue in issues],
            )

    def test_signal_cannot_reference_evidence_awaiting_human_strength_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_dir = root / "artifacts"
            copytree(ROOT / "fixtures" / "public-dummy" / "artifacts", artifact_dir)
            copytree(ROOT / "fixtures" / "public-dummy" / "interviews", root / "interviews")
            evidence_path = artifact_dir / "evidence.jsonl"
            records = [json.loads(line) for line in evidence_path.read_text(encoding="utf-8").splitlines()]
            records[1]["strength"] = "awaiting_human_tag"
            records[1]["approved_by"] = None
            evidence_path.write_text(
                "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
                encoding="utf-8",
            )

            issues = validate_artifact_directory(artifact_dir)
            self.assertTrue(
                any(
                    "source_evidence_ids references evidence awaiting human strength approval"
                    in issue.message
                    for issue in issues
                ),
                [issue.render() for issue in issues],
            )

    def test_external_write_approval_requires_scoped_reference(self) -> None:
        record = {
            "action_id": "ACT-20260726-001",
            "decision_id": "DEC-20260726-001",
            "created_at": "2026-07-26T00:00:00Z",
            "action_type": "publish_content",
            "status": "approved",
            "owner": "owner",
            "metric_ids": ["MET-20260726-001"],
            "external_write": True,
            "approved_by": "model-self-approved",
        }
        issues = validate_record("action", record, "action[1]")
        self.assertTrue(
            any("APR-" in issue.message for issue in issues),
            [issue.render() for issue in issues],
        )

    def test_external_write_rejects_unregistered_apr_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact_dir = Path(directory)
            record = {
                "action_id": "ACT-20260726-001",
                "decision_id": "DEC-20260726-001",
                "created_at": "2026-07-26T00:00:00Z",
                "action_type": "publish_content",
                "status": "approved",
                "owner": "owner",
                "metric_ids": ["MET-20260726-001"],
                "external_write": True,
                "approved_by": "APR-MODEL-SELF",
            }
            (artifact_dir / "actions.jsonl").write_text(
                json.dumps(record) + "\n",
                encoding="utf-8",
            )

            issues = validate_artifact_directory(artifact_dir)
            self.assertTrue(
                any("unknown approval ID" in issue.message for issue in issues),
                [issue.render() for issue in issues],
            )

    def test_approval_artifact_rejects_model_as_approver(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact_dir = Path(directory)
            approval = {
                "approval_id": "APR-20260726-001",
                "decided_at": "2026-07-26T00:00:00Z",
                "approver_id": "claude",
                "approver_type": "model",
                "user_turn_ref": "TURN-001",
                "status": "approved",
                "scope": {
                    "decision_ids": [],
                    "action_ids": ["ACT-20260726-001"],
                    "external_write": True,
                    "expires_at": None,
                },
            }
            (artifact_dir / "approvals.jsonl").write_text(
                json.dumps(approval) + "\n",
                encoding="utf-8",
            )

            issues = validate_artifact_directory(artifact_dir)
            self.assertTrue(
                any("approver_type" in issue.message for issue in issues),
                [issue.render() for issue in issues],
            )

    def test_external_write_approval_must_cover_the_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact_dir = Path(directory)
            action = {
                "action_id": "ACT-20260726-001",
                "decision_id": "DEC-20260726-001",
                "created_at": "2026-07-26T00:00:00Z",
                "action_type": "publish_content",
                "status": "approved",
                "owner": "owner",
                "metric_ids": ["MET-20260726-001"],
                "external_write": True,
                "approved_by": "APR-20260726-001",
            }
            approval = {
                "approval_id": "APR-20260726-001",
                "decided_at": "2026-07-26T00:00:00Z",
                "approver_id": "instructor",
                "approver_type": "human",
                "user_turn_ref": "TURN-001",
                "status": "approved",
                "scope": {
                    "decision_ids": [],
                    "action_ids": ["ACT-20260726-999"],
                    "external_write": True,
                    "expires_at": None,
                },
            }
            (artifact_dir / "actions.jsonl").write_text(
                json.dumps(action) + "\n",
                encoding="utf-8",
            )
            (artifact_dir / "approvals.jsonl").write_text(
                json.dumps(approval) + "\n",
                encoding="utf-8",
            )

            issues = validate_artifact_directory(artifact_dir)
            self.assertTrue(
                any("does not cover action" in issue.message for issue in issues),
                [issue.render() for issue in issues],
            )

    def test_approved_decision_rejects_unregistered_apr_reference(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact_dir = Path(directory)
            decision = {
                "decision_id": "DEC-20260726-001",
                "made_at": "2026-07-26T00:00:00Z",
                "status": "approved",
                "decision_question": "가격 정책을 변경할 것인가?",
                "selected_option": "보류",
                "hypothesis": "추가 근거가 필요하다.",
                "evidence_ids": ["EV-20260726-001"],
                "counterevidence": [],
                "alternatives": ["변경하지 않는다."],
                "not_build": ["즉시 가격 변경"],
                "reversibility": "hard_to_reverse",
                "owner": "owner",
                "review_at": "2026-08-26T00:00:00Z",
                "success_condition": "사람이 승인한다.",
                "stop_condition": "승인이 없다.",
                "causal_confidence": "low",
                "approved_by": "APR-MODEL-SELF",
                "supersedes": None,
            }
            (artifact_dir / "decisions.jsonl").write_text(
                json.dumps(decision, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            issues = validate_artifact_directory(artifact_dir)
            self.assertTrue(
                any("unknown approval ID" in issue.message for issue in issues),
                [issue.render() for issue in issues],
            )

    def test_decision_approval_must_cover_the_decision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact_dir = Path(directory)
            source_decision = json.loads(
                (ROOT / "fixtures/public-dummy/artifacts/decisions.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()[0]
            )
            source_decision["approved_by"] = "APR-20260726-001"
            approval = {
                "approval_id": "APR-20260726-001",
                "decided_at": "2026-07-26T00:00:00Z",
                "approver_id": "instructor",
                "approver_type": "human",
                "user_turn_ref": "TURN-001",
                "status": "approved",
                "scope": {
                    "decision_ids": ["DEC-20260726-999"],
                    "action_ids": [],
                    "external_write": False,
                    "expires_at": None,
                },
            }
            (artifact_dir / "decisions.jsonl").write_text(
                json.dumps(source_decision, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (artifact_dir / "approvals.jsonl").write_text(
                json.dumps(approval) + "\n",
                encoding="utf-8",
            )

            issues = validate_artifact_directory(artifact_dir)
            self.assertTrue(
                any("does not cover decision" in issue.message for issue in issues),
                [issue.render() for issue in issues],
            )


if __name__ == "__main__":
    unittest.main()
