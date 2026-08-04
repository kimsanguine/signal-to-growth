"""Verify the optional `event_type` classification on a growth decision.

`supersedes` records *which* decision an event replaces. It cannot record *why*,
so narrowing scope, redefining a success condition, and stopping a decision after
mature outcomes are indistinguishable in a log that carries only lineage.
`event_type` classifies the change.

The field is optional on purpose: every decision written before it existed must
keep validating, and an unclassified record must not be silently read as an
initial decision. These tests encode that boundary — absence stays valid, and a
present classification has to agree with the lineage the record actually carries.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.contracts import (  # noqa: E402
    DECISION_CHANGE_EVENT_TYPES,
    DECISION_EVENT_TYPES,
    REQUIRED_FIELDS,
    validate_record,
)
from signal_growth.schema_validation import validate_schema_record  # noqa: E402


FIXTURE = ROOT / "fixtures" / "public-dummy" / "artifacts" / "decisions.jsonl"


def _decision(**overrides: object) -> dict:
    """Return the public fixture decision, optionally overridden."""
    record = json.loads(FIXTURE.read_text(encoding="utf-8").splitlines()[0])
    record.pop("record_hash", None)
    record.pop("prev_hash", None)
    record.update(overrides)
    return record


class DecisionEventTypeTests(unittest.TestCase):
    def test_event_type_is_not_required(self) -> None:
        """A decision written before this field existed must stay valid."""
        record = _decision()
        self.assertNotIn("event_type", REQUIRED_FIELDS["decision"])
        self.assertNotIn("event_type", record)
        self.assertEqual([], validate_record("decision", record, "decision[1]"))
        self.assertEqual([], validate_schema_record("decision.schema.json", record))

    def test_initial_decision_without_predecessor_is_valid(self) -> None:
        record = _decision(event_type="initial_decision", supersedes=None)
        self.assertEqual([], validate_record("decision", record, "decision[1]"))

    def test_change_event_with_predecessor_is_valid(self) -> None:
        for event_type in sorted(DECISION_CHANGE_EVENT_TYPES):
            with self.subTest(event_type=event_type):
                record = _decision(
                    event_type=event_type,
                    supersedes="DEC-20260725-001",
                )
                self.assertEqual(
                    [],
                    validate_record("decision", record, "decision[1]"),
                )

    def test_unknown_event_type_is_rejected(self) -> None:
        record = _decision(event_type="spec_revision")
        issues = validate_record("decision", record, "decision[1]")
        self.assertTrue(
            any("event_type" in issue.message for issue in issues),
            [issue.render() for issue in issues],
        )
        self.assertTrue(validate_schema_record("decision.schema.json", record))

    def test_change_event_must_name_the_decision_it_changes(self) -> None:
        for event_type in sorted(DECISION_CHANGE_EVENT_TYPES):
            with self.subTest(event_type=event_type):
                record = _decision(event_type=event_type, supersedes=None)
                issues = validate_record("decision", record, "decision[1]")
                self.assertTrue(
                    any("supersedes" in issue.message for issue in issues),
                    [issue.render() for issue in issues],
                )
                self.assertTrue(
                    validate_schema_record("decision.schema.json", record),
                    f"{event_type} with supersedes=null must fail the schema too",
                )

    def test_initial_decision_must_not_supersede(self) -> None:
        record = _decision(
            event_type="initial_decision",
            supersedes="DEC-20260724-001",
        )
        issues = validate_record("decision", record, "decision[1]")
        self.assertTrue(
            any("initial_decision" in issue.message for issue in issues),
            [issue.render() for issue in issues],
        )
        self.assertTrue(validate_schema_record("decision.schema.json", record))

    def test_schema_and_deterministic_check_share_one_enum(self) -> None:
        """A value accepted by one layer and refused by the other is a defect."""
        schema = json.loads(
            (ROOT / "contracts" / "decision.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            sorted(DECISION_EVENT_TYPES),
            sorted(schema["properties"]["event_type"]["enum"]),
        )
        self.assertTrue(DECISION_CHANGE_EVENT_TYPES < DECISION_EVENT_TYPES)


if __name__ == "__main__":
    unittest.main()
