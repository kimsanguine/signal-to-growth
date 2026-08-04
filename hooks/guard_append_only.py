#!/usr/bin/env python3
"""PreToolUse hook: deny direct writes to append-only JSONL artifacts.

Reads the standard PreToolUse JSON payload from stdin and, when the target
tool is Edit, Write, or a recognized mutating Bash command and the target is
one of Signal to Growth's append-only artifacts, denies the call and points the
model at the append-record CLI command instead.

Threat model — read this before trusting it
-------------------------------------------
This hook is a **mistake guard, not an adversarial defense.** It inspects a
Bash command as *text* before any shell runs it, so it cannot know what that
text will expand to. Complete blocking by static parsing is impossible in
principle: a shell resolves globs, variables, command substitution, aliases,
and quoting at execution time, and any of those can produce a protected path
the matcher never saw.

It therefore denies two classes of command:

1. A protected filename appearing literally (`rm artifacts/evidence.jsonl`).
2. A mutating command whose target is *opaque* — it contains a glob or an
   expansion — and points somewhere a protected artifact plausibly lives
   (`rm artifacts/*.jsonl`, `rm artifacts/${NAME}l`). These were confirmed to
   slip past the literal-only matcher.

Known gaps that remain open by design, because closing them would deny
ordinary commands:

- A bare glob with no literal prefix (`rm *`) inside an artifacts directory.
- A path assembled entirely at runtime (`rm "$(cat target.txt)"`).
- Any interpreter invoked with a script file rather than an inline command.
- Anything run outside the hooked tool, such as a subshell spawned by a script.

Durable protection lives in git history and the append-record CLI, not here.
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
        "release-notes.jsonl",
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
_SANCTIONED_APPEND = re.compile(
    r"(?:scripts/stg\.py|signal-to-growth)\s+append-record\b"
)
# A token whose final value the hook cannot know: it holds a glob metacharacter,
# a parameter expansion, or command substitution.
_OPAQUE_TOKEN = re.compile(r"[^\s;&|<>'\"]*(?:[*?\[]|\$\{|\$[A-Za-z_(]|`)[^\s;&|<>'\"]*")
# Directory names that hold append-only artifacts in this repository.
_ARTIFACT_DIR = re.compile(r"artifacts?\b", re.I)


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


def _opaque_target_hits_append_only(target: str) -> bool:
    """Report whether an unresolvable token could name a protected artifact."""
    directory, _, basename = target.rpartition("/")
    if _ARTIFACT_DIR.search(directory):
        return True
    if "jsonl" in target.lower():
        return True
    # `evidence*` cannot be resolved, but its literal prefix already commits to
    # a protected name. A token starting with a metacharacter commits to
    # nothing, so it is left alone rather than denying every `rm *`.
    literal_prefix = re.split(r"[*?\[$`]", basename, maxsplit=1)[0]
    return bool(literal_prefix) and any(
        name.startswith(literal_prefix) for name in APPEND_ONLY_FILES
    )


def _opaque_append_only_target(command: str) -> str | None:
    for match in _OPAQUE_TOKEN.finditer(command):
        target = match.group(0)
        if _opaque_target_hits_append_only(target):
            return target
    return None


def _bash_mutates_append_only(command: str) -> str | None:
    if _SANCTIONED_APPEND.search(command):
        return None

    mutating = any(pattern.search(command) for pattern in _SHELL_MUTATION_PATTERNS)

    filename = next(
        (name for name in APPEND_ONLY_FILES if name in command),
        None,
    )
    if filename is not None:
        for match in _REDIRECTION_TARGET.finditer(command):
            if filename in match.group("target"):
                return filename
        if mutating:
            return filename

    # Glob and expansion bypasses: the literal check above never sees the
    # filename, so judge the unresolvable token instead.
    opaque = _opaque_append_only_target(command)
    if opaque is None:
        return None
    if mutating:
        return opaque
    for match in _REDIRECTION_TARGET.finditer(command):
        if _opaque_target_hits_append_only(match.group("target")):
            return opaque
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
