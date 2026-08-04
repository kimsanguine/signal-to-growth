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
# A primary artifact may be schema-valid while the skill is still incomplete.
# Keep the whole output contract here so routing cannot silently skip the
# learner-facing handoff artifacts documented by each specialist skill.
SKILL_OUTPUT_FILES = {
    "plan-customer-reach": (
        "reach-plan.json",
        "contact-drafts.md",
        "recruitment-log.csv",
    ),
    "run-switch-interview": (
        "interview-guide.md",
        "timeline-notes.md",
        "follow-up-questions.md",
    ),
    "synthesize-interviews": (
        "evidence.jsonl",
        "theme-cards.md",
        "counterevidence.md",
        "synthesis-summary.md",
    ),
    "triage-customer-signals": (
        "signals.jsonl",
        "risk-queue.jsonl",
        "theme-digest.md",
        "dead-letter.jsonl",
    ),
    "define-growth-metrics": (
        "metrics.jsonl",
        "growth-loop-map.md",
        "measurement-plan.md",
    ),
    "record-growth-decision": (
        "decisions.jsonl",
        "approvals.jsonl",
        "hplan-intake.json",
        "decision-summary.md",
        "review-queue.md",
    ),
    "design-first-user-loop": (
        "first-user-loop.json",
        "actions.jsonl",
        "approvals.jsonl",
        "experiment-cards.md",
        "channel-backlog.md",
        "learning-review.md",
    ),
    # The two optional-branch skills have no entry in CORE_SKILL_FILES because
    # nothing downstream requires them. They still belong here: without a routed
    # output contract, the three-way drift check silently degrades to a two-way
    # one and the router can call either skill done with artifacts missing.
    "audit-answer-visibility": (
        "visibility-observations.jsonl",
        "citation-gaps.md",
        "technical-findings.md",
        "recommendations.md",
    ),
    "draft-evidence-content": (
        "content-brief.md",
        "claim-ledger.jsonl",
        "draft.md",
        "review-checklist.md",
    ),
}
CONNECTOR_SKILL = "connect-customer-channels"
CONNECTOR_FILES = (
    "channel-connection.json",
    "cs-events.jsonl",
    "connector-state.json",
)
APPROVAL_FILE = "approvals.jsonl"
# The optional content branch is reachable once the first-user loop is complete,
# so a product introduction page is written from a validated loop rather than
# from an untested claim. Adding this edge is why no twelfth skill was created.
CONTENT_SKILL = "draft-evidence-content"
CONTENT_PREREQUISITE = "design-first-user-loop"
# The visibility audit is the other entry to the optional content branch. It
# reads public surfaces rather than the growth loop, so it has no prerequisite
# skill and is only reachable from an explicit objective.
VISIBILITY_SKILL = "audit-answer-visibility"
OBJECTIVE_ROUTES = (
    (("연결", "connector", "webhook", "channel talk", "카카오"), CONNECTOR_SKILL),
    (("신호", "triage", "signal", "cs 분류"), "triage-customer-signals"),
    (("지표", "metric", "activation", "retention"), "define-growth-metrics"),
    (("결정", "decision", "what not to build"), "record-growth-decision"),
    (("첫 사용자", "first user", "activation experiment"), "design-first-user-loop"),
    (("인터뷰 합성", "synthesis", "quote"), "synthesize-interviews"),
    (("인터뷰 질문", "switch interview"), "run-switch-interview"),
    (("인터뷰 모집", "research participant"), "plan-customer-reach"),
    (
        (
            "가시성",
            # Not a bare "인용": an interview quote is 인용 too, and that work
            # belongs to synthesize-interviews.
            "인용 현황",
            "answer engine",
            "ai 검색",
            "citation",
            "visibility audit",
        ),
        VISIBILITY_SKILL,
    ),
    (
        ("소개 페이지", "소개페이지", "landing page", "답변형 콘텐츠", "content draft"),
        CONTENT_SKILL,
    ),
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


def _unreviewed_evidence_ids(artifact_directory: Path) -> list[str]:
    return [
        record["evidence_id"]
        for record in _valid_jsonl_objects(artifact_directory / "evidence.jsonl")
        if isinstance(record.get("evidence_id"), str)
        and record.get("strength") == "awaiting_human_tag"
    ]


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


def _missing_skill_outputs(artifact_directory: Path, skill_name: str) -> list[str]:
    return [
        filename
        for filename in SKILL_OUTPUT_FILES[skill_name]
        if not _nonempty_file(artifact_directory / filename)
    ]


def _skill_complete(
    artifact_directory: Path,
    skill_name: str,
    valid_artifacts: set[str],
) -> bool:
    # An optional-branch skill has no primary artifact that later skills depend
    # on, so its output contract is the whole completion gate.
    primary = dict(CORE_SKILL_FILES).get(skill_name)
    if primary is not None and primary not in valid_artifacts:
        return False
    if _missing_skill_outputs(artifact_directory, skill_name):
        return False
    if skill_name == "synthesize-interviews" and _unreviewed_evidence_ids(
        artifact_directory
    ):
        return False
    return True


def _incomplete_reason(
    artifact_directory: Path,
    skill_name: str,
    valid_artifacts: set[str],
) -> str:
    primary = dict(CORE_SKILL_FILES).get(skill_name)
    if primary is not None and primary not in valid_artifacts:
        return f"{primary} does not exist yet or fails validation."
    missing = _missing_skill_outputs(artifact_directory, skill_name)
    if missing:
        # A missing approvals.jsonl is a person who has not decided yet, not a
        # file the model forgot to write. Naming it as a missing artifact invites
        # the model to fabricate an approval.
        pending = [filename for filename in missing if filename != APPROVAL_FILE]
        reason = ""
        if pending:
            reason = (
                f"{skill_name} is missing required output-contract artifacts: "
                + ", ".join(pending)
                + "."
            )
        if APPROVAL_FILE in missing:
            awaiting = (
                f"{skill_name} is awaiting human approval in a later user turn: "
                f"{APPROVAL_FILE} has no scoped approval record yet."
            )
            return f"{reason} {awaiting}".strip()
        return reason
    unreviewed = _unreviewed_evidence_ids(artifact_directory)
    if skill_name == "synthesize-interviews" and unreviewed:
        return (
            "Evidence is structurally valid but awaiting human strength approval: "
            + ", ".join(unreviewed)
            + "."
        )
    return f"{skill_name} is not complete."


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
    if requested == CONTENT_SKILL:
        if _skill_complete(artifact_directory, CONTENT_PREREQUISITE, valid):
            return CONTENT_SKILL, (
                f"The stated objective points to '{CONTENT_SKILL}' and "
                f"'{CONTENT_PREREQUISITE}' is complete, so the optional content "
                "branch can run on a validated first-user loop."
            )
        return CONTENT_PREREQUISITE, (
            f"The stated objective points to '{CONTENT_SKILL}', which follows "
            f"'{CONTENT_PREREQUISITE}': "
            + _incomplete_reason(artifact_directory, CONTENT_PREREQUISITE, valid)
        )
    if requested is not None:
        if requested == CONNECTOR_SKILL or (
            requested in SKILL_OUTPUT_FILES
            and not _skill_complete(artifact_directory, requested, valid)
        ):
            return requested, (
                f"The stated objective points to '{requested}': "
                + _incomplete_reason(artifact_directory, requested, valid)
            )

    has_customer_input = (
        "evidence.jsonl" in valid
        or connector_state == "valid"
        or "signals.jsonl" in valid
    )
    if has_customer_input:
        if (
            "evidence.jsonl" not in valid
            or not _skill_complete(artifact_directory, "synthesize-interviews", valid)
        ) and connector_state != "valid":
            return "synthesize-interviews", (
                _incomplete_reason(artifact_directory, "synthesize-interviews", valid)
            )
        if not _skill_complete(artifact_directory, "triage-customer-signals", valid):
            return "triage-customer-signals", (
                _incomplete_reason(artifact_directory, "triage-customer-signals", valid)
            )
        if not _skill_complete(artifact_directory, "define-growth-metrics", valid):
            return "define-growth-metrics", (
                _incomplete_reason(artifact_directory, "define-growth-metrics", valid)
            )
        if not _skill_complete(artifact_directory, "record-growth-decision", valid):
            return "record-growth-decision", (
                _incomplete_reason(artifact_directory, "record-growth-decision", valid)
            )
        if not _skill_complete(artifact_directory, "design-first-user-loop", valid):
            return "design-first-user-loop", (
                _incomplete_reason(artifact_directory, "design-first-user-loop", valid)
            )
        outcome_review_reason = _outcome_review_reason(artifact_directory)
        if outcome_review_reason is not None:
            return "record-growth-decision", outcome_review_reason
        return None, (
            "All core skill artifacts and the connector state are valid — "
            "there is no required next skill."
        )

    for skill_name, filename in CORE_SKILL_FILES[:3]:
        if not _skill_complete(artifact_directory, skill_name, valid):
            return skill_name, _incomplete_reason(artifact_directory, skill_name, valid)
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
        if filename in valid and _skill_complete(artifact_directory, skill_name, valid)
    ]
    if _connector_state(artifact_directory) == "valid":
        completed.append(CONNECTOR_SKILL)
    return completed
