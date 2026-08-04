from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.append_only import (
    APPEND_ONLY_FILES,
    AppendOnlyError,
    append_record,
    compute_record_hash,
)
from signal_growth.connector_validation import _CHAINED_CONNECTOR_FILES
from signal_growth.contracts import (
    ARTIFACT_KIND_FILES,
    CHAINED_KINDS,
    _check_append_chain,
)
from signal_growth.integrations import CHAINED_INTEGRATION_FILES


def _records(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class AppendOnlyTests(unittest.TestCase):
    def test_appends_a_single_line_and_returns_new_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.jsonl"
            self.assertEqual(1, append_record(path, {"evidence_id": "EV-20260728-001"}))
            self.assertEqual(2, append_record(path, {"evidence_id": "EV-20260728-002"}))
            records = _records(path)
            self.assertEqual(2, len(records))
            self.assertEqual("EV-20260728-001", records[0]["evidence_id"])

    def test_preserves_existing_lines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decisions.jsonl"
            path.write_text('{"decision_id": "DEC-20260728-001"}\n', encoding="utf-8")
            append_record(path, {"decision_id": "DEC-20260728-002"})
            records = _records(path)
            self.assertEqual(2, len(records))
            self.assertEqual(
                {"decision_id": "DEC-20260728-001"}, records[0]
            )

    def test_rejects_unrecognized_filename(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notes.jsonl"
            with self.assertRaises(AppendOnlyError):
                append_record(path, {"anything": True})
            self.assertFalse(path.exists())

    def test_field_values_with_newlines_stay_on_one_line(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "signals.jsonl"
            append_record(path, {"summary": "line one\nline two"})
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(1, len(lines))
            self.assertEqual("line one\nline two", json.loads(lines[0])["summary"])

    def test_appending_after_a_file_without_a_trailing_newline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.jsonl"
            path.write_text('{"evidence_id": "EV-20260728-001"}', encoding="utf-8")
            append_record(path, {"evidence_id": "EV-20260728-002"})
            self.assertEqual(2, len(_records(path)))


class AppendChainTests(unittest.TestCase):
    """The chain exists so an edited or deleted line cannot pass as history."""

    def test_appended_records_link_into_a_verifiable_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.jsonl"
            append_record(path, {"evidence_id": "EV-20260728-001"})
            append_record(path, {"evidence_id": "EV-20260728-002"})
            first, second = _records(path)

            self.assertIsNone(first["prev_hash"])
            self.assertTrue(first["record_hash"].startswith("sha256:"))
            self.assertEqual(first["record_hash"], second["prev_hash"])
            self.assertEqual([], _check_append_chain({"evidence": [first, second]}))

    def test_editing_a_recorded_value_breaks_its_own_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decisions.jsonl"
            append_record(path, {"decision_id": "DEC-20260728-001", "status": "draft"})
            records = _records(path)
            records[0]["status"] = "approved"

            issues = _check_append_chain({"decision": records})
            self.assertEqual(1, len(issues))
            self.assertIn("does not match the record contents", issues[0].message)

    def test_removing_a_middle_record_breaks_the_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "actions.jsonl"
            for index in (1, 2, 3):
                append_record(path, {"action_id": f"ACT-20260728-00{index}"})
            records = _records(path)
            del records[1]

            issues = _check_append_chain({"action": records})
            self.assertEqual(1, len(issues))
            self.assertIn("prev_hash does not match", issues[0].message)
            self.assertEqual("actions.jsonl[2]", issues[0].path)

    def test_stripping_the_hash_after_the_chain_started_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "outcomes.jsonl"
            append_record(path, {"outcome_id": "OUT-20260728-001"})
            append_record(path, {"outcome_id": "OUT-20260728-002"})
            records = _records(path)
            records[1].pop("record_hash")
            records[1].pop("prev_hash")

            issues = _check_append_chain({"outcome": records})
            self.assertEqual(1, len(issues))
            self.assertEqual("outcomes.jsonl[2]", issues[0].path)
            self.assertIn("record_hash is missing", issues[0].message)

    def test_stripping_the_hash_before_the_chain_started_is_rejected(self) -> None:
        """Opting a leading record out of the chain must not be a free pass.

        Dropping both fields from an edited record used to leave the file valid
        as long as the record sat ahead of the first hashed one, which made the
        whole chain opt-out per record instead of per file.
        """
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "signals.jsonl"
            append_record(path, {"signal_id": "SIG-20260728-001"})
            append_record(path, {"signal_id": "SIG-20260728-002"})
            records = _records(path)
            records[0].pop("record_hash")
            records[0].pop("prev_hash")
            # Relink the survivor so it is internally consistent: the partial
            # chain is then the only remaining evidence of the removal.
            records[1]["prev_hash"] = None
            records[1]["record_hash"] = compute_record_hash(records[1], None)

            issues = _check_append_chain({"signal": records})
            self.assertEqual(1, len(issues))
            self.assertEqual("signals.jsonl[1]", issues[0].path)
            self.assertIn("record_hash is missing", issues[0].message)

    def test_an_entirely_unchained_artifact_is_rejected(self) -> None:
        """Deleting every hash used to be a free pass out of tamper evidence.

        The exemption was written for artifacts predating the chain, but a file
        with no hashes at all is indistinguishable from one whose hashes were
        stripped on purpose, so the cheapest forgery was also the only one that
        passed.
        """
        unchained = [{"approval_id": "APR-001"}, {"approval_id": "APR-002"}]
        issues = _check_append_chain({"approval": unchained})
        self.assertEqual(2, len(issues))
        self.assertEqual("approvals.jsonl[1]", issues[0].path)
        self.assertIn("record_hash is missing", issues[0].message)

    def test_forging_content_then_deleting_every_hash_is_caught(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decisions.jsonl"
            append_record(path, {"decision_id": "DEC-20260728-001", "status": "draft"})
            append_record(path, {"decision_id": "DEC-20260728-002", "status": "draft"})
            records = _records(path)
            records[0]["status"] = "approved"
            for record in records:
                record.pop("record_hash")
                record.pop("prev_hash")

            self.assertTrue(_check_append_chain({"decision": records}))

    def test_every_append_only_artifact_is_chain_verified_somewhere(self) -> None:
        """Coverage is measured against all of APPEND_ONLY_FILES, not a subset.

        The previous version intersected the expectation with the same table it
        derived the actual coverage from, so a file no module verified could
        never fail it. `integration-references.jsonl` was exactly that: chained
        on write, recomputed by nobody.
        """
        verified = (
            {ARTIFACT_KIND_FILES[kind] for kind in CHAINED_KINDS}
            | set(_CHAINED_CONNECTOR_FILES)
            | set(CHAINED_INTEGRATION_FILES)
        )
        self.assertEqual(set(APPEND_ONLY_FILES), verified)

    def test_connector_ledgers_are_chained_too(self) -> None:
        for filename in ("cs-events.jsonl", "reply-drafts.jsonl", "delivery-events.jsonl"):
            with self.subTest(filename=filename):
                self.assertIn(filename, _CHAINED_CONNECTOR_FILES)

    def test_a_tampered_claim_is_detected(self) -> None:
        """The published claim ledger is the artifact a reader most needs to trust."""
        records = [
            json.loads(line)
            for line in (
                ROOT / "fixtures" / "public-dummy" / "artifacts" / "claim-ledger.jsonl"
            )
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        self.assertEqual([], _check_append_chain({"claim": records}))

        records[0]["claim"] = "a claim nobody approved"
        issues = _check_append_chain({"claim": records})
        self.assertTrue(issues)
        self.assertIn("does not match the record contents", issues[0].message)

    def test_caller_supplied_hashes_do_not_override_the_writer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "approvals.jsonl"
            append_record(
                path,
                {
                    "approval_id": "APR-forged-001",
                    "record_hash": "sha256:" + "0" * 64,
                    "prev_hash": "sha256:" + "f" * 64,
                },
            )
            record = _records(path)[0]

            self.assertIsNone(record["prev_hash"])
            self.assertNotEqual("sha256:" + "0" * 64, record["record_hash"])
            self.assertEqual([], _check_append_chain({"approval": [record]}))


if __name__ == "__main__":
    unittest.main()
