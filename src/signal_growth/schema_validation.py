"""Run the repository JSON Schemas as the runtime contract authority."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker


def _contract_directory() -> Path:
    configured_root = os.environ.get("SIGNAL_TO_GROWTH_ROOT")
    candidates = []
    if configured_root:
        candidates.append(Path(configured_root).expanduser().resolve() / "contracts")
    candidates.extend(
        (
            Path(__file__).resolve().parents[2] / "contracts",
            Path.cwd().resolve() / "contracts",
        )
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(
        "Signal to Growth contracts directory was not found; "
        "set SIGNAL_TO_GROWTH_ROOT to the repository root"
    )


@lru_cache(maxsize=None)
def _validator(schema_filename: str) -> Draft202012Validator:
    schema_path = _contract_directory() / schema_filename
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def validate_schema_record(
    schema_filename: str,
    record: Mapping[str, Any],
) -> list[str]:
    """Return stable, human-readable JSON Schema failures."""
    errors = sorted(
        _validator(schema_filename).iter_errors(dict(record)),
        key=lambda error: (list(error.absolute_path), error.message),
    )
    rendered: list[str] = []
    for error in errors:
        field_path = ".".join(str(part) for part in error.absolute_path)
        prefix = f"{field_path}: " if field_path else ""
        rendered.append(f"{prefix}{error.message}")
    return rendered
