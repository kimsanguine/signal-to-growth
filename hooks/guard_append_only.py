#!/usr/bin/env python3
"""PreToolUse hook: deny direct Edit/Write on append-only JSONL artifacts.

Reads the standard PreToolUse JSON payload from stdin and, when the target
tool is Edit or Write and the file is one of Signal to Growth's append-only
artifacts, denies the call and points the model at the append-record CLI
command instead.
"""

from __future__ import annotations

import json
import os
import sys

APPEND_ONLY_FILES = frozenset(
    {
        "evidence.jsonl",
        "signals.jsonl",
        "metrics.jsonl",
        "decisions.jsonl",
        "actions.jsonl",
        "outcomes.jsonl",
        "cs-events.jsonl",
        "reply-drafts.jsonl",
        "delivery-events.jsonl",
        "integration-references.jsonl",
        "claim-ledger.jsonl",
        "visibility-observations.jsonl",
    }
)


def main() -> int:
    payload = json.load(sys.stdin)
    tool_name = payload.get("tool_name")
    file_path = payload.get("tool_input", {}).get("file_path", "")
    filename = os.path.basename(file_path)

    if tool_name in ("Edit", "Write") and filename in APPEND_ONLY_FILES:
        reason = (
            f"{filename} is an append-only artifact. Do not Edit/Write it "
            'directly — append one line with: python3 "${CLAUDE_PLUGIN_ROOT}"'
            "/scripts/stg.py append-record <file> '<json-object>'"
        )
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
