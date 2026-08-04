"""Deterministic bridges for PMF Radar imports and hplan gate intake."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from .append_only import chain_records
from .connector_validation import validate_cs_event_record
from .contracts import load_records, validate_artifact_directory
from .schema_validation import validate_schema_record


class IntegrationContractError(ValueError):
    """An integration artifact cannot be accepted without inventing state."""


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


def _integration_id(system: str, external_id: str) -> str:
    digest = hashlib.sha256(f"{system}\0{external_id}".encode("utf-8")).hexdigest()
    return f"INT-{digest[:24].upper()}"


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
