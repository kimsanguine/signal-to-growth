"""Deterministic bridges for PMF Radar imports and hplan gate intake."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from .append_only import append_record, chain_records, verify_append_chain
from .connector_validation import validate_cs_event_record
from .contracts import load_records, validate_artifact_directory
from .schema_validation import validate_schema_record


class IntegrationContractError(ValueError):
    """An integration artifact cannot be accepted without inventing state."""


# The append-only ledgers this module materializes. `integration-references.jsonl`
# is emitted here and nowhere else, so if this module does not recompute its
# chain, nothing in the repository ever does and the hashes it writes are
# decoration rather than evidence.
CHAINED_INTEGRATION_FILES = ("cs-events.jsonl", "integration-references.jsonl")
HPLAN_HANDOFF_SCHEMA = "hplan-growth-handoff-profile.schema.json"
HPLAN_REFERENCE_FILENAME = "integration-references.jsonl"
STG_RECONSIDERATION_SCHEMA = "stg-hplan-reconsideration-profile.schema.json"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise IntegrationContractError(
                f"{path}:{line_number}: invalid JSON: {exc.msg}"
            ) from exc
        if not isinstance(value, dict):
            raise IntegrationContractError(
                f"{path}:{line_number}: each record must be an object"
            )
        records.append(value)
    if not records:
        raise IntegrationContractError(f"{path}: at least one export record is required")
    return records


def _render_jsonl(records: Iterable[Mapping[str, Any]]) -> str:
    return "".join(
        json.dumps(dict(record), ensure_ascii=False, separators=(",", ":")) + "\n"
        for record in records
    )


def _parse_jsonl_text(text: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _integration_id(system: str, external_id: str) -> str:
    digest = hashlib.sha256(f"{system}\0{external_id}".encode("utf-8")).hexdigest()
    return f"INT-{digest[:24].upper()}"


def _canonical_fingerprint(record: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        dict(record),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_required_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrationContractError(f"{label}: invalid JSON object") from exc
    if not isinstance(value, dict):
        raise IntegrationContractError(f"{label}: expected one JSON object")
    return value


def _validate_hplan_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    issues = validate_schema_record(HPLAN_HANDOFF_SCHEMA, profile)
    if issues:
        raise IntegrationContractError("hplan profile: " + "; ".join(issues))
    return dict(profile)


def _safe_hplan_output_directory(output_directory: Path, input_path: Path) -> Path:
    if ".." in output_directory.parts:
        raise IntegrationContractError("output directory path traversal is not allowed")
    absolute_directory = output_directory.absolute()
    if absolute_directory == Path(absolute_directory.anchor):
        raise IntegrationContractError("output directory must not be the filesystem root")
    current = Path(absolute_directory.anchor)
    for component in absolute_directory.parts[1:]:
        current /= component
        # macOS exposes system aliases such as /var at the filesystem root.
        # They are outside the caller's controllable output path; every deeper
        # symlink is rejected before a directory or ledger can be created.
        if current.is_symlink() and current.parent != Path(current.anchor):
            raise IntegrationContractError("output directory must not contain symlinks")
    if output_directory.exists() and not output_directory.is_dir():
        raise IntegrationContractError("output directory must be a directory")
    output_path = output_directory / HPLAN_REFERENCE_FILENAME
    if output_path.is_symlink():
        raise IntegrationContractError("output ledger must not be a symlink")
    if output_path.absolute() == input_path.absolute():
        raise IntegrationContractError("output must not target the input profile")
    return output_path


def _load_hplan_references(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = _read_jsonl(path)
    issues = verify_append_chain(records, path.name)
    if issues:
        raise IntegrationContractError(
            "; ".join(f"{location}: {message}" for location, message in issues)
        )
    for index, record in enumerate(records, 1):
        schema_issues = validate_schema_record("integration-reference.schema.json", record)
        if schema_issues:
            raise IntegrationContractError(
                f"{path.name}[{index}]: " + "; ".join(schema_issues)
            )
    return records


def import_hplan_handoff(
    input_path: Path,
    *,
    output_directory: Path | None = None,
    write: bool = False,
) -> dict[str, Any]:
    """Accept only an approved hplan gate reference; never project a decision.

    The source profile stays authoritative.  STG stores its opaque source URI and
    a fingerprint for replay detection, not hplan's evidence, metrics, owner,
    or status fields.
    """
    profile = _validate_hplan_profile(_load_required_object(input_path, "hplan profile"))
    source_record_ref = profile["source_record_ref"]
    fingerprint = _canonical_fingerprint(profile)
    reference = {
        "integration_id": _integration_id("hplan", source_record_ref),
        "system": "hplan",
        "external_id": source_record_ref,
        "source_record_ref": source_record_ref,
        "direction": "import",
        "local_artifact_ids": [_integration_id("hplan", source_record_ref)],
        "observed_at": profile["review_at"],
        "contract_version": "ai-pm-handoff-profile.v0",
        "status": "validated",
        "context": {
            "product_scope": profile["project_id"],
            "segment": None,
            "source_fingerprint": fingerprint,
        },
    }
    reference_issues = validate_schema_record("integration-reference.schema.json", reference)
    if reference_issues:
        raise IntegrationContractError("hplan reference: " + "; ".join(reference_issues))

    duplicate = False
    write_path: Path | None = None
    if output_directory is not None:
        write_path = _safe_hplan_output_directory(output_directory, input_path)
        existing = _load_hplan_references(write_path)
        matching = [
            item
            for item in existing
            if item.get("system") == "hplan" and item.get("external_id") == source_record_ref
        ]
        if matching:
            fingerprints = {
                item.get("context", {}).get("source_fingerprint") for item in matching
            }
            if fingerprints != {fingerprint}:
                raise IntegrationContractError("hplan handoff replay conflicts with recorded source")
            duplicate = True

    if write:
        if output_directory is None or write_path is None:
            raise IntegrationContractError("--write requires an output directory")
        if not duplicate:
            write_path.parent.mkdir(parents=True, exist_ok=True)
            append_record(write_path, reference)

    return {
        "source_system": "hplan",
        "contract_version": "ai-pm-handoff-profile.v0",
        "source_record_ref": source_record_ref,
        "source_status": profile["status"],
        "duplicate": duplicate,
        "write_performed": write and not duplicate,
        "created_decision_ids": [],
        "output_directory": str(output_directory.absolute()) if output_directory else None,
    }


def _select_unique_record(
    records: list[dict[str, Any]],
    *,
    field: str,
    value: str | None,
    label: str,
) -> dict[str, Any]:
    if value is not None:
        matches = [record for record in records if record.get(field) == value]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise IntegrationContractError(f"{label} not found: {value}")
        raise IntegrationContractError(f"{label} is not unique: {value}")
    if len(records) == 1:
        return records[0]
    raise IntegrationContractError(f"--{field.replace('_', '-')} is required")


def _read_validated_records(path: Path, schema_filename: str) -> list[dict[str, Any]]:
    try:
        records = _read_jsonl(path)
    except OSError as exc:
        raise IntegrationContractError(f"{path.name}: unable to read ledger") from exc
    chain_issues = verify_append_chain(records, path.name)
    if chain_issues:
        raise IntegrationContractError(
            "; ".join(f"{location}: {message}" for location, message in chain_issues)
        )
    for index, record in enumerate(records, 1):
        issues = validate_schema_record(schema_filename, record)
        if issues:
            raise IntegrationContractError(
                f"{path.name}[{index}]: " + "; ".join(issues)
            )
    return records


def _utc_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IntegrationContractError("outcome observed_at must be RFC 3339") from exc
    if parsed.tzinfo is None:
        raise IntegrationContractError("outcome observed_at must include a UTC offset")
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def build_hplan_reconsideration(
    artifact_directory: Path,
    *,
    integration_directory: Path,
    project_id: str,
    owner: str,
    outcome_id: str | None = None,
) -> dict[str, Any]:
    """Build a reference-only request for human hplan reconsideration.

    A mature, executed STG outcome can ask for a human review.  It cannot
    select an hplan verdict or create an STG decision on that person's behalf.
    """
    if not isinstance(project_id, str) or not project_id.strip():
        raise IntegrationContractError("project_id must be a non-empty string")
    if not isinstance(owner, str) or not owner.strip():
        raise IntegrationContractError("owner must be a non-empty string")

    references = _load_hplan_references(
        integration_directory / HPLAN_REFERENCE_FILENAME
    )
    accepted_hplan = [
        reference
        for reference in references
        if reference.get("system") == "hplan"
        and reference.get("status") == "validated"
        and reference.get("context", {}).get("product_scope") == project_id
    ]
    if not accepted_hplan:
        raise IntegrationContractError("validated hplan handoff is required for project")

    outcomes = _read_validated_records(
        artifact_directory / "outcomes.jsonl",
        "outcome.schema.json",
    )
    outcome = _select_unique_record(
        outcomes,
        field="outcome_id",
        value=outcome_id,
        label="outcome",
    )
    if outcome["maturity_status"] != "mature":
        raise IntegrationContractError("outcome must be mature before hplan reconsideration")
    if outcome["comparison"] in {"unknown", "inconclusive"}:
        raise IntegrationContractError("outcome comparison must be conclusive")
    if outcome["conclusion"] == "unknown":
        raise IntegrationContractError("outcome conclusion must be recorded")

    actions = _read_validated_records(
        artifact_directory / "actions.jsonl",
        "action.schema.json",
    )
    action = _select_unique_record(
        actions,
        field="action_id",
        value=outcome["action_id"],
        label="action",
    )
    if action["status"] != "executed":
        raise IntegrationContractError("outcome action must be executed")
    if outcome["metric_id"] not in action["metric_ids"]:
        raise IntegrationContractError("outcome metric must be declared by the executed action")

    metrics = _read_validated_records(
        artifact_directory / "metrics.jsonl",
        "metric.schema.json",
    )
    _select_unique_record(
        metrics,
        field="metric_id",
        value=outcome["metric_id"],
        label="metric",
    )

    profile = {
        "profile_version": "0.1",
        "project_id": project_id,
        "source_system": "signal-to-growth",
        "source_record_ref": f"stg://outcome/{outcome['outcome_id']}",
        "handoff_kind": "growth_outcome_to_reconsideration",
        "status": "COMPLETED",
        "evidence_refs": [],
        "metric_refs": [f"stg://metric/{outcome['metric_id']}"],
        "owner": owner,
        "review_at": _utc_timestamp(outcome["observed_at"]),
        "reopen_reason": "Completed Signal to Growth outcome requires human reconsideration.",
    }
    issues = validate_schema_record(STG_RECONSIDERATION_SCHEMA, profile)
    if issues:
        raise IntegrationContractError("hplan reconsideration: " + "; ".join(issues))
    return profile


def import_pmf_radar(
    input_path: Path,
    *,
    output_directory: Path | None = None,
    write: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Validate PMF Radar exports and optionally materialize connector artifacts."""
    exports = _read_jsonl(input_path)
    events: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for index, export in enumerate(exports, 1):
        location = f"{input_path.name}[{index}]"
        outer_issues = validate_schema_record("pmf-radar-export.schema.json", export)
        if outer_issues:
            raise IntegrationContractError(
                f"{location}: " + "; ".join(outer_issues)
            )
        event = export["event"]
        event_issues = validate_cs_event_record(event, f"{location}.event")
        if event_issues:
            raise IntegrationContractError(
                "; ".join(issue.render() for issue in event_issues)
            )
        event_id = event["event_id"]
        if event_id in seen_ids:
            continue
        seen_ids.add(event_id)
        events.append(dict(event))
        external_id = f"{event['provider']}:{event['provider_event_id']}"
        reference = {
            "integration_id": _integration_id("pmf_radar", external_id),
            "system": "pmf_radar",
            "external_id": external_id,
            "source_record_ref": export["source_record_ref"],
            "direction": "import",
            "local_artifact_ids": [event_id],
            "observed_at": event["received_at"],
            "contract_version": export["export_version"],
            "status": "validated",
            "context": {
                "product_scope": export["product_scope"],
                "segment": export["segment"],
            },
        }
        ref_issues = validate_schema_record(
            "integration-reference.schema.json",
            reference,
        )
        if ref_issues:
            raise IntegrationContractError(
                f"{location}: " + "; ".join(ref_issues)
            )
        references.append(reference)

    # Both files are append-only artifacts. This writer materializes them whole
    # rather than appending line by line, so it links the chain itself; without
    # this the import would emit unchained ledgers that no later reader can
    # verify.
    output_files = {
        "cs-events.jsonl": _render_jsonl(chain_records(events)),
        "integration-references.jsonl": _render_jsonl(chain_records(references)),
    }
    # Verify what will actually be persisted, re-read from the rendered text
    # rather than from the in-memory records. Checking the objects we just
    # chained would only restate `chain_records`; checking the bytes catches a
    # serialization defect that would ship a ledger nobody can verify.
    for filename in CHAINED_INTEGRATION_FILES:
        chain_issues = verify_append_chain(
            _parse_jsonl_text(output_files[filename]),
            filename,
        )
        if chain_issues:
            raise IntegrationContractError(
                "; ".join(
                    f"{location}: {message}" for location, message in chain_issues
                )
            )
    if write:
        if output_directory is None:
            raise IntegrationContractError("--write requires an output directory")
        output_directory.mkdir(parents=True, exist_ok=True)
        for filename, content in output_files.items():
            path = output_directory / filename
            if path.exists() and not force:
                raise IntegrationContractError(
                    f"{path} already exists; use --force to replace it"
                )
            path.write_text(content, encoding="utf-8")

    return {
        "source_system": "pmf_radar",
        "contract_version": "pmf-radar.stg.v1",
        "input_records": len(exports),
        "imported_events": len(events),
        "duplicate_events": len(exports) - len(events),
        "write_performed": write,
        "output_directory": (
            str(output_directory.resolve()) if output_directory is not None else None
        ),
        "next_skill": "connect-customer-channels" if write else None,
    }


