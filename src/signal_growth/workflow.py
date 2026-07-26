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

CONNECTOR_POSITION = 3
CONNECTOR_SKILL = "connect-customer-channels"
CONNECTOR_FILES = (
    "channel-connection.json",
    "cs-events.jsonl",
    "connector-state.json",
)


def _connector_state(artifact_directory: Path) -> str:
    exists = [(artifact_directory / filename).exists() for filename in CONNECTOR_FILES]
    if all(exists):
        return "complete"
    if any(exists):
        return "partial"
    return "not-configured"


def next_skill(artifact_directory: Path) -> str | None:
    """Return the first skill whose required artifact is absent."""
    for index, (skill_name, filenames) in enumerate(SKILL_GATES):
        if index == CONNECTOR_POSITION and _connector_state(artifact_directory) == "partial":
            return CONNECTOR_SKILL
        if not all((artifact_directory / filename).exists() for filename in filenames):
            return skill_name
    return None


def completed_skills(artifact_directory: Path) -> list[str]:
    completed: list[str] = []
    for index, (skill_name, filenames) in enumerate(SKILL_GATES):
        if index == CONNECTOR_POSITION:
            connector_state = _connector_state(artifact_directory)
            if connector_state == "partial":
                break
            if connector_state == "complete":
                completed.append(CONNECTOR_SKILL)
        if all((artifact_directory / filename).exists() for filename in filenames):
            completed.append(skill_name)
        else:
            break
    return completed
