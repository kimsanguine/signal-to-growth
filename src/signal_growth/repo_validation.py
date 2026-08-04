"""Validate repository structure and portable skill metadata."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from .contracts import ValidationIssue
from .workflow import SKILL_OUTPUT_FILES


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


OUTPUT_FILENAME = re.compile(
    r"`([A-Za-z0-9][A-Za-z0-9._-]*\.(?:json|jsonl|md|csv))`"
)


def _declared_output_files(skill_text: str) -> set[str]:
    """Filenames listed as bullets under the SKILL.md `## Outputs` heading."""
    names: set[str] = set()
    in_outputs = False
    for line in skill_text.splitlines():
        if line.startswith("## "):
            in_outputs = line.strip() == "## Outputs"
            continue
        if in_outputs and line.lstrip().startswith("- "):
            names.update(OUTPUT_FILENAME.findall(line))
    return names


def _documented_output_files(contract_text: str) -> set[str]:
    """Filenames used as `## `-level headings in an output contract."""
    return {
        name
        for line in contract_text.splitlines()
        if line.startswith("## ")
        for name in OUTPUT_FILENAME.findall(line)
    }


def _check_output_contract_alignment(skill_root: Path) -> list[ValidationIssue]:
    """Fail when a skill's three output declarations disagree.

    SKILL.md tells the model what to write, output-contract.md tells it how, and
    workflow.SKILL_OUTPUT_FILES decides when the skill counts as complete. If
    they drift apart, the router can call a skill done while a documented
    artifact was never produced.
    """
    issues: list[ValidationIssue] = []
    for skill_name in sorted(EXPECTED_SKILLS):
        skill_file = skill_root / skill_name / "SKILL.md"
        contract_file = skill_root / skill_name / "references" / "output-contract.md"
        if not skill_file.exists() or not contract_file.exists():
            continue

        sources: dict[str, set[str]] = {
            str(skill_file): _declared_output_files(
                skill_file.read_text(encoding="utf-8")
            ),
            str(contract_file): _documented_output_files(
                contract_file.read_text(encoding="utf-8")
            ),
        }
        routed = SKILL_OUTPUT_FILES.get(skill_name)
        if routed is not None:
            sources["src/signal_growth/workflow.py"] = set(routed)

        expected: set[str] = set().union(*sources.values())
        for location, declared in sources.items():
            missing = sorted(expected - declared)
            if missing:
                issues.append(
                    ValidationIssue(
                        location,
                        f"{skill_name} output drift — declared elsewhere but not "
                        f"here: {', '.join(missing)}",
                    )
                )
    return issues


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
        if "Do not use" not in description:
            issues.append(
                ValidationIssue(
                    str(skill_file),
                    "description must include a 'Do not use' negative trigger so a "
                    "neighbouring skill is not selected by accident",
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

    try:
        project_metadata = tomllib.loads(
            (root / "pyproject.toml").read_text(encoding="utf-8")
        )["project"]
        project_version = project_metadata["version"]
        project_dependencies = project_metadata.get("dependencies", [])
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        project_version = None
        project_dependencies = []
        issues.append(
            ValidationIssue("pyproject.toml", "project.version is missing or invalid")
        )

    dependency_names = {
        re.split(r"[\s<>=!~;\[]", str(dependency), maxsplit=1)[0].casefold()
        for dependency in project_dependencies
    }
    requirements_path = root / "requirements.txt"
    try:
        requirement_names = {
            re.split(r"[\s<>=!~;\[]", line.strip(), maxsplit=1)[0].casefold()
            for line in requirements_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
    except (OSError, UnicodeError):
        requirement_names = set()
        issues.append(
            ValidationIssue(
                "requirements.txt",
                "hosted runtime dependency file is missing or unreadable",
            )
        )
    missing_hosted_dependencies = dependency_names - requirement_names
    if missing_hosted_dependencies:
        issues.append(
            ValidationIssue(
                "requirements.txt",
                "hosted runtime is missing project dependencies: "
                + ", ".join(sorted(missing_hosted_dependencies)),
            )
        )

    try:
        lock_payload = tomllib.loads(
            (root / "uv.lock").read_text(encoding="utf-8")
        )
        locked_projects = [
            package
            for package in lock_payload.get("package", [])
            if package.get("name") == "signal-to-growth"
        ]
        locked_project = locked_projects[0]
        lock_version = locked_project["version"]
        lock_dependency_names = {
            dependency.get("name", "").casefold()
            for dependency in locked_project.get("dependencies", [])
            if isinstance(dependency, dict)
        }
    except (OSError, KeyError, IndexError, tomllib.TOMLDecodeError):
        lock_version = None
        lock_dependency_names = set()
        issues.append(
            ValidationIssue(
                "uv.lock",
                "hosted lockfile is missing or invalid",
            )
        )
    if project_version is not None and lock_version != project_version:
        issues.append(
            ValidationIssue(
                "uv.lock",
                f"project version must match pyproject.toml ({project_version})",
            )
        )
    missing_lock_dependencies = dependency_names - lock_dependency_names
    if missing_lock_dependencies:
        issues.append(
            ValidationIssue(
                "uv.lock",
                "hosted runtime is missing project dependencies: "
                + ", ".join(sorted(missing_lock_dependencies)),
            )
        )

    manifest_versions: list[tuple[str, object]] = []
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
        if relative in {
            ".claude-plugin/plugin.json",
            ".codex-plugin/plugin.json",
        }:
            manifest_versions.append((relative, payload.get("version")))
        elif relative == ".claude-plugin/marketplace.json":
            manifest_versions.append(
                (f"{relative}:metadata", payload.get("metadata", {}).get("version"))
            )
            plugins = payload.get("plugins", [])
            manifest_versions.extend(
                (f"{relative}:plugins[{index}]", plugin.get("version"))
                for index, plugin in enumerate(plugins)
                if isinstance(plugin, dict)
            )
        elif relative == ".agents/plugins/marketplace.json":
            plugins = payload.get("plugins", [])
            manifest_versions.extend(
                (f"{relative}:plugins[{index}]", plugin.get("version"))
                for index, plugin in enumerate(plugins)
                if isinstance(plugin, dict)
            )

    if project_version is not None:
        for location, version in manifest_versions:
            if version != project_version:
                issues.append(
                    ValidationIssue(
                        location,
                        f"version must match pyproject.toml ({project_version})",
                    )
                )

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

    issues.extend(_check_output_contract_alignment(skill_root))

    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if re.search(r"\[(?:TODO|PLACEHOLDER)[^\]]*\]", text, re.I):
            issues.append(ValidationIssue(str(path), "contains unresolved placeholder"))
    return issues
