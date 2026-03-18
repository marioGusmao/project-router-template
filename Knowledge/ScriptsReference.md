# Scripts Reference

Scripts grouped by purpose. For the raw command list, see `CLAUDE.md`. This reference focuses on **why and when** to use each script.

## Setup

| Script | Purpose | Prerequisites |
|--------|---------|---------------|
| `scripts/bootstrap_private_repo.py` | Promote a fresh derived copy into a private operational repository with tracked upstream-sync metadata | Run in a freshly cloned/derived repo, not in the template itself |
| `scripts/bootstrap_local.py` | Create local-only config files (`.env.local`, `projects/registry.local.json`) | Run once per machine |
| `scripts/refresh_knowledge_local.py` | Preview or backfill the derived `Knowledge/local/` scaffold from the template-owned source | Private-derived repo with `Knowledge/Templates/local/` present |
| `scripts/knowledge_local_scaffold.py` | Shared helpers for comparing and materializing the Knowledge/local scaffold from templates | Library module imported by bootstrap and refresh scripts |

## Sync

| Script | Purpose | Prerequisites |
|--------|---------|---------------|
| `scripts/project_router_client.py sync` | Fetch new captures from the VoiceNotes API into `data/raw/voicenotes/` | `.env.local` with VoiceNotes API token |

## Pipeline

| Script | Stage | Purpose | Prerequisites |
|--------|-------|---------|---------------|
| `scripts/project_router.py normalize` | normalize | Convert raw JSON to markdown with frontmatter | Raw files in `data/raw/{source}/` |
| `scripts/project_router.py triage` | triage | Classify notes by destination, intent, capture_kind | Normalized files in `data/normalized/{source}/` |
| `scripts/project_router.py compile` | compile | Generate enriched project-ready briefs | Triaged files (frontmatter has destination) |
| `scripts/project_router.py review` | review | Copy notes into status-based queue directories for inspection | Compiled or triaged notes exist |
| `scripts/project_router.py decide` | decide | Record user decision (approve/reject/defer) for a specific note | Note has been reviewed; requires `--note-id` and `--decision` |
| `scripts/project_router.py dispatch` | dispatch | Write compiled packages to downstream project inboxes | Compiled + approved notes; `registry.local.json` with valid paths; requires `--confirm-user-approval` and `--note-id` |
| `scripts/project_router.py discover` | discover | Cluster `pending_project` notes to identify potential new destinations | Notes in pending_project queue |
| `scripts/project_router.py status` | status | Show current queue counts across all stages | None |
| `scripts/project_router.py scan-outboxes` | scan-outboxes | Read-only ingestion of downstream project outbox directories | `registry.local.json` with valid `router_root_path` values |
| `scripts/project_router.py doctor` | doctor | Validate a downstream project's protocol compliance | `--project` flag; downstream project has `router/` directory |
| `scripts/project_router.py init-router-root` | init-router-root | Create a fresh downstream `router/` scaffold (contract, dirs, fixtures) | `--project` (must exist in shared registry) and `--router-root` (absolute path) |
| `scripts/project_router.py adopt-router-root` | adopt-router-root | Migrate from legacy `inbox_path` to `router_root_path` with scaffold repair | `--project` or `--all`; `--confirm` to apply; optional `--router-root` for explicit target |
| `scripts/project_router.py ingest` | ingest | Scan configured filesystem inboxes, copy blobs, run extractors, write manifests, archive originals | `registry.local.json` with `sources.filesystem_inboxes` configured |
| `scripts/project_router.py extract` | extract | List notes needing AI extraction, or update extraction for a specific note | Ingested + normalized filesystem notes |
| `scripts/project_router.py context` | context | Generate a live project briefing in the terminal from current state | None |
| `scripts/project_router.py template-update-status` | template-update-status | Report the installed template metadata and optionally compare it with the latest upstream GitHub release | `template-base.json` or equivalent template metadata; add `--check-remote` to query GitHub |
| `scripts/project_router.py inbox-intake` | inbox-intake | Ingest and archive inbox packets from `router/inbox/` | Local router contract exists |
| `scripts/project_router.py inbox-status` | inbox-status | List open inbox packet states | Inbox packets ingested |
| `scripts/project_router.py inbox-ack` | inbox-ack | Acknowledge a packet (record decision: applied, blocked, rejected) | Inbox packets ingested; requires `--packet-id` and `--status` |

## Governance

| Script | Purpose | Prerequisites |
|--------|---------|---------------|
| `scripts/check_agent_surface_parity.py` | Verify alignment between .agents/skills/, .claude/skills/, and .codex/skills/ | None; use `--pre-publish` before publishing template changes |
| `scripts/check_repo_ownership.py` | Validate ownership.manifest.json against actual repo files | None; run before publishing |
| `scripts/check_knowledge_structure.py` | Validate Knowledge/ directory structure and required files | None |
| `scripts/check_sync_manifest_alignment.py` | Validate that the upstream-sync workflow only targets paths allowed by the ownership manifest | None |
| `scripts/check_adr_related_links.py` | Validate that `## Related` sections in ADR files point to real files; catches self-references and malformed entries | None; use `--mode block` in CI |
| `scripts/check_managed_blocks.py` | Validate that all managed block markers exist in matched begin/end pairs across CLAUDE.md, AGENTS.md, and README files | None |
| `scripts/check_customization_contracts.py` | Validate the customization contract registry against the ownership manifest, @import presence, and overlay path safety | None |

## Template Sync

| Script | Purpose | Prerequisites |
|--------|---------|---------------|
| `scripts/sync_ai_files.py` | Restore customization-contract blocks into AI files after upstream overwrite during sync | Called by `template-upstream-sync.yml` Pass 2 |
| `scripts/render_template_sync_pr_body.py` | Render the PR body for template sync PRs with diff-only diffs | Called by `template-upstream-sync.yml` Pass 5 |
| `scripts/apply_managed_block_sync.py` | Sync managed blocks from upstream into local README files, preserving content outside markers | Called by `template-upstream-sync.yml` Pass 3 |
| `scripts/migrate_add_contract_block.py` | Insert customization-contract markers into CLAUDE.md/AGENTS.md for old derived repos that lack them | Run once before first sync; also called by Pass 0 of the sync workflow |

## Testing

| Script | Purpose | Prerequisites |
|--------|---------|---------------|
| `python3 -m pytest tests/test_project_router.py -v` | Run all tests | None (uses unittest + tempfile isolation) |
| `python3 -m pytest tests/test_project_router.py -v -k "test_name"` | Run a single test | None |
