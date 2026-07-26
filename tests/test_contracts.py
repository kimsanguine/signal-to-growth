from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
