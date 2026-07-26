"""Validate repository structure and portable skill metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .contracts import ValidationIssue


EXPECTED_SKILLS = {
    "plan-customer-reach",
    "run-switch-interview",
    "synthesize-interviews",
    "connect-customer-channels",
    "triage-customer-signals",
    "define-growth-metrics",
    "record-growth-decision",
    "audit-answer-visibility",
    "draft-evidence-content",
    "design-first-user-loop",
    "run-growth-loop",
}

EXPECTED_CONNECTOR_CONTRACTS = {
    "channel-connection.schema.json",
    "connector-state.schema.json",
    "cs-event.schema.json",
    "delivery-event.schema.json",
    "reply-draft.schema.json",
}


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    try:
        block = text.split("---\n", 2)[1]
    except IndexError as exc:
        raise ValueError("unterminated YAML frontmatter") from exc
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError("frontmatter must use simple key-value fields")
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields


def validate_repository(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    skill_root = root / "skills"
    actual_skills = {
        path.name
        for path in skill_root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    } if skill_root.exists() else set()

    if actual_skills != EXPECTED_SKILLS:
        missing = sorted(EXPECTED_SKILLS - actual_skills)
        extra = sorted(actual_skills - EXPECTED_SKILLS)
        if missing:
            issues.append(ValidationIssue("skills", f"missing skills: {', '.join(missing)}"))
        if extra:
            issues.append(ValidationIssue("skills", f"unexpected skills: {', '.join(extra)}"))

    for skill_name in sorted(EXPECTED_SKILLS):
        skill_file = skill_root / skill_name / "SKILL.md"
        if not skill_file.exists():
            continue
        text = skill_file.read_text(encoding="utf-8")
        if "TODO" in text:
            issues.append(ValidationIssue(str(skill_file), "contains TODO placeholder"))
        try:
            metadata = _frontmatter(text)
        except ValueError as exc:
            issues.append(ValidationIssue(str(skill_file), str(exc)))
            continue
        if set(metadata) != {"name", "description"}:
            issues.append(
                ValidationIssue(
                    str(skill_file),
                    "frontmatter must contain only name and description",
                )
            )
        if metadata.get("name") != skill_name:
            issues.append(ValidationIssue(str(skill_file), "name must match folder"))
        description = metadata.get("description", "")
        if len(description) < 60 or "Use when" not in description:
            issues.append(
                ValidationIssue(
                    str(skill_file),
                    "description must explain what the skill does and include 'Use when'",
                )
            )
        if len(text.splitlines()) >= 500:
            issues.append(ValidationIssue(str(skill_file), "SKILL.md must stay under 500 lines"))

        reference = skill_root / skill_name / "references" / "output-contract.md"
        if not reference.exists():
            issues.append(ValidationIssue(str(reference), "required reference is missing"))

        openai_yaml = skill_root / skill_name / "agents" / "openai.yaml"
        if not openai_yaml.exists():
            issues.append(ValidationIssue(str(openai_yaml), "UI metadata is missing"))
        else:
            ui_text = openai_yaml.read_text(encoding="utf-8")
            if f"${skill_name}" not in ui_text:
                issues.append(
                    ValidationIssue(
                        str(openai_yaml),
                        "default_prompt must mention the skill explicitly",
                    )
                )

    for relative in (
        ".claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
        ".codex-plugin/plugin.json",
        ".agents/plugins/marketplace.json",
    ):
        path = root / relative
        if not path.exists():
            issues.append(ValidationIssue(relative, "manifest is missing"))
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(ValidationIssue(relative, f"invalid JSON: {exc.msg}"))
            continue
        if relative.endswith("plugin.json") and payload.get("name") != "signal-to-growth":
            issues.append(ValidationIssue(relative, "plugin name must be signal-to-growth"))

    contract_root = root / "contracts"
    for filename in sorted(EXPECTED_CONNECTOR_CONTRACTS):
        path = contract_root / filename
        if not path.exists():
            issues.append(ValidationIssue(str(path), "connector contract is missing"))
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            issues.append(ValidationIssue(str(path), f"invalid JSON: {exc.msg}"))
            continue
        if payload.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            issues.append(
                ValidationIssue(
                    str(path),
                    "connector contract must use JSON Schema draft 2020-12",
                )
            )

    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"\[(?:TODO|PLACEHOLDER)[^\]]*\]", text, re.I):
            issues.append(ValidationIssue(str(path), "contains unresolved placeholder"))
    return issues
