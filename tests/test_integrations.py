from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth import integrations  # noqa: E402
from signal_growth.append_only import verify_append_chain  # noqa: E402
from signal_growth.integrations import (  # noqa: E402
    CHAINED_INTEGRATION_FILES,
    IntegrationContractError,
    build_hplan_intake,
    build_hplan_reconsideration,
    import_hplan_handoff,
    import_pmf_radar,
)
from signal_growth.schema_validation import validate_schema_record  # noqa: E402


PMF_EXPORT = (
    ROOT
    / "fixtures"
    / "public-dummy"
    / "integrations"
    / "pmf-radar"
    / "stg-export.jsonl"
)
ARTIFACTS = ROOT / "fixtures" / "public-dummy" / "artifacts"
HPLAN_FLOW = ROOT / "fixtures" / "public-dummy" / "integrations" / "hplan"


HPLAN_PROFILE = {
    "profile_version": "0.1",
    "project_id": "synthetic-project-0001",
    "source_system": "hplan",
    "source_record_ref": "hplan://checkpoint/dec-001",
    "handoff_kind": "build_gate_to_growth",
    "status": "build",
    "evidence_refs": [],
    "metric_refs": [],
    "owner": "fixture-owner",
    "review_at": "2026-08-18T09:00:00Z",
}


