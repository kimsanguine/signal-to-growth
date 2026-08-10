from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.repo_validation import (
    EXPECTED_SKILLS,
    _check_output_contract_alignment,
    _declared_output_files,
    _documented_output_files,
    validate_repository,
)
from signal_growth.workflow import SKILL_OUTPUT_FILES


SKILL_TEMPLATE = """---
name: record-growth-decision
description: "placeholder"
---

## Workflow

1. `not-an-output.md` outside the Outputs section is ignored.

## Outputs

Create or append:

{bullets}

Read [references/output-contract.md](references/output-contract.md) before writing them.

## Stop conditions

Stop when evidence is invalid.
"""


def _write_skill(root: Path, bullets: list[str], headings: list[str]) -> Path:
    skill_root = root / "skills"
    skill_directory = skill_root / "record-growth-decision"
    (skill_directory / "references").mkdir(parents=True)
    (skill_directory / "SKILL.md").write_text(
        SKILL_TEMPLATE.format(bullets="\n".join(bullets)), encoding="utf-8"
    )
    (skill_directory / "references" / "output-contract.md").write_text(
        "# Output contract\n\n"
        + "\n\n".join(f"## {heading}\n\nText." for heading in headings)
        + "\n\n## Completion gate\n\nText.\n",
        encoding="utf-8",
    )
    return skill_root


class RepositoryValidationTests(unittest.TestCase):
    def test_repository_structure_is_valid(self) -> None:
        issues = validate_repository(ROOT)
        self.assertEqual([], issues, [issue.render() for issue in issues])


class OutputContractAlignmentTests(unittest.TestCase):
    """SKILL.md, output-contract.md, and workflow.py must name the same files."""

    # The real record-growth-decision output contract, kept in one place.
    ALIGNED = [
        "`decisions.jsonl`",
        "`approvals.jsonl`",
        "`hplan-intake.json`",
        "`decision-summary.md`",
        "`review-queue.md`",
        "`introduction-loop-decision.md`",
    ]

    def test_only_bullets_under_the_outputs_heading_count(self) -> None:
        text = SKILL_TEMPLATE.format(
            bullets="- `decisions.jsonl`\n- append a scoped `approvals.jsonl` record"
        )
        self.assertEqual(
            {"decisions.jsonl", "approvals.jsonl"}, _declared_output_files(text)
        )

    def test_prose_bullets_without_a_filename_are_not_outputs(self) -> None:
        text = SKILL_TEMPLATE.format(
            bullets="- `metrics.jsonl`\n- optional query stubs marked unverified"
        )
        self.assertEqual({"metrics.jsonl"}, _declared_output_files(text))

    def test_non_filename_contract_headings_are_ignored(self) -> None:
        contract = "## `run-state.json`\n\n## Apply artifacts\n\n## Completion gate\n"
        self.assertEqual({"run-state.json"}, _documented_output_files(contract))

    def test_aligned_declarations_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root = _write_skill(
                Path(directory),
                [f"- {name}" for name in self.ALIGNED],
                self.ALIGNED,
            )
            self.assertEqual([], _check_output_contract_alignment(skill_root))

    def test_a_file_missing_from_skill_md_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root = _write_skill(
                Path(directory),
                [f"- {name}" for name in self.ALIGNED if "hplan" not in name],
                self.ALIGNED,
            )
            issues = _check_output_contract_alignment(skill_root)

            self.assertEqual(1, len(issues), [issue.render() for issue in issues])
            self.assertTrue(issues[0].path.endswith("SKILL.md"))
            self.assertIn("hplan-intake.json", issues[0].message)

    def test_a_file_missing_from_the_output_contract_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skill_root = _write_skill(
                Path(directory),
                [f"- {name}" for name in self.ALIGNED],
                [name for name in self.ALIGNED if "review-queue" not in name],
            )
            issues = _check_output_contract_alignment(skill_root)

            self.assertEqual(1, len(issues), [issue.render() for issue in issues])
            self.assertTrue(issues[0].path.endswith("output-contract.md"))
            self.assertIn("review-queue.md", issues[0].message)

    def test_a_file_missing_from_workflow_routing_is_reported(self) -> None:
        extra = self.ALIGNED + ["`late-addition.md`"]
        with tempfile.TemporaryDirectory() as directory:
            skill_root = _write_skill(
                Path(directory), [f"- {name}" for name in extra], extra
            )
            issues = _check_output_contract_alignment(skill_root)

            self.assertEqual(1, len(issues), [issue.render() for issue in issues])
            self.assertIn("workflow.py", issues[0].path)
            self.assertIn("late-addition.md", issues[0].message)


class RoutedSkillCoverageTests(unittest.TestCase):
    """A skill absent from SKILL_OUTPUT_FILES is only checked two ways.

    `_check_output_contract_alignment` compares whichever sources exist, so a
    skill with no routing entry degrades from a three-way check to a two-way one
    without failing anything. Naming the exemptions here makes that a decision
    someone has to change on purpose.
    """

    # All three skills emit a different artifact set per requested operation or
    # mode, so no fixed completion list can describe them. optimize-search-
    # visibility's reports also describe an external website rather than this
    # repository's own growth-loop state, so there is nothing to route to next.
    EXEMPT = {"connect-customer-channels", "run-growth-loop", "optimize-search-visibility"}

    def test_every_skill_is_routed_unless_deliberately_exempt(self) -> None:
        self.assertEqual(
            EXPECTED_SKILLS - self.EXEMPT,
            set(SKILL_OUTPUT_FILES),
        )

    def test_routed_outputs_match_each_skill_on_disk(self) -> None:
        for skill_name, routed in SKILL_OUTPUT_FILES.items():
            with self.subTest(skill=skill_name):
                declared = _declared_output_files(
                    (ROOT / "skills" / skill_name / "SKILL.md").read_text(
                        encoding="utf-8"
                    )
                )
                self.assertEqual(set(routed), declared)


if __name__ == "__main__":
    unittest.main()
