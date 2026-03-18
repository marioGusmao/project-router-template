# Project Router Template

English | [Português (Portugal)](README.pt-PT.md)

<!-- repository-mode:begin -->
This repository is a private operational Project Router repo for VoiceNotes derived from the shared `project-router-template` upstream.

The upstream relationship is tracked in `private.meta.json` and `template-base.json`, and updates from `marioGusmao/project-router-template` should arrive through reviewed `chore/template-sync` pull requests rather than manual copy-paste.
<!-- repository-mode:end -->

<!-- template-onboarding:begin -->
## Private Repo First Steps

If this is a private-derived operational copy:

1. Run `python3 scripts/bootstrap_local.py`.
2. Run `python3 scripts/project_router.py context`.
3. Review `Knowledge/local/Roadmap.md` and adapt it to your project.
<!-- template-onboarding:end -->

## Repository Model

- `project-router-template`: public GitHub template repo, neutral and shareable
- `project-router-private`: private daily repo derived from the template, free to keep branded routing packs and personal workflow wording

The template is the shared upstream. The private repo is the real operational home.

## Core Goals

- Keep one immutable local JSON copy of every captured note.
- Normalize notes into Markdown with stable frontmatter.
- Classify conservatively.
- Compile project-ready briefs before any downstream write.
- Never auto-dispatch.
- Require explicit approval for exact `source_note_id` values.
- Keep ambiguous and not-yet-placeable notes in review queues.
- Preserve thread relationships across follow-up notes.

## Repository Layout

```text
data/
  raw/
    voicenotes/
    project_router/
    filesystem/
  normalized/
    voicenotes/
    project_router/
    filesystem/
  compiled/
    voicenotes/
    project_router/
    filesystem/
  review/
    voicenotes/
    project_router/
    filesystem/
  dispatched/
  processed/
Knowledge/
  ADR/
  Templates/
  local/
  runbooks/plans/
router/
  inbox/
  outbox/
  conformance/
  archive/
projects/
  registry.shared.json
  registry.example.json
  registry.local.json
repo-governance/
  ownership.manifest.json
scripts/
  apply_managed_block_sync.py
  bootstrap_private_repo.py
  bootstrap_local.py
  check_adr_related_links.py
  check_agent_surface_parity.py
  check_customization_contracts.py
  check_knowledge_structure.py
  check_managed_blocks.py
  check_repo_ownership.py
  check_sync_manifest_alignment.py
  knowledge_local_scaffold.py
  migrate_add_contract_block.py
  project_router.py
  project_router_client.py
  refresh_knowledge_local.py
  sync_ai_files.py
src/
  project_router/
    cli.py
    sync_client.py
.agents/skills/
.codex/skills/
.claude/skills/
.github/workflows/
version.txt
CHANGELOG.md
template.meta.json
template-base.json
private.meta.json
```

## Knowledge

The `Knowledge/` directory provides curated onboarding docs, architectural decision records, and a glossary. Read `Knowledge/ContextPack.md` for a routing guide to the codebase, or run `python3 scripts/project_router.py context` for a project briefing that reflects current repo state including demo indicators and pending migrations.

## Local Configuration

If you created a derived private repository, promote it first:

```bash
python3 scripts/bootstrap_private_repo.py
```

The promotion bootstrap:

- switches `README.md`, `README.pt-PT.md`, `AGENTS.md`, and `CLAUDE.md` to private-repo posture using managed blocks
- creates `private.meta.json` for private-repo metadata
- creates `template-base.json` so `.github/workflows/template-upstream-sync.yml` can resolve the upstream template
- keeps the runtime safety rules and pipeline commands unchanged

See [docs/private-derived-bootstrap.md](docs/private-derived-bootstrap.md) for the full promotion contract.

Run the bootstrap on a new machine:

```bash
python3 scripts/bootstrap_local.py
```

Bootstrap behavior:

