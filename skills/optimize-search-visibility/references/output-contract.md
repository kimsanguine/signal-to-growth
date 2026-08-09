# Output contract

Create only the report the requested operation needs. Every report states its observation date and separates what was directly observed (fetched page, script output, live query) from what was inferred or recommended.

## `geo-citability-score.md`

Include the 0-100 score as a range with sample size (never a bare single number), the dimension breakdown from `scripts/citability_scorer.py`, and whether the score came from the deterministic local heuristic or a live query via `live_citation.py`.

## `geo-crawler-access.md`

List each of the 14 checked AI crawlers, whether robots.txt/meta/X-Robots blocks it, and the exact directive found. Do not report a crawler as "allowed" without checking all three surfaces.

## `geo-brand-mentions.md`

List each mention found, its source URL, and whether `scripts/brand_scanner.py` classified it as authoritative. Do not infer sentiment the scanner did not report.

## `geo-platform-optimization.md`

Per-platform (ChatGPT, Perplexity, Google AI Overviews, Gemini, Copilot) findings from `references/platform-algorithms.md`, with the source-date of the underlying research and a staleness flag when the reference is older than 6 months.

## `geo-schema-report.md`

For each `schema/*.json` template checked: present / missing / invalid, with the specific validation error when invalid.

## `geo-audit-report.md`

Full-audit output only. Include:

- combined GEO score (0-100) and the six category scores that produced it;
- issue list tagged Critical / High / Medium / Low;
- a 30-day action plan ordered by severity;
- an appendix listing every page URL analyzed and its fetch timestamp.

## `llms.txt`

Generated for the target site being audited, not for this repository. State the source URL it was generated from and the generation date in the accompanying report, not inside the file itself.

## Completion gate

A report is ready when every score cites the script or fetch that produced it, every missing credential is named as "skipped" rather than folded into a lower score, and no finding claims a live ranking or citation that was not actually queried during this run.
