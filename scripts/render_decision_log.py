#!/usr/bin/env python3
"""Regenerate `runtime/decision-log.md` from the append-only gate log.

The gate log is the source; the document is the projection. This script refuses
to render a log that fails `contracts/gate-decision.schema.json`, so an invalid
record cannot be laundered into readable prose.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.contracts import (  # noqa: E402
    load_records,
    render_issues,
    validate_gate_decision_log,
)
from signal_growth.decision_log import render_decision_log  # noqa: E402


GATE_LOG = ROOT / "harness" / "decisions.jsonl"
DOCUMENT = ROOT / "runtime" / "decision-log.md"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the document is out of date instead of rewriting it",
    )
    args = parser.parse_args()

    issues = validate_gate_decision_log(GATE_LOG)
    if issues:
        print(render_issues(issues), file=sys.stderr)
        print(
            "gate log is invalid; refusing to render runtime/decision-log.md",
            file=sys.stderr,
        )
        return 1

    rendered = render_decision_log(load_records(GATE_LOG))
    if args.check:
        current = DOCUMENT.read_text(encoding="utf-8") if DOCUMENT.exists() else ""
        if current != rendered:
            print(
                "runtime/decision-log.md is out of date; "
                "run python3 scripts/render_decision_log.py",
                file=sys.stderr,
            )
            return 1
        print(f"{DOCUMENT.relative_to(ROOT)} matches {GATE_LOG.relative_to(ROOT)}")
        return 0

    DOCUMENT.write_text(rendered, encoding="utf-8")
    print(f"wrote {DOCUMENT.relative_to(ROOT)} from {GATE_LOG.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
