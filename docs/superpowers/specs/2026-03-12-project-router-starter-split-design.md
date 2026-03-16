# Project Router Split: Template + Private + Parity

> Historical note: this design document predates the 2026-03-13 source-aware reset. References here to `inbox_path`, `VN_INBOX_*`, and flat `data/` storage describe the earlier transition plan and are superseded by the current `router_root_path` plus source-aware layout implemented in the repository.

## Context

Project Router for VoiceNotes is used by 3 people, each with their own projects and downstream destinations. The current repo mixes shared workflow logic with personal project config. This plan splits it into a reusable GitHub template and a private daily repo, with executable parity between Codex and Claude surfaces, automated versioning, and upstream sync.

The branch `codex/harden-system-review` already implements ~50% of the foundation: shared/local registry overlay, optional `inbox_path`, neutral client wrapper, `.claude/skills/` mirror, and GitHub sharing documentation.

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Publishing model | GitHub template repo | Users create from template, not fork |
| Alias system | **None** | Private repo keeps its own keys. No migration needed. |
| Registry examples | Realistic but neutral names | Not `my_project`, not branded. E.g. `home_renovation` |
| Bootstrap scope | Full (files + env vars + interactive) | Supports headless and hands-on setup |
| Client canonical path | `src/project_router/sync_client.py` | Neutral, alongside existing CLI module |
| Parity validator | Executable contract, not convention | All 3 users use both Codex and Claude |
| Scope | Single integrated plan | Template, private, parity, semver, sync workflows |
| Template visibility | **Private** | Shared by invite among 3 users. Pre-publish sanitization still applies for hygiene. |
| Registry example language | **English-only** | Template is universal. Bilingual stopwords stay in code; examples stay in English. |

## Repository Model

### project-router-template (private GitHub template repo)

Contains only shared, reusable assets:

- `src/`, `scripts/`, `tests/`
- `CLAUDE.md`, `AGENTS.md`, `README.md`
- `.codex/skills/`, `.claude/skills/`
- `projects/registry.shared.json` (neutral example projects, no `inbox_path`)
- `projects/registry.example.json` (local overlay template)
- `.env.example`
- `.github/workflows/` (release + upstream sync)
- `version.txt`, `CHANGELOG.md`, `template.meta.json`
- `scripts/bootstrap_local.py`, `scripts/check_agent_surface_parity.py`

Works out-of-the-box for: `bootstrap → status → normalize → triage → compile → review → discover`. Dispatch requires local config.

### project-router-private (private, created from current state)

Contains personal operational layer:

- Real private project keys in its own `registry.shared.json`
- Real skill wording and personal workflow rules
- Real naming conventions
- `data/`, `state/` (gitignored, machine-local)
- `.env.local`, `projects/registry.local.json` (gitignored, machine-local)

### Local-only (never in Git, either repo)

- `.env.local` (API keys)
- `projects/registry.local.json` (absolute inbox paths)
- `state/` (sync checkpoints, decisions, discoveries)
- `data/` (all note artifacts)

## Component Designs

### 1. Registry and Dispatch

**No changes to registry overlay model** — already implemented:
- `projects/registry.shared.json` (committed): metadata, keywords, thresholds, note_types
- `projects/registry.local.json` (gitignored): `inbox_path` + local overrides
- `projects/registry.example.json` (committed): template for local overlay

**Dispatch behavior change:**

Current: `load_registry(require_local=True)` validates ALL projects have valid `inbox_path` at load time.
New: registry loads without validating paths → dispatch validates each candidate individually inside the dispatch loop.

Implementation detail:
- `load_registry()` loads shared + local, merges, returns all projects. No path validation at load time.
- `dispatch_command()` iterates candidates. For each note being dispatched:
  - If target project has no `inbox_path` → **skip** that note, add `{"note_id": "...", "skip_reason": "no local inbox_path for project 'X'"}` to dispatch summary
  - If target project has invalid/non-absolute `inbox_path` → **fail** that note (as today)
  - If valid → **dispatch** normally
- Missing `registry.local.json` entirely → **fail** for dispatch (as today, at load time)
- Missing approval or stale compiled → **fail** per note (as today)
- Dispatch summary output includes both dispatched and skipped notes with reasons

