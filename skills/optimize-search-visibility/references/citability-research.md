# Citability Scoring — Research Basis

This document records the academic evidence behind the dimension weights in
`scripts/citability_scorer.py`. It exists so that the weighting is auditable:
every weight change can be traced to a specific study and a specific number.

The scorer rates each content passage 0–100 across five dimensions whose caps
sum to 100. The weights below were re-balanced (v2) to favor the signals that
peer-reviewed GEO research shows actually move AI-citation visibility —
statistics and cited sources — over surface-structural signals.

---

## 1. Source studies

### Princeton GEO — Aggarwal et al., *KDD 2024*
- "Generative Engine Optimization." ~10k-query benchmark (GEO-bench) across
  multiple answer-engine setups.
- Two reporting frames appear in the literature, and **both come from this same
  paper** (see Limitations §4):
  - **Headline / absolute-style figures** (often cited for low-visibility or
    low-rank pages): **Cite Sources +115%**, **Statistics +40%**.
  - **Per-method relative-improvement figures** (average lift of each method):
    **Quotation +41%**, **Statistics +33%**, **Fluency +29%**,
    **Cited Sources +27%**.
- Takeaway used here: adding statistics and citing sources are the strongest
  levers; fluency is real but the weakest of the measured methods.

### AutoGEO — *ICLR 2026*, arXiv 2510.11438
- Automated GEO content rewriting. Reports **+50.99%** citation visibility over
  a **Fluency-Optimization baseline**.
- Takeaway used here: substance-oriented optimization beats style/fluency-only
  optimization — corroborates de-emphasizing pure structural/fluency signals.

### C-SEO Bench — 2025, arXiv 2506.11097
- Benchmark of "conversational SEO" / GEO manipulation tactics.
- Finding: **surface-level manipulation is largely ineffective**; what matters
  is infrastructure and substantive signals.
- Takeaway used here: cap `structural_readability` lower; it is a surface
  signal and over-weighting it would reward exactly the tactics this benchmark
  found unreliable.

---

## 2. Dimension → study → number mapping

| Scorer dimension | v1 cap | v2 cap | Δ | Maps to GEO method | Evidence (study · number) |
|---|---|---|---|---|---|
| `answer_block_quality` | 30 | 30 | 0 | Quotation + Cite Sources + answer-first placement | Princeton: Quotation **+41%** per-method; "according to / research shows" sub-signal = Cite Sources **+27%** per-method (**+115%** low-rank) |
| `self_containment` | 25 | 22 | −3 | (extraction-quality proxy; not a Princeton per-method lever) | No direct per-method number — heuristic for clean extractability; yields 3 pts to statistics |
| `structural_readability` | 20 | 15 | −5 | Fluency | Princeton: Fluency **+29%** per-method (weakest cited lever); C-SEO Bench: surface manipulation largely ineffective |
| `statistical_density` | 15 | 25 | +10 | Statistics + Cite Sources (named-source sub-signal) | Princeton: Statistics **+40%** headline / **+33%** per-method; Cite Sources **+115%** low-rank / **+27%** per-method |
| `uniqueness_signals` | 10 | 8 | −2 | Originality / E-E-A-T (substance-over-style) | AutoGEO **+50.99%** over fluency baseline (directional support; not a Princeton per-method number); yields 2 pts to statistics |
| **Total** | **100** | **100** | **0** | — | sum preserved (normalization unchanged) |

Net effect: the 5 + 3 + 2 = 10 points removed from
`structural_readability`, `self_containment`, and `uniqueness_signals` were all
moved into `statistical_density`, the dimension carrying the two strongest
empirical levers (Statistics, Cite Sources). `answer_block_quality` was held at
30 because it already carries the Quotation and Cite-Sources signals and the
answer-first placement that GEO research treats as critical.

### Sub-signal re-scaling (within-dimension)
Because each dimension clamps its internal sub-scores to its cap, the
sub-score increments were re-scaled when a cap changed, so the new cap is
actually reachable and the proportions stay intentional:

- `self_containment` (22): word-count 7 / pronoun 8 / proper-noun 7.
- `structural_readability` (15): sentence-length 6 / list-words 3 / numbered 3 / paragraph 3.
- `statistical_density` (25): percentages ≤10 / dollars ≤7 / contextual numbers ≤4 / year +2 / named sources +2 each (max possible 29, clamped to 25 — headroom is intentional so genuinely stat-dense passages saturate the dimension).
- `uniqueness_signals` (8): original-data 4 / case-study 2 / tool-mention 2.

---

## 3. What was NOT changed
- **CLI interface** (`python citability_scorer.py <url>`) — unchanged.
- **Output JSON schema** — all keys and nesting unchanged:
  `total_score`, `grade`, `label`, `breakdown.{answer_block_quality,
  self_containment, structural_readability, statistical_density,
  uniqueness_signals}`, `url`, `total_blocks_analyzed`,
  `average_citability_score`, `optimal_length_passages`, `grade_distribution`,
  `top_5_citable`, `bottom_5_citable`, `all_blocks`, etc.
- **Grade thresholds** (A ≥80, B ≥65, C ≥50, D ≥35, F <35) — unchanged. Because
  the dimension caps still sum to 100, the 0–100 scale and these thresholds
  remain comparable to v1 in magnitude.

Only the weight constants and explanatory comments inside `score_passage()`
were edited.

---

## 4. Limitations & caveats

1. **Mixed reporting frames from one paper.** The scorer's comments and this
   doc cite both the headline figures (Statistics +40%, Cite Sources +115%)
   and the per-method relative gains (Quotation +41%, Statistics +33%,
   Fluency +29%, Cited Sources +27%). **Both sets originate from the same
   Princeton GEO (KDD 2024) paper** but measure different things (absolute /
   low-rank-page impact vs. average per-method relative improvement). They are
   not additive and should not be summed; they are used here only as ordinal
   evidence for *which* signals to weight more.

2. **Heuristic proxy, not the studies' instrument.** The scorer detects signals
   via regex (percent signs, "according to", proper nouns, etc.). It does not
   reproduce the experimental conditions of any cited paper. A high
   `statistical_density` score means "this passage contains the textual
   markers the research associates with higher citation rates," not "this
   passage will be cited X% more."

3. **Weights are ordinal, not calibrated.** The +10/−5/−3/−2 reallocation
   reflects the *relative ranking* of levers in the research, not a fitted
   regression on citation outcomes. No held-out validation of these specific
   caps against AI-citation data was performed.

4. **Cite Sources lever is split across two dimensions.** The "according to /
   research shows" pattern lives in `answer_block_quality`, while named-source
   detection lives in `statistical_density`. So the single Princeton "Cite
   Sources" method is represented in two places; neither dimension fully
   isolates it.

5. **Source-page recency.** Princeton GEO is KDD 2024; AutoGEO is ICLR 2026
   (arXiv 2510.11438); C-SEO Bench is 2025 (arXiv 2506.11097). Answer-engine
   ranking behavior changes over time, so these weights should be revisited as
   newer GEO benchmarks appear.
