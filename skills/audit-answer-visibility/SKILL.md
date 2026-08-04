---
name: audit-answer-visibility
description: "Audit how a page or product answer is discoverable and citable using dated observations, technical checks, and source-backed findings. Use when reviewing SEO, GEO, AEO, answer visibility, citation readiness, 검색 노출, or 생성형 검색 대응. Do not use for drafting or publishing content, changing a live site, or reporting a ranking you did not observe."
---

# Audit Answer Visibility

Produce an evidence audit, not an invented probability of being cited. Separate live observation, inference, and recommendation.

## Inputs

Require:

- target URLs or files;
- target audience, questions, locale, and competitors;
- observation date;
- access and authentication constraints;
- claim and source policy.

Use current authoritative sources when platform behavior may have changed.

## Workflow

1. Record the exact surface, date, locale, and access state.
2. Check response status, canonical, robots, structured data, heading hierarchy, answer blocks, and cited sources.
3. Test target questions only on surfaces the user authorized.
4. Record what was directly observed without interpreting it.
5. Add inference with confidence and alternative explanations.
6. Add recommendations linked to observed gaps.
7. Record inaccessible or unverified surfaces as unknown.
8. If using a diagnostic score, expose weights and label the score as a heuristic.

An optional third-party citability scorer covers step 8 without hand-weighting.
It is not required and never changes the rest of the audit:

```bash
pip install -e ".[geo]"   # optional
```

```python
from signal_growth.geo_visibility import score_citability
result = score_citability(markup_you_already_fetched, surface_url)
```

Installed, it returns a heuristic score with every method weight, and the
finding is `reported` — a third-party tool said it, nobody observed a citation.
Not installed, the same call returns `unknown` with no number. Do not fill the
gap with an estimate, and do not fetch a page just to score it; score only
markup the user already authorized you to read.

## Boundaries

- Let the model organize questions, gaps, and recommendations.
- Use deterministic checks for HTTP and markup facts where available.
- Require a person to interpret competitive importance and approve investment.
- Do not claim ranking, citation, or answer inclusion without a dated observation.
- Do not treat crawler accessibility as proof that an answer system used the page.
- Do not present a proprietary score as a calibrated probability.

## Outputs

Create:

- `visibility-observations.jsonl`
- `citation-gaps.md`
- `technical-findings.md`
- `recommendations.md`

Read [references/output-contract.md](references/output-contract.md) before writing them.

Add every new record to `visibility-observations.jsonl` with the `append-
record` command, never by writing or editing the file:

```bash
python3 scripts/stg.py append-record <artifact-directory>/visibility-observations.jsonl '<json-object>'
```

It takes an exclusive lock and hash-chains each line to the one before it, so a
later reader can tell whether history was rewritten. In a packaged runtime the
same command is `signal-to-growth append-record`.

## Stop conditions

Stop when the target cannot be accessed, observation context is missing, a requested claim needs unavailable live verification, or a source cannot be attributed.

## Verification

Confirm every finding has one of these states:

- `observed`
- `reported`
- `inferred`
- `recommended`
- `unknown`

Rerun time-sensitive observations before publication.
