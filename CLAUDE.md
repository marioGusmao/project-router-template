# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Project Router Template — intake and classification layer for VoiceNotes captures before routing to downstream project inboxes. Pure Python, zero external package dependencies, file-based storage.

This repository is designed to be shareable on GitHub:

- committed files contain the common workflow, routing rules, and agent guidance
- local files contain secrets, machine-specific router roots, and runtime artifacts
- Codex and Claude should follow the same operational contract even when their project surfaces differ

<!-- repository-mode:begin -->
## Repository Mode

- Current role: private derived repository.
- This copy is the operational home for private routing packs, branded wording, and day-to-day note handling.
- Keep the upstream relationship to `project-router-template` in `private.meta.json` and `template-base.json`.
- Expect shared updates from `marioGusmao/project-router-template` to arrive via reviewed `chore/template-sync` pull requests.
<!-- repository-mode:end -->

## Commands

```bash
# Promote a fresh derived copy into a private operational repository
python3 scripts/bootstrap_private_repo.py

# Bootstrap local-only config
python3 scripts/bootstrap_local.py

# Preview or backfill the derived Knowledge/local scaffold
python3 scripts/refresh_knowledge_local.py

# Run the CLI
python3 scripts/project_router.py <command>

# Pipeline commands (in order)
python3 scripts/project_router.py normalize --source voicenotes      # raw JSON → markdown
python3 scripts/project_router.py triage --source voicenotes         # classify and route
python3 scripts/project_router.py compile --source voicenotes        # generate project-ready briefs
python3 scripts/project_router.py review --source voicenotes         # inspect decision packets
python3 scripts/project_router.py dispatch --dry-run  # preview dispatch targets
python3 scripts/project_router.py discover       # cluster pending_project notes
python3 scripts/project_router.py status         # queue counts
python3 scripts/project_router.py scan-outboxes  # ingest downstream outboxes read-only
python3 scripts/project_router.py doctor --project home_renovation   # validate a downstream contract
python3 scripts/project_router.py init-router-root --project home_renovation --router-root /path/to/router  # scaffold downstream
python3 scripts/project_router.py adopt-router-root --project home_renovation  # migrate inbox_path → router_root_path
python3 scripts/project_router.py migrate-source-layout --dry-run  # preview legacy migration

# Filesystem ingestion
python3 scripts/project_router.py ingest --integration filesystem  # ingest files from local inbox
python3 scripts/project_router.py ingest --integration filesystem --dry-run  # preview ingest
python3 scripts/project_router.py extract --source filesystem  # list notes needing extraction
python3 scripts/project_router.py extract --note-id fs_xxx --text "..." --observations '{}'  # update extraction

# Record user decisions
python3 scripts/project_router.py decide --note-id vn_123 --decision approve

# Real dispatch (requires explicit approval)
python3 scripts/project_router.py dispatch --confirm-user-approval --note-id vn_123

# Sync from the VoiceNotes API
python3 scripts/project_router_client.py sync --output-dir ./data/raw/voicenotes

# Governance checks
python3 scripts/check_agent_surface_parity.py
python3 scripts/check_repo_ownership.py
python3 scripts/check_sync_manifest_alignment.py
python3 scripts/check_knowledge_structure.py
python3 scripts/check_adr_related_links.py
python3 scripts/check_managed_blocks.py
python3 scripts/check_customization_contracts.py
python3 scripts/project_router.py context
```

### Testing

```bash
# Run all tests
python3 -m pytest tests/test_project_router.py -v

# Run a single test
python3 -m pytest tests/test_project_router.py -v -k "test_name_here"

# Alternative (unittest)
python3 -m unittest tests.test_project_router -v
```

No linter or formatter is configured. No build step required.

## Architecture

**Entry point:** `scripts/project_router.py` → `src/project_router/cli.py::main(argv)` using argparse subcommands.

**Single-module CLI:** All logic lives in `src/project_router/cli.py`. No external dependencies — stdlib only.

**Pipeline flow:** `sync → normalize → triage → compile → review/decide → dispatch`, plus read-only downstream intake via `scan-outboxes`, and `ingest → normalize → extract → triage → compile → dispatch` for the filesystem source.

