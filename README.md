# Project Router Template

English | [Português (Portugal)](README.pt-PT.md)

Project Router Template is the shared starter upstream for a VoiceNotes triage workflow that works in both Codex and Claude Code.

The starter keeps the common pipeline, safety rules, governance tooling, and neutral routing examples in Git. Each user keeps local secrets, local inbox paths, and live note artifacts outside Git. A private daily repo can then add branded projects, personal skills, and personal operational rules on top of this base.

## New To GitHub Templates

A GitHub template repository is a starter project you can copy into your own repository.

For this project, the template is useful because it gives you:

- the VoiceNotes workflow and scripts
- the safety rules and validation checks
- neutral example routing
- a clean public starting point without your private notes, tokens, or local paths

Use a template when you want your own copy of the project to customize safely.

In this case, the recommended setup is:

1. Open this repository on GitHub.
2. Click `Use this template`.
3. Choose `Create a new repository`.
4. Create your own repository from it.
5. Set your new repository to `Private` unless you explicitly want to share your derived version.
6. Clone your new repository to your machine.
7. Run `python3 scripts/bootstrap_local.py` in your copy.

Important differences from a fork:

- a template gives you your own clean starting repository
- your repository can stay private even if this template is public
- your local `.env.local`, `data/`, and `state/` stay only on your machine

If you only want to use the workflow, create a repository from the template. You do not need to contribute back to this upstream repository.

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
  normalized/
  compiled/
  review/
    ambiguous/
    needs_review/
    pending_project/
  dispatched/
  processed/
projects/
  registry.shared.json
  registry.example.json
  registry.local.json
repo-governance/
  ownership.manifest.json
scripts/
  bootstrap_local.py
  check_agent_surface_parity.py
  check_repo_ownership.py
  voice_notes.py
  voicenotes_client.py
src/
  voice_notes/
    cli.py
    sync_client.py
.agents/skills/
.codex/skills/
.claude/skills/
.github/workflows/
VERSION
CHANGELOG.md
template.meta.json
```

## Local Configuration

Run the bootstrap on a new machine:

```bash
python3 scripts/bootstrap_local.py
```

Bootstrap behavior:

- creates `.env.local` from `.env.example` only if missing
- creates `projects/registry.local.json` only if missing, unless `--force`
- reads `projects/registry.shared.json` for the project keys to configure
- respects `VN_INBOX_<PROJECT_KEY>` environment variables before prompting
- allows blank input so a project can stay inactive on that machine

Keep these files out of Git:

- `.env.local`
- `projects/registry.local.json`
- `state/`
- `data/`

## Registry Overlay

The routing registry is split into three files:

- `projects/registry.shared.json`: committed metadata, keywords, thresholds, and note types
- `projects/registry.local.json`: gitignored local inbox paths and local-only overrides
- `projects/registry.example.json`: starter template for the local overlay

The starter ships neutral example projects such as `home_renovation` and `weekly_meal_prep`. Real inbox paths still live only in `projects/registry.local.json`.

Classification can run from the shared registry alone. Real dispatch requires the local overlay.

## Workflow

```bash
python3 scripts/bootstrap_local.py
python3 scripts/voicenotes_client.py sync --output-dir ./data/raw
python3 scripts/voice_notes.py normalize
python3 scripts/voice_notes.py triage
python3 scripts/voice_notes.py compile
python3 scripts/voice_notes.py review
python3 scripts/voice_notes.py dispatch --dry-run
python3 scripts/voice_notes.py discover
```

Real dispatch always requires note-specific approval:

```bash
python3 scripts/voice_notes.py dispatch --confirm-user-approval --note-id vn_123 --note-id vn_456
```

Dispatch behavior is intentionally fail-closed:

- missing `projects/registry.local.json` blocks dispatch
- missing `inbox_path` for a candidate project skips that candidate with an explicit reason
- invalid local `inbox_path` blocks that candidate
- missing or stale compiled packages block that candidate
- approval must name the exact `source_note_id` values being dispatched

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
- all surfaces use `python3 scripts/voicenotes_client.py`
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

- `VERSION`
- `CHANGELOG.md`
- `template.meta.json`
- `.github/workflows/template-release.yml`

Release automation is driven by Conventional Commits and `release-please`.

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
3. Confirm `projects/registry.shared.json` contains only neutral examples
4. Confirm `.env.local`, `projects/registry.local.json`, `data/`, and `state/` are not tracked
5. Confirm `.agents/skills/`, `.codex/skills/`, and `.claude/skills/` still describe the same workflow contract
6. Enable GitHub Template Repository on the upstream repo
7. Enable branch protection and required checks for tests, parity, ownership, and release automation

## Contributing

External contributors can use the public issue templates and pull request template included in this repository.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the expected workflow, validation commands, and the list of local-only artifacts that must never be committed.
