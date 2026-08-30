#!/usr/bin/env python3
"""
Citability Scorer — Analyzes content blocks for AI citation readiness.
Scores passages based on how likely AI models are to cite them.

Based on research showing optimal AI-cited passages are:
- 134-167 words long
- Self-contained (extractable without context)
- Fact-rich with specific statistics
- Structured with clear answer patterns

LANGUAGE NOTE: the research bands above are measured in ENGLISH words. Korean is
written in 어절 (whitespace-delimited phrases) which carry more information per
token, so an untranslated threshold silently under-scores Korean pages. Every
count-based band is therefore scaled by KO_WORD_FACTOR, and every English-only
regex has a Korean counterpart. Without both, a Korean page is penalised on
length while being handed free marks on pronoun density (the English pronoun
regex matches nothing), which makes the total meaningless rather than merely low.
"""

import sys
import json
import re
from typing import Optional

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Required packages not installed. Run: pip install -r requirements.txt")
    sys.exit(1)


# Korean 어절 -> English word equivalence for the research bands.
# 0.6 is an approximation for technical prose (1 어절 ~ 1.6-1.7 English words).
# CALIBRATION PENDING: refine against a measured bilingual pair corpus. Exposed
# as a named constant so the tuning is one edit, not a hunt through the bands.
KO_WORD_FACTOR = 0.6

# A passage is treated as Korean when Hangul syllables make up more than this
# share of its letter characters. Mixed KO/EN technical prose sits well above it.
KO_HANGUL_RATIO = 0.2


