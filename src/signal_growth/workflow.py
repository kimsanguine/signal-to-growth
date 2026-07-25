"""Determine the next evidence-to-growth step from workspace artifacts."""

from __future__ import annotations

from pathlib import Path


SKILL_GATES = (
    ("plan-customer-reach", ("reach-plan.json",)),
    ("run-switch-interview", ("interview-guide.md",)),
    ("synthesize-interviews", ("evidence.jsonl",)),
    ("triage-customer-signals", ("signals.jsonl",)),
    ("define-growth-metrics", ("metrics.jsonl",)),
    ("record-growth-decision", ("decisions.jsonl",)),
    ("audit-answer-visibility", ("visibility-observations.jsonl",)),
    ("draft-evidence-content", ("claim-ledger.jsonl",)),
    ("design-first-user-loop", ("first-user-loop.json",)),
)


def next_skill(artifact_directory: Path) -> str | None:
    """Return the first skill whose required artifact is absent."""
    for skill_name, filenames in SKILL_GATES:
        if not all((artifact_directory / filename).exists() for filename in filenames):
            return skill_name
    return None


def completed_skills(artifact_directory: Path) -> list[str]:
    completed: list[str] = []
    for skill_name, filenames in SKILL_GATES:
        if all((artifact_directory / filename).exists() for filename in filenames):
            completed.append(skill_name)
        else:
            break
    return completed
