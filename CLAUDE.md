# CLAUDE.md

## Purpose

This repository contains one portable Agent Skills source tree with thin adapters for Claude Code and Codex. Preserve artifact contracts, human approval boundaries, and cross-runtime behavior.

## Source of truth

- Skill behavior: `skills/*/SKILL.md`
- Structured artifacts: `contracts/*.schema.json`
- Safety defaults: `policies/default-policy.json`
- Deterministic validation: `src/signal_growth/`
- Public examples: `fixtures/public-dummy/`

Do not duplicate skill instructions in platform-specific manifests.

## Working rules

- Read the target skill, its `references/output-contract.md`, and the applicable root schema before editing.
- Keep each `SKILL.md` under 500 lines with only `name` and `description` in frontmatter.
- Keep customer quotes traceable to a source locator. Never invent quotes or treat model text as observed evidence.
- Keep thresholds in policy or metric artifacts. Do not add universal response, retention, or PMF targets.
- Keep email, DM, publishing, deletion, refund, deployment, and other external writes disabled until explicit human approval.
- Never add real customer data, credentials, account identifiers, or private URLs to fixtures.
- Update both platform manifests when release metadata changes.

## Verification

Run from the repository root:

```bash
python3 scripts/stg.py validate-repo .
python3 scripts/stg.py demo .
python3 -m unittest discover -s tests -v
python3 /Users/sanguinekim/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

Also run `quick_validate.py` for every changed skill.