Each stage reads from the previous stage's source-aware output directory:
- `data/raw/voicenotes/` → `normalize --source voicenotes` → `data/normalized/voicenotes/`
- `data/raw/project_router/<project>/` → `normalize --source project_router` → `data/normalized/project_router/<project>/`
- `data/raw/filesystem/<inbox_key>/manifests/` → `normalize --source filesystem` → `data/normalized/filesystem/`
- `data/normalized/...` → `triage` / `compile` → source-aware `data/review/...` and `data/compiled/...`
- `data/compiled/...` → `dispatch` → `data/dispatched/` + downstream inbox mirror

**Extractors:** Modular content extraction in `src/project_router/extractors/`. Stdlib-only for text formats; optional `pymupdf` and `python-docx` for binary formats (see `requirements-extractors.txt`). Core pipeline remains zero-dep per ADR-001; extractors gracefully degrade when optional deps are missing.

**State directory** (`state/`, gitignored): sync checkpoints, user decision packets (JSON), discovery reports.

**Project registry overlay:**

- `projects/registry.shared.json` (committed): common project metadata, keywords, note types, thresholds
- `projects/registry.local.json` (gitignored): machine-local `router_root_path` values and optional local overrides
- `projects/registry.example.json` (committed): starter template for the local overlay

Classification can run from the shared registry alone. Real dispatch requires the local overlay with real absolute `router_root_path` values or explicit legacy `inbox_path` overrides.

**Project-router protocol:**

- Downstream repositories expose `router/router-contract.json`, `router/inbox/`, `router/outbox/`, and `router/conformance/`
- `scan-outboxes` reads downstream `outbox/` directories without mutating them
- `doctor` validates the contract and packet schema either repo-locally or from the central router

**Template/private split:**

- The managed `Repository Mode` block above is authoritative for the current repo role.
- Private downstream repos may keep their own branded `projects/registry.shared.json` and private docs.
- Private operating rules live in `Knowledge/local/AI/` (loaded via `@import` in CLAUDE.md and prose in AGENTS.md).
- Local skill additions in `.claude/skills/` are preserved during sync but do not require parity mirroring.
- The sync boundary is enforced through `repo-governance/ownership.manifest.json` and `repo-governance/customization-contracts.json`.

**Agent surfaces:**

- `.agents/skills/`: canonical neutral reference layer for shared workflow rules
- `AGENTS.md` + `.codex/skills/`: Codex-facing project surface
- `CLAUDE.md` + `.claude/skills/`: Claude-facing project surface
- The Codex and Claude surfaces should adapt `.agents/skills/`, not diverge from it.
- All surfaces must keep the same safety boundaries and workflow semantics.

**Tests:** Single file `tests/test_project_router.py` using `unittest` + `tempfile.TemporaryDirectory` for isolation. Tests mock CLI module-level path constants to point at temp dirs via `prepare_repo()`.

## Knowledge Foundation

Run `python3 scripts/project_router.py context` for a live project briefing, or read `Knowledge/ContextPack.md` for orientation. Architecture decisions are recorded in `Knowledge/ADR/`. Scripts are documented with "why/when" context in `Knowledge/ScriptsReference.md`.

## Session Defaults

At the beginning of a session:

1. Run `python3 scripts/project_router.py status`
2. If the machine is new, run `python3 scripts/bootstrap_local.py`
3. Confirm `.env.local` and `projects/registry.local.json` exist
4. If `.env.local` exists, use:
   - `python3 scripts/project_router_client.py sync --output-dir ./data/raw/voicenotes`
   - `python3 scripts/project_router.py normalize`
   - `python3 scripts/project_router.py triage`
   - `python3 scripts/project_router.py compile`
5. If filesystem inboxes are configured, run:
   - `python3 scripts/project_router.py ingest --integration filesystem`
   - `python3 scripts/project_router.py normalize --source filesystem`
   - `python3 scripts/project_router.py extract --source filesystem` (list pending, then extract each)
   - `python3 scripts/project_router.py triage --source filesystem`
   - `python3 scripts/project_router.py compile --source filesystem`
6. Run `python3 scripts/project_router.py review`
7. If `pending_project` is non-zero, run `python3 scripts/project_router.py discover`
8. Stop there and ask the user what to approve, reject, or refine

If `.env.local` is missing, skip `sync` and explain that the local VoiceNotes token is not configured on this machine.

## Safety Rules

These are critical — never violate:

