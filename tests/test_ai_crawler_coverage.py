"""Anthropic's search and user-request crawlers must be audited.

WHY: Anthropic documents three crawlers (ClaudeBot, Claude-User,
Claude-SearchBot). A robots.txt audit that only checks ClaudeBot reports a
site as open to Claude search even when Claude-SearchBot is blocked, so the
GEO audit silently misses the bot that decides whether Claude can cite the page.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "optimize-search-visibility" / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        raise unittest.SkipTest(f"{name} dependencies missing")
    return mod


class AnthropicCrawlerCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fetch_page = _load("fetch_page")

    def test_blocked_claude_search_bot_is_reported(self) -> None:
        robots = "User-agent: Claude-SearchBot\nDisallow: /\n\nUser-agent: Claude-User\nDisallow: /\n"
        response = mock.Mock(status_code=200, text=robots)
        with mock.patch.object(self.fetch_page.requests, "get", return_value=response):
            result = self.fetch_page.fetch_robots_txt("https://example.com/page")
        status = result["ai_crawler_status"]
        self.assertIn("Claude-SearchBot", status)
        self.assertIn("Claude-User", status)
        self.assertNotEqual(status["Claude-SearchBot"], status.get("GPTBot"))


if __name__ == "__main__":
    unittest.main()
