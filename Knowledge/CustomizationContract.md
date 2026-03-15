# Customization Contract

This document describes how each repository surface is owned, synced, and customized during template upgrades. It is generated from `repo-governance/customization-contracts.json` — the normative source of truth.

For the architectural rationale, see [ADR-006](ADR/006-template-upgrade-process.md). For the practical merge guide, see [UpgradeGuide.md](UpgradeGuide.md).

## Surface Table

| Surface | Ownership | Sync Model | Where to Customize |
|---------|-----------|------------|--------------------|
| `CLAUDE.md` | shared_review | full overwrite + preserve contract | `Knowledge/local/AI/claude.md` via `@import` |
| `AGENTS.md` | shared_review | full overwrite + preserve contract | `Knowledge/local/AI/codex.md` via prose |
| `README.md` | shared_review | managed blocks | Content outside `repository-mode` and `template-onboarding` markers |
| `README.pt-PT.md` | shared_review | managed blocks | Content outside `repository-mode` and `template-onboarding` markers |
| `.claude/skills/**` | shared_review | extensible directory | Add extra skill dirs — they survive sync |
| `.codex/skills/**` | shared_review | extensible directory | Add extra skill dirs — they survive sync |
| `.agents/**` | shared_review | extensible directory | Add extra skill dirs — they survive sync |
| `src/**`, `scripts/**`, `tests/**` | template_owned | overwrite | Do not customize — changes are overwritten |
| `docs/**` | template_owned | overwrite | Do not customize — changes are overwritten |
| `Knowledge/ADR/**` | template_owned | overwrite | `Knowledge/local/ADR/` (numbers 100+) |
| `Knowledge/Templates/**` | template_owned | overwrite | Do not customize — changes are overwritten |
| `Knowledge/*.md` | template_owned | overwrite | Do not customize — changes are overwritten |
| `Knowledge/local/**` | private_owned | never synced | Your private content — safe from all syncs |
| `.gitignore` | shared_review | diff only | Manual review — diff shown in PR body |
| `CONTRIBUTING.md` | shared_review | diff only | Manual review — diff shown in PR body |
| `projects/registry.shared.json` | private_owned | never synced | Your routing config — safe from all syncs |
| `.claude/settings.local.json` | local_only | never synced | Bootstrapped from `.claude/settings.example.json` |

## Key Principles

1. **Template updates arrive automatically** for template_owned and full-overwrite surfaces.
2. **Private rules live in overlays** (`Knowledge/local/AI/`), not in synced AI files.
3. **Skill directories are extensible** — local additions survive, but template skills update.
4. **Local extras do not need parity** — a custom `.claude/skills/my-tool/` does not need mirrors in `.codex/` or `.agents/`.
5. **The contract registry is normative** — run `check_customization_contracts.py` to validate.

## Validators

| Script | What it checks |
|--------|----------------|
| `check_managed_blocks.py` | All managed block markers exist in matched begin/end pairs |
| `check_customization_contracts.py` | Registry ↔ manifest consistency, @import presence, overlay safety |
| `check_agent_surface_parity.py` | Required template skills present in all three surfaces |
| `check_repo_ownership.py` | All files classified, no sync violations |
| `check_sync_manifest_alignment.py` | Workflow sync paths match manifest rules |
