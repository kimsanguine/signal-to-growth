## What changed

Describe the user-visible or contract-level change.

## Evidence and approval boundary

- Evidence or issue:
- Human approval required:
- External write performed: no

## Verification

- [ ] `python3 scripts/stg.py validate-repo .`
- [ ] `python3 scripts/stg.py demo .`
- [ ] `python3 -m unittest discover -s tests -v`
- [ ] Changed skills passed `quick_validate.py`
- [ ] Fixtures contain only public dummy data
- [ ] No credentials or private URLs are included

## Compatibility

- [ ] Claude Code manifest remains valid
- [ ] Codex manifest remains valid
- [ ] Artifact schema compatibility was considered
