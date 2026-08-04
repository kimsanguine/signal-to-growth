# Output contract

## `visibility-observations.jsonl`

Each record needs an observation ID, surface, URL or file, locale, question, observation date, access state, result, claim state, and source pointer.

## `citation-gaps.md`

Connect each gap to a target question and observed evidence. Label any competitor interpretation as inference.

## `technical-findings.md`

Record status, canonical, robots, structured data, heading, answer block, and source-link findings. Separate not checked from not present.

### Optional citability score row

A diagnostic score is optional. If `signal_growth.geo_visibility.score_citability`
returned `claim_state: "reported"`, record one row with the score, its `0-100`
scale, the scorer name and version, and a link to the method weights it
returned. Mark the row a heuristic, never a probability of being cited.

If it returned `claim_state: "unknown"` — the optional scorer is not installed —
record the row as `unknown` with the reason. An absent score is not a low score,
and no other row's state changes because of it.

## `recommendations.md`

Link every recommendation to an observation ID, expected mechanism, owner, verification method, and update risk.

## Completion gate

Observed, reported, inferred, recommended, and unknown statements are visibly distinct, with no unsupported ranking or citation claim.
