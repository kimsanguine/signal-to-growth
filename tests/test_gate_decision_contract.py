"""Verify the gate decision log contract and the two newly contracted artifacts.

`harness/decisions.jsonl` records repository gate verdicts. It is deliberately
governed by `contracts/gate-decision.schema.json` rather than
`contracts/decision.schema.json`, because a growth decision and a gate decision
answer different questions and the gate log is append-only.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.contracts import (  # noqa: E402
    REQUIRED_FIELDS,
    validate_gate_decision_log,
    validate_record,
)
from signal_growth.repo_validation import validate_repository  # noqa: E402


GATE_LOG = ROOT / "harness" / "decisions.jsonl"
ARTIFACTS = ROOT / "fixtures" / "public-dummy" / "artifacts"


def _write_log(directory: str, records: list[dict]) -> Path:
    path = Path(directory) / "decisions.jsonl"
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )
    return path


def _first_line(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8").splitlines()[0])


def _validate_single(record: dict) -> list[str]:
    with tempfile.TemporaryDirectory() as directory:
        issues = validate_gate_decision_log(_write_log(directory, [record]))
    return [issue.message for issue in issues]


class GateDecisionLogTests(unittest.TestCase):
    def test_repository_gate_log_satisfies_its_own_contract(self) -> None:
        issues = validate_gate_decision_log(GATE_LOG)
        self.assertEqual([], issues, [issue.render() for issue in issues])

    def test_gate_log_is_not_governed_by_the_growth_decision_contract(self) -> None:
        """The seam exists because the growth contract rejects every gate record.

        If this ever stops failing, the two contracts have converged and the
        separate gate contract should be reconsidered rather than kept by habit.
        """
        record = _first_line(GATE_LOG)
        self.assertTrue(REQUIRED_FIELDS["decision"] - set(record))
        issues = validate_record("decision", record, "harness/decisions.jsonl[1]")
        self.assertNotEqual([], issues)

    def test_verdict_outside_the_enum_is_rejected(self) -> None:
        messages = _validate_single({**_first_line(GATE_LOG), "decision": "ship"})
        self.assertTrue(any("is not one of" in message for message in messages), messages)

    def test_verdict_without_a_reason_is_rejected(self) -> None:
        messages = _validate_single({**_first_line(GATE_LOG), "reasons": []})
        self.assertTrue(any("non-empty" in message for message in messages), messages)

    def test_verdict_without_a_review_trigger_is_rejected(self) -> None:
        record = _first_line(GATE_LOG)
        record.pop("review_trigger")
        messages = _validate_single(record)
        self.assertTrue(
            any("'review_trigger' is a required property" in m for m in messages),
            messages,
        )

    def test_unstated_supersedes_lineage_is_rejected(self) -> None:
        record = _first_line(GATE_LOG)
        record.pop("supersedes")
        messages = _validate_single(record)
        self.assertTrue(
            any("'supersedes' is a required property" in m for m in messages),
            messages,
        )

    def test_growth_decision_identifier_is_rejected(self) -> None:
        messages = _validate_single(
            {**_first_line(GATE_LOG), "decision_id": "DEC-20260726-001"}
        )
        self.assertTrue(any("does not match" in message for message in messages), messages)

    def test_duplicate_decision_id_is_rejected(self) -> None:
        record = _first_line(GATE_LOG)
        with tempfile.TemporaryDirectory() as directory:
            issues = validate_gate_decision_log(_write_log(directory, [record, record]))
        self.assertTrue(
            any("not unique" in issue.message for issue in issues),
            [issue.render() for issue in issues],
        )

    def test_supersedes_must_reference_an_earlier_record(self) -> None:
        messages = _validate_single(
            {**_first_line(GATE_LOG), "supersedes": "dec-stg-absent-20260101-001"}
        )
        self.assertTrue(
            any("recorded earlier in the log" in message for message in messages),
            messages,
        )

    def test_validate_repository_covers_the_gate_log(self) -> None:
        issues = validate_repository(ROOT)
        self.assertEqual([], issues, [issue.render() for issue in issues])


class ClaimLedgerContractTests(unittest.TestCase):
    def _record(self) -> dict:
        return _first_line(ARTIFACTS / "claim-ledger.jsonl")

    def test_public_fixture_satisfies_the_contract(self) -> None:
        issues = validate_record("claim", self._record(), "claim-ledger.jsonl[1]")
        self.assertEqual([], issues, [issue.render() for issue in issues])

    def test_claim_state_outside_the_vocabulary_is_rejected(self) -> None:
        issues = validate_record(
            "claim", {**self._record(), "state": "true"}, "claim-ledger.jsonl[1]"
        )
        self.assertNotEqual([], issues)

    def test_public_claim_without_an_approver_is_rejected(self) -> None:
        record = self._record()
        record.pop("approved_by")
        issues = validate_record("claim", record, "claim-ledger.jsonl[1]")
        self.assertTrue(
            any("approved_by" in issue.message for issue in issues),
            [issue.render() for issue in issues],
        )

    def test_observed_claim_without_evidence_is_rejected(self) -> None:
        issues = validate_record(
            "claim",
            {**self._record(), "state": "observed", "evidence_ids": []},
            "claim-ledger.jsonl[1]",
        )
        self.assertNotEqual([], issues)

    def test_observed_claim_may_anchor_on_a_source_url_instead(self) -> None:
        """A repository-sourced claim has a locator but no EV- record to name.

        The skill output contract asks for "evidence IDs or source URLs", so an
        observed claim that names its source stays valid rather than forcing an
        evidence ID that would resolve to nothing.
        """
        issues = validate_record(
            "claim",
            {
                **self._record(),
                "state": "observed",
                "evidence_ids": [],
                "source_urls": ["README.md:12-13"],
            },
            "claim-ledger.jsonl[1]",
        )
        self.assertEqual([], issues, [issue.render() for issue in issues])


class VisibilityObservationContractTests(unittest.TestCase):
    def _record(self) -> dict:
        return _first_line(ARTIFACTS / "visibility-observations.jsonl")

    def test_public_fixture_satisfies_the_contract(self) -> None:
        issues = validate_record(
            "visibility_observation", self._record(), "visibility-observations.jsonl[1]"
        )
        self.assertEqual([], issues, [issue.render() for issue in issues])

    def test_claim_state_outside_the_vocabulary_is_rejected(self) -> None:
        issues = validate_record(
            "visibility_observation",
            {**self._record(), "claim_state": "definitely"},
            "visibility-observations.jsonl[1]",
        )
        self.assertNotEqual([], issues)

    def test_observation_without_a_surface_is_rejected(self) -> None:
        record = self._record()
        record.pop("surface")
        issues = validate_record(
            "visibility_observation", record, "visibility-observations.jsonl[1]"
        )
        self.assertTrue(
            any("surface" in issue.message for issue in issues),
            [issue.render() for issue in issues],
        )


if __name__ == "__main__":
    unittest.main()
