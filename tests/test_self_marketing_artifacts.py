"""Hold this repository's own marketing ledgers to the contracts they cite.

`docs/self-marketing/` is written by the skills in this repository, applied to
the repository itself. It is not a run's artifact directory: its sources are
files across the whole repo, so `validate-artifacts` cannot cover it (evidence
locators there must resolve under the artifact directory's parent). Without
this module the two ledgers are a CI blind spot — Round 1 shipped 19 claim
records that used field names no contract defines, and nothing failed.

These tests check what is checkable for a self-referential ledger:
per-record schema conformance, the append chain, and whether every
`file:line` pointer still resolves in the current tree.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from signal_growth.append_only import verify_append_chain
from signal_growth.contracts import validate_record

ROOT = Path(__file__).resolve().parents[1]
LEDGERS = ROOT / "docs" / "self-marketing"

# A repository pointer such as `README.md:531-533` or `eval/summary.md:49`,
# wherever it appears inside a record's strings.
_POINTER = re.compile(r"(?<![\w*])([A-Za-z0-9_./-]+\.[A-Za-z0-9]+):(\d+)(?:-(\d+))?")


def _records(filename: str) -> list[dict]:
    lines = (LEDGERS / filename).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


class SelfMarketingLedgerTests(unittest.TestCase):
    cases = (
        ("claim-ledger.jsonl", "claim"),
        ("visibility-observations.jsonl", "visibility_observation"),
    )

    def test_every_record_satisfies_its_contract(self) -> None:
        for filename, kind in self.cases:
            with self.subTest(filename):
                issues = [
                    issue.render()
                    for index, record in enumerate(_records(filename), 1)
                    for issue in validate_record(kind, record, f"{filename}[{index}]")
                ]
                self.assertEqual([], issues, issues)

    def test_every_ledger_carries_an_unbroken_append_chain(self) -> None:
        for filename, _ in self.cases:
            with self.subTest(filename):
                broken = verify_append_chain(_records(filename), filename)
                self.assertEqual([], broken, broken)

    def test_every_file_line_pointer_still_resolves(self) -> None:
        """A locator that drifted is a false citation, not a cosmetic problem.

        This is a floor, not a semantic check: it catches a pointer to a file
        that no longer exists or to a line past its end. A pointer that still
        lands inside the file but on different content — README.md:41 once
        named a headline and later named a blank line — needs a human read.
        """
        stale: list[str] = []
        for source in sorted(LEDGERS.iterdir()):
            if not source.is_file():
                continue
            for path_text, start, end in _POINTER.findall(
                source.read_text(encoding="utf-8")
            ):
                target = ROOT / path_text
                if not target.is_file():
                    stale.append(f"{source.name}: {path_text} does not exist")
                    continue
                last = len(target.read_text(encoding="utf-8").splitlines())
                if int(end or start) > last:
                    stale.append(
                        f"{source.name}: {path_text}:{start}-{end or start} "
                        f"is past the end of the file ({last} lines)"
                    )
        self.assertEqual([], stale, stale)


if __name__ == "__main__":
    unittest.main()
