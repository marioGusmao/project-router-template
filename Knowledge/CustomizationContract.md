# Customization Contract

This document describes how each repository surface is owned, synced, and customized during template upgrades. It is kept aligned with `repo-governance/customization-contracts.json` — the normative source of truth.

For the architectural rationale, see [ADR-006](ADR/006-template-upgrade-process.md). For the practical merge guide, see [UpgradeGuide.md](UpgradeGuide.md).

## Surface Table

### AI Files (full overwrite + preserve contract)

| Surface | Ownership | Sync Model | Where to Customize |
|---------|-----------|------------|--------------------|
| `CLAUDE.md` | shared_review | full overwrite + preserve contract | `Knowledge/local/AI/claude.md` via `@import` |
| `AGENTS.md` | shared_review | full overwrite + preserve contract | `Knowledge/local/AI/codex.md` via prose |

### Documentation (managed blocks)

| Surface | Ownership | Sync Model | Where to Customize |
|---------|-----------|------------|--------------------|
| `README.md` | shared_review | managed blocks | Content outside `repository-mode` and `template-onboarding` markers |
| `README.pt-PT.md` | shared_review | managed blocks | Content outside `repository-mode` and `template-onboarding` markers |

### Skill Directories (extensible)

| Surface | Ownership | Sync Model | Where to Customize |
|---------|-----------|------------|--------------------|
| `.claude/skills/**` | shared_review | extensible directory | Add extra skill dirs — they survive sync |
| `.codex/skills/**` | shared_review | extensible directory | Add extra skill dirs — they survive sync |
| `.agents/**` | shared_review | extensible directory | Add extra skill dirs — they survive sync |

### Code & Scripts (overwrite)

| Surface | Ownership | Sync Model | Where to Customize |
|---------|-----------|------------|--------------------|
| `src/**` | template_owned | overwrite | Do not customize — changes are overwritten |
| `scripts/**` | template_owned | overwrite | Do not customize — changes are overwritten |
| `tests/**` | template_owned | overwrite | Do not customize — changes are overwritten |
| `docs/**` | template_owned | overwrite | Do not customize — changes are overwritten |

### Knowledge (overwrite)

| Surface | Ownership | Sync Model | Where to Customize |
|---------|-----------|------------|--------------------|
| `Knowledge/ADR/**` | template_owned | overwrite | `Knowledge/local/ADR/` (numbers 100+) |
| `Knowledge/Templates/**` | template_owned | overwrite | Do not customize — changes are overwritten |
| `Knowledge/*.md` | template_owned | overwrite | Do not customize — changes are overwritten |

### Governance & Metadata (overwrite)

| Surface | Ownership | Sync Model | Where to Customize |
|---------|-----------|------------|--------------------|
| `repo-governance/**` | template_owned | overwrite | Do not customize — changes are overwritten; changes require `CHANGELOG.md` |
| `parity.manifest.json` | template_owned | overwrite | Do not customize — changes are overwritten |
| `version.txt` | template_owned | overwrite | Do not customize — changes are overwritten |
| `CHANGELOG.md` | template_owned | overwrite | Do not customize — changes are overwritten |
| `template.meta.json` | template_owned | overwrite | Do not customize — changes are overwritten |
| `.release-please-config.json` | template_owned | overwrite | Do not customize — changes are overwritten |
| `.release-please-manifest.json` | template_owned | overwrite | Do not customize — changes are overwritten |
| `.env.example` | template_owned | overwrite | Do not customize — changes are overwritten |
| `.claude/settings.example.json` | template_owned | overwrite | Do not customize — changes are overwritten |
| `projects/registry.example.json` | template_owned | overwrite | Do not customize — changes are overwritten |
| `.github/workflows/template-release.yml` | template_owned | overwrite | Do not customize — changes are overwritten |
| `.github/workflows/template-upstream-sync.yml` | template_owned | overwrite | Do not customize — changes are overwritten; changes require `CHANGELOG.md` |
| `.github/workflows/template-ci.yml` | template_owned | overwrite | Do not customize — changes are overwritten |
| `.github/ISSUE_TEMPLATE/**` | shared_review | overwrite | Do not customize — changes are overwritten |

### Shared Review (diff only)

| Surface | Ownership | Sync Model | Where to Customize |
|---------|-----------|------------|--------------------|
| `.gitignore` | shared_review | diff only | Manual review — diff shown in PR body |
| `CONTRIBUTING.md` | shared_review | diff only | Manual review — diff shown in PR body |
| `.github/pull_request_template.md` | shared_review | diff only | Manual review — diff shown in PR body |

### Shared Review (skip / no sync)

| Surface | Ownership | Sync Model | Where to Customize |
|---------|-----------|------------|--------------------|
| `template-base.json` | shared_review | skip | No sync — reviewed manually when template version changes |
| `router/**` | shared_review | skip | No sync — reviewed manually when contract changes |

### Private Owned (never synced)

| Surface | Ownership | Sync Model | Where to Customize |
|---------|-----------|------------|--------------------|
| `projects/registry.shared.json` | private_owned | never synced | Your routing config — safe from all syncs |
| `private.meta.json` | private_owned | never synced | Your private metadata — safe from all syncs |
| `Knowledge/local/**` | private_owned | never synced | Your private content — safe from all syncs |

### Local Only (never committed)

| Surface | Ownership | Sync Model | Where to Customize |
|---------|-----------|------------|--------------------|
| `.claude/settings.local.json` | local_only | never synced | Bootstrapped from `.claude/settings.example.json` |
| `.env.local` | local_only | never synced | Machine-local secrets — never committed |
| `projects/registry.local.json` | local_only | never synced | Machine-local registry overlay — never committed |
| `data/**` | local_only | never synced | Runtime pipeline data — never committed |
| `state/**` | local_only | never synced | Runtime pipeline state — never committed |

## Key Principles

1. **Template updates arrive automatically** for template_owned and full-overwrite surfaces.
2. **Private rules live in overlays** (`Knowledge/local/AI/`), not in synced AI files.
3. **Skill directories are extensible** — local additions survive, but template skills update.
4. **Local extras do not need parity** — a custom `.claude/skills/my-tool/` does not need mirrors in `.codex/` or `.agents/`.
5. **The contract registry is normative** — run `check_customization_contracts.py` to validate.
6. **Upgrade-contract changes need release notes** — changes to `repo-governance/**` and `.github/workflows/template-upstream-sync.yml` must land with a `CHANGELOG.md` update.

## Validators

| Script | What it checks |
|--------|----------------|
| `check_managed_blocks.py` | All managed block markers exist in matched begin/end pairs |
| `check_customization_contracts.py` | Registry ↔ manifest consistency, overlay safety, conflict marker checks, `*.rej` checks, and release-note policy |
| `check_agent_surface_parity.py` | Required template skills present in all three surfaces |
| `check_repo_ownership.py` | All files classified, no sync violations |
| `check_sync_manifest_alignment.py` | Workflow sync paths are covered by both the manifest and the contract registry |