**Existing tests that will change behavior:**
- `test_shared_registry_requires_local_inbox_override_for_dispatch` → currently expects `SystemExit` when a project lacks `inbox_path`. Must be updated to expect skip-with-reason instead.

**Files to modify:** `src/project_router/cli.py` (dispatch validation logic, dispatch summary output)

### 2. Client Migration

Move canonical VoiceNotes API client from `.codex/skills/project-router-direct-sync/scripts/project_router_client.py` to `src/project_router/sync_client.py`.

- `scripts/project_router_client.py` becomes thin wrapper importing from `src.project_router.sync_client`
- `.codex/skills/.../scripts/project_router_client.py` is removed
- Both skill surfaces reference `python3 scripts/project_router_client.py`
- Tests update `importlib.util` path to new location

**Path calculation change:** The current client calculates `REPO_ROOT = Path(__file__).resolve().parents[4]` (because it lives 4 levels deep under `.codex/skills/.../scripts/`). After moving to `src/project_router/sync_client.py`, this must become `parents[2]`.

**Test helper change:** `load_sync_module()` in `tests/test_project_router.py` currently hardcodes the `.codex/skills/.../scripts/project_router_client.py` path via `importlib.util`. Must update to load from `src/project_router/sync_client.py`.

**Wrapper implementation:** `scripts/project_router_client.py` (~10 lines) adds repo root to `sys.path` and delegates to `src.project_router.sync_client.main()`. Same pattern as `scripts/project_router.py`.

**Files to create:** `src/project_router/sync_client.py`
**Files to modify:** `scripts/project_router_client.py`, `.codex/skills/project-router-direct-sync/SKILL.md`, `.claude/skills/project-router-direct-sync/SKILL.md`, `tests/test_project_router.py` (wrapper + `load_sync_module()` path)
**Files to remove:** `.codex/skills/project-router-direct-sync/scripts/project_router_client.py`

### 3. Bootstrap (`scripts/bootstrap_local.py`)

Contract:
- Non-destructive by default
- Creates `.env.local` from `.env.example` if missing
- Creates `projects/registry.local.json` from `registry.example.json` if missing
- Does not overwrite existing files without `--force`
- Reads `registry.shared.json` to discover project keys to configure

Precedence for `inbox_path` per project:
1. Existing `registry.local.json` value
2. Environment variable `VN_INBOX_<PROJECT_KEY>` (uppercased)
3. Interactive prompt (blank = project inactive on this machine)

Behavior:
- Unknown `VN_INBOX_*` env vars → warning, not failure
- Partial activation supported (some projects active, others inactive)
- Final output: prints next commands (`status`, `sync`)

Implementation: stdlib only, `argparse` for `--force`. ~150-200 lines.

**Files to create:** `scripts/bootstrap_local.py`

### 4. Parity Validator (`scripts/check_agent_surface_parity.py`)

**Default mode** (`python3 scripts/check_agent_surface_parity.py`):
- For each skill in `.codex/skills/`, verify corresponding exists in `.claude/skills/` (and vice-versa)
- Verify `AGENTS.md` and `CLAUDE.md` both contain core safety strings (configurable list)
- Verify command references in both surfaces use `scripts/project_router_client.py` (not `.codex/...` paths)
- Verify both surfaces document the same pipeline commands (`sync`, `normalize`, `triage`, `compile`, `review`, `decide`, `dispatch`, `discover`, `status`)
- Verify both surfaces define the same dispatch safety rules (never auto-dispatch, require explicit approval, compiled must be fresh)

**Required parity (must match):**
- Same skill IDs exist on both sides
- Core safety strings present on both sides (list defined in validator, e.g. "never auto-dispatch", "never delete canonical raw", "compiled packages must be fresh")
- Same pipeline commands referenced
- Neutral entrypoint `scripts/project_router_client.py` used (no `.codex/` or `.claude/` internal paths)

**Allowed divergence:**
- Wording and phrasing differences
- Platform-specific notes (e.g. "OpenClaw" in Codex, "Claude Code" in Claude)
- Different examples or different level of detail in examples
- One surface may have more documentation than the other

**Pre-publish mode** (`--pre-publish`):
- All default checks plus:
- No `inbox_path` with real absolute paths in `registry.shared.json`
- No secret patterns in committed files (API keys, tokens)
- Exit code 0 if all pass, non-zero with details otherwise

