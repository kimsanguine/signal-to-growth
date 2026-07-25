# Contributing

Signal to Growth welcomes focused improvements to skill behavior, artifact contracts, fixtures, and cross-runtime compatibility.

## Before changing a skill

1. Read the target `SKILL.md`.
2. Read its `references/output-contract.md`.
3. Read the related file under `contracts/`.
4. Add or update a public dummy fixture.
5. Add a negative case when changing a safety boundary.

Do not include real customer transcripts, private URLs, credentials, account identifiers, or internal operational data.

## Local checks

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
make check
```

Validate each changed skill with the Agent Skills validator:

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py skills/<skill-name>
```

## Pull requests

Explain:

- what user problem changes;
- which artifact contract changes;
- whether the change is backward compatible;
- what positive and negative fixtures were used;
- which checks passed.

Keep platform-specific metadata in its adapter. Do not fork the core skill instructions into separate Claude Code and Codex copies.
