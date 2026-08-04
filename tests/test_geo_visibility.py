"""The optional citability scorer must never fake a score or a claim state.

The whole risk of an optional dependency is that its absence goes unnoticed and
a downstream reader treats a missing number as a low number. These tests pin the
two branches: installed produces a `reported` heuristic with its weights, and
missing produces `unknown` with no number at all.
"""

from __future__ import annotations

import builtins
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from signal_growth.geo_visibility import (  # noqa: E402
    GEO_PACKAGE,
    score_citability,
)

SAMPLE_HTML = (
    "<html><body><h1>What is evidence lineage?</h1>"
    "<blockquote>We lost the quote before the decision. — PM</blockquote>"
    "<p>42% of teams reported this. Updated 2026-08-04. "
    '<a href="https://example.com/source">source</a></p>'
    "</body></html>"
)


def _scorer_installed() -> bool:
    try:
        import geo_optimizer.core.citability  # noqa: F401
    except ImportError:
        return False
    return True


class ScoreCitabilityTest(unittest.TestCase):
    @unittest.skipUnless(_scorer_installed(), f"{GEO_PACKAGE} is not installed")
    def test_installed_scorer_reports_a_labelled_heuristic(self) -> None:
        result = score_citability(SAMPLE_HTML, "https://example.com/page")

        # `reported` and not `observed`: we observed markup, not a citation.
        self.assertEqual(result["claim_state"], "reported")
        self.assertTrue(result["heuristic"])
        self.assertIsInstance(result["total_score"], int)
        self.assertEqual(result["score_scale"], 100)
        self.assertIsNotNone(result["scorer_version"])
        # Weights have to travel with the number, or the skill's "expose
        # weights" rule is satisfied only on paper.
        self.assertTrue(result["methods"])
        for method in result["methods"]:
            self.assertIn("max_score", method)

    @unittest.skipUnless(_scorer_installed(), f"{GEO_PACKAGE} is not installed")
    def test_same_markup_scores_the_same_twice(self) -> None:
        first = score_citability(SAMPLE_HTML, "https://example.com/page")
        second = score_citability(SAMPLE_HTML, "https://example.com/page")

        self.assertEqual(first["total_score"], second["total_score"])

    def test_missing_scorer_yields_unknown_and_no_number(self) -> None:
        real_import = builtins.__import__

        def blocked_import(name, *args, **kwargs):
            if name.startswith(("geo_optimizer", "bs4")):
                raise ImportError(f"blocked for test: {name}")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = blocked_import
        try:
            result = score_citability(SAMPLE_HTML, "https://example.com/page")
        finally:
            builtins.__import__ = real_import

        self.assertEqual(result["claim_state"], "unknown")
        self.assertIsNone(result["total_score"])
        self.assertIsNone(result["grade"])
        self.assertEqual(result["methods"], [])
        self.assertIn(GEO_PACKAGE, result["note"])


if __name__ == "__main__":
    unittest.main()
