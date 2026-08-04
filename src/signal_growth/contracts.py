"""Validate Signal to Growth artifacts without external dependencies."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .append_only import APPEND_ONLY_FILES, verify_append_chain
from .schema_validation import validate_schema_record


CLAIM_STATES = frozenset(
    {"observed", "reported", "inferred", "recommended", "unknown"}
)

ID_PATTERNS = {
    "evidence": re.compile(r"^EV-\d{8}-\d{3,}$"),
    "signal": re.compile(r"^SIG-\d{8}-\d{3,}$"),
    "metric": re.compile(r"^MET-\d{8}-\d{3,}$"),
    "decision": re.compile(r"^DEC-\d{8}-\d{3,}$"),
    "action": re.compile(r"^ACT-\d{8}-\d{3,}$"),
    "outcome": re.compile(r"^OUT-\d{8}-\d{3,}$"),
    "run_state": re.compile(r"^RUN-\d{8}-\d{3,}$"),
    "approval": re.compile(r"^APR-[A-Za-z0-9][A-Za-z0-9._-]{2,127}$"),
    "claim": re.compile(r"^CLM-\d{8}-\d{3,}$"),
    "visibility_observation": re.compile(r"^VIS-\d{8}-\d{3,}$"),
}

ID_FIELDS = {
    "evidence": "evidence_id",
    "signal": "signal_id",
    "metric": "metric_id",
    "decision": "decision_id",
    "action": "action_id",
    "outcome": "outcome_id",
    "run_state": "run_id",
    "approval": "approval_id",
    "claim": "claim_id",
    "visibility_observation": "observation_id",
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
        "timezone",
        "cohort_maturity_rule",
        "exclusions",
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
        "decision_question",
        "selected_option",
        "hypothesis",
        "evidence_ids",
        "counterevidence",
        "alternatives",
        "not_build",
        "reversibility",
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
        "sample_size",
        "maturity_status",
        "query_version",
        "comparison",
        "conclusion",
        "next_decision_id",
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
    "approval": {
        "approval_id",
        "decided_at",
        "approver_id",
        "approver_type",
        "user_turn_ref",
        "status",
        "scope",
    },
    "claim": {
        "claim_id",
        "claim",
        "evidence_ids",
        "state",
        "public",
    },
    "visibility_observation": {
        "observation_id",
        "observed_at",
        "surface",
        "status",
        "claim_state",
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
    ("approval", "status"): {"approved", "revoked"},
    ("claim", "state"): CLAIM_STATES,
    ("visibility_observation", "claim_state"): CLAIM_STATES,
}

ARTIFACT_FILES = {
    "evidence.jsonl": "evidence",
    "signals.jsonl": "signal",
    "metrics.jsonl": "metric",
    "decisions.jsonl": "decision",
    "actions.jsonl": "action",
    "outcomes.jsonl": "outcome",
    "run-state.json": "run_state",
    "approvals.jsonl": "approval",
    "claim-ledger.jsonl": "claim",
    "visibility-observations.jsonl": "visibility_observation",
}
REQUIRED_COMPLETE_FILES = frozenset(
    {
        "evidence.jsonl",
        "signals.jsonl",
        "metrics.jsonl",
        "decisions.jsonl",
        "actions.jsonl",
        "outcomes.jsonl",
        "run-state.json",
    }
)
ARTIFACT_KIND_FILES = {kind: filename for filename, kind in ARTIFACT_FILES.items()}

SCHEMA_FILES = {
    "evidence": "evidence.schema.json",
    "signal": "signal.schema.json",
    "metric": "metric.schema.json",
    "decision": "decision.schema.json",
    "action": "action.schema.json",
    "outcome": "outcome.schema.json",
    "run_state": "run-state.schema.json",
    "approval": "approval.schema.json",
    "claim": "claim-ledger.schema.json",
    "visibility_observation": "visibility-observation.schema.json",
}

GATE_DECISION_SCHEMA_FILE = "gate-decision.schema.json"


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
    issues = [
        ValidationIssue(location, message)
        for message in validate_schema_record(SCHEMA_FILES[kind], record)
    ]
    missing = sorted(REQUIRED_FIELDS[kind] - set(record))
    if missing:
        if not any("required property" in issue.message for issue in issues):
            issues.append(
                ValidationIssue(location, f"missing fields: {', '.join(missing)}")
            )
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
            and record.get("status") in {"approved", "executed"}
            and (
                not isinstance(record.get("approved_by"), str)
                or not record["approved_by"].startswith("APR-")
            )
        ):
            issues.append(
                ValidationIssue(
                    location,
                    "approved or executed external writes require an APR- approval reference",
                )
            )

    return issues


def _check_evidence_sources(
    artifact_directory: Path,
    records: list[dict[str, Any]],
) -> list[ValidationIssue]:
    """Verify that each evidence excerpt exists at its declared source locator."""
    issues: list[ValidationIssue] = []
    allowed_root = artifact_directory.resolve().parent
    for index, record in enumerate(records, 1):
        location = f"evidence.jsonl[{index}]"
        locator = record.get("locator")
        excerpt = record.get("excerpt")
        if not isinstance(locator, dict) or not isinstance(excerpt, str):
            continue
        relative_file = locator.get("file")
        if not isinstance(relative_file, str) or not relative_file:
            continue
        source_path = Path(relative_file)
        if source_path.is_absolute():
            issues.append(
                ValidationIssue(location, "locator.file must be relative to the artifact directory")
            )
            continue
        resolved = (artifact_directory / source_path).resolve()
        try:
            resolved.relative_to(allowed_root)
        except ValueError:
            issues.append(
                ValidationIssue(location, "locator.file escapes the approved source root")
            )
            continue
        if not resolved.is_file():
            issues.append(
                ValidationIssue(location, "locator.file does not exist")
            )
            continue
        try:
            lines = resolved.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            issues.append(
                ValidationIssue(location, "locator.file cannot be read as UTF-8")
            )
            continue

        declared_line = locator.get("line")
        if declared_line is None:
            if excerpt not in "\n".join(lines):
                issues.append(
                    ValidationIssue(location, "excerpt does not exist in locator.file")
                )
            continue
        if (
            not isinstance(declared_line, int)
            or isinstance(declared_line, bool)
            or declared_line < 1
            or declared_line > len(lines)
        ):
            issues.append(
                ValidationIssue(location, "locator.line is outside the source file")
            )
            continue
        source_window = "\n".join(lines[declared_line - 1 : declared_line + 19])
        excerpt_first_line = excerpt.splitlines()[0]
        if (
            excerpt_first_line not in lines[declared_line - 1]
            or excerpt not in source_window
        ):
            issues.append(
                ValidationIssue(
                    location,
                    "excerpt does not match the declared locator.file and locator.line",
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
                    ValidationIssue(
                        f"{ARTIFACT_KIND_FILES[kind]}[{index}]",
                        f"{field} must be an array",
                    )
                )
                continue
            for value in values:
                if value not in ids.get(target_kind, set()):
                    issues.append(
                        ValidationIssue(
                            f"{ARTIFACT_KIND_FILES[kind]}[{index}]",
                            f"{field} references unknown {target_kind} ID",
                        )
                    )

    def check_one(kind: str, field: str, target_kind: str) -> None:
        for index, record in enumerate(records.get(kind, []), 1):
            value = record.get(field)
            if value not in ids.get(target_kind, set()):
                issues.append(
                    ValidationIssue(
                        f"{ARTIFACT_KIND_FILES[kind]}[{index}]",
                        f"{field} references unknown {target_kind} ID",
                    )
                )

    check_many("signal", "source_evidence_ids", "evidence")
    check_many("decision", "evidence_ids", "evidence")
    check_many("claim", "evidence_ids", "evidence")
    check_many("action", "metric_ids", "metric")
    check_many("outcome", "evidence_ids", "evidence")
    check_one("action", "decision_id", "decision")
    check_one("outcome", "action_id", "action")
    check_one("outcome", "metric_id", "metric")

    approved_evidence_ids = {
        record.get("evidence_id")
        for record in records.get("evidence", [])
        if record.get("strength") != "awaiting_human_tag"
        and isinstance(record.get("approved_by"), str)
        and record["approved_by"].strip()
    }

    def check_approved_evidence(kind: str, field: str) -> None:
        """Do not let evidence awaiting human strength review drive downstream work."""
        for index, record in enumerate(records.get(kind, []), 1):
            values = record.get(field, [])
            if not isinstance(values, list):
                continue
            for value in values:
                if value in ids.get("evidence", set()) and value not in approved_evidence_ids:
                    issues.append(
                        ValidationIssue(
                            f"{ARTIFACT_KIND_FILES[kind]}[{index}]",
                            f"{field} references evidence awaiting human strength approval",
                        )
                    )

    check_approved_evidence("signal", "source_evidence_ids")
    check_approved_evidence("decision", "evidence_ids")
    check_approved_evidence("outcome", "evidence_ids")
    check_approved_evidence("claim", "evidence_ids")

    approvals_by_id = {
        approval.get("approval_id"): approval
        for approval in records.get("approval", [])
        if isinstance(approval.get("approval_id"), str)
    }
    for index, decision in enumerate(records.get("decision", []), 1):
        if decision.get("status") != "approved":
            continue
        location = f"decisions.jsonl[{index}]"
        approval_id = decision.get("approved_by")
        approval = approvals_by_id.get(approval_id)
        if approval is None:
            issues.append(
                ValidationIssue(location, "approved_by references unknown approval ID")
            )
            continue
        scope = approval.get("scope")
        decision_ids = scope.get("decision_ids", []) if isinstance(scope, dict) else []
        if decision.get("decision_id") not in decision_ids:
            issues.append(
                ValidationIssue(location, "approval does not cover decision ID")
            )
        if approval.get("status") != "approved":
            issues.append(
                ValidationIssue(location, "approval is not in approved status")
            )

    for index, action in enumerate(records.get("action", []), 1):
        if not (
            action.get("external_write") is True
            and action.get("status") in {"approved", "executed"}
        ):
            continue
        location = f"actions.jsonl[{index}]"
        approval_id = action.get("approved_by")
        approval = approvals_by_id.get(approval_id)
        if approval is None:
            issues.append(
                ValidationIssue(location, "approved_by references unknown approval ID")
            )
            continue
        scope = approval.get("scope")
        action_ids = scope.get("action_ids", []) if isinstance(scope, dict) else []
        if action.get("action_id") not in action_ids:
            issues.append(
                ValidationIssue(location, "approval does not cover action ID")
            )
        if approval.get("status") != "approved":
            issues.append(
                ValidationIssue(location, "approval is not in approved status")
            )
    return issues


# Every append-only artifact this module owns. `run_state` is absent on purpose:
# run-state.json is a mutable state file that is rewritten in place, not an
# append-only ledger, so it has no chain to verify.
CHAINED_KINDS = tuple(
    kind
    for filename, kind in ARTIFACT_FILES.items()
    if filename in APPEND_ONLY_FILES
)


def _check_append_chain(
    records: dict[str, list[dict[str, Any]]],
) -> list[ValidationIssue]:
    """Recompute each append-only artifact's chain and report any break."""
    return [
        ValidationIssue(location, message)
        for kind in CHAINED_KINDS
        for location, message in verify_append_chain(
            records.get(kind, []),
            ARTIFACT_KIND_FILES[kind],
        )
    ]


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
            if require_complete and filename in REQUIRED_COMPLETE_FILES:
                issues.append(ValidationIssue(filename, "required artifact is missing"))
            continue
        try:
            items = load_records(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            issues.append(ValidationIssue(filename, str(exc)))
            continue
        if not items:
            issues.append(
                ValidationIssue(filename, "artifact must contain at least one record")
            )
            continue
        records[kind] = items
        for index, record in enumerate(items, 1):
            issues.extend(validate_record(kind, record, f"{filename}[{index}]"))

    if records:
        issues.extend(
            _check_evidence_sources(directory, records.get("evidence", []))
        )
        issues.extend(_check_references(records, _collect_ids(records)))
        issues.extend(_check_append_chain(records))
    return issues


def validate_gate_decision_log(path: Path) -> list[ValidationIssue]:
    """Validate the repository gate log against contracts/gate-decision.schema.json.

    ``harness/decisions.jsonl`` records build and release gate verdicts for this
    repository. It is a different artifact from a run's ``decisions.jsonl``,
    which holds evidence-traced growth decisions. Validating the gate log
    against the growth-decision contract would report a false violation on every
    line, so the two contracts are kept separate and this log is never rewritten
    to fit the other shape.
    """
    issues: list[ValidationIssue] = []
    try:
        records = load_records(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [ValidationIssue(str(path), str(exc))]
    if not records:
        return [ValidationIssue(str(path), "gate decision log must contain at least one record")]

    seen_ids: set[str] = set()
    for index, record in enumerate(records, 1):
        location = f"{path.name}[{index}]"
        issues.extend(
            ValidationIssue(location, message)
            for message in validate_schema_record(GATE_DECISION_SCHEMA_FILE, record)
        )
        identifier = record.get("decision_id")
        if isinstance(identifier, str):
            if identifier in seen_ids:
                issues.append(
                    ValidationIssue(location, "decision_id is not unique in the gate log")
                )
            seen_ids.add(identifier)
        supersedes = record.get("supersedes")
        if isinstance(supersedes, str) and supersedes not in seen_ids:
            issues.append(
                ValidationIssue(
                    location,
                    "supersedes must reference a decision_id recorded earlier in the log",
                )
            )
    return issues


def render_issues(issues: Iterable[ValidationIssue]) -> str:
    return "\n".join(issue.render() for issue in issues)
