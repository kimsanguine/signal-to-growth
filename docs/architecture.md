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

Provider and product remain separate fields. For example, `channel_talk` can be the helpdesk provider while `kakao_consulttalk` is the customer-facing product. Kakao Developers user messaging is not treated as a customer-service connector.

Read-only adapters may build and validate backfill requests, but actual network access requires an approved test connection. Reply, send, assignment, template mutation, and fallback stay disabled without explicit human approval.

Webhook and polling are recovery pairs. A provider acceptance response never proves delivery, and fallback transport is recorded as a separate attempt.

## Orchestrator boundary

`run-growth-loop` reads state and routes the next specialist. It uses the manual signal path when no connector is configured and routes partial connector state back to `connect-customer-channels`. It must not call provider APIs or reproduce interview synthesis, metric design, content audit, or channel strategy. This reduces rule drift and makes specialist skills independently testable.
