# Output contract

## `evidence.jsonl`

Follow `contracts/evidence.schema.json`. Use one object per line and a stable `EV-YYYYMMDD-NNN` ID.

Keep:

- verbatim excerpt;
- source file and line;
- participant ID when applicable;
- interpretation separate from excerpt;
- `awaiting_human_tag` until a person reviews strength;
- privacy classification.

## `theme-cards.md`

For each theme include evidence IDs, distinct participant count, role differences, counterevidence, confidence limits, and the decision it may inform.

## `counterevidence.md`

Preserve contradictory, outlier, and missing-segment evidence. Do not hide it in an appendix.

## `synthesis-summary.md`

Separate observed, reported, inferred, recommended, and unknown claims.

## Completion gate

Every material statement has a valid evidence ID or an explicit non-observed claim state.