def detect_language(text: str) -> str:
    """Return 'ko' or 'en' from Hangul share. Only these two are calibrated."""
    hangul = len(re.findall(r"[\uac00-\ud7a3]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    total = hangul + latin
    if total == 0:
        return "en"
    return "ko" if (hangul / total) > KO_HANGUL_RATIO else "en"


def _band(value: float, lang: str) -> float:
    """Scale an English-word threshold into the passage's unit of counting."""
    return value * KO_WORD_FACTOR if lang == "ko" else value


def score_passage(text: str, heading: Optional[str] = None) -> dict:
    """Score a single passage for AI citability (0-100)."""
    words = text.split()
    word_count = len(words)
    lang = detect_language(text)

    scores = {
        "answer_block_quality": 0,
        "self_containment": 0,
        "structural_readability": 0,
        "statistical_density": 0,
        "uniqueness_signals": 0,
    }

    # --- Dimension weights (caps sum to 100); re-weighted per GEO research.
    # See references/citability-research.md for the full method→study mapping.
    # Quotation/citation/statistics signals are raised relative to surface
    # structure, because those are the empirically strongest GEO levers:
    #   - Statistics +40% (headline) / +33% per-method (Princeton GEO, KDD 2024)
    #   - Cite Sources +115% on low-rank pages / +27% per-method (Princeton GEO)
    #   - Quotation +41% per-method (Princeton GEO)
    #   - Fluency +29% per-method (weakest cited lever) (Princeton GEO)
    # C-SEO Bench (arXiv 2506.11097, 2025) further warns that surface/structural
    # manipulation is largely ineffective vs. substantive signals, so
    # structural_readability is reduced. AutoGEO (ICLR 2026, arXiv 2510.11438)
    # corroborates substance-over-style with +50.99% over a fluency-only baseline.

    # === 1. Answer Block Quality (30%) ===
    # Cap held at 30: carries quotation (+41%) and citation ("according to /
    # research shows" = Cite Sources +27% per-method) signals, both top GEO
    # levers, plus answer-first placement which GEO research shows is critical.
    abq_score = 0

    # Check for definition patterns ("X is...", "X refers to...", "X means...")
    definition_patterns = [
        r"\b\w+\s+is\s+(?:a|an|the)\s",
        r"\b\w+\s+refers?\s+to\s",
        r"\b\w+\s+means?\s",
        r"\b\w+\s+(?:can be |are )?defined\s+as\s",
        r"\bin\s+(?:simple|other)\s+(?:terms|words)\s*,",
        # 한국어 정의문: "X란 ~이다/입니다", "~를 말한다/뜻한다/의미한다", "즉/다시 말해"
        r"[^\s]+(?:란|이란|라는 것은)\s",
        r"(?:을|를)\s*(?:말한다|뜻한다|의미한다|가리킨다)",
        r"(?:즉|다시 말해|쉽게 말해|한마디로)\s*,?",
        r"[^\s]+(?:은|는)\s+[^\s]+(?:이다|입니다)\b",
    ]
    for pattern in definition_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            abq_score += 15
            break

    # Check if answer appears early (first 60 words)
    first_60_words = " ".join(words[:60])
    if any(
        re.search(p, first_60_words, re.IGNORECASE)
        for p in [
            r"\b(?:is|are|was|were|means?|refers?)\b",
            r"\d+%",
            r"\$[\d,]+",
            r"\d+\s+(?:million|billion|thousand)",
            # 한국어 단정 종결·정의 표지와 금액 표기
            r"(?:입니다|이다|란|합니다|한다)\b",
            r"\d[\d,]*\s*(?:원|만원|억원)",
        ]
    ):
        abq_score += 15

    # Question-based heading bonus
    if heading and heading.endswith("?"):
        abq_score += 10

    # Clear, direct sentence structure
    sentences = re.split(r"[.!?]+", text)
    short_clear_sentences = sum(
        1 for s in sentences
        if _band(5, lang) <= len(s.split()) <= _band(25, lang)
    )
    if sentences:
        clarity_ratio = short_clear_sentences / len(sentences)
        abq_score += int(clarity_ratio * 10)

    # Has specific, quotable claim
    if re.search(
        r"(?:according to|research shows|studies? (?:show|indicate|suggest|found)|data (?:shows|indicates|suggests))"
        r"|(?:에 따르면|연구 결과|조사 결과|실측 결과|측정 결과|확인됐다|확인되었다)",
        text,
        re.IGNORECASE,
    ):
        abq_score += 10

    scores["answer_block_quality"] = min(abq_score, 30)

    # === 2. Self-Containment (22%) ===
    # Cap lowered 25 -> 22: length/pronoun heuristics are extraction-quality
    # proxies, not a Princeton-measured per-method lever, so they yield 3 pts
    # to statistical_density. Sub-scores re-scaled (7 + 8 + 7 = 22).
    sc_score = 0

    # Optimal length. English 134-167 words; Korean ~80-100 어절 (KO_WORD_FACTOR).
    if _band(134, lang) <= word_count <= _band(167, lang):
        sc_score += 7
    elif _band(100, lang) <= word_count <= _band(200, lang):
        sc_score += 5
    elif _band(80, lang) <= word_count <= _band(250, lang):
        sc_score += 3
    elif word_count < _band(30, lang) or word_count > _band(400, lang):
        sc_score += 0
    else:
        sc_score += 1

    # Low pronoun density (fewer pronouns = more self-contained)
    pronoun_count = len(
        re.findall(
            r"\b(?:it|they|them|their|this|that|these|those|he|she|his|her)\b"
            # 한국어 지시어. '그'·'이' 단독은 접두 오탐이 많아 제외하고 다음절만 센다.
            r"|(?:그것|이것|저것|그런|이런|저런|그러한|이러한|해당|위의|앞서|그들|이들)",
            text,
            re.IGNORECASE,
        )
    )
    if word_count > 0:
        pronoun_ratio = pronoun_count / word_count
        if pronoun_ratio < 0.02:
            sc_score += 8
        elif pronoun_ratio < 0.04:
            sc_score += 5
        elif pronoun_ratio < 0.06:
            sc_score += 3

    # Contains named entities (proper nouns, brands, specific terms)
    proper_nouns = len(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text))
    if proper_nouns >= 3:
        sc_score += 7
    elif proper_nouns >= 1:
        sc_score += 4

    scores["self_containment"] = min(sc_score, 22)

    # === 3. Structural Readability (15%) ===
    # Cap lowered 20 -> 15: this dimension is Fluency-adjacent, the weakest
    # cited lever (Fluency +29% per-method, Princeton GEO KDD2024), and C-SEO
    # Bench (arXiv 2506.11097) finds surface/structural manipulation largely
    # ineffective vs. substantive signals. The 5 freed pts go to
    # statistical_density. Sub-scores re-scaled (6 + 3 + 3 + 3 = 15).
    sr_score = 0

    # Sentence count and length distribution
    if sentences:
        avg_sentence_length = word_count / len(sentences)
        if _band(10, lang) <= avg_sentence_length <= _band(20, lang):
            sr_score += 6
        elif _band(8, lang) <= avg_sentence_length <= _band(25, lang):
            sr_score += 4
        else:
            sr_score += 2

    # Contains list-like structures
    if re.search(
        r"(?:first|second|third|finally|additionally|moreover|furthermore)"
        r"|(?:첫째|둘째|셋째|먼저|다음으로|마지막으로|또한|따라서|그러므로|한편)",
        text, re.IGNORECASE,
    ):
        sr_score += 3

    # Contains numbered items or bullet-like content
    if re.search(
        r"(?:\d+[\.\)]\s|\b(?:step|tip|point)\s+\d+)"
        r"|(?:\d+\s*(?:단계|번째|항목)|[①-⑳])",
        text, re.IGNORECASE,
    ):
        sr_score += 3

    # Paragraph breaks (indicates structure)
    if "\n" in text:
        sr_score += 3

    scores["structural_readability"] = min(sr_score, 15)

    # === 4. Statistical Density (25%) ===
    # Cap raised 15 -> 25 (+10), the single largest re-weight. This dimension
    # carries the two empirically strongest GEO levers measured by Princeton
    # GEO (KDD 2024, ~10k queries): adding Statistics lifts citation visibility
    # +40% (headline) / +33% per-method, and citing/naming Sources lifts it
    # +115% on low-rank pages / +27% per-method. The named-source sub-signal
    # below is the "Cite Sources" lever; the percent/dollar/number sub-signals
    # are the "Statistics" lever. Sub-scores re-scaled so the new cap is
    # reachable (10 + 7 + 4 + 2 + 6 = 29, clamped to 25).
    sd_score = 0

    # Percentages (Statistics lever, Princeton GEO +33% per-method)
    pct_count = len(re.findall(r"\d+(?:\.\d+)?%", text))
    sd_score += min(pct_count * 4, 10)

    # Dollar amounts (Statistics lever)
    dollar_count = len(re.findall(
        r"\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|M|B|K))?"
        r"|\d[\d,]*\s*(?:원|만원|억원|천만원)",
        text))
    sd_score += min(dollar_count * 4, 7)

    # Other numbers with context (Statistics lever)
    number_count = len(re.findall(
        r"\b\d+(?:,\d{3})*(?:\.\d+)?\s+(?:users|customers|pages|sites|companies|businesses|people|percent|times|x\b)"
        r"|\d+(?:,\d{3})*(?:\.\d+)?\s*(?:명|건|개|배|회|줄|시간|일|주|개월|년|페이지|문항|커밋)",
        text, re.IGNORECASE))
    sd_score += min(number_count * 2, 4)

    # Year references (indicates timeliness)
    year_count = len(re.findall(r"\b20(?:2[3-6]|1\d)\b", text))
    if year_count > 0:
        sd_score += 2

    # Named sources (Cite Sources lever, Princeton GEO +115% low-rank / +27%)
    source_patterns = [
        r"(?:according to|per|from|by)\s+[A-Z]",
        r"(?:Gartner|Forrester|McKinsey|Harvard|Stanford|MIT|Google|Microsoft|OpenAI|Anthropic)",
        r"\([A-Z][a-z]+(?:\s+\d{4})?\)",
        r"(?:에 따르면|출처[:：]|참조[:：]|인용[:：])",
    ]
    for pattern in source_patterns:
        if re.search(pattern, text):
            sd_score += 2

    scores["statistical_density"] = min(sd_score, 25)

    # === 5. Uniqueness Signals (8%) ===
    # Cap lowered 10 -> 8: supports originality/E-E-A-T (consistent with
    # AutoGEO's substance-over-style finding) but is not a Princeton-measured
    # per-method lever, so it yields 2 pts to statistical_density. Sub-scores
    # re-scaled (4 + 2 + 2 = 8).
    us_score = 0

    # Original data indicators
    if re.search(
        r"(?:our (?:research|study|data|analysis|survey|findings)|we (?:found|discovered|analyzed|surveyed|measured))"
        r"|(?:자체\s*(?:조사|분석|측정|실측)|직접\s*(?:측정|확인|실측|조사)|실측 결과|우리가\s*(?:측정|확인|분석))",
        text,
        re.IGNORECASE,
    ):
        us_score += 4

    # Case study or example indicators
    if re.search(
        r"(?:case study|for example|for instance|in practice|real-world|hands-on)"
        r"|(?:예를 들어|예컨대|사례|실제로|실무에서|현장에서)",
        text,
        re.IGNORECASE,
    ):
        us_score += 2

    # Specific tool/product mentions (shows practical experience)
    if re.search(
        r"(?:using|with|via|through)\s+[A-Z][a-z]+"
        r"|[A-Z][A-Za-z]+(?:을|를|으로|로|에서)\s",
        text,
    ):
        us_score += 2

    scores["uniqueness_signals"] = min(us_score, 8)

    # === Calculate total ===
    total = sum(scores.values())

    # Determine grade
    if total >= 80:
        grade = "A"
        label = "Highly Citable"
    elif total >= 65:
        grade = "B"
        label = "Good Citability"
    elif total >= 50:
        grade = "C"
        label = "Moderate Citability"
    elif total >= 35:
        grade = "D"
        label = "Low Citability"
    else:
        grade = "F"
        label = "Poor Citability"

    return {
        "heading": heading,
        "language": lang,
        "word_count": word_count,
        "word_unit": "eojeol" if lang == "ko" else "word",
        "total_score": total,
        "grade": grade,
        "label": label,
        "breakdown": scores,
        "preview": " ".join(words[:30]) + ("..." if word_count > 30 else ""),
    }


def analyze_page_citability(url: str) -> dict:
    """Analyze all content blocks on a page for citability."""
    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
            timeout=30,
        )
        response.raise_for_status()
    except Exception as e:
        return {"error": f"Failed to fetch page: {str(e)}"}

    soup = BeautifulSoup(response.text, "lxml")

    # Remove non-content elements
    for element in soup.find_all(
        ["script", "style", "nav", "footer", "header", "aside", "form"]
    ):
        element.decompose()

    # Extract content blocks
    blocks = []
    current_heading = "Introduction"
    current_paragraphs = []

    page_lang = detect_language(soup.get_text(" ", strip=True)[:4000])
    min_block = int(_band(20, page_lang))
    min_para = int(_band(5, page_lang))

    for element in soup.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol", "table"]):
        if element.name.startswith("h"):
            # Save previous section
            if current_paragraphs:
                combined = " ".join(current_paragraphs)
                if len(combined.split()) >= min_block:
                    blocks.append(
                        {"heading": current_heading, "content": combined}
                    )
            current_heading = element.get_text(strip=True)
            current_paragraphs = []
        else:
            text = element.get_text(strip=True)
            if text and len(text.split()) >= min_para:
                current_paragraphs.append(text)

    # Last block
    if current_paragraphs:
        combined = " ".join(current_paragraphs)
        if len(combined.split()) >= min_block:
            blocks.append({"heading": current_heading, "content": combined})

    # Score each block
    scored_blocks = []
    for block in blocks:
        score = score_passage(block["content"], block["heading"])
        scored_blocks.append(score)

    # Calculate page-level metrics
    if scored_blocks:
        avg_score = sum(b["total_score"] for b in scored_blocks) / len(scored_blocks)
        top_blocks = sorted(scored_blocks, key=lambda x: x["total_score"], reverse=True)[:5]
        bottom_blocks = sorted(scored_blocks, key=lambda x: x["total_score"])[:5]

        # Optimal passage count (134-167 words)
        optimal_count = sum(
            1 for b in scored_blocks
            if _band(134, b.get("language", "en")) <= b["word_count"]
            <= _band(167, b.get("language", "en"))
        )
    else:
        avg_score = 0
        top_blocks = []
        bottom_blocks = []
        optimal_count = 0

    # Grade distribution
    grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for block in scored_blocks:
        grade_dist[block["grade"]] += 1

    return {
        "url": url,
        "total_blocks_analyzed": len(scored_blocks),
        "average_citability_score": round(avg_score, 1),
        "optimal_length_passages": optimal_count,
        "grade_distribution": grade_dist,
        "top_5_citable": top_blocks,
        "bottom_5_citable": bottom_blocks,
        "all_blocks": scored_blocks,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python citability_scorer.py <url>")
        print("Returns JSON with citability analysis for all content blocks.")
        sys.exit(1)

    url = sys.argv[1]
    result = analyze_page_citability(url)
    print(json.dumps(result, indent=2, default=str))
