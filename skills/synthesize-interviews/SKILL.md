---
name: synthesize-interviews
description: "Turn consented interview transcripts into source-linked evidence, themes, outliers, and counterevidence. Use when synthesizing customer interviews, VOC, JTBD research, 인터뷰 합성, or preparing evidence before a product or growth decision."
---

# Synthesize Interviews

Create traceable synthesis without turning model-generated themes into approved customer truth.

## Inputs

Require:

- consented transcript or notes;
- pseudonymous participant ID and role;
- interview date and source file;
- evidence and privacy policy;
- the decision the synthesis should inform.

Reject summaries that contain no source material.

## Workflow

1. Preserve each transcript as a read-only source.
2. Extract candidate quotes exactly and attach a file and line locator.
3. Separate the quote from its interpretation.
4. Assign stable `EV-YYYYMMDD-NNN` identifiers.
5. Mark strength as `awaiting_human_tag`.
6. Code evidence across participants without counting multiple quotes from one person as multiple people.
7. Propose no more themes than the source can support.
8. Record outliers, counterevidence, role differences, and missing segments.
9. Ask a person to approve evidence strength and theme wording.
10. Write the synthesis only after reference integrity passes.

Do not use `awaiting_human_tag` evidence to create downstream signals,
decisions, or outcomes. Stop for a person's strength review; after the person
sets `weak`, `medium`, or `strong`, record their identifier in `approved_by`.

## Boundaries

- Let the model extract candidate quotes, codes, and themes.
- Use deterministic checks for exact source locators, IDs, distinct participants, schema, and references.
- Require a person to approve evidence strength and any claim used in a decision.
- Do not create a persona automatically.
- Do not convert frequency into importance without context.
- Do not use a fixed interview count as a universal gate.

## Outputs

Create:

- `evidence.jsonl`
- `theme-cards.md`
- `counterevidence.md`
- `synthesis-summary.md`

Read [references/output-contract.md](references/output-contract.md) before writing them.

## Stop conditions

Stop when:

- consent or source location is missing;
- a quote cannot be found in the source;
- participant identity cannot be pseudonymized;
- a requested conclusion has no supporting evidence;
- public output would expose restricted material.

## Verification

Keep `evidence.jsonl` with the other run artifacts, then run:

```bash
python3 scripts/stg.py validate-artifacts artifacts/
python3 scripts/stg.py scan-privacy synthesis-summary.md
```

Every material claim must cite an evidence ID or be labeled as an inference, recommendation, or unknown.
