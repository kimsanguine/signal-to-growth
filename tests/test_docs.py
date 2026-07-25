from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class DocumentationTests(unittest.TestCase):
    def test_relative_markdown_links_exist(self) -> None:
        missing: list[str] = []
        for markdown in ROOT.rglob("*.md"):
            if ".venv" in markdown.parts:
                continue
            text = markdown.read_text(encoding="utf-8")
            for target in MARKDOWN_LINK.findall(text):
                clean_target = target.split("#", 1)[0]
                if (
                    not clean_target
                    or "://" in clean_target
                    or clean_target.startswith("mailto:")
                ):
                    continue
                resolved = (markdown.parent / clean_target).resolve()
                if not resolved.exists():
                    missing.append(f"{markdown.relative_to(ROOT)} -> {target}")
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
