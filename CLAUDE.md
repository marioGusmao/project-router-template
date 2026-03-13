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

- Current role: shared starter upstream.
- Use `python3 scripts/bootstrap_private_repo.py` in a fresh derived repository when you want to promote it into a private operational repo with tracked upstream-sync metadata.
- Keep the template neutral; keep branded routing packs and private wording in the derived repository under the ownership rules.
<!-- repository-mode:end -->

## Commands

```bash
# Promote a fresh derived copy into a private operational repository
python3 scripts/bootstrap_private_repo.py

# Bootstrap local-only config
python3 scripts/bootstrap_local.py

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

# Record user decisions
python3 scripts/project_router.py decide --note-id vn_123 --decision approve

# Real dispatch (requires explicit approval)
python3 scripts/project_router.py dispatch --confirm-user-approval --note-id vn_123

# Sync from the VoiceNotes API
python3 scripts/project_router_client.py sync --output-dir ./data/raw/voicenotes

# Governance checks
python3 scripts/check_agent_surface_parity.py
python3 scripts/check_repo_ownership.py
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

**Single-module CLI:** All logic lives in `src/project_router/cli.py` (~2000 lines). No external dependencies — stdlib only.

**Pipeline flow:** `sync → normalize → triage → compile → review/decide → dispatch`, plus read-only downstream intake via `scan-outboxes`

Each stage reads from the previous stage's source-aware output directory:
- `data/raw/voicenotes/` → `normalize --source voicenotes` → `data/normalized/voicenotes/`
- `data/raw/project_router/<project>/` → `normalize --source project_router` → `data/normalized/project_router/<project>/`
- `data/normalized/...` → `triage` / `compile` → source-aware `data/review/...` and `data/compiled/...`
- `data/compiled/...` → `dispatch` → `data/dispatched/` + downstream inbox mirror

**State directory** (`state/`, gitignored): sync checkpoints, user decision packets (JSON), discovery reports.

**Project registry overlay:**

- `projects/registry.shared.json` (committed): common project metadata, keywords, note types, thresholds
- `projects/registry.local.json` (gitignored): machine-local `router_root_path` values and optional local overrides
- `projects/registry.example.json` (committed): starter template for the local overlay

Classification can run from the shared registry alone. Real dispatch requires the local overlay with real absolute `router_root_path` values or explicit legacy `inbox_path` overrides.

**Project-router protocol:**

- Downstream repositories expose `project-router/router-contract.json`, `project-router/inbox/`, `project-router/outbox/`, and `project-router/conformance/`
- `scan-outboxes` reads downstream `outbox/` directories without mutating them
- `doctor` validates the contract and packet schema either repo-locally or from the central router

**Template/private split:**

- The managed `Repository Mode` block above is authoritative for the current repo role.
- Private downstream repos may keep their own branded `projects/registry.shared.json`, private skills, and private docs.
- The sync boundary is enforced through `repo-governance/ownership.manifest.json`.

**Agent surfaces:**

- `.agents/skills/`: canonical neutral reference layer for shared workflow rules
- `AGENTS.md` + `.codex/skills/`: Codex-facing project surface
- `CLAUDE.md` + `.claude/skills/`: Claude-facing project surface
- The Codex and Claude surfaces should adapt `.agents/skills/`, not diverge from it.
- All surfaces must keep the same safety boundaries and workflow semantics.

**Tests:** Single file `tests/test_project_router.py` using `unittest` + `tempfile.TemporaryDirectory` for isolation. Tests mock CLI module-level path constants to point at temp dirs via `prepare_repo()`.

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
5. Run `python3 scripts/project_router.py review`
6. If `pending_project` is non-zero, run `python3 scripts/project_router.py discover`
7. Stop there and ask the user what to approve, reject, or refine

If `.env.local` is missing, skip `sync` and explain that the local VoiceNotes token is not configured on this machine.

## Safety Rules

These are critical — never violate:

- **Never delete or overwrite canonical raw JSON** — it is the source of truth
- **Never auto-dispatch** — always require explicit user approval in the current conversation before any real downstream write
- **Treat confirmation as note-specific by `source_note_id`** — real dispatch must name the exact approved `source_note_id` values with `--note-id`
- **Never dispatch a normalized note directly** — compile first and dispatch from the compiled artifact
- **Compiled packages must be fresh** relative to the canonical normalized note before dispatch
- **Never write to a downstream project during session opening or review analysis** — stop at `review` and ask the user what to approve
- **Never mutate downstream `project-router/outbox/` content during scan or review** — `scan-outboxes` is read-only
- **Registry paths must be absolute** — placeholder paths trigger validation errors during dispatch
- **Fail closed** when local config is missing or uses placeholder paths
- **Canonical metadata lives in source-aware `data/normalized/` paths** — review copies are queue views, not the source of truth
- **The pipeline is idempotent** — re-running must not duplicate notes or dispatch records
- **Run the parity and ownership checks before publishing starter changes** — use `python3 scripts/check_agent_surface_parity.py --pre-publish` and `python3 scripts/check_repo_ownership.py`
- **If a downstream repository must be edited**, read that repository's local agent instructions first

## Key Conventions

- **Filenames:** `{ISO_TIMESTAMP}--{SOURCE_NOTE_ID}.{ext}` — collision-resistant, immutable
- **Note ID validation:** alphanumeric + dash + underscore only (`NOTE_ID_PATTERN`)
- **Metadata model is layered:** `capture_kind`, `intent`, and `destination` are distinct fields — never conflate them
- **Bilingual stopwords:** English + Portuguese (supports downstream Portuguese-language projects)
- **Re-normalization preserves user metadata:** `user_keywords`, `thread_id`, `continuation_of`, `related_note_ids` survive re-triage
- **Errors use `SystemExit(message)`** for validation failures, not exceptions
- **Classification is rule-based:** recording_type mapping + keyword matching + sentence-level heuristics — no ML

## Claude Skills

Repository-local Claude workflow references live under `.claude/skills/`:

- `project-router-session-opener`
- `project-router-direct-sync`
- `project-router-triage-review`

Treat `.agents/skills/` as the canonical neutral reference for shared workflow rules.
Keep the Claude skills aligned with both `.agents/skills/` and the Codex skill surface under `.codex/skills/`, but do not assume byte-for-byte identity is required.
