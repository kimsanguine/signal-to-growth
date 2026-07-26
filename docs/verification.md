# Verification

## Release evidence

Local verification date: 2026-07-26.

Environment:

- Python 3.13 local execution with package support declared for Python 3.11+
- Claude Code 2.1.220
- Codex CLI 0.145.0

Results:

| Surface | Result |
|---|---|
| Repository validator | passed |
| Public dummy end-to-end validation | passed |
| Unit, schema, negative, integration, and documentation tests | 34 passed |
| Eleven `SKILL.md` files with `quick_validate.py` | 11 passed |
| Codex plugin with `validate_plugin.py` | passed |
| Claude marketplace with `claude plugin validate .` | passed |
| Editable install in `.venv` | passed |
| Connector artifact validation | passed with public dummy fixtures |
| Naver event normalization | passed offline with deterministic replay ID |
| Channel Talk webhook/backfill dedupe | passed with injected offline transport |

Runtime marketplace installation was not performed during local implementation because it changes user-level plugin state. Static plugin validation and clean package execution are confirmed; installation from the published GitHub source is a separate verification state.

Commands:

```bash
python3 scripts/stg.py validate-repo .
python3 scripts/stg.py demo .
python3 scripts/stg.py validate-connectors \
  fixtures/public-dummy/connector-artifacts \
  --require-complete
python3 -m unittest discover -s tests -v
```

Release checks also require:

- tracked-file secret and private-data scan;
- published GitHub commit and default branch;
- remote README, manifests, and skill count.

## Connector evidence boundary

Confirmed locally:

- five Draft 2020-12 connector schemas;
- credential-free public dummy fixtures;
- Naver event-only normalization, redaction, stable identity, and dedupe;
- Channel Talk read-only webhook/backfill identity reconciliation;
- `accepted != delivered`, non-regressing state, and separate fallback attempts;
- reply/send capabilities disabled by policy.

Not verified:

- a real Channel Talk or Naver test account;
- a public HTTPS webhook endpoint and durable restricted inbox;
- Kakao ConsultTalk migration or live conversation ingestion;
- provider credential health, callback behavior, and production retention;
- any external reply or send.

## Status vocabulary

- **Implemented:** source exists.
- **Statically validated:** structure and contract checks pass.
- **Locally executed:** commands ran in the checkout.
- **Runtime discovered:** the target agent listed the skill.
- **Published:** the commit is on GitHub.
- **Operational:** a real authorized workflow completed.

Do not use one state as proof of another.
