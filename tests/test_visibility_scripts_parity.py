"""Fixes that once lived only in the plugin cache, pinned in the source copy.

WHY these tests exist
---------------------
2026-08-26 fixes (sitemap via robots.txt, Korean proper nouns and attribution,
web-search citation probe) were made in the installed cache copy and never
reached this source tree; the 2026-08-30 Korean calibration was made here and
never reached the cache. The two diverged and the same page scored 44.1 vs 50.6.
Each test names the user-visible failure that comes back if its fix is lost.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

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


class CitabilityKoreanFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scorer = _load("citability_scorer")

    def test_brands_with_glued_korean_particles_are_counted_as_named_entities(self) -> None:
        # Lost fix: "FastCampus에서 GitHub를 PayPal로" matched zero proper nouns,
        # so every Korean page naming real brands lost the self-containment points.
        with_brands = self.scorer.score_passage("FastCampus에서 GitHub를 쓰고 PayPal로 결제한다.")
        without = self.scorer.score_passage("학원에서 저장소를 쓰고 은행으로 결제한다.")
        self.assertGreater(
            with_brands["breakdown"]["self_containment"], without["breakdown"]["self_containment"]
        )

    def test_korean_attribution_verb_counts_as_a_named_source(self) -> None:
        # Lost fix: "SVPG가 지적했다" earned nothing on Cite Sources, so a page
        # that names its source scored the same as one that does not.
        cited = self.scorer.score_passage("SVPG가 지적했다 PM의 역할이 바뀐다.")
        uncited = self.scorer.score_passage("누군가 생각한다 PM의 역할이 바뀐다.")
        self.assertGreater(
            cited["breakdown"]["statistical_density"], uncited["breakdown"]["statistical_density"]
        )

    def test_korean_attribution_is_not_double_counted(self) -> None:
        # Guard on the merge itself: "~에 따르면" matched two source patterns
        # and silently added +4 instead of +2.
        one = self.scorer.score_passage("연구에 따르면 PM의 역할이 바뀐다.")
        none = self.scorer.score_passage("연구가 보여주듯 PM의 역할이 바뀐다.")
        self.assertEqual(
            one["breakdown"]["statistical_density"] - none["breakdown"]["statistical_density"], 2
        )


class SeoAuditSitemap(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.audit = _load("seo_audit")

    def _fake_fetch(self, pages: dict):
        return lambda url, timeout=30: (pages.get(url), None, None)

    def test_sitemap_declared_in_robots_is_found(self) -> None:
        # Lost fix: blog.habix.ai serves /sitemap-index.xml (declared in robots.txt),
        # /sitemap.xml is 404; the audit reported "no sitemap" for a site that has one.
        self.audit.fetch_url = self._fake_fetch(
            {
                "https://blog.test/robots.txt": "User-agent: *\nSitemap: https://blog.test/sitemap-index.xml\n",
                "https://blog.test/sitemap-index.xml": "<?xml version='1.0'?><sitemapindex></sitemapindex>",
            }
        )
        self.assertTrue(self.audit.check_sitemap("https://blog.test/post"))

    def test_missing_sitemap_is_still_reported_missing(self) -> None:
        # Guard against over-fixing: no robots line and no /sitemap.xml must stay False.
        self.audit.fetch_url = self._fake_fetch({"https://none.test/robots.txt": "User-agent: *\n"})
        self.assertFalse(self.audit.check_sitemap("https://none.test/"))


class LiveCitationUsesWebSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.live = _load("live_citation")

    def test_openai_probe_forces_web_search_and_reads_output_text(self) -> None:
        # Lost fix: the chat/completions probe answers from pretraining only, so a
        # "0/10 cited" result could never move no matter what the live page said.
        seen = {}

        def fake_post(url, payload, key):
            seen["url"], seen["payload"] = url, payload
            return {
                "output": [
                    {"type": "web_search_call"},
                    {"type": "message", "content": [{"type": "output_text", "text": "답변 본문"}]},
                ]
            }, None

        self.live._post_json = fake_post
        text, err = self.live.query_openai_once("질문", "k", "m")
        self.assertIsNone(err)
        self.assertEqual(text, "답변 본문")
        self.assertTrue(seen["url"].endswith("/v1/responses"))
        self.assertEqual(seen["payload"]["tools"], [{"type": "web_search"}])
        self.assertEqual(seen["payload"]["tool_choice"], "required")


if __name__ == "__main__":
    unittest.main()