def _load_optional_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrationContractError(f"{path}: invalid JSON") from exc
    if not isinstance(value, dict):
        raise IntegrationContractError(f"{path}: expected one JSON object")
    return value


def _select_decision(
    artifact_directory: Path,
    decision_id: str | None,
) -> dict[str, Any]:
    path = artifact_directory / "decisions.jsonl"
    if not path.exists():
        raise IntegrationContractError("decisions.jsonl is required")
    decisions = load_records(path)
    if decision_id is None:
        if len(decisions) != 1:
            raise IntegrationContractError(
                "--decision-id is required when decisions.jsonl has multiple records"
            )
        return decisions[0]
    for decision in decisions:
        if decision.get("decision_id") == decision_id:
            return decision
    raise IntegrationContractError(f"decision not found: {decision_id}")


def build_hplan_intake(
    artifact_directory: Path,
    *,
    decision_id: str | None = None,
    product_name: str | None = None,
    jtbd: str | None = None,
    functional_requirements: Iterable[str] = (),
    cogs_ceiling: str | None = None,
    latency_budget: str | None = None,
    counter_position: str | None = None,
    mvp_slice: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Project validated STG artifacts into a draft hplan gate intake."""
    issues = validate_artifact_directory(artifact_directory)
    if issues:
        raise IntegrationContractError(
            "; ".join(issue.render() for issue in issues)
        )
    decision = _select_decision(artifact_directory, decision_id)
    evidence = (
        load_records(artifact_directory / "evidence.jsonl")
        if (artifact_directory / "evidence.jsonl").exists()
        else []
    )
    metrics = (
        load_records(artifact_directory / "metrics.jsonl")
        if (artifact_directory / "metrics.jsonl").exists()
        else []
    )
    actions = (
        load_records(artifact_directory / "actions.jsonl")
        if (artifact_directory / "actions.jsonl").exists()
        else []
    )
    reach = _load_optional_object(artifact_directory / "reach-plan.json") or {}
    first_user = (
        _load_optional_object(artifact_directory / "first-user-loop.json") or {}
    )
    selected_evidence = [
        item
        for item in evidence
        if item.get("evidence_id") in decision.get("evidence_ids", [])
    ]
    selected_actions = [
        item for item in actions if item.get("decision_id") == decision["decision_id"]
    ]
    selected_metric_ids = sorted(
        {
            metric_id
            for action in selected_actions
            for metric_id in action.get("metric_ids", [])
        }
    )
    available_metric_ids = {item.get("metric_id") for item in metrics}
    selected_metric_ids = [
        metric_id
        for metric_id in selected_metric_ids
        if metric_id in available_metric_ids
    ]

    brief: dict[str, Any] = {
        "brief_version": "stg.hplan-intake.v1",
        "generated_at": generated_at or datetime.now(UTC).isoformat(),
        "status": "draft_for_gate",
        "source_decision_id": decision["decision_id"],
        "product_name": product_name,
        "problem": reach.get("research_question"),
        "icp": reach.get("segment"),
        "jtbd": jtbd,
        "functional_requirements": list(functional_requirements),
        "acceptance_criteria": [
            decision["success_condition"],
            f"Stop: {decision['stop_condition']}",
        ],
        "cogs_ceiling": cogs_ceiling,
        "latency_budget": latency_budget,
        "counter_position": counter_position,
        "not_build": list(decision.get("not_build", [])),
        "mvp_slice": mvp_slice or first_user.get("offer"),
        "stg_decision_status": decision["status"],
        "hplan_gate_decision": None,
        "strong_signals_list": [
            (
                f"{item['evidence_id']}: {item['excerpt']} "
                f"({item['locator']['file']}:{item['locator'].get('line')})"
            )
            for item in selected_evidence
            if item.get("strength") == "strong"
        ],
        "source_refs": {
            "evidence_ids": [item["evidence_id"] for item in selected_evidence],
            "metric_ids": selected_metric_ids,
            "action_ids": [item["action_id"] for item in selected_actions],
        },
        "unknown_fields": [],
    }
    required_for_review = (
        "product_name",
        "problem",
        "icp",
        "jtbd",
        "functional_requirements",
        "cogs_ceiling",
        "latency_budget",
        "counter_position",
        "mvp_slice",
    )
    brief["unknown_fields"] = [
        field
        for field in required_for_review
        if brief[field] is None or brief[field] == []
    ]
    if not brief["unknown_fields"] and decision["status"] == "approved":
        brief["status"] = "ready_for_gate_review"
    schema_issues = validate_schema_record("hplan-intake-brief.schema.json", brief)
    if schema_issues:
        raise IntegrationContractError("; ".join(schema_issues))
    return brief


def write_json(
    value: Mapping[str, Any],
    path: Path,
    *,
    force: bool = False,
) -> None:
    if path.exists() and not force:
        raise IntegrationContractError(f"{path} already exists; use --force to replace it")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