Implementation: stdlib only. ~100-150 lines.

**Files to create:** `scripts/check_agent_surface_parity.py`

### 5. Versioning (`template` repo only)

**Semantic versioning** driven by Conventional Commits:

- `version.txt` file at repo root (single line, e.g. `0.1.0`)
- `CHANGELOG.md` auto-generated from commit messages
- `template.meta.json`: machine-readable metadata for derived repos

```json
{
  "template_name": "project-router-triage-hub",
  "version": "0.1.0",
  "min_python": "3.10"
}
```

**Release automation:** GitHub Actions workflow (`.github/workflows/template-release.yml`):
- Triggered by push to `main`
- Uses `release-please` (or equivalent GitHub-native action)
- Creates GitHub Release with changelog
- Tags with semver

**Files to create:** `version.txt`, `CHANGELOG.md`, `template.meta.json`, `.github/workflows/template-release.yml`

### 6. Upstream Sync Workflow

> **Note (2026-03-16):** This section is partially outdated. The implementation stores the base template version in `template-base.json` (not `template.meta.json`), and resolves the upstream via GitHub API rather than requiring a configured `upstream` remote. Kept as historical design record; refer to the actual workflow file for current behavior.

**Inherited workflow** (`.github/workflows/template-upstream-sync.yml`):
- Included in template, inherited by derived repos
- Runs on schedule (e.g. weekly) and manual trigger
- Compares derived repo's template version against latest stable release of template
- Opens PR as **draft** when update available
- **Never auto-merges** — always requires human review
- Tracks **latest stable release**, not `main` HEAD

The derived repo stores its base template version in `template.meta.json` (the `version` field reflects what release it was created from or last synced to).

**Sync scope:** The workflow syncs shared infrastructure files (`src/`, `scripts/`, `.github/workflows/`, `CLAUDE.md`, `AGENTS.md`, `README.md`). It does NOT sync user-customized content (`projects/registry.shared.json` project definitions, skill wording customizations). Conflicts in synced files require manual resolution.

**First sync:** The first upstream sync on a derived repo should be triggered manually (not scheduled). The user reviews the diff before merging. Subsequent syncs can run on schedule.

**Prerequisites:**
- Derived repo must configure an `upstream` remote: `git remote add upstream <template-repo-url>`
- Sync workflow needs the default `GITHUB_TOKEN` (sufficient for opening PRs in the same repo)
- If the template is private, derived repos need read access to the template (via GitHub collaborator or org membership)

**Files to create:** `.github/workflows/template-upstream-sync.yml`

### 7. Neutralize Template Content

Replace branded project examples in `registry.shared.json` with realistic neutral ones:
- `home_renovation` (language: en, note_type: project-idea, keywords: renovation, contractor, etc.)
- `weekly_meal_prep` (language: en, note_type: daily-ops, keywords: groceries, recipe, etc.)

Update all documentation to reference neutral examples. Remove any personal/branded wording from starter skill surfaces.

**Files to modify:** `projects/registry.shared.json`, `README.md`, skill SKILL.md files as needed

### 8. Documentation and Governance

**README.md** updates:
- This repo is the starter upstream template
- Real work happens in a derived private repo
- What belongs in upstream vs private
- Multi-PC setup via bootstrap
- How upstream sync works

**AGENTS.md** and **CLAUDE.md** updates:
- Reference neutral client path
- Reference bootstrap as first setup step (before `status` or `sync`)
- Session defaults reference `scripts/project_router_client.py`
- Add `bootstrap_local.py` to Commands section

**Promotion runbook** (in README or separate doc):
- Improvement discovered in private repo
- Generalize the change
- Promote to template via PR
- New release created automatically
- Sync workflow opens PR back to private repos

## Implementation Phases

### Phase 1: Freeze and Duplicate

1. Freeze current working directory as reference (no further commits)
2. Create `project-router-template-work` — copy of current state for neutralization
3. Create `project-router-private-work` — copy of current state preserving everything real

### Phase 2: Close the Private Repo First

In `project-router-private-work`:
1. Preserve all current branded content (skills, naming, project packs, rules)
2. Add `template.meta.json` with initial version (e.g. `0.1.0`)
3. Ensure bootstrap works with existing local config
4. Minimal adjustments only — this is preservation, not transformation

