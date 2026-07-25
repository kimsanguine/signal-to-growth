"""Validate Signal to Growth artifacts without external dependencies."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ID_PATTERNS = {
    "evidence": re.compile(r"^EV-\d{8}-\d{3,}$"),
    "signal": re.compile(r"^SIG-\d{8}-\d{3,}$"),
    "metric": re.compile(r"^MET-\d{8}-\d{3,}$"),
    "decision": re.compile(r"^DEC-\d{8}-\d{3,}$"),
    "action": re.compile(r"^ACT-\d{8}-\d{3,}$"),
    "outcome": re.compile(r"^OUT-\d{8}-\d{3,}$"),
    "run_state": re.compile(r"^RUN-\d{8}-\d{3,}$"),
}

ID_FIELDS = {
    "evidence": "evidence_id",
    "signal": "signal_id",
    "metric": "metric_id",
    "decision": "decision_id",
    "action": "action_id",
    "outcome": "outcome_id",
    "run_state": "run_id",
}

REQUIRED_FIELDS = {
    "evidence": {
        "evidence_id",
        "source_id",
        "source_type",
        "observed_at",
        "excerpt",
        "locator",
        "interpretation",
        "strength",
        "privacy",
        "created_by",
        "approved_by",
    },
    "signal": {
        "signal_id",
        "source_id",
        "observed_at",
        "channel",
        "category",
        "severity",
        "summary",
        "source_evidence_ids",
        "privacy",
        "status",
    },
    "metric": {
        "metric_id",
        "name",
        "purpose",
        "entity",
        "population",
        "numerator",
        "denominator",
        "window",
        "value_event",
        "data_source",
        "query_version",
        "baseline",
        "target",
        "target_source",
        "owner",
        "counter_metric_ids",
    },
    "decision": {
        "decision_id",
        "made_at",
        "status",
        "hypothesis",
        "evidence_ids",
        "counterevidence",
        "alternatives",
        "owner",
        "review_at",
        "success_condition",
        "stop_condition",
        "causal_confidence",
        "approved_by",
        "supersedes",
    },
    "action": {
        "action_id",
        "decision_id",
        "created_at",
        "action_type",
        "status",
        "owner",
        "metric_ids",
        "external_write",
        "approved_by",
    },
    "outcome": {
        "outcome_id",
        "action_id",
        "metric_id",
        "observed_at",
        "value",
        "interpretation",
        "evidence_ids",
        "recorded_by",
    },
    "run_state": {
        "run_id",
        "updated_at",
        "objective",
        "phase",
        "status",
        "completed_skills",
        "blocked_reasons",
        "approvals",
        "artifact_versions",
    },
}

ENUM_FIELDS = {
    ("evidence", "strength"): {"awaiting_human_tag", "weak", "medium", "strong"},
    ("evidence", "privacy"): {"public", "internal", "restricted"},
    ("evidence", "created_by"): {"human", "model", "deterministic"},
    ("signal", "severity"): {"low", "medium", "high", "critical"},
    ("signal", "privacy"): {"public", "internal", "restricted"},
    ("signal", "status"): {"new", "awaiting_human_review", "approved", "closed"},
    ("decision", "status"): {
        "draft",
        "awaiting_human_review",
        "approved",
        "rejected",
        "superseded",
    },
    ("decision", "causal_confidence"): {"unknown", "low", "medium", "high"},
    ("action", "status"): {
        "draft",
        "awaiting_human_review",
        "approved",
        "executed",
        "blocked",
    },
    ("run_state", "status"): {
        "draft",
        "active",
        "awaiting_human_review",
        "blocked",
        "complete",
    },
}

ARTIFACT_FILES = {
    "evidence.jsonl": "evidence",
    "signals.jsonl": "signal",
    "metrics.jsonl": "metric",
    "decisions.jsonl": "decision",
    "actions.jsonl": "action",
    "outcomes.jsonl": "outcome",
    "run-state.json": "run_state",
}


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str

    def render(self) -> str:
        return f"{self.path}: {self.message}"


def load_records(path: Path) -> list[dict[str, Any]]:
    """Load a JSON object/list or JSONL file."""
    if path.suffix == ".jsonl":
        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: each JSONL record must be an object")
            records.append(value)
        return records

    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        return value
    raise ValueError(f"{path}: JSON must be an object or a list of objects")


def validate_record(kind: str, record: dict[str, Any], location: str) -> list[ValidationIssue]:
    """Validate required fields, identifiers, enums, and approval invariants."""
    issues: list[ValidationIssue] = []
    missing = sorted(REQUIRED_FIELDS[kind] - set(record))
    if missing:
        issues.append(ValidationIssue(location, f"missing fields: {', '.join(missing)}"))
        return issues

    id_field = ID_FIELDS[kind]
    identifier = record.get(id_field)
    if not isinstance(identifier, str) or not ID_PATTERNS[kind].fullmatch(identifier):
        issues.append(ValidationIssue(location, f"invalid {id_field} format"))

    for (enum_kind, field), allowed in ENUM_FIELDS.items():
        if enum_kind == kind and record.get(field) not in allowed:
            issues.append(
                ValidationIssue(
                    location,
                    f"{field} must be one of: {', '.join(sorted(allowed))}",
                )
            )

    if kind == "evidence":
        locator = record.get("locator")
        if not isinstance(locator, dict) or not locator.get("file"):
            issues.append(ValidationIssue(location, "locator.file is required"))
        if record.get("strength") != "awaiting_human_tag" and not record.get("approved_by"):
            issues.append(
                ValidationIssue(
                    location,
                    "approved_by is required after evidence strength is assigned",
                )
            )

    if kind == "decision":
        if not isinstance(record.get("evidence_ids"), list):
            issues.append(ValidationIssue(location, "evidence_ids must be an array"))
        if record.get("status") == "approved" and not record.get("approved_by"):
            issues.append(
                ValidationIssue(location, "approved decisions require approved_by")
            )

    if kind == "action":
        if not isinstance(record.get("external_write"), bool):
            issues.append(ValidationIssue(location, "external_write must be boolean"))
        if (
            record.get("external_write") is True
            and record.get("status") == "executed"
            and not record.get("approved_by")
        ):
            issues.append(
                ValidationIssue(
                    location,
                    "executed external writes require approved_by",
                )
            )

    return issues


def _collect_ids(records: dict[str, list[dict[str, Any]]]) -> dict[str, set[str]]:
    ids: dict[str, set[str]] = {}
    for kind, items in records.items():
        field = ID_FIELDS[kind]
        ids[kind] = {
            item[field]
            for item in items
            if isinstance(item.get(field), str)
        }
    return ids


def _check_references(
    records: dict[str, list[dict[str, Any]]],
    ids: dict[str, set[str]],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    def check_many(
        kind: str,
        field: str,
        target_kind: str,
    ) -> None:
        for index, record in enumerate(records.get(kind, []), 1):
            values = record.get(field, [])
            if not isinstance(values, list):
                issues.append(
                    ValidationIssue(f"{kind}[{index}]", f"{field} must be an array")
                )
                continue
            for value in values:
                if value not in ids.get(target_kind, set()):
                    issues.append(
                        ValidationIssue(
                            f"{kind}[{index}]",
                            f"{field} references unknown {target_kind} ID",
                        )
                    )

    def check_one(kind: str, field: str, target_kind: str) -> None:
        for index, record in enumerate(records.get(kind, []), 1):
            value = record.get(field)
            if value not in ids.get(target_kind, set()):
                issues.append(
                    ValidationIssue(
                        f"{kind}[{index}]",
                        f"{field} references unknown {target_kind} ID",
                    )
                )

    check_many("signal", "source_evidence_ids", "evidence")
    check_many("decision", "evidence_ids", "evidence")
    check_many("action", "metric_ids", "metric")
    check_many("outcome", "evidence_ids", "evidence")
    check_one("action", "decision_id", "decision")
    check_one("outcome", "action_id", "action")
    check_one("outcome", "metric_id", "metric")
    return issues


def validate_artifact_directory(
    directory: Path,
    *,
    require_complete: bool = False,
) -> list[ValidationIssue]:
    """Validate supported artifacts and cross-artifact references."""
    issues: list[ValidationIssue] = []
    records: dict[str, list[dict[str, Any]]] = {}

    for filename, kind in ARTIFACT_FILES.items():
        path = directory / filename
        if not path.exists():
            if require_complete:
                issues.append(ValidationIssue(filename, "required artifact is missing"))
            continue
        try:
            items = load_records(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            issues.append(ValidationIssue(filename, str(exc)))
            continue
        records[kind] = items
        for index, record in enumerate(items, 1):
            issues.extend(validate_record(kind, record, f"{filename}[{index}]"))

    if records:
        issues.extend(_check_references(records, _collect_ids(records)))
    return issues


def render_issues(issues: Iterable[ValidationIssue]) -> str:
    return "\n".join(issue.render() for issue in issues)
