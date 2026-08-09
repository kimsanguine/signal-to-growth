#!/usr/bin/env python3
"""
Distribution Scorer — Runs an aeo-harness analysis script N times and reports
each numeric score field as a DISTRIBUTION (median / min / max / stdev), not a
single number.

WHY distributional reporting is needed
--------------------------------------
AI visibility measured against live answer engines is unstable across repeated
queries, so a single point score is false precision:
  - SE Ranking: querying the same prompt 3 times yielded only a 9.2% URL
    overlap across the three result sets.
  - SparkToro: the same brand list appeared in fewer than 1 out of 100 repeated
    runs of the same brand query.
Reporting a single "AI visibility score" therefore hides the variance and
overstates confidence.

HONEST CAVEAT — our local heuristic is deterministic, not live
--------------------------------------------------------------
The aeo-harness citability/SEO scripts operate on a FIXED fetched HTML document
and apply a deterministic heuristic. Re-running them on the same URL yields
(barring page changes or transient fetch differences) identical numbers —
variance 0. That stability is NOT evidence that real AI-engine citation is
stable; it only reflects that we are not actually querying a live LLM. True
AI-engine citation variance (the 9.2% / <1/100 instability above) can only be
measured with live LLM queries via a bring-your-own-API path, which is NOT
implemented here. This tool labels the deterministic case explicitly so the
distinction is never silently conflated.

Usage
-----
    distribution.py <script_name> <url> [--runs N]

Runs `<.venv>/python3 <scripts_dir>/<script_name>.py <url>` as a subprocess N
times (default N=5), parses each run's stdout as JSON, extracts the top-level
numeric score fields, and reports per-field distribution stats plus a stability
label. Result JSON is printed to stdout; diagnostics go to stderr.

stdlib only (subprocess, json, statistics, argparse, sys, os). No external deps.
"""

import argparse
import json
import os
import statistics
import subprocess
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
VENV_PYTHON = os.path.join(SKILL_DIR, ".venv", "bin", "python3")

DETERMINISTIC_NOTE = (
    "이 지표는 고정 HTML 기반 결정론적 휴리스틱. 진짜 AI 엔진 인용 변동은 "
    "라이브 LLM 질의(BYO-API)가 필요하며 현재 미구현."
)
VARIANCE_NOTE = "report as range, not single number."


def run_once(script_name, url):
    """
    Execute the target script once and return its parsed JSON dict.

    Returns (result_dict, error_str). Exactly one is non-None.
    Parse failure is reported explicitly — never silently treated as 0.
    """
    script_path = os.path.join(SCRIPTS_DIR, script_name + ".py")
    if not os.path.isfile(script_path):
        return None, f"script not found: {script_path}"

    try:
        proc = subprocess.run(
            [VENV_PYTHON, script_path, url],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return None, "subprocess timed out after 120s"
    except Exception as exc:  # pragma: no cover - defensive
        return None, f"subprocess failed to start: {exc}"

    stdout = proc.stdout.strip()
    if not stdout:
        return None, (
            f"empty stdout (exit code {proc.returncode}); "
            f"stderr: {proc.stderr.strip()[:500]!r}"
        )

    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return None, (
            f"stdout was not valid JSON ({exc}); "
            f"first 300 chars: {stdout[:300]!r}"
        )

    if not isinstance(parsed, dict):
        return None, f"parsed JSON was {type(parsed).__name__}, expected object/dict"

    return parsed, None


def extract_numeric_fields(result):
    """Top-level keys whose value is a real number (excludes bool)."""
    fields = {}
    for key, value in result.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            fields[key] = float(value)
    return fields


def summarize(values):
    """Compute distribution stats for one field's values across runs."""
    summary = {
        "n": len(values),
        "values": values,
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "range": round(max(values) - min(values), 6),
    }
    # stdev requires >= 2 data points.
    summary["stdev"] = round(statistics.stdev(values), 6) if len(values) > 1 else 0.0

    if summary["range"] == 0:
        summary["stability"] = "deterministic (variance 0)"
        summary["note"] = DETERMINISTIC_NOTE
    else:
        summary["stability"] = "variable"
        summary["note"] = VARIANCE_NOTE
    return summary


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run an aeo-harness script N times and report each numeric score "
            "field as a distribution (median/min/max/stdev) instead of a single "
            "number."
        )
    )
    parser.add_argument("script_name", help="script base name, e.g. citability_scorer")
    parser.add_argument("url", help="URL passed through to the target script")
    parser.add_argument(
        "--runs", type=int, default=5, help="number of repeated runs (default 5)"
    )
    args = parser.parse_args()

    if args.runs < 1:
        print("ERROR: --runs must be >= 1", file=sys.stderr)
        sys.exit(2)

    if not os.path.isfile(VENV_PYTHON):
        print(f"ERROR: venv python not found at {VENV_PYTHON}", file=sys.stderr)
        sys.exit(2)

    per_run_fields = []  # list of dict[str, float], one per successful run
    run_errors = []  # list of {"run": i, "error": str}

    for i in range(1, args.runs + 1):
        print(
            f"[distribution] run {i}/{args.runs}: {args.script_name} {args.url}",
            file=sys.stderr,
        )
        result, error = run_once(args.script_name, args.url)
        if error is not None:
            run_errors.append({"run": i, "error": error})
            print(f"[distribution] run {i} FAILED: {error}", file=sys.stderr)
            continue
        fields = extract_numeric_fields(result)
        if not fields:
            run_errors.append(
                {"run": i, "error": "no top-level numeric fields found in output JSON"}
            )
            print(
                f"[distribution] run {i}: no numeric fields in output", file=sys.stderr
            )
            continue
        per_run_fields.append(fields)

    successful = len(per_run_fields)

    # Build per-field distributions. A field is only summarized over the runs in
    # which it actually appeared; mismatched presence is reported, not hidden.
    distributions = {}
    all_keys = set()
    for fields in per_run_fields:
        all_keys.update(fields.keys())

    for key in sorted(all_keys):
        present = [f[key] for f in per_run_fields if key in f]
        summary = summarize(present)
        if len(present) != successful:
            summary["warning"] = (
                f"field present in {len(present)}/{successful} successful runs"
            )
        distributions[key] = summary

    output = {
        "script_name": args.script_name,
        "url": args.url,
        "runs_requested": args.runs,
        "runs_succeeded": successful,
        "runs_failed": len(run_errors),
        "run_errors": run_errors,
        "distributions": distributions,
    }

    if successful == 0:
        output["status"] = "NO_DATA"
        output["message"] = (
            "no run produced parseable numeric output; see run_errors. "
            "Parse failures are reported, NOT treated as 0."
        )
    else:
        any_variable = any(
            d["stability"] != "deterministic (variance 0)"
            for d in distributions.values()
        )
        if any_variable:
            output["status"] = "VARIABLE"
            output["message"] = (
                "at least one field varied across runs — " + VARIANCE_NOTE
            )
        else:
            output["status"] = "DETERMINISTIC"
            output["message"] = DETERMINISTIC_NOTE

    print(json.dumps(output, indent=2))
    # Non-zero exit if we got nothing usable, so callers can detect failure.
    sys.exit(0 if successful > 0 else 1)


if __name__ == "__main__":
    main()