class IntegrationTests(unittest.TestCase):
    def test_hplan_handoff_is_dry_run_and_never_creates_a_growth_decision(self) -> None:
        """A gate approval may start growth work, but it is not an STG decision.

        Removing the dry-run boundary or projecting the hplan status into a
        local decision must fail this test.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile_path = root / "hplan-profile.json"
            output = root / "stg-import"
            profile_path.write_text(json.dumps(HPLAN_PROFILE), encoding="utf-8")

            report = import_hplan_handoff(profile_path, output_directory=output)

            self.assertFalse(report["write_performed"])
            self.assertEqual("build", report["source_status"])
            self.assertEqual([], report["created_decision_ids"])
            self.assertFalse(output.exists())

    def test_completed_growth_outcome_creates_only_a_human_reconsideration_request(self) -> None:
        """Removing completion checks or emitting a gate verdict must fail.

        The profile points hplan at an STG outcome; it never turns that outcome
        into a new hplan GO/HOLD decision.
        """
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile_path = root / "hplan-profile.json"
            bridge = root / "bridge"
            artifacts = root / "artifacts"
            profile_path.write_text(json.dumps(HPLAN_PROFILE), encoding="utf-8")
            import_hplan_handoff(profile_path, output_directory=bridge, write=True)
            artifacts.mkdir()
            (artifacts / "actions.jsonl").write_text(
                json.dumps(
                    integrations.chain_records([{
                        "action_id": "ACT-20260817-001",
                        "decision_id": "DEC-20260817-001",
                        "created_at": "2026-08-17T08:00:00Z",
                        "action_type": "first_user_experiment",
                        "status": "executed",
                        "owner": "growth-owner",
                        "metric_ids": ["MET-20260817-001"],
                        "external_write": False,
                        "approved_by": "fixture-reviewer",
                    }])[0]
                )
                + "\n",
                encoding="utf-8",
            )
            (artifacts / "outcomes.jsonl").write_text(
                json.dumps(
                    integrations.chain_records([{
                        "outcome_id": "OUT-20260817-001",
                        "action_id": "ACT-20260817-001",
                        "metric_id": "MET-20260817-001",
                        "observed_at": "2026-08-17T09:00:00Z",
                        "value": 4,
                        "sample_size": 12,
                        "maturity_status": "mature",
                        "query_version": "synthetic-v1",
                        "comparison": "worse",
                        "conclusion": "change",
                        "next_decision_id": None,
                        "interpretation": "Synthetic completed cohort needs a human review.",
                        "evidence_ids": [],
                        "recorded_by": "fixture-reviewer",
                    }])[0]
                )
                + "\n",
                encoding="utf-8",
            )

            profile = build_hplan_reconsideration(
                artifacts,
                integration_directory=bridge,
                project_id="synthetic-project-0001",
                owner="growth-owner",
                outcome_id="OUT-20260817-001",
            )

            self.assertEqual("signal-to-growth", profile["source_system"])
            self.assertEqual("growth_outcome_to_reconsideration", profile["handoff_kind"])
            self.assertEqual("COMPLETED", profile["status"])
            self.assertEqual([], profile["evidence_refs"])
            self.assertEqual(["stg://metric/MET-20260817-001"], profile["metric_refs"])
            self.assertNotIn("decision", profile)
            self.assertNotIn("gate_decision", profile)

    def test_hplan_reference_loop_runs_through_the_public_synthetic_fixture(self) -> None:
        """A removed CLI command or an automatic gate verdict must fail.

        This is intentionally a public synthetic loop: approved hplan reference
        -> STG import -> completed experiment outcome -> human reconsideration.
        """
        with tempfile.TemporaryDirectory() as directory:
            bridge = Path(directory) / "bridge"
            imported = subprocess.run(
                [
                    sys.executable,
                    "scripts/stg.py",
                    "import-hplan-handoff",
                    "--input",
                    str(HPLAN_FLOW / "approved-build-gate.json"),
                    "--output-directory",
                    str(bridge),
                    "--write",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, imported.returncode, imported.stderr)

            exported = subprocess.run(
                [
                    sys.executable,
                    "scripts/stg.py",
                    "export-hplan-reconsideration",
                    "--artifacts",
                    str(HPLAN_FLOW / "completed-growth"),
                    "--integration-directory",
                    str(bridge),
                    "--project-id",
                    "synthetic-project-0001",
                    "--owner",
                    "fixture-owner",
                    "--outcome-id",
                    "OUT-20260817-001",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, exported.returncode, exported.stderr)
            profile = json.loads(exported.stdout)
            self.assertEqual("COMPLETED", profile["status"])
            self.assertNotIn("decision", profile)

    def test_hplan_handoff_rejects_malformed_wrong_and_unsafe_profiles(self) -> None:
        """Weakening the accepted hplan envelope must fail these cases."""
        cases = {
            "malformed": "{",
            "wrong-source": {**HPLAN_PROFILE, "source_system": "signal-to-growth"},
            "wrong-kind": {**HPLAN_PROFILE, "handoff_kind": "growth_outcome_to_reconsideration"},
            "wrong-status": {**HPLAN_PROFILE, "status": "GO"},
            "unsafe-reference": {
                **HPLAN_PROFILE,
                "source_record_ref": "hplan://checkpoint/../decision",
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, payload in cases.items():
                with self.subTest(name=name):
                    path = root / f"{name}.json"
                    path.write_text(
                        payload if isinstance(payload, str) else json.dumps(payload),
                        encoding="utf-8",
                    )
                    with self.assertRaises(IntegrationContractError):
                        import_hplan_handoff(path)

    def test_hplan_handoff_replay_is_idempotent_but_conflicts_fail_closed(self) -> None:
        """Dropping replay protection could silently replace source authority."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile_path = root / "profile.json"
            bridge = root / "bridge"
            profile_path.write_text(json.dumps(HPLAN_PROFILE), encoding="utf-8")
            import_hplan_handoff(profile_path, output_directory=bridge, write=True)
            ledger = bridge / "integration-references.jsonl"
            before = ledger.read_bytes()

            replay = import_hplan_handoff(profile_path, output_directory=bridge, write=True)

            self.assertTrue(replay["duplicate"])
            self.assertFalse(replay["write_performed"])
            self.assertEqual(before, ledger.read_bytes())

            profile_path.write_text(
                json.dumps({**HPLAN_PROFILE, "status": "CONDITIONAL_GO"}),
                encoding="utf-8",
            )
            with self.assertRaises(IntegrationContractError):
                import_hplan_handoff(profile_path, output_directory=bridge, write=True)
            self.assertEqual(before, ledger.read_bytes())

    def test_hplan_import_refuses_unsafe_output_paths_without_writing(self) -> None:
        """Allowing traversal or symlink targets would bypass the write boundary."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile_path = root / "profile.json"
            profile_path.write_text(json.dumps(HPLAN_PROFILE), encoding="utf-8")
            escaped = root / "escaped"
            with self.assertRaises(IntegrationContractError):
                import_hplan_handoff(
                    profile_path,
                    output_directory=root / "safe" / ".." / "escaped",
                    write=True,
                )
            self.assertFalse(escaped.exists())

            target = root / "target"
            target.mkdir()
            linked = root / "linked"
            linked.symlink_to(target, target_is_directory=True)
            with self.assertRaises(IntegrationContractError):
                import_hplan_handoff(profile_path, output_directory=linked, write=True)
            self.assertFalse((target / "integration-references.jsonl").exists())

            bridge = root / "bridge"
            bridge.mkdir()
            linked_ledger = bridge / "integration-references.jsonl"
            linked_ledger.symlink_to(root / "outside-ledger.jsonl")
            with self.assertRaises(IntegrationContractError):
                import_hplan_handoff(profile_path, output_directory=bridge, write=True)
            self.assertFalse((root / "outside-ledger.jsonl").exists())

    def test_reconsideration_refuses_an_incomplete_outcome(self) -> None:
        """Treating a not-mature cohort as completed would create false certainty."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile_path = root / "profile.json"
            bridge = root / "bridge"
            artifacts = root / "artifacts"
            profile_path.write_text(json.dumps(HPLAN_PROFILE), encoding="utf-8")
            import_hplan_handoff(profile_path, output_directory=bridge, write=True)
            shutil.copytree(HPLAN_FLOW / "completed-growth", artifacts)
            outcome_path = artifacts / "outcomes.jsonl"
            outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
            outcome["maturity_status"] = "not_mature"
            outcome_path.write_text(json.dumps(outcome) + "\n", encoding="utf-8")

            with self.assertRaises(IntegrationContractError):
                build_hplan_reconsideration(
                    artifacts,
                    integration_directory=bridge,
                    project_id="synthetic-project-0001",
                    owner="growth-owner",
                    outcome_id="OUT-20260817-001",
                )

    def test_reconsideration_refuses_a_tampered_outcome_ledger(self) -> None:
        """Removing the append-chain check would accept rewritten outcomes."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile_path = root / "profile.json"
            bridge = root / "bridge"
            artifacts = root / "artifacts"
            profile_path.write_text(json.dumps(HPLAN_PROFILE), encoding="utf-8")
            import_hplan_handoff(profile_path, output_directory=bridge, write=True)
            shutil.copytree(HPLAN_FLOW / "completed-growth", artifacts)
            outcome_path = artifacts / "outcomes.jsonl"
            outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
            outcome["value"] = 999
            outcome_path.write_text(json.dumps(outcome) + "\n", encoding="utf-8")

            with self.assertRaises(IntegrationContractError):
                build_hplan_reconsideration(
                    artifacts,
                    integration_directory=bridge,
                    project_id="synthetic-project-0001",
                    owner="growth-owner",
                    outcome_id="OUT-20260817-001",
                )

    def test_pmf_import_is_dry_run_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            report = import_pmf_radar(
                PMF_EXPORT,
                output_directory=output,
            )

            self.assertEqual(1, report["imported_events"])
            self.assertFalse(report["write_performed"])
            self.assertEqual([], list(output.iterdir()))

    def test_pmf_import_writes_only_validated_bridge_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            report = import_pmf_radar(
                PMF_EXPORT,
                output_directory=output,
                write=True,
            )

            self.assertTrue(report["write_performed"])
            self.assertTrue((output / "cs-events.jsonl").is_file())
            refs = [
                json.loads(line)
                for line in (output / "integration-references.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(1, len(refs))
            self.assertEqual("pmf_radar", refs[0]["system"])
            self.assertEqual(
                "ref:pmf_radar_inbox_001",
                refs[0]["source_record_ref"],
            )
            self.assertEqual(
                [],
                validate_schema_record(
                    "integration-reference.schema.json",
                    refs[0],
                ),
            )

    def test_pmf_import_rejects_raw_identifier_fields(self) -> None:
        record = json.loads(PMF_EXPORT.read_text(encoding="utf-8"))
        record["event"]["recipient_no"] = "synthetic-raw-identifier"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unsafe.jsonl"
            path.write_text(
                json.dumps(record, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(IntegrationContractError):
                import_pmf_radar(path)

    def test_emitted_ledgers_carry_a_verifiable_chain(self) -> None:
        """This module is the only writer of `integration-references.jsonl`.

        If it does not recompute the chain, nothing in the repository ever does
        and the hashes it emits are decoration rather than tamper evidence.
        """
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            import_pmf_radar(PMF_EXPORT, output_directory=output, write=True)

            for filename in CHAINED_INTEGRATION_FILES:
                with self.subTest(filename=filename):
                    records = [
                        json.loads(line)
                        for line in (output / filename)
                        .read_text(encoding="utf-8")
                        .splitlines()
                        if line.strip()
                    ]
                    self.assertTrue(records)
                    self.assertEqual([], verify_append_chain(records, filename))

    def test_an_unchained_render_is_refused_instead_of_written(self) -> None:
        """Prove the chain check can fail, so it is not a decorative call.

        Simulating a defect in the chaining writer is the only way to reach it:
        with `chain_records` working, the check passes by construction and a
        broken one would otherwise ship silently.
        """
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            original = integrations.chain_records
            integrations.chain_records = lambda records: list(records)
            try:
                with self.assertRaises(IntegrationContractError) as caught:
                    import_pmf_radar(PMF_EXPORT, output_directory=output, write=True)
            finally:
                integrations.chain_records = original

            self.assertIn("record_hash is missing", str(caught.exception))
            self.assertEqual([], list(output.iterdir()))

    def test_hplan_intake_keeps_unknowns_and_never_claims_gate_decision(self) -> None:
        brief = build_hplan_intake(
            ARTIFACTS,
            generated_at="2026-07-26T00:00:00Z",
        )

        self.assertEqual("draft_for_gate", brief["status"])
        self.assertIsNone(brief["hplan_gate_decision"])
        self.assertIn("product_name", brief["unknown_fields"])
        self.assertTrue(brief["not_build"])

    def test_hplan_intake_can_be_ready_for_human_gate_review(self) -> None:
        brief = build_hplan_intake(
            ARTIFACTS,
            product_name="Signal to Growth",
            jtbd="고객 근거를 잃지 않고 다음 성장 결정을 내린다.",
            functional_requirements=("근거 ID를 결정과 연결한다.",),
            cogs_ceiling="사람이 설정할 프로젝트 정책",
            latency_budget="비동기 분석, 사용자 설정",
            counter_position="상담 자동화가 아니라 근거 계보를 관리한다.",
            mvp_slice="한 고객 신호를 승인된 결정까지 연결한다.",
            generated_at="2026-07-26T00:00:00Z",
        )

        self.assertEqual("ready_for_gate_review", brief["status"])
        self.assertEqual([], brief["unknown_fields"])
        self.assertIsNone(brief["hplan_gate_decision"])
        self.assertEqual(
            [],
            validate_schema_record("hplan-intake-brief.schema.json", brief),
        )


if __name__ == "__main__":
    unittest.main()
