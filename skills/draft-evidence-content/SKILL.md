---
name: draft-evidence-content
description: "Use when creating evidence-based articles, FAQs, landing-page copy, comparison content, 답변형 콘텐츠, or GEO-ready drafts without publishing. Do not use for publishing, scheduling, distributing content, or inventing customer quotes."
---

# Draft Evidence Content

Create a useful answer while preserving which claims are observed, reported, inferred, recommended, or unknown.

## Inputs

Require:

- audience and question;
- approved evidence IDs;
- current authoritative sources for time-sensitive facts;
- product claim policy;
- public, internal, and restricted data boundaries;
- CTA and publication approval boundaries.

## Workflow

1. State the reader question and desired next decision.
2. Build a claim ledger before drafting.
3. Link each material claim to evidence IDs or external sources.
4. Label inference and recommendation rather than presenting them as observed facts.
5. Write the direct answer before background detail.
6. Add limitations, counterevidence, and update dates where they change interpretation.
7. Remove or generalize restricted customer detail.
8. Create a review checklist for accuracy, privacy, brand, legal, and CTA.
9. Stop at a draft. Never publish without explicit approval.

## Boundaries

- Let the model propose structure, explanation, examples, and CTA wording.
- Use deterministic checks for claim IDs, evidence references, dates, links, and private-data patterns.
- Require a person to approve product, legal, commercial, and public claims.
- Do not invent testimonials, customer quotes, benchmarks, or product capabilities.
- Do not convert internal evidence into public proof without permission.

## Outputs

Create:

- `content-brief.json`
- `content-brief.md`
- `draft.md`
- `claim-ledger.jsonl`
- `review-checklist.md`

Read [references/output-contract.md](references/output-contract.md) before writing them.

Create `content-brief.json` first. It is the schema-valid shared scope that
later fanout surfaces reuse. `content-brief.md` is a readable mirror; it does
not replace the JSON contract.

Add every new record to `claim-ledger.jsonl` with the `append-record` command,
never by writing or editing the file:

```bash
python3 scripts/stg.py append-record <artifact-directory>/claim-ledger.jsonl '<json-object>'
```

It takes an exclusive lock and hash-chains each line to the one before it, so a
later reader can tell whether history was rewritten. In a packaged runtime the
same command is `signal-to-growth append-record`.

## Stop conditions

Stop when a core claim is unsupported, restricted evidence is required for the argument, the source is stale and cannot be refreshed, or publication is requested without a final approved target.

## Verification

Run:

```bash
python3 scripts/stg.py scan-privacy draft.md
```

Require zero unsupported material claims and keep the publish action outside this skill.