- **Never delete or overwrite canonical raw JSON** — it is the source of truth
- **Never auto-dispatch** — always require explicit user approval in the current conversation before any real downstream write
- **Treat confirmation as note-specific by `source_note_id`** — real dispatch must name the exact approved `source_note_id` values with `--note-id`
- **Never dispatch a normalized note directly** — compile first and dispatch from the compiled artifact
- **Compiled packages must be fresh** relative to the canonical normalized note before dispatch
- **Never write to a downstream project during session opening or review analysis** — stop at `review` and ask the user what to approve
- **Never mutate downstream `router/outbox/` content during scan or review** — `scan-outboxes` is read-only
- **Send uncertain notes to the source-aware review queues** under `data/review/voicenotes/` or `data/review/project_router/` when no current project/rule exists yet
- **Registry paths must be absolute** — `router_root_path` and `inbox_path` in the registry use absolute paths; placeholder paths trigger validation errors during dispatch. Internal metadata paths (`canonical_path`, `raw_payload_path`, `compiled_from_path`) use project-relative paths.
- **Fail closed** when local config is missing or uses placeholder paths
- **Canonical metadata lives in source-aware `data/normalized/` paths** — review copies are queue views, not the source of truth
- **The pipeline is idempotent** — re-running must not duplicate notes or dispatch records
- **Run the parity and ownership checks before publishing starter changes** — use `python3 scripts/check_agent_surface_parity.py --pre-publish` and `python3 scripts/check_repo_ownership.py`
- **If a downstream repository must be edited**, read that repository's local agent instructions first
- **CLAUDE.md and AGENTS.md are template-owned** — do not edit directly; use `Knowledge/local/AI/` overlays for private rules
- **New files must be declared** in `customization-contracts.json` with all fields before merging
- **Private AI rules belong in `Knowledge/local/AI/`** — never in synced AI files
- **Private ADRs belong in `Knowledge/local/ADR/`**
- **Skills dirs are extensible** — local skill additions are preserved during sync and do not require parity mirroring, but operational rules live in overlays
- **Run `check_customization_contracts.py` before publishing**

## Language

- Write project-facing repository files in English.
- Preserve the downstream project's language conventions when generating notes for that project.

## Key Conventions

- **Filenames:** `{ISO_TIMESTAMP}--{SOURCE_NOTE_ID}.{ext}` — collision-resistant, immutable
- **Note ID validation:** alphanumeric + dash + underscore only (`NOTE_ID_PATTERN`)
- **Metadata model is layered:** `capture_kind`, `intent`, and `destination` are distinct fields — never conflate them
- **Bilingual stopwords:** English + Portuguese (supports downstream Portuguese-language projects)
- **Re-normalization preserves user metadata:** `user_keywords`, `thread_id`, `continuation_of`, `related_note_ids` survive re-triage
- **Errors use `SystemExit(message)`** for validation failures, not exceptions
- **Classification is rule-based:** recording_type mapping + keyword matching + sentence-level heuristics — no ML
- **Compiled notes must be rich:** include summary, facts, tasks, decisions, open questions, follow-ups, timeline, ambiguities, and evidence spans whenever available

## Workflow Preferences

- Prefer `python3 scripts/project_router_client.py` for direct VoiceNotes API access — do not use ad-hoc `curl`
- Prefer `python3 scripts/project_router.py doctor` before trusting a downstream `router/` surface
- Prefer `python3 scripts/project_router.py migrate-source-layout --dry-run` before changing or auditing old local copies that still use the flat pre-source-aware layout
- Validate with focused commands first, then broader checks if the repository grows more tooling later

## Claude Skills

Template skills live in `.claude/skills/`. Private operating rules live in `Knowledge/local/AI/claude.md` (loaded via `@import` below). Local skill additions in `.claude/skills/` are preserved during sync but do not require parity mirroring.

Treat `.agents/skills/` as the canonical neutral reference for shared workflow rules.
Keep the Claude skills aligned with both `.agents/skills/` and the Codex skill surface under `.codex/skills/`, but do not assume byte-for-byte identity is required.

<!-- customization-contract:begin -->
## Private AI Rules

Tracked AI surfaces (this file, AGENTS.md, skills) are upstream shared_review base.
Private operating rules live in Knowledge/local/AI/:

@Knowledge/local/AI/README.md
@Knowledge/local/AI/claude.md

Do not store private rules directly in this file — they will be overwritten during template sync.
<!-- customization-contract:end -->
