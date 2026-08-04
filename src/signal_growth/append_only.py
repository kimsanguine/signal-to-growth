"""Append one JSON record to a Signal to Growth JSONL artifact.

This is the only sanctioned way to add a line to an append-only artifact.
It refuses non-artifact files, rejects records that would not serialize to a
single line, and holds an exclusive file lock while writing so that two
concurrent agents cannot interleave partial lines into the same file.

Each appended record also carries `prev_hash` and `record_hash`, so a later
reader can recompute the chain and detect an edited or removed line instead of
trusting that history was never rewritten.
"""

from __future__ import annotations

import fcntl
import hashlib
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


HASH_PREFIX = "sha256:"
RECORD_HASH_FIELD = "record_hash"
PREV_HASH_FIELD = "prev_hash"


class AppendOnlyError(ValueError):
    """Raised when a record cannot be appended to an artifact."""


def compute_record_hash(record: dict[str, Any], prev_hash: str | None) -> str:
    """Return the chain hash of `record` as linked to `prev_hash`.

    The record's own `record_hash` is excluded so the value can be recomputed,
    while `prev_hash` is always included so relinking a record to a different
    predecessor also invalidates its hash.
    """
    payload = {key: value for key, value in record.items() if key != RECORD_HASH_FIELD}
    payload[PREV_HASH_FIELD] = prev_hash
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return HASH_PREFIX + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _tail_record_hash(lines: list[str], path: Path) -> str | None:
    """Return the `record_hash` of the last record, or None for a fresh chain."""
    if not lines:
        return None
    try:
        last = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise AppendOnlyError(
            f"{path.name} ends with a line that is not valid JSON, so the "
            f"append chain cannot be extended: {exc.msg}"
        ) from exc
    if not isinstance(last, dict):
        raise AppendOnlyError(
            f"{path.name} ends with a record that is not a JSON object."
        )
    tail_hash = last.get(RECORD_HASH_FIELD)
    if tail_hash is not None and not isinstance(tail_hash, str):
        raise AppendOnlyError(
            f"{path.name} ends with a non-string {RECORD_HASH_FIELD}."
        )
    return tail_hash


def append_record(path: Path, record: dict[str, Any]) -> int:
    """Append `record` as one chained JSON line to `path`. Return the line count.

    Any caller-supplied `prev_hash` or `record_hash` is replaced: the writer,
    not the caller, decides where a record sits in the chain.
    """
    if path.name not in APPEND_ONLY_FILES:
        raise AppendOnlyError(
            f"{path.name} is not a recognized append-only artifact "
            f"({', '.join(sorted(APPEND_ONLY_FILES))})."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.seek(0)
            existing = handle.read()
            lines = [line for line in existing.splitlines() if line.strip()]

            chained = {
                key: value
                for key, value in record.items()
                if key not in (RECORD_HASH_FIELD, PREV_HASH_FIELD)
            }
            chained[PREV_HASH_FIELD] = _tail_record_hash(lines, path)
            chained[RECORD_HASH_FIELD] = compute_record_hash(
                chained,
                chained[PREV_HASH_FIELD],
            )

            handle.seek(0, 2)
            # A file left without a trailing newline would otherwise merge the
            # previous record into this one and break the chain.
            prefix = "" if not existing or existing.endswith("\n") else "\n"
            handle.write(prefix + json.dumps(chained, ensure_ascii=False) + "\n")
            handle.flush()
            return len(lines) + 1
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
