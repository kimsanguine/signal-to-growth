from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.append_only import AppendOnlyError, append_record


class AppendOnlyTests(unittest.TestCase):
    def test_appends_a_single_line_and_returns_new_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.jsonl"
            self.assertEqual(1, append_record(path, {"evidence_id": "EV-20260728-001"}))
            self.assertEqual(2, append_record(path, {"evidence_id": "EV-20260728-002"}))
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(2, len(lines))
            self.assertEqual(
                {"evidence_id": "EV-20260728-001"}, json.loads(lines[0])
            )

    def test_preserves_existing_lines(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "decisions.jsonl"
            path.write_text('{"decision_id": "DEC-20260728-001"}\n', encoding="utf-8")
            append_record(path, {"decision_id": "DEC-20260728-002"})
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(2, len(lines))
            self.assertEqual(
                {"decision_id": "DEC-20260728-001"}, json.loads(lines[0])
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
            self.assertEqual(
                {"summary": "line one\nline two"}, json.loads(lines[0])
            )


if __name__ == "__main__":
    unittest.main()
