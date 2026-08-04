"""Hold a customer release note to the two claims it is allowed to make.

A release note is the one artifact in this repository that speaks to customers
about work that already happened, so it has exactly two ways to be dishonest.

1. It can announce a change nobody shipped. The contract answers that by
   requiring `change_ref` and `change_source` on every entry, with no enum value
   for "a model wrote this from memory" — a change with no deterministic origin
   cannot be represented at all.
2. It can claim the release answered a customer need it never answered. The
   contract answers that with `link_state`, which keeps a model's guess and a
   person's confirmation as different values, and with a reference check that
   resolves every linked ID against the run's own signals and decisions.

These tests encode both, plus the boundary that drafting is not sending.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.append_only import (  # noqa: E402
    APPEND_ONLY_FILES,
    verify_append_chain,
)
from signal_growth.contracts import (  # noqa: E402
    ARTIFACT_FILES,
    ARTIFACT_KIND_FILES,
    REQUIRED_COMPLETE_FILES,
    _check_references,
    _collect_ids,
    validate_record,
)
from signal_growth.schema_validation import validate_schema_record  # noqa: E402


ARTIFACTS = ROOT / "fixtures" / "public-dummy" / "artifacts"
FIXTURE = ARTIFACTS / "release-notes.jsonl"
SCHEMA = "release-note.schema.json"


def _note(**overrides: object) -> dict:
    """Return the public fixture release note, optionally overridden."""
    record = json.loads(FIXTURE.read_text(encoding="utf-8").splitlines()[0])
    record.pop("record_hash", None)
    record.pop("prev_hash", None)
    record.update(overrides)
    return record


def _change(index: int = 0, **overrides: object) -> dict:
    change = dict(_note()["changes"][index])
    change.update(overrides)
    return change


def _with_change(change: dict) -> dict:
    return _note(changes=[change])


def _records(filename: str) -> list[dict]:
    lines = (ARTIFACTS / filename).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _release_note_issues(note: dict, *, kinds: tuple[str, ...]) -> list[str]:
    """Cross-check `note` against real fixture records of `kinds`.

    Only issues raised against the note itself are returned. The neighbouring
    artifacts are loaded as a reference universe, not as subjects: evidence.jsonl
    is deliberately absent, so their own reference checks would otherwise report
    gaps this module is not testing.
    """
    records = {kind: _records(ARTIFACT_KIND_FILES[kind]) for kind in kinds}
    records["release_note"] = [note]
    return [
        issue.render()
        for issue in _check_references(records, _collect_ids(records))
        if issue.path.startswith("release-notes.jsonl")
    ]


class ReleaseNoteFixtureTests(unittest.TestCase):
    def test_the_public_fixture_satisfies_its_contract(self) -> None:
        issues = [
            issue.render()
            for index, record in enumerate(_records("release-notes.jsonl"), 1)
            for issue in validate_record(
                "release_note", record, f"release-notes.jsonl[{index}]"
            )
        ]
        self.assertEqual([], issues, issues)

    def test_the_fixture_carries_an_unbroken_append_chain(self) -> None:
        broken = verify_append_chain(
            _records("release-notes.jsonl"), "release-notes.jsonl"
        )
        self.assertEqual([], broken, broken)

    def test_the_artifact_is_append_only_and_optional(self) -> None:
        """A note is history, but a run without a release still validates."""
        self.assertIn("release-notes.jsonl", APPEND_ONLY_FILES)
        self.assertEqual("release_note", ARTIFACT_FILES["release-notes.jsonl"])
        self.assertNotIn("release-notes.jsonl", REQUIRED_COMPLETE_FILES)

    def test_the_guard_hook_protects_the_same_files_as_the_writer(self) -> None:
        """The hook keeps its own copy of the list, so drift unprotects a file.

        `hooks/guard_append_only.py` cannot import the package — it runs as a
        standalone script — so the two lists are maintained by hand. A file added
        to one and not the other is append-only in name only.
        """
        namespace: dict = {}
        exec(  # noqa: S102 - reading a constant out of a standalone hook script
            compile(
                (ROOT / "hooks" / "guard_append_only.py").read_text(encoding="utf-8"),
                "guard_append_only.py",
                "exec",
            ),
            namespace,
        )
        self.assertEqual(APPEND_ONLY_FILES, namespace["APPEND_ONLY_FILES"])


class ChangeOriginTests(unittest.TestCase):
    """Every announced change must say where it came from."""

    def test_a_change_without_a_reference_is_rejected(self) -> None:
        errors = validate_schema_record(SCHEMA, _with_change(_change(change_ref="")))
        self.assertTrue(errors)

    def test_a_change_must_declare_a_deterministic_source(self) -> None:
        for source in ("human_provided", "git_log", "changelog"):
            with self.subTest(source=source):
                self.assertEqual(
                    [],
                    validate_schema_record(
                        SCHEMA, _with_change(_change(change_source=source))
                    ),
                )

    def test_there_is_no_source_value_for_a_model_written_change(self) -> None:
        """The absence of this enum value is the anti-fabrication control."""
        for invented in ("model_generated", "inferred", "unknown", ""):
            with self.subTest(invented=invented):
                self.assertTrue(
                    validate_schema_record(
                        SCHEMA, _with_change(_change(change_source=invented))
                    )
                )

    def test_a_note_needs_at_least_one_change(self) -> None:
        self.assertTrue(validate_schema_record(SCHEMA, _note(changes=[])))


class LinkStateTests(unittest.TestCase):
    """A model's guess and a person's confirmation are different records."""

    def test_an_unlinked_change_must_not_carry_references(self) -> None:
        record = _with_change(
            _change(link_state="none", signal_ids=["SIG-20260725-001"])
        )
        self.assertTrue(validate_schema_record(SCHEMA, record))

    def test_a_linked_change_must_name_what_it_links_to(self) -> None:
        for link_state in ("human_confirmed", "model_inferred"):
            with self.subTest(link_state=link_state):
                record = _with_change(
                    _change(link_state=link_state, signal_ids=[], decision_ids=[])
                )
                self.assertTrue(validate_schema_record(SCHEMA, record))

    def test_a_decision_only_link_is_enough(self) -> None:
        record = _with_change(
            _change(
                link_state="human_confirmed",
                signal_ids=[],
                decision_ids=["DEC-20260725-001"],
            )
        )
        self.assertEqual([], validate_schema_record(SCHEMA, record))

    def test_the_fixture_reports_unlinked_work_instead_of_hiding_it(self) -> None:
        """A note where every change traced to a signal is the suspicious one."""
        states = {change["link_state"] for change in _note()["changes"]}
        self.assertIn("none", states)


class LinkResolutionTests(unittest.TestCase):
    """A link is only a link if the thing it names exists in this run."""

    def _cross_check(self, note: dict) -> list[str]:
        return _release_note_issues(note, kinds=("signal", "decision", "action"))

    def test_the_fixture_links_resolve_against_the_run(self) -> None:
        self.assertEqual([], self._cross_check(_note()))

    def test_a_link_to_an_unrecorded_signal_is_rejected(self) -> None:
        note = _with_change(
            _change(link_state="model_inferred", signal_ids=["SIG-20991231-999"])
        )
        issues = self._cross_check(note)
        self.assertTrue(any("unknown signal ID" in issue for issue in issues), issues)

    def test_a_link_to_an_unrecorded_decision_is_rejected(self) -> None:
        note = _with_change(
            _change(
                link_state="human_confirmed",
                signal_ids=[],
                decision_ids=["DEC-20991231-999"],
            )
        )
        issues = self._cross_check(note)
        self.assertTrue(any("unknown decision ID" in issue for issue in issues), issues)


class PublicationBoundaryTests(unittest.TestCase):
    """Drafting wording is not authority to send it."""

    def test_the_fixture_proposes_no_send(self) -> None:
        self.assertIsNone(_note()["publication_action_id"])

    def test_a_note_awaiting_review_must_carry_the_wording_to_review(self) -> None:
        record = _note(status="awaiting_human_review", customer_summary=None)
        self.assertTrue(validate_schema_record(SCHEMA, record))

    def test_a_draft_may_still_be_untranslated(self) -> None:
        record = _note(status="draft", customer_summary=None)
        self.assertEqual([], validate_schema_record(SCHEMA, record))

    def test_a_send_must_point_at_an_external_write_action(self) -> None:
        """ACT-20260725-001 is an internal analysis, not a customer send.

        Naming it would let a note claim a publishing path that the approval
        contract never treats as an external write.
        """
        issues = _release_note_issues(
            _note(publication_action_id="ACT-20260725-001"), kinds=("action",)
        )
        self.assertTrue(
            any("not an external write" in issue for issue in issues), issues
        )

    def test_a_send_pointing_at_an_unknown_action_is_rejected(self) -> None:
        issues = _release_note_issues(
            _note(publication_action_id="ACT-20991231-999"), kinds=("action",)
        )
        self.assertTrue(
            any("unknown action ID" in issue for issue in issues), issues
        )


if __name__ == "__main__":
    unittest.main()
