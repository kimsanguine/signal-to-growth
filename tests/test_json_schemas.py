from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.contracts import ARTIFACT_FILES, load_records


class JsonSchemaTests(unittest.TestCase):
    def test_schemas_are_valid_and_accept_public_fixtures(self) -> None:
        artifact_directory = ROOT / "fixtures" / "public-dummy" / "artifacts"
        for filename, kind in ARTIFACT_FILES.items():
            schema_path = ROOT / "contracts" / f"{kind.replace('_', '-')}.schema.json"
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            validator = Draft202012Validator(schema)
            records = load_records(artifact_directory / filename)
            for record in records:
                validator.validate(record)


if __name__ == "__main__":
    unittest.main()
