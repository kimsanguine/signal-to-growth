"""Determine the next valid evidence-to-growth step from workspace artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .connector_validation import validate_connector_directory
from .contracts import validate_artifact_directory
from .schema_validation import validate_schema_record


CORE_SKILL_FILES = (
    ("plan-customer-reach", "reach-plan.json"),
    ("run-switch-interview", "interview-guide.md"),
    ("synthesize-interviews", "evidence.jsonl"),
    ("triage-customer-signals", "signals.jsonl"),
    ("define-growth-metrics", "metrics.jsonl"),
    ("record-growth-decision", "decisions.jsonl"),
    ("design-first-user-loop", "first-user-loop.json"),
)
CONNECTOR_SKILL = "connect-customer-channels"
CONNECTOR_FILES = (
    "channel-connection.json",
    "cs-events.jsonl",
    "connector-state.json",
)
OBJECTIVE_ROUTES = (
    (("연결", "connector", "webhook", "channel talk", "카카오"), CONNECTOR_SKILL),
    (("신호", "triage", "signal", "cs 분류"), "triage-customer-signals"),
    (("지표", "metric", "activation", "retention"), "define-growth-metrics"),
    (("결정", "decision", "what not to build"), "record-growth-decision"),
    (("첫 사용자", "first user", "activation experiment"), "design-first-user-loop"),
    (("인터뷰 합성", "synthesis", "quote"), "synthesize-interviews"),
    (("인터뷰 질문", "switch interview"), "run-switch-interview"),
    (("인터뷰 모집", "research participant"), "plan-customer-reach"),
)


def _connector_state(artifact_directory: Path) -> str:
    exists = [(artifact_directory / filename).exists() for filename in CONNECTOR_FILES]
    if all(exists):
        issues = validate_connector_directory(
            artifact_directory,
            require_complete=True,
        )
        return "valid" if not issues else "invalid"
    if any(exists):
        return "partial"
    return "not-configured"


def _artifact_issue_files(artifact_directory: Path) -> set[str]:
    return {
        issue.path.split("[", 1)[0]
        for issue in validate_artifact_directory(artifact_directory)
    }


def _nonempty_file(path: Path) -> bool:
    try:
        return path.is_file() and bool(path.read_text(encoding="utf-8").strip())
    except (OSError, UnicodeError):
        return False


def _valid_json_object(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _valid_jsonl_objects(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        values = [json.loads(line) for line in lines if line.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError):
        return []
    return values if all(isinstance(value, dict) for value in values) else []


def _outcome_review_reason(artifact_directory: Path) -> str | None:
    run_state = _valid_json_object(artifact_directory / "run-state.json")
    outcomes = _valid_jsonl_objects(artifact_directory / "outcomes.jsonl")
    if not run_state or not outcomes:
        return None
    if run_state.get("phase") != "outcome-review" or run_state.get("status") not in {
        "awaiting_human_review",
        "blocked",
    }:
        return None

    latest = outcomes[-1]
    if latest.get("next_decision_id") is not None:
        return None
    maturity = latest.get("maturity_status")
    conclusion = latest.get("conclusion")
    if maturity == "not_mature":
        return (
            "The latest outcome is not mature and the outcome-review run is awaiting "
            "human review — append a follow-up decision with the resume condition."
        )
    if conclusion in {"change", "stop", "hold"}:
        return (
            f"The latest outcome conclusion is '{conclusion}' and has no linked next "
            "decision — append a follow-up decision."
        )
    return None


def _first_user_loop_valid(artifact_directory: Path) -> bool:
    payload = _valid_json_object(artifact_directory / "first-user-loop.json")
    return payload is not None and not validate_schema_record(
        "first-user-loop.schema.json",
        payload,
    )


def _valid_artifacts(artifact_directory: Path) -> set[str]:
    invalid = _artifact_issue_files(artifact_directory)
    valid: set[str] = set()
    for _, filename in CORE_SKILL_FILES:
        path = artifact_directory / filename
        if not path.exists():
            continue
        if filename == "first-user-loop.json":
            if _first_user_loop_valid(artifact_directory):
                valid.add(filename)
        elif filename in {"reach-plan.json", "interview-guide.md"}:
            if _nonempty_file(path):
                valid.add(filename)
        elif filename not in invalid:
            valid.add(filename)
    return valid


def _objective_route(objective: str | None) -> str | None:
    if not objective:
        return None
    normalized = objective.casefold()
    for hints, skill in OBJECTIVE_ROUTES:
        if any(hint in normalized for hint in hints):
            return skill
    return None


def _route(
    artifact_directory: Path,
    objective: str | None = None,
) -> tuple[str | None, str]:
    """Return (next_skill, reason) using objective, validity, and dependencies."""
    connector_state = _connector_state(artifact_directory)
    if connector_state in {"partial", "invalid"}:
        return CONNECTOR_SKILL, (
            f"CS connector artifacts are {connector_state} — finish or fix the "
            "connection with connect-customer-channels."
        )

    valid = _valid_artifacts(artifact_directory)
    requested = _objective_route(objective)
    if requested is not None:
        requested_file = dict(CORE_SKILL_FILES).get(requested)
        if requested == CONNECTOR_SKILL or requested_file not in valid:
            return requested, (
                f"The stated objective points to '{requested}' and its artifact "
                "is not yet valid."
            )

    has_customer_input = (
        "evidence.jsonl" in valid
        or connector_state == "valid"
        or "signals.jsonl" in valid
    )
    if has_customer_input:
        if "evidence.jsonl" not in valid and connector_state != "valid":
            return "synthesize-interviews", (
                "Customer input exists but evidence.jsonl is not yet valid."
            )
        if "signals.jsonl" not in valid:
            return "triage-customer-signals", (
                "Evidence is valid but signals.jsonl is not yet valid."
            )
        if "metrics.jsonl" not in valid:
            return "define-growth-metrics", (
                "Signals are valid but metrics.jsonl is not yet valid."
            )
        if "decisions.jsonl" not in valid:
            return "record-growth-decision", (
                "Metrics are valid but decisions.jsonl is not yet valid."
            )
        if "first-user-loop.json" not in valid:
            return "design-first-user-loop", (
                "A decision is valid but first-user-loop.json is not yet valid."
            )
        outcome_review_reason = _outcome_review_reason(artifact_directory)
        if outcome_review_reason is not None:
            return "record-growth-decision", outcome_review_reason
        return None, (
            "All core skill artifacts and the connector state are valid — "
            "there is no required next skill."
        )

    for skill_name, filename in CORE_SKILL_FILES[:3]:
        if filename not in valid:
            return skill_name, f"{filename} does not exist yet."
    return "triage-customer-signals", (
        "Initial research artifacts exist but signal triage has not run yet."
    )


def next_skill(
    artifact_directory: Path,
    objective: str | None = None,
) -> str | None:
    """Return the next specialist using objective, validity, and dependencies."""
    return _route(artifact_directory, objective)[0]


def next_skill_reason(
    artifact_directory: Path,
    objective: str | None = None,
) -> str:
    """Return a plain-language reason for the next_skill routing decision."""
    return _route(artifact_directory, objective)[1]


def completed_skills(artifact_directory: Path) -> list[str]:
    """Return only skills whose current artifact passes its completion gate."""
    valid = _valid_artifacts(artifact_directory)
    completed = [
        skill_name
        for skill_name, filename in CORE_SKILL_FILES
        if filename in valid
    ]
    if _connector_state(artifact_directory) == "valid":
        completed.append(CONNECTOR_SKILL)
    return completed
