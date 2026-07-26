#!/usr/bin/env python3
"""Capture five fresh, read-only evaluator perspectives for a runtime run."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "eval" / "evaluator-output.schema.json"
PERSONAS = {
    "primary-user": "Korean AI-native SaaS founder and product lead. Judge task success and next-action clarity.",
    "product-rigor": "Senior PM/CPO. Judge JTBD, counterevidence, metric and decision rigor.",
    "korean-cs-ops": "Korean CS and Growth Ops lead. Judge provider truth, PII, dedupe, recovery, and paid-capability boundaries.",
    "cross-runtime": "Agent Skills portability engineer. Judge install, discovery, explicit invocation, artifact parity, and path portability.",
    "red-team": "Evidence, privacy, and approval adversary. Try to find fabricated evidence, unsafe writes, secret leakage, and overclaims.",
}


def prompt_for(name: str, description: str, run_dir: Path) -> str:
    return "\n".join(
        (
            f"You are the {name} evaluator: {description}",
            "Perform a fresh, read-only review of the Signal to Growth formal evaluation.",
            "Read AGENTS.md, eval/skill-evaluation-plan.md, eval/expected-behaviors.md,",
            f"{run_dir.relative_to(ROOT) / 'codex-canonical.json'}, and",
            f"{run_dir.relative_to(ROOT) / 'codex-anchors.json'}.",
            "The Codex run is fixture-only semantic evaluation, not generated-artifact E2E.",
            "Claude runtime output is unavailable because the account monthly spend limit returned HTTP 429.",
            "Do not infer Claude/Codex parity, real plugin installation, provider E2E, or production readiness.",
            "Do not write files, call network, use credentials, or expose fixture identifiers.",
            "Return only JSON matching the supplied schema. A missing Claude runtime must prevent GO.",
        )
    )


def run_one(name: str, description: str, run_dir: Path) -> dict[str, Any]:
    command = [
        "codex", "exec", "-C", str(ROOT), "-s", "read-only", "--ephemeral",
        "--output-schema", str(SCHEMA_PATH), prompt_for(name, description, run_dir),
    ]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    raw_path = run_dir / f"evaluator-{name}.raw.json"
    raw_path.write_text(completed.stdout, encoding="utf-8")
    (run_dir / f"evaluator-{name}.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode:
        raise RuntimeError(f"{name} returned {completed.returncode}")
    result = json.loads(completed.stdout)
    errors = list(Draft202012Validator(json.loads(SCHEMA_PATH.read_text())).iter_errors(result))
    if errors:
        raise RuntimeError(f"{name} schema failure: {errors[0].message}")
    result.update({"evaluated_at": datetime.now(UTC).isoformat(), "runtime": "codex"})
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    if not (run_dir / "codex-canonical.json").is_file():
        parser.error("--run-dir must contain codex-canonical.json")
    results: list[dict[str, Any]] = []
    for name, description in PERSONAS.items():
        try:
            results.append(run_one(name, description, run_dir))
        except (RuntimeError, json.JSONDecodeError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
    output = {
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "evaluated_at": datetime.now(UTC).isoformat(),
        "mode": "fresh-read-only-persona-review-of-codex-fixture-run",
        "claude_runtime": "blocked_by_monthly_spend_limit_http_429",
        "evaluators": results,
    }
    output_path = run_dir / "evaluator-rescore.json"
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
