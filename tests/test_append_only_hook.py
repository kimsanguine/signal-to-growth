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


class OpaqueTargetBypassTests(unittest.TestCase):
    """The literal-filename matcher missed anything the shell expands later.

    Both commands below were confirmed to pass the guard before this matcher
    existed, even though each destroys every append-only artifact it finds.
    """

    def deny_decision(self, command: str) -> dict[str, object] | None:
        result = run_hook({"tool_name": "Bash", "tool_input": {"command": command}})
        return None if result is None else result["hookSpecificOutput"]

    def assertDenied(self, command: str) -> None:
        decision = self.deny_decision(command)
        self.assertIsNotNone(decision, f"expected deny for: {command}")
        self.assertEqual("deny", decision["permissionDecision"])

    def assertAllowed(self, command: str) -> None:
        self.assertIsNone(
            self.deny_decision(command),
            f"expected allow for: {command}",
        )

    def test_denies_glob_that_expands_to_append_only_artifacts(self) -> None:
        self.assertDenied("rm artifacts/*.jsonl")

    def test_denies_variable_expansion_that_rebuilds_a_protected_name(self) -> None:
        self.assertDenied("F=evidence.json; rm artifacts/${F}l")

    def test_denies_glob_whose_literal_prefix_names_a_protected_artifact(self) -> None:
        self.assertDenied("rm evidence*")

    def test_denies_truncation_through_a_glob(self) -> None:
        self.assertDenied("truncate -s 0 artifacts/*.jsonl")

    def test_denies_redirection_into_an_expanded_artifact_path(self) -> None:
        self.assertDenied("printf x > artifacts/${F}l")

    def test_allows_unrelated_globs_so_the_guard_stays_usable(self) -> None:
        # A guard that denies ordinary cleanup gets disabled, which protects
        # nothing. These must keep working.
        for command in (
            "rm build/*.o",
            "rm -rf node_modules/*",
            "rm -rf ${BUILD_DIR}",
            "cp $SRC $DST",
            "ls artifacts/",
        ):
            with self.subTest(command=command):
                self.assertAllowed(command)

    def test_allows_sanctioned_append_record_with_a_variable_path(self) -> None:
        self.assertAllowed(
            "python3 scripts/stg.py append-record artifacts/${NAME}.jsonl "
            "'{\"evidence_id\":\"EV-20260728-001\"}'"
        )


if __name__ == "__main__":
    unittest.main()