### Phase 3: Neutralize the Template

In `project-router-template-work`:
1. Replace branded project keys with neutral examples in `registry.shared.json`
2. Move client implementation to `src/project_router/sync_client.py`
3. Update wrapper in `scripts/project_router_client.py`
4. Create `scripts/bootstrap_local.py`
5. Create `scripts/check_agent_surface_parity.py`
6. Add version metadata (`version.txt`, `CHANGELOG.md`, `template.meta.json`)
7. Add GitHub Actions workflows (release + upstream sync)
8. Update documentation (README, AGENTS, CLAUDE)
9. Neutralize skill wording in both surfaces

### Phase 4: Close Governance

1. Run parity validator — fix any drift
2. Run pre-publish sanitization — fix any leaks
3. Verify consistency between README, AGENTS.md, CLAUDE.md, and skill surfaces
4. Define promotion runbook: private improvement → generalization → template PR → release → sync PR back

### Phase 5: Publish

1. Push `project-router-template` to GitHub
2. Enable: Template Repository, release automation, parity checks
3. Push `project-router-private` to GitHub (private)
4. Configure `origin` and `upstream` remotes in private repo
5. Configure secrets if template stays private
6. Run bootstrap on each machine
7. Validate full pipeline on private repo with real data

## Edge Cases

- **Empty shared registry:** User deletes all example projects from `registry.shared.json`. This is valid — all notes route to `pending_project`. Triage, review, and discover all continue to work. Status shows "0 projects configured".
- **No bootstrap run:** User clones template and runs `status` without bootstrap. CLI should fail gracefully with a message pointing to `python3 scripts/bootstrap_local.py`.
- **First upstream sync divergence:** Private repo will have customizations by the time sync runs. First sync should be manual. Sync PRs are drafts. Conflicts require manual resolution.

## Test Plan

### Registry and Dispatch
- Shared-only classification works (no local registry)
- Dispatch skips notes whose project lacks local `inbox_path`, with explicit skip reason
- Valid configured candidates still dispatch successfully
- Invalid local path still blocks that candidate (fail-closed)
- Batch dispatch with mix of configured/unconfigured projects
- Empty shared registry: all notes route to `pending_project`
- **Existing test changes:** `test_shared_registry_requires_local_inbox_override_for_dispatch` must be updated to expect skip-with-reason, not `SystemExit`

### Bootstrap
- Creates `.env.local` from template when missing
- Creates `registry.local.json` from example when missing
- Does not overwrite existing files without `--force`
- Env vars populate `inbox_path` correctly
- Blank interactive input = project inactive
- Unknown `VN_INBOX_*` vars produce warning, not failure
- Precedence: existing file > env vars > interactive

### Neutral Client
- `python3 scripts/project_router_client.py --help` works without `.codex/` dependency
- `python3 scripts/project_router_client.py sync --output-dir ./data/raw` works from `src/` module

### Parity Validator
- Passes when both surfaces are aligned
- Fails on missing skill in either surface
- Fails on missing safety clause
- Fails on `.codex/...` command reference in shared docs
- Pre-publish: fails if `registry.shared.json` contains real `inbox_path`
- Pre-publish: fails if committed files contain secret patterns

### Versioning and Sync
- Release workflow creates GitHub Release with correct semver tag
- `template.meta.json` version matches `version.txt` file
- Upstream sync workflow detects new release and opens PR
- Sync workflow does not auto-merge

### Smoke Tests
- Clean clone of template → bootstrap → status → parity validator → help commands
- Private repo created from template → branded layer preserved → local bootstrap → full pipeline
- Two different machines with different downstream paths via bootstrap

## Assumptions

- The current branded/project-specific configuration is preserved by copying into the private repo. Nothing is lost.
- The template stays neutral and reusable. Personal operational layer does not live there.
- No alias system. Each repo defines its own project keys independently.
- Candidate-level dispatch skipping is acceptable as long as skip reasons are explicit.
- The current repo is only deleted after both new repos are validated by the user.
- Semver is driven by Conventional Commits via release-please or equivalent.
- Upstream sync tracks stable releases, never `main` HEAD.