- creates `.env.local` from `.env.example` only if missing
- creates `projects/registry.local.json` only if missing, unless `--force`
- reads `projects/registry.shared.json` for the project keys to configure
- respects `VN_ROUTER_ROOT_<PROJECT_KEY>` environment variables before prompting
- allows blank input so a project can stay inactive on that machine

Keep these files out of Git:

- `.env.local`
- `projects/registry.local.json`
- `state/`
- `data/`

## Registry Overlay

The routing registry is split into three files:

- `projects/registry.shared.json`: committed metadata, keywords, thresholds, and note types
- `projects/registry.local.json`: gitignored local `router_root_path` values and local-only overrides
- `projects/registry.example.json`: starter template for the local overlay

The starter ships neutral example projects such as `home_renovation` and `weekly_meal_prep`. Real project-router roots still live only in `projects/registry.local.json`.

Classification can run from the shared registry alone. Real dispatch requires the local overlay.

## Parser Language Profiles

Parsing and extraction language support is configured separately from downstream project language:

- `src/project_router/parser_language_profiles.json`: committed parser profiles, active languages, stopwords, and heuristic trigger terms
- `projects/registry.shared.json -> projects.<key>.language`: downstream/output language for that project
- `router/router-contract.json -> default_language`: downstream packet default for a specific router root

This separation matters: parser profiles decide how normalize/triage/compile interpret multilingual notes, while project/contract language still controls downstream packet defaults.

## Local Project-Router Contract

Each participating repository should expose:

- `router/router-contract.json`
- `router/inbox/`
- `router/outbox/`
- `router/conformance/`

The central router reads downstream `outbox/` folders in read-only mode via `scan-outboxes`. It never moves or rewrites files in downstream repositories during scan or review.

Downstream repositories are read-only by default from this hub. Prefer the downstream repository's `project-router` `inbox/` and `outbox/` surfaces for cross-project communication, and only switch to direct edits when the user explicitly asks for changes in that target repository.

## Workflow

```bash
python3 scripts/bootstrap_local.py
python3 scripts/project_router_client.py sync --output-dir ./data/raw/voicenotes
python3 scripts/project_router.py normalize --source voicenotes
python3 scripts/project_router.py triage --source voicenotes
python3 scripts/project_router.py compile --source voicenotes
python3 scripts/project_router.py review --source voicenotes
python3 scripts/project_router.py dispatch --dry-run
python3 scripts/project_router.py discover
python3 scripts/project_router.py scan-outboxes
python3 scripts/project_router.py doctor --project home_renovation
python3 scripts/project_router.py init-router-root --project home_renovation --router-root /path/to/router
python3 scripts/project_router.py adopt-router-root --project home_renovation
```

Real dispatch always requires note-specific approval:

```bash
python3 scripts/project_router.py dispatch --confirm-user-approval --note-id vn_123 --note-id vn_456
```

Dispatch behavior is intentionally fail-closed:

- missing `projects/registry.local.json` blocks dispatch
- missing `router_root_path` or derived inbox for a candidate project skips that candidate with an explicit reason
- invalid local derived inbox path blocks that candidate
- missing or stale compiled packages block that candidate
- approval must name the exact `source_note_id` values being dispatched

Outbox scanning is intentionally read-only:

- `scan-outboxes` never writes into downstream repositories
- invalid packets stay in the downstream `router/outbox/`
- parse errors are recorded locally under `data/review/project_router/parse_errors/`
- ingest status is tracked locally in `state/project_router/outbox_scan_state.json`

## Agent Surfaces

This starter uses a three-layer agent contract:

- Reference: `.agents/skills/`
- Codex: `AGENTS.md` + `.codex/skills/`
- Claude: `CLAUDE.md` + `.claude/skills/`

The intended implementation model is:

- `.agents/skills/` is the canonical neutral reference layer for shared workflow and safety rules
- `.codex/skills/` and `.claude/skills/` adapt that reference layer to each tool surface
- platform-specific notes are allowed, but the operational contract must stay aligned across all surfaces

The parity contract is executable:

```bash
python3 scripts/check_agent_surface_parity.py
python3 scripts/check_agent_surface_parity.py --pre-publish
```

The validator checks:

- required skill IDs exist on all three surfaces
- all surfaces document the same critical safety rules
- all surfaces use `python3 scripts/project_router_client.py`
- shared docs do not reference internal `.codex/...` client paths

## Ownership and Sync Governance

The template/private sync boundary is defined in `repo-governance/ownership.manifest.json`.

Ownership classes:

- `template_owned`: safe for automatic template updates
- `shared_review`: shared files that should update only through reviewable PRs
- `private_owned`: reserved for private-repo customization
- `local_only`: never commit or sync

Validate ownership rules with:

```bash
python3 scripts/check_repo_ownership.py
```

In a private repo, template sync must never touch `private_owned` or `local_only` paths.

## Versioning

The template is versioned with semantic releases:

- `version.txt`
- `CHANGELOG.md`
- `template.meta.json`
- `.github/workflows/template-release.yml`

Release automation is driven by Conventional Commits and `release-please`.

The release workflow requires a `RELEASE_PLEASE_TOKEN` secret with `contents: write` and `pull-requests: write`.
Do not rely on the default `GITHUB_TOKEN` for release PR creation, because PRs opened by that token do not trigger the required `template-ci` pull request checks.
Under the default protected `main` policy, release PRs still require manual approval and merge after `template-ci` passes.

## Template Upstream Sync

The template also ships `.github/workflows/template-upstream-sync.yml` for derived repos.

The sync contract is:

- schedule weekly and allow manual runs
- compare the current repo against the latest stable template release
- open or update one draft PR on branch `chore/template-sync`
- never auto-merge
- respect `repo-governance/ownership.manifest.json`

The workflow expects:

- repository variable `TEMPLATE_UPSTREAM_REPO` or a populated `template-base.json`
- optional secret `TEMPLATE_UPSTREAM_TOKEN` when the template repo is private

For a fresh derived repository, the recommended setup is:

```bash
python3 scripts/bootstrap_private_repo.py
python3 scripts/bootstrap_local.py
python3 scripts/refresh_knowledge_local.py
```

## Safety Guarantees

- Never delete or overwrite canonical raw JSON.
- Never auto-dispatch.
- Treat confirmation as note-specific by `source_note_id`.
- Never dispatch a normalized note directly.
- Compiled packages must be fresh before dispatch.
- Canonical metadata lives in `data/normalized/`; review copies are queue views only.
- Re-running the pipeline must stay idempotent.

## Publish Checklist

Before publishing the template:

1. Run `python3 scripts/check_agent_surface_parity.py --pre-publish`
2. Run `python3 scripts/check_repo_ownership.py`
3. Run `python3 scripts/check_sync_manifest_alignment.py`
4. Run `python3 scripts/check_knowledge_structure.py --strict`
5. Run `python3 scripts/check_adr_related_links.py --mode block`
6. Run `python3 scripts/check_managed_blocks.py`
7. Run `python3 scripts/check_customization_contracts.py`
8. Confirm `projects/registry.shared.json` contains only neutral examples
9. Confirm `.env.local`, `projects/registry.local.json`, `data/`, and `state/` are not tracked
10. Confirm `.agents/skills/`, `.codex/skills/`, and `.claude/skills/` still describe the same workflow contract
11. Enable GitHub Template Repository on the upstream repo
12. Enable branch protection and required checks for tests, parity, ownership, and release automation
13. Confirm maintainers manually approve and merge release PRs when `main` requires reviews

## Contributing

External contributors can use the public issue templates and pull request template included in this repository.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the expected workflow, validation commands, and the list of local-only artifacts that must never be committed.
