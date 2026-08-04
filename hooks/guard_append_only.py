#!/usr/bin/env python3
"""PreToolUse hook: deny direct writes to append-only JSONL artifacts.

Reads the standard PreToolUse JSON payload from stdin and, when the target
tool is Edit, Write, or a recognized mutating Bash command and the target is
one of Signal to Growth's append-only artifacts, denies the call and points the
model at the append-record CLI command instead.
"""

from __future__ import annotations

import json
import os
import re
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
        "approvals.jsonl",
    }
)

_SHELL_MUTATION_PATTERNS = (
    re.compile(r"\b(?:rm|mv|cp|truncate|tee)\b"),
    re.compile(r"\bsed\s+(?:-[A-Za-z]*i[A-Za-z]*|--in-place)\b"),
    re.compile(r"\bperl\s+-[A-Za-z]*i[A-Za-z]*\b"),
    re.compile(r"\.(?:write_text|write_bytes)\s*\("),
    re.compile(r"\bopen\s*\([^)]*,\s*['\"][wax+]"),
)
_REDIRECTION_TARGET = re.compile(
    r"(?<!<)>{1,2}\s*(?P<target>(?:'[^']+'|\"[^\"]+\"|[^\s;&|]+))"
)


def _deny(reason: str) -> None:
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


def _bash_mutates_append_only(command: str) -> str | None:
    filename = next(
        (name for name in APPEND_ONLY_FILES if name in command),
        None,
    )
    if filename is None:
        return None
    if re.search(
        r"(?:scripts/stg\.py|signal-to-growth)\s+append-record\b",
        command,
    ):
        return None
    for match in _REDIRECTION_TARGET.finditer(command):
        if filename in match.group("target"):
            return filename
    if any(pattern.search(command) for pattern in _SHELL_MUTATION_PATTERNS):
        return filename
    return None


def main() -> int:
    payload = json.load(sys.stdin)
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    filename = os.path.basename(file_path)

    if tool_name in ("Edit", "Write") and filename in APPEND_ONLY_FILES:
        reason = (
            f"{filename} is an append-only artifact. Do not Edit/Write it "
            'directly — append one line with: python3 "${CLAUDE_PLUGIN_ROOT}"'
            "/scripts/stg.py append-record <file> '<json-object>'"
        )
        _deny(reason)
        return 0

    if tool_name == "Bash":
        protected = _bash_mutates_append_only(str(tool_input.get("command", "")))
        if protected is not None:
            _deny(
                f"Bash may overwrite append-only artifact {protected}. "
                "Use signal-to-growth append-record instead."
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
