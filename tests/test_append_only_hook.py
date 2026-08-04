from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "guard_append_only.py"


def run_hook(payload: dict[str, object]) -> dict[str, object] | None:
    completed = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(completed.stdout) if completed.stdout else None


class AppendOnlyHookTests(unittest.TestCase):
    def test_denies_shell_redirection_to_append_only_artifact(self) -> None:
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "printf x > artifacts/evidence.jsonl",
                },
            }
        )

        self.assertIsNotNone(result)
        decision = result["hookSpecificOutput"]
        self.assertEqual("deny", decision["permissionDecision"])

    def test_denies_python_write_to_append_only_artifact_from_bash(self) -> None:
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": (
                        "python3 -c \"from pathlib import Path; "
                        "Path('artifacts/decisions.jsonl').write_text('x')\""
                    ),
                },
            }
        )

        self.assertIsNotNone(result)
        decision = result["hookSpecificOutput"]
        self.assertEqual("deny", decision["permissionDecision"])

    def test_allows_sanctioned_append_record_command(self) -> None:
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": (
                        "python3 scripts/stg.py append-record artifacts/evidence.jsonl "
                        "'{\"evidence_id\":\"EV-20260728-001\"}'"
                    ),
                },
            }
        )

        self.assertIsNone(result)

    def test_allows_read_only_command_with_stderr_redirection(self) -> None:
        result = run_hook(
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "cat artifacts/evidence.jsonl 2>/dev/null",
                },
            }
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
