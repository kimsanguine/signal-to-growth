"""Optional third-party citability scoring for `audit-answer-visibility`.

`audit-answer-visibility` refuses to invent a probability of being cited. It
still allows a *diagnostic* score when the weights are exposed and the number
is labelled a heuristic (`skills/audit-answer-visibility/SKILL.md`, "If using a
diagnostic score, expose weights and label the score as a heuristic").

This module is the only place that decision is implemented. It wraps the
optional `geo-optimizer-skill` package (`pip install -e ".[geo]"`) and returns a
record the skill can copy into `technical-findings.md` without editing the
numbers. When the package is absent the audit does not degrade into a guess: the
same function returns `claim_state="unknown"`, which is already one of the five
states the skill's Verification section requires.

Two deliberate non-features:

- No network. The caller passes markup it already fetched under its own access
  and authorization rules, so this module cannot turn an audit into an
  unapproved live request.
- No score of our own. We never recompute, rescale, or blend the third-party
  number, which is what keeps README's "타 저장소의 고유 scoring 공식을 포함하지
  않습니다" true while still using the package.
"""

from __future__ import annotations

from typing import Any

GEO_PACKAGE = "geo-optimizer-skill"

# Every number this module reports is produced by the third-party scorer, so the
# state can never be `observed` (we observed markup, not a citation) and never
# `inferred` (we did not reason about it). `reported` is the honest state.
SCORED_CLAIM_STATE = "reported"
UNKNOWN_CLAIM_STATE = "unknown"

_MISSING_NOTE = (
    f"{GEO_PACKAGE} is not installed, so no diagnostic citability score was "
    'computed. Install it with `pip install -e ".[geo]"` to score, or leave this '
    "finding as unknown."
)
_SCORED_NOTE = (
    "Heuristic diagnostic score from a third-party scorer, not a calibrated "
    "probability of being cited. Weights are listed in `methods`. A person "
    "decides whether any gap is worth investment."
)


def _scorer_version() -> str | None:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version(GEO_PACKAGE)
    except PackageNotFoundError:
        return None


def score_citability(html: str, base_url: str) -> dict[str, Any]:
    """Score already-fetched markup, or report `unknown` when unscoreable.

    `html` is markup the caller already has; `base_url` is the surface it came
    from. The return value always carries `claim_state`, so a caller that
    ignores the difference between a score and no score still writes a labelled
    finding rather than a bare number.
    """
    try:
        from bs4 import BeautifulSoup
        from geo_optimizer.core.citability import audit_citability
    except ImportError:
        return {
            "claim_state": UNKNOWN_CLAIM_STATE,
            "scorer": GEO_PACKAGE,
            "scorer_version": None,
            "heuristic": True,
            "total_score": None,
            "score_scale": None,
            "grade": None,
            "methods": [],
            "top_improvements": [],
            "note": _MISSING_NOTE,
        }

    result = audit_citability(BeautifulSoup(html, "html.parser"), base_url)
    return {
        "claim_state": SCORED_CLAIM_STATE,
        "scorer": GEO_PACKAGE,
        "scorer_version": _scorer_version(),
        "heuristic": True,
        "total_score": result.total_score,
        # The scorer normalizes to 0-100 rather than to the sum of its own
        # per-method maxima, so stating the scale keeps a reader from dividing
        # `total_score` by that sum and reporting a different number.
        "score_scale": 100,
        "grade": result.grade,
        "methods": [
            {
                "name": method.name,
                "label": method.label,
                "detected": method.detected,
                "score": method.score,
                "max_score": method.max_score,
            }
            for method in result.methods
        ],
        "top_improvements": list(result.top_improvements),
        "note": _SCORED_NOTE,
    }
