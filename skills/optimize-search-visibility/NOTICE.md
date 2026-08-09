# optimize-search-visibility — Attribution

This skill combines two prior open-source works into one Claude Code skill.

## 1. geo-seo-claude — MIT License

- Source: https://github.com/zubair-trabzada/geo-seo-claude
- Copyright (c) Zubair Trabzada
- Full license text: `LICENSE-geo-seo-claude` (retain copyright and license notice)
- Adapted: `scripts/citability_scorer.py`, `scripts/brand_scanner.py`, `scripts/llmstxt_generator.py`, `scripts/fetch_page.py`, `schema/*.json` (6 JSON-LD templates), and the citability/crawler/llms.txt/brand/platform GEO methodology in `references/`.

## 2. seo-geo (ReScienceLab, opc-skills) — Apache License 2.0

- Source: https://github.com/ReScienceLab/opc-skills/tree/main/skills/seo-geo
- Author: ReScienceLab
- Full license text: `LICENSE-seo-geo` (retain copyright, license, and change notices)
- Adapted: DataForSEO-based keyword/SERP/backlink/domain-overview scripts (`scripts/keyword_research.py`, `scripts/related_keywords.py`, `scripts/autocomplete_ideas.py`, `scripts/serp_analysis.py`, `scripts/backlinks.py`, `scripts/competitor_gap.py`, `scripts/domain_overview.py`, `scripts/seo_audit.py`, `scripts/dataforseo_api.py`, `scripts/credential.py`) and associated `references/` methodology.
- Files adapted from this source were modified for this skill (renamed imports, integrated into a combined SKILL.md, credential handling aligned to this repo's conventions).

## Excluded from this port

`crm_dashboard.py`, `scripts/webapp/`, and PDF report templates from the original geo-seo-claude work were not carried forward (sales-tooling scope, out of bounds for this repository).
