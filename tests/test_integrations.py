from __future__ import annotations

import json
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


class IntegrationTests(unittest.TestCase):
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
