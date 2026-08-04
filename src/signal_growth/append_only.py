"""Append one JSON record to a Signal to Growth JSONL artifact.

This is the only sanctioned way to add a line to an append-only artifact.
It refuses non-artifact files, rejects records that would not serialize to a
single line, and holds an exclusive file lock while writing so that two
concurrent agents cannot interleave partial lines into the same file.
"""

from __future__ import annotations

import fcntl
import json
from pathlib import Path
from typing import Any


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


class AppendOnlyError(ValueError):
    """Raised when a record cannot be appended to an artifact."""


def append_record(path: Path, record: dict[str, Any]) -> int:
    """Append `record` as one JSON line to `path`. Return the new line count."""
    if path.name not in APPEND_ONLY_FILES:
        raise AppendOnlyError(
            f"{path.name} is not a recognized append-only artifact "
            f"({', '.join(sorted(APPEND_ONLY_FILES))})."
        )

    line = json.dumps(record, ensure_ascii=False)

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.write(line + "\n")
            handle.flush()
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    with open(path, encoding="utf-8") as handle:
        return sum(1 for _ in handle)
