# Architecture

## Design goal

Maintain one portable skill source while giving Claude Code and Codex their native plugin metadata. Keep model reasoning, deterministic validation, and human decisions visibly separate.

## Layers

```text
Platform adapter
  .claude-plugin / .codex-plugin / marketplace
        ↓
Portable skills
  SKILL.md / references / UI metadata
        ↓
Customer-channel gateway (optional)
  provider verification / normalization / dedupe / recovery
        ↓
Artifact contracts
  channel event / evidence / signal / metric / decision / action / outcome / run state
        ↓
Deterministic checks
  schema / reference / privacy pattern / question lint / routing
        ↓
Human approval
  evidence strength / decision / external write / public claim
```

## Responsibility split

| Responsibility | Model | Deterministic code | Human |
|---|:---:|:---:|:---:|
| Candidate quote and theme | Yes | Source/reference check | Strength approval |
| Provider event identity | No | Auth, normalization, dedup, state | Connection approval |
| Signal category | Yes | PII, schema, routing | High-risk review |
| Metric candidates | Yes | Required contract fields | Value event and target |
| Alternatives and counterarguments | Yes | ID and state validation | Decision approval |
| Content structure | Yes | Claim and privacy checks | Public claim approval |
| Channel experiment options | Yes | Capacity and metric references | Spend and external action |

## Portability

Core skill instructions must not depend on a platform-only tool name. Platform-specific metadata belongs in:

- `.claude-plugin/`
- `.codex-plugin/`
- `.agents/plugins/`
- skill-level `agents/openai.yaml`

Scripts resolve paths from their own location or an explicit argument. They do not require Claude- or Codex-specific environment variables.

## Connector boundary

`connect-customer-channels` handles provider mechanics before `triage-customer-signals` interprets the customer problem.

```text
raw provider event
  → verify
  → durable inbox identity
  → normalize
  → redact
  → dedupe
  → canonical CS event
  → signal triage
```

Provider and product remain separate fields. For example, `kakao_openbuilder`
is the chatbot platform while `kakao_channel_chatbot` is the channel surface;
`channel_talk` can be the helpdesk provider while `kakao_consulttalk` is the
customer-facing product. Kakao Developers user messaging is not treated as a
customer-service connector. Open Builder chatbot requests are not relabeled as
ConsultTalk or native Channel 1:1 counselor chat.

Read-only adapters may build and validate backfill requests, but actual network access requires an approved test connection. Reply, send, assignment, template mutation, and fallback stay disabled without explicit human approval.

## hplan reference loop

The hplan integration is a reference bridge, not a shared decision ledger.

```text
hplan approved Build Gate Profile v0
  -> imported URI + fingerprint reference
  -> Signal to Growth experiment, metric, decision, evidence, approval, outcome
  -> completed Profile v0 reconsideration request
  -> human hplan re-evaluation
```

Import accepts only canonical forward-capable hplan statuses and records no
copied hplan decision, evidence, or gate status. Reconsideration requires the
same imported opaque handoff reference on the executed action and mature,
conclusive outcome, plus locally resolvable metric, decision, evidence, and
human-approval provenance. It only requests human review; it never creates a
new hplan `GO`/`HOLD` result or an automatic growth decision.

Webhook and polling are recovery pairs. A provider acceptance response never proves delivery, and fallback transport is recorded as a separate attempt.

PMF Radar may operate the long-running inbox, retry, raw-retention, and operator
queue. In that deployment, it exports `pmf-radar.stg.v1`; Signal to Growth
validates and imports only the redacted canonical event and bridge metadata.
See [PMF Radar and hplan integration](INTEGRATIONS.md).

## Orchestrator boundary

`run-growth-loop` reads the objective, validates available artifacts, and routes
the next specialist through a dependency graph. It does not require research
recruiting when a valid CS or analytics artifact already exists. It uses the
manual signal path when no connector is configured and routes partial connector
state back to `connect-customer-channels`. It must not call provider APIs or
reproduce specialist judgment.
