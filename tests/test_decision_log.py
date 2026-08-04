"""Verify the published decision log stays a projection of the gate log.

`docs/decision-log.md` exists so a reader can see what this repository actually
decided about itself. A published page that is edited by hand drifts from the
append-only ledger it claims to show, and a drifted page is worse than none: it
reads as evidence while asserting something the ledger does not.

These tests hold the projection to the source, not the wording to a snapshot.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.contracts import load_records  # noqa: E402
from signal_growth.decision_log import render_decision_log  # noqa: E402


GATE_LOG = ROOT / "harness" / "decisions.jsonl"
DOCUMENT = ROOT / "docs" / "decision-log.md"


class DecisionLogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.records = load_records(GATE_LOG)

    def test_document_matches_the_gate_log(self) -> None:
        self.assertEqual(
            render_decision_log(self.records),
            DOCUMENT.read_text(encoding="utf-8"),
            "docs/decision-log.md is stale; run python3 scripts/render_decision_log.py",
        )

    def test_every_recorded_decision_is_published(self) -> None:
        text = DOCUMENT.read_text(encoding="utf-8")
        for record in self.records:
            with self.subTest(decision_id=record["decision_id"]):
                self.assertIn(record["decision_id"], text)
                for reason in record["reasons"]:
                    self.assertIn(reason, text)
                self.assertIn(record["review_trigger"], text)

    def test_unobserved_outcome_is_not_rendered_as_a_result(self) -> None:
        """`outcome: null` means untested, so it must not read as an outcome."""
        rendered = render_decision_log(
            [
                {
                    "decision_id": "dec-test-20260804-001",
                    "recorded_at": "2026-08-04T00:00:00+09:00",
                    "project": "signal-to-growth",
                    "gate": "build",
                    "decision": "hold",
                    "reasons": ["테스트 근거"],
                    "review_trigger": "테스트 재검토 조건",
                    "outcome": None,
                    "supersedes": None,
                }
            ]
        )
        self.assertIn("아직 관측되지 않음", rendered)
        self.assertNotIn("None", rendered)

    def test_reasons_are_never_summarized_away(self) -> None:
        rendered = render_decision_log(
            [
                {
                    "decision_id": "dec-test-20260804-002",
                    "recorded_at": "2026-08-04T00:00:00+09:00",
                    "project": "signal-to-growth",
                    "gate": "build",
                    "decision": "build",
                    "reasons": ["근거 하나", "근거 둘", "근거 셋"],
                    "review_trigger": "조건",
                    "outcome": None,
                    "supersedes": "dec-test-20260804-001",
                }
            ]
        )
        for reason in ("근거 하나", "근거 둘", "근거 셋"):
            self.assertIn(reason, rendered)
        self.assertIn("dec-test-20260804-001", rendered)


if __name__ == "__main__":
    unittest.main()
