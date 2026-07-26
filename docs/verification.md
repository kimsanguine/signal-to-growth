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
| Unit, schema, negative, integration, and documentation tests | 57 passed |
| Eleven `SKILL.md` files with `quick_validate.py` | 11 passed |
| Codex plugin with `validate_plugin.py` | passed |
| Claude marketplace with `claude plugin validate .` | passed |
| Universal installer smoke | isolated project install copied all 11 skills to Claude Code and Codex paths |
| Editable install in `.venv` | passed |
| Connector artifact validation | passed with public dummy fixtures |
| Naver event normalization | passed offline with deterministic replay ID |
| Channel Talk webhook/backfill dedupe | passed with injected offline transport |
| Kakao Open Builder request normalization | passed with public dummy fixture and `X-Request-Id` |
| Kakao Open Builder `version=2.0` response | passed as a deterministic local contract |
| Supabase restricted event sink | passed with injected HTTP transport; server secret is not sent as Bearer auth |
| Approval audit reference | passed locally; a valid `APR-...` reference is sent as a separate Supabase column |
| Synthetic-event expiry marker | migration records a seven-day `expires_at`; no automatic deletion is claimed |
| Vercel WSGI route discovery | passed locally with `vercel dev` |
| Vercel preview build | passed with the Python 3.12 runtime |
| Hosted root route | passed locally; returns only safe service metadata |
| Unconfigured hosted endpoint | `/api/health` and `/api/kakao/skill` both failed closed with HTTP 503 |

The universal installer was exercised from the local checkout in an isolated
temporary project and did not change user-level plugin state. Official Claude
and Codex marketplace installation from the published GitHub default branch is
a separate verification state.

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
- Kakao Open Builder skill-request normalization and simple-text response construction;
- Vercel-recognized WSGI entry point and fail-closed route behavior;
- Supabase REST insert contract, two-second timeout, and idempotent conflict handling;
- RLS-enabled migration with `anon` and `authenticated` access revoked;
- explicit `service_role` Data API grant for the restricted event table;
- separate approval reference and synthetic-event deletion-eligibility marker;
- no scheduled deletion job or production-retention claim;
- `accepted != delivered`, non-regressing state, and separate fallback attempts;
- reply/send capabilities disabled by policy.

Not verified:

- a real Channel Talk or Naver test account;
- a deployed public HTTPS endpoint and actual Supabase insert;
- SQL execution of both migrations against an isolated Supabase test project;
- a Kakao Channel development-channel round trip;
- repeated identical Kakao utterances to confirm live `X-Request-Id` identity behavior;
- Kakao ConsultTalk migration or live conversation ingestion;
- provider credential health, callback behavior, scheduled cleanup, and production retention;
- any external reply or send.

## Status vocabulary

- **Implemented:** source exists.
- **Statically validated:** structure and contract checks pass.
- **Locally executed:** commands ran in the checkout.
- **Runtime discovered:** the target agent listed the skill.
- **Published:** the commit is on GitHub.
- **Operational:** a real authorized workflow completed.

Do not use one state as proof of another.
