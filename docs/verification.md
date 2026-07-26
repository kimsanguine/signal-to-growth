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
| Unit, schema, negative, integration, and documentation tests | 70 passed |
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
| Isolated Supabase project | Pro organization project created in Seoul; all migrations applied |
| Supabase role boundary | RLS enabled; browser grants revoked; explicit deny policy added |
| Supabase Security Advisor | no findings after the deny-policy migration |
| Supabase Performance Advisor | two expected INFO notices: unused expiry index on the new test table and default Auth connection allocation |
| Vercel WSGI route discovery | passed locally with `vercel dev` |
| Vercel preview build | passed with the Python 3.12 runtime |
| Hosted root route | passed on preview; returns only safe service metadata |
| Unconfigured hosted endpoint | `/api/health` and `/api/kakao/skill` both failed closed with HTTP 503 |
| Configured hosted health | preview returned HTTP 200 with `status=configured` |
| Kakao request authentication | an incorrect synthetic `x-api-key` returned HTTP 401 |
| Kakao-to-Supabase preview E2E | two identical authorized synthetic requests returned HTTP 200 and Kakao `version=2.0` |
| Live idempotency | the repeated `X-Request-Id` produced exactly one Supabase test row |
| Vercel runtime log | preview recorded health HTTP 200 and two Kakao skill HTTP 200 requests without payload or secret output |
| Five-agent baseline evaluation | static/adversarial review completed; mean 67/100, release `NO-GO` |
| PMF Radar import and hplan intake | implemented and locally covered by deterministic integration tests |

Hosted verification target:

- environment: Vercel Preview only, not Production;
- source commit: `903f571`;
- branch: `agent/korean-cs-connectors-v0-2`;
- draft PR: `https://github.com/kimsanguine/signal-to-growth/pull/1`;
- URL: `https://signal-to-growth-kz41ouqdt-sanguine-s-projects.vercel.app`;
- synthetic request ID: `request-github-preview-20260726-001`;
- persisted result: one row after two authorized requests.
- remote CI: Python 3.11, Python 3.12, and Vercel checks passed.

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
- explicit deny policy for `anon` and `authenticated`;
- explicit `service_role` Data API grant for the restricted event table;
- separate approval reference and synthetic-event deletion-eligibility marker;
- no scheduled deletion job or production-retention claim;
- `accepted != delivered`, non-regressing state, and separate fallback attempts;
- reply/send capabilities disabled by policy.

Confirmed on an isolated hosted test stack on 2026-07-26:

- Vercel preview deployment reached `READY` with Python 3.12;
- five required runtime values and two explicit-default values are encrypted
  and scoped to the feature branch;
- `GET /api/health` returned HTTP 200 and `status=configured`;
- an incorrect synthetic `x-api-key` failed closed with HTTP 401;
- two authorized sends of the public Kakao fixture returned HTTP 200 and
  Kakao `version=2.0`;
- Supabase stored one row for the repeated `X-Request-Id`, preserving the
  approval reference and seven-day deletion-eligibility marker;
- Supabase Security Advisor returned no findings;
- Supabase Performance Advisor retained two INFO notices: the expiry index is
  unused on the new test table, and Auth uses an absolute connection allocation.
- Supabase project, SQL, API logs, and advisors were checked through the
  connected Supabase control surface;
- the Vercel connector session required reauthentication, so authenticated
  Vercel CLI was used for environment, deployment, and runtime-log verification.

Not verified:

- a real Channel Talk or Naver test account;
- a Kakao Channel development-channel round trip;
- Kakao ConsultTalk migration or live conversation ingestion;
- provider credential health, callback behavior, scheduled cleanup, and production retention;
- merge to the default branch, release tag, and Production promotion;
- any external reply or send.
- the formal 30-case Claude Code and Codex runtime evaluation;
- production wiring of the PMF Radar export or an hplan Build Gate decision.

## Status vocabulary

- **Implemented:** source exists.
- **Statically validated:** structure and contract checks pass.
- **Locally executed:** commands ran in the checkout.
- **Runtime discovered:** the target agent listed the skill.
- **Published:** the commit is on GitHub.
- **Operational:** a real authorized workflow completed.

Do not use one state as proof of another.
