"""Citability scorer language calibration.

WHY these tests exist
---------------------
The scorer's bands come from English-language GEO research (optimal cited
passage = 134-167 words). Korean is written in 어절, which carry more
information per whitespace token, so applying the English numbers unchanged
does two things at once:

  1. penalises Korean length even when the passage is the right size, and
  2. hands Korean a free full score on pronoun density, because the pronoun
     regex only lists English pronouns and matches nothing.

Those two errors do not cancel. Together they make the total meaningless
rather than merely low, which is worse: a meaningless number still looks
like a measurement and gets acted on.

These tests pin the intent, not the implementation:
  - English scoring must not move (regression guard for the existing corpus).
  - A Korean passage must be scored on Korean-scaled bands.
  - Korean discourse markers must actually be detected, so Korean text can
    lose points it deserves to lose.
"""

import os
import sys
import importlib.util

import pytest

_SCORER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills", "optimize-search-visibility", "scripts", "citability_scorer.py",
)

_spec = importlib.util.spec_from_file_location("citability_scorer", _SCORER)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["citability_scorer"] = _mod
try:
    _spec.loader.exec_module(_mod)
except SystemExit:  # scorer exits when requests/bs4 are absent
    pytest.skip("citability_scorer dependencies missing", allow_module_level=True)

detect_language = _mod.detect_language
score_passage = _mod.score_passage
KO_WORD_FACTOR = _mod.KO_WORD_FACTOR


KO_PASSAGE = (
    "Loop Engineering이란 팀의 반복 업무를 AI가 실행하고 사람이 검증하며 그 결과가 "
    "다음 실행 기준으로 축적되게 설계하는 방법론입니다. 즉 도구 사용법을 익히는 것이 "
    "아니라 운영 루프를 만드는 일입니다. 첫째, 팀이 목표와 성공 기준을 합의합니다. "
    "둘째, 실행에 필요한 지식과 권한을 연결합니다. 셋째, 사람이 근거와 예외를 검토합니다. "
    "실측 결과 22개 에이전트를 운영하며 검증 단계에서 걸러진 오류가 전체의 31%였습니다. "
    "예를 들어 문서 분류 루프에서는 3건의 오분류가 승인 전에 잡혔습니다."
)

EN_PASSAGE = (
    "Loop Engineering is a method for turning a team's repeated work into a "
    "verifiable loop. AI executes, a human verifies, and the verified result "
    "becomes the standard for the next run. First, the team agrees on the goal "
    "and the success criteria. Second, the knowledge and permissions needed for "
    "execution are connected. Third, a person reviews the evidence and the "
    "exceptions. According to our measurements across 22 agents, 31% of errors "
    "were caught at the verification step. For example, in a document "
    "classification loop, 3 misclassifications were caught before approval."
)


class TestLanguageDetection:
    def test_korean_prose_is_korean(self):
        assert detect_language(KO_PASSAGE) == "ko"

    def test_english_prose_is_english(self):
        assert detect_language(EN_PASSAGE) == "en"

    def test_korean_with_heavy_english_tech_terms_still_korean(self):
        # Korean technical writing is full of Latin-script product names.
        # Those must not flip the passage to the English bands.
        text = "Claude Code와 LangGraph, Supabase를 연결해 에이전트 루프를 구성합니다."
        assert detect_language(text) == "ko"

    def test_empty_text_defaults_to_english(self):
        # No signal must not raise; English is the calibrated default.
        assert detect_language("") == "en"
        assert detect_language("123 456 !!!") == "en"


class TestEnglishUnchanged:
    """Regression guard: the English corpus must score as it did before."""

    def test_english_optimal_band_is_still_134_to_167(self):
        band = _mod._band
        assert band(134, "en") == 134
        assert band(167, "en") == 167

    def test_english_passage_reports_word_unit(self):
        r = score_passage(EN_PASSAGE, heading="What is Loop Engineering?")
        assert r["language"] == "en"
        assert r["word_unit"] == "word"

    def test_english_scoring_contract_keys_preserved(self):
        # distribution.py and output-contract.md depend on these.
        r = score_passage(EN_PASSAGE)
        for key in ("heading", "word_count", "total_score", "grade", "label",
                    "breakdown", "preview"):
            assert key in r


class TestKoreanBands:
    def test_korean_bands_are_scaled_down(self):
        band = _mod._band
        assert band(134, "ko") == pytest.approx(134 * KO_WORD_FACTOR)
        assert band(134, "ko") < 134

    def test_korean_passage_reports_eojeol_unit(self):
        r = score_passage(KO_PASSAGE, heading="Loop Engineering이란?")
        assert r["language"] == "ko"
        assert r["word_unit"] == "eojeol"

    def test_korean_passage_is_not_length_penalised_like_english(self):
        """The core defect: same content, same size, wildly different score.

        The Korean passage is a faithful equivalent of the English one. Under
        the unscaled English bands the Korean version lands in the
        'word_count < 30' zero-point zone purely because 어절 count is lower.
        With scaling, its self_containment length credit must be non-zero.
        """
        ko = score_passage(KO_PASSAGE)
        assert ko["breakdown"]["self_containment"] > 0

    def test_korean_and_english_equivalents_score_comparably(self):
        ko = score_passage(KO_PASSAGE)
        en = score_passage(EN_PASSAGE)
        # Not identical — the two languages trip different sub-signals — but a
        # faithful translation must not fall a whole grade band apart.
        assert abs(ko["total_score"] - en["total_score"]) < 25


class TestKoreanSignalsAreActuallyDetected:
    """Korean must be able to LOSE points, not just gain them."""

    def test_korean_demonstratives_count_as_pronouns(self):
        # Before the fix the English-only regex matched nothing here, so this
        # passage collected the full pronoun sub-score despite being vague.
        vague = " ".join([
            "그것은 이런 방식으로 동작합니다.",
            "이러한 그것들은 해당 위의 그런 저런 이것 저것을 그러한 이들 그들과 함께 씁니다.",
        ] * 3)
        opaque = score_passage(vague)
        specific = score_passage(KO_PASSAGE)
        assert opaque["breakdown"]["self_containment"] < specific["breakdown"]["self_containment"]

    def test_korean_definition_pattern_scores_answer_block(self):
        defined = score_passage("Loop Engineering이란 팀의 반복 업무를 검증 가능한 루프로 바꾸는 방법론입니다.")
        undefined = score_passage("이 페이지에서는 여러 가지를 다룹니다. 아래를 참고하세요.")
        assert defined["breakdown"]["answer_block_quality"] > undefined["breakdown"]["answer_block_quality"]

    def test_korean_units_count_as_statistics(self):
        with_stats = score_passage("실측 결과 22개 에이전트에서 오류 3건을 확인했고 비용은 12만원 절감됐습니다.")
        without = score_passage("에이전트를 여러 개 운영하며 오류를 줄였고 비용도 아꼈습니다.")
        assert with_stats["breakdown"]["statistical_density"] > without["breakdown"]["statistical_density"]

    def test_korean_source_attribution_counts(self):
        cited = score_passage("Princeton GEO 연구에 따르면 통계 추가는 인용률을 40% 높입니다.")
        assert cited["breakdown"]["statistical_density"] > 0
