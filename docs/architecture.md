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
Artifact contracts
  evidence / signal / metric / decision / action / outcome / run state
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
| Signal category | Yes | PII, dedup, schema, routing | High-risk review |
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

## Orchestrator boundary

`run-growth-loop` reads state and routes the next specialist. It must not reproduce interview synthesis, metric design, content audit, or channel strategy. This reduces rule drift and makes specialist skills independently testable.
