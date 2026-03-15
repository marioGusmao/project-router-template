# ADR-006: Template Upgrade Process and Customization Contract

**Status:** accepted

**Date:** 2026-03-15

## Context

The project-router-template is a shared upstream from which users create private derived repositories. Updates propagate via a GitHub Actions workflow (`template-upstream-sync.yml`) that creates draft PRs. The core challenge: how to guarantee that template updates never destroy user customizations.

Prior to this decision, the sync workflow used a single `rsync -a --delete` pass for all paths. This worked for code (`src/`, `scripts/`) but was unsafe for files that contain both template-authored and user-authored content (CLAUDE.md, AGENTS.md, README.md, skill directories).

## Decision

### Customization model taxonomy

Each repository surface is assigned a `customization_model` that determines its sync behavior:

| Model | Behavior | Used for |
|-------|----------|----------|
| `overwrite` | `rsync -a --delete` — full replacement | `src/`, `scripts/`, `tests/`, `docs/`, `Knowledge/ADR/`, `Knowledge/Templates/` |
| `full_overwrite_preserve_contract` | Full overwrite, then restore `customization-contract` managed block from local backup | `CLAUDE.md`, `AGENTS.md` |
| `managed_blocks` | Replace content inside `begin`/`end` markers; preserve content outside | `README.md`, `README.pt-PT.md` |
| `extensible_directory` | `rsync -a` without `--delete` — template skills update, local additions preserved | `.claude/skills/`, `.codex/skills/`, `.agents/` |
| `diff_only` | No overwrite — generate diff in PR body for manual review | `.gitignore`, `CONTRIBUTING.md` |
| `skip` | Never synced | `projects/registry.shared.json`, `.claude/settings.local.json`, `Knowledge/local/` |

### AI file ownership

CLAUDE.md and AGENTS.md are template-owned. The sync overwrites the entire file, then restores the `customization-contract` managed block which contains:
- `@import` references (Claude) pointing to `Knowledge/local/AI/claude.md`
- Prose instructions (Codex) referencing `Knowledge/local/AI/codex.md`

All private operating rules live in `Knowledge/local/AI/`, which is `private_owned` and never synced.

### Skills directory model

Skill directories use the `extensible_directory` model. Template skills update via rsync without `--delete`, so local skill additions survive. Local extras do not need parity mirroring across the three surfaces (`.agents/`, `.codex/skills/`, `.claude/skills/`). The parity check validates only required template skills.

### Contract registry

`repo-governance/customization-contracts.json` is the normative source of truth. It declares ownership, sync_policy, customization_model, private_overlay, bootstrap_source, agent_load_rule, migration_policy, and validator_hooks for each surface. `check_customization_contracts.py` validates the registry against the ownership manifest and the repository state.

### Sync workflow (5 passes)

1. **Pass 0 — Migrate:** Insert missing `customization-contract` markers (for old derived repos)
2. **Pass 1 — Overwrite:** Full replacement of `template_owned` paths and AI files
3. **Pass 2 — Restore:** Restore `customization-contract` blocks in AI files from local backup
4. **Pass 3 — Managed blocks:** Update content inside markers in READMEs
5. **Pass 4 — Extensible:** Sync skill directories without `--delete`
6. **Pass 5 — Diff-only:** Generate diffs for manual review

## Consequences

### Easier

- Template updates to Safety Rules, Commands, Architecture, etc. arrive automatically in derived repos.
- Users never need to manually merge CLAUDE.md or AGENTS.md — the contract block is the only user-facing seam.
- Local skill additions and private operating rules survive all syncs.
- The contract registry provides a single source of truth for how every file is managed.

### Harder

- Adding a new file to the repo requires declaring it in `customization-contracts.json`.
- The 5-pass workflow is more complex than a single rsync loop.
- Old derived repos need the migration script before the first sync with the new workflow.

### Trade-offs

- Upstream skill renames/deletes leave orphaned local copies (acceptable for v1; v2 can detect and warn).
- `.gitignore` and `CONTRIBUTING.md` are diff-only — manual review burden, but these change rarely.
- Full overwrite of AI files means any accidental edits by the user are lost — by design, since the overlay model provides the correct escape hatch.

## Related

- ADR-002: Template/private split model
- ADR-003: Knowledge foundation structure

---

> **Numbering convention:** Template ADRs use numbers 000--099. Your project-specific ADRs go in `Knowledge/local/ADR/` starting at 100.
