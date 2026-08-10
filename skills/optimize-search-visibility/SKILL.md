---
name: optimize-search-visibility
description: "Audit and improve how a website ranks in traditional search and gets cited by AI answer engines (ChatGPT, Perplexity, Google AI Overviews, Gemini, Copilot) — keyword/SERP/backlink research, passage citability scoring, AI crawler access checks, llms.txt generation, brand-mention authority, schema markup, and a combined GEO score with a distributional (not single-number) confidence range. Use when the user mentions SEO(검색엔진 최적화), GEO, AEO, citability, llms.txt, schema markup, keyword or SERP research(키워드·SERP 리서치), backlinks, AI search visibility(AI 검색 노출), or gives a URL to analyze. Do not use for simple factual or coding questions unrelated to a website's search or AI-answer visibility, for publishing or changing a live site, or for reporting a ranking or citation you did not observe."
---

# Optimize Search Visibility

Score and improve a website's visibility in both ranking search (SEO) and citation-based AI answer engines (GEO/AEO). Report what was actually observed versus inferred; never invent a ranking or citation.

## Attribution

Ported from two prior open-source skills. See `NOTICE.md`, `LICENSE-geo-seo-claude`, and `LICENSE-seo-geo` before redistributing this skill on its own.

## Inputs

Require:

- target URL(s) and the business type or product;
- target audience, key questions the page should answer, and locale;
- named competitors, if any;
- observation date;
- `DATAFORSEO_LOGIN` / `DATAFORSEO_PASSWORD` for paid SEO features — proceed with the free path and say so explicitly when absent;
- `OPENAI_API_KEY` / `PERPLEXITY_API_KEY` for live citation measurement — skip that check explicitly when absent, never silently.

Never request or persist a raw credential in a document, commit, or chat message. Read keys only from environment variables via `scripts/credential.py`.

## Routing

- **Single check** ("citability score", "is our crawler access blocked", "keyword research for X") → run the one matching script or reference below, report that category alone.
- **Full audit** ("audit our GEO", "full SEO+GEO review") → run the Full Audit flow.

## Capabilities

### SEO (requires `DATAFORSEO_LOGIN`/`DATAFORSEO_PASSWORD`; `seo_audit.py` is free)

| Task | Script |
|---|---|
| Keyword research | `scripts/keyword_research.py` |
| Related keywords | `scripts/related_keywords.py` |
| Autocomplete ideas | `scripts/autocomplete_ideas.py` |
| SERP analysis | `scripts/serp_analysis.py` |
| Backlinks | `scripts/backlinks.py` |
| Competitor gap | `scripts/competitor_gap.py` |
| Domain overview | `scripts/domain_overview.py` |
| Free technical SEO check | `scripts/seo_audit.py` |

### GEO / AEO

| Task | Method |
|---|---|
| Passage-level citability score (0-100) | `scripts/citability_scorer.py <url>` |
| AI crawler access map (14 crawlers) | robots.txt / meta / X-Robots checks + `scripts/fetch_page.py` |
| llms.txt analysis or generation | `scripts/llmstxt_generator.py <url>` |
| Brand-mention authority | `scripts/brand_scanner.py <brand> <url>` |
| Platform-specific optimization (5 AI platforms) | `references/platform-algorithms.md`, `references/platform-citation-factors.md` (citation-source distribution — re-verify staleness before treating as a per-platform strategy basis) |
| Schema detection, validation, generation | `schema/*.json` (6 templates) + `scripts/fetch_page.py` |
| Live citation rate (BYO-API) | `scripts/live_citation.py <brand/domain> <query> [--runs N] [--engine openai\|perplexity\|all]` — queries a real answer engine N times and reports cited/N as a distribution, not a single heuristic number |

Citability scoring weights are grounded in Princeton GEO (KDD'24), AutoGEO (ICLR'26), and C-SEO Bench (2025) — see `references/citability-research.md`. Re-verify against current research before reuse; source-dated 2026-06-05.

### Distributional scoring

Report AI-visibility scores as a range with a sample size ("approx. 55, range 48-61, N=5"), never a bare single number — that is false precision. Run:

```bash
python3 skills/optimize-search-visibility/scripts/distribution.py <script_name> <url> --runs N
```

The local citability heuristic is deterministic (fixed HTML in, same score out every run) — that is not evidence of stability, it means no live model was queried. Only `live_citation.py` measures real answer-engine variance. Cite the deterministic heuristic as a proxy, not as measured citation behavior.

## Full Audit flow

For a full-site request, run these steps yourself in order — do not assume a named subagent exists on the installing system; every check here is one script or reference read, sequenced by this skill.

0. **Preflight**: check for `requests`/`beautifulsoup4`/`lxml` (see `requirements.txt`), `DATAFORSEO_LOGIN`/`DATAFORSEO_PASSWORD`, and `OPENAI_API_KEY`/`PERPLEXITY_API_KEY`. Report each missing piece as "skipped — no credential", not as a zero score.
1. **Discovery**: fetch the target URL with `scripts/fetch_page.py` and identify business type and key pages.
2. **Category checks**, each independent and each producing its own findings:
   - AI citability — `scripts/citability_scorer.py`
   - Brand authority — `scripts/brand_scanner.py`
   - Content E-E-A-T — `references/geo-research.md` checklist against the fetched page
   - Technical GEO (crawler access, llms.txt) — robots.txt/meta checks + `scripts/llmstxt_generator.py`
   - Structured data — `schema/*.json` templates against the fetched page
   - Platform optimization — `references/platform-algorithms.md`
3. **Synthesis**: combine into one GEO score (0-100): AI Citability 25%, Brand Authority 20%, Content E-E-A-T 20%, Technical GEO 15%, Structured Data 10%, Platform Optimization 10%.

## Outputs

Create only the reports the requested operation needs:

- `geo-citability-score.md`
- `geo-crawler-access.md`
- `geo-brand-mentions.md`
- `geo-platform-optimization.md`
- `geo-schema-report.md`
- `geo-audit-report.md` — full-audit output: combined score, per-category breakdown, issue severity (Critical/High/Medium/Low), a 30-day action plan, and an appendix of pages analyzed.
- `llms.txt` — generated file for the target site, not this repository.

Read [references/output-contract.md](references/output-contract.md) before writing them.

## DataForSEO credential branch

- Credential present → full SEO feature set.
- Credential absent → run `scripts/seo_audit.py` (free) plus WebFetch-based checks; all GEO features still work unaffected. For a paid SEO feature with no credential, explain how to set one and stop — do not fail silently or fabricate a result.

## Boundary

- Does not publish, deploy, or modify a live site — every output is a report or a standalone file (like `llms.txt`) for the user to review and apply themselves.
- Does not report a ranking, citation, or score the underlying script or fetch did not actually observe.
- Not for questions unrelated to a website's search or AI-answer visibility.

## References

- Methodology: `references/geo-research.md`, `references/platform-algorithms.md`, `references/seo-checklist.md`, `references/schema-templates.md`, `references/tools-and-apis.md`
- Scoring basis: `references/citability-research.md`, `references/platform-citation-factors.md` (staleness warning included)
- Attribution: `NOTICE.md`, `LICENSE-geo-seo-claude`, `LICENSE-seo-geo`
