# AGENTS.md

## Project
- This repository is the central triage hub for VoiceNotes captures before they are dispatched to other local projects.
- Primary responsibilities: ingest notes, preserve canonical raw JSON copies, classify conservatively, queue ambiguous or not-yet-placeable notes for review, and dispatch approved notes to downstream project inboxes.

## Language
- Write project-facing repository files in English.
- Preserve the downstream project's language conventions when generating notes for that project.

<!-- repository-mode:begin -->
## Repository Mode
- Current mode: private derived repository.
- Treat this repository as the operational home for private routing packs, branded docs, and project wording.
- Keep the upstream link to `project-router-template` via `private.meta.json` and `template-base.json`.
- Pull shared updates from `marioGusmao/project-router-template` through reviewed `chore/template-sync` pull requests, not by rewriting private-owned or local-only files by hand.
<!-- repository-mode:end -->

## Safety Rules
- Never delete or overwrite the canonical source note captured from VoiceNotes.
- Never auto-dispatch a note, even when the routing confidence is high.
- Always ask the user for explicit confirmation before writing any note into a downstream project inbox.
- Treat confirmation as note-specific by `source_note_id`. A batch dispatch must name the exact approved `source_note_id` values.
- Send uncertain notes to the source-aware review queues under `data/review/voicenotes/`, `data/review/project_router/`, or `data/review/filesystem/` when no current project/rule exists yet.
- Treat downstream project writes as derived exports. The canonical note always remains in this repository.
- Never dispatch a normalized note directly. Compile a project-ready package first and dispatch from that compiled artifact.
- Compiled packages must be fresh before dispatch.
- Registry paths must be absolute. `router_root_path` and `inbox_path` use absolute paths; placeholder paths trigger validation errors during dispatch.
- Treat downstream project-router outboxes as read-only during scan and review.
- AGENTS.md and CLAUDE.md are template-owned — do not edit directly; use `Knowledge/local/AI/` overlays for private rules.
- New files must be declared in `customization-contracts.json` with all fields before merging.
- Private AI rules belong in `Knowledge/local/AI/` — never in synced AI files.
- Private ADRs belong in `Knowledge/local/ADR/`.
- Skills dirs are extensible — local skill additions are preserved during sync and do not require parity mirroring.
- Run `check_customization_contracts.py` before publishing.

## Project Boundaries
- Treat the managed `Repository Mode` block above as authoritative. In template mode this repository is the shared starter upstream; in private-derived mode it becomes the operational private home while upstream updates arrive through reviewed sync PRs.
- Keep shareable routing defaults in `projects/registry.shared.json`.
- Keep the local overlay template in `projects/registry.example.json`.
- Keep shared neutral agent workflow references in `.agents/skills/`.
- Keep Codex-specific adaptations in `.codex/skills/`.
- Keep Claude-specific adaptations in `.claude/skills/`.
- Keep machine-specific routing paths in `projects/registry.local.json`, which must stay out of Git.
- Use `router_root_path` as the standard local path for downstream project-router integrations.
- Keep stateful note artifacts under `data/`.
- Keep machine-local checkpoints under `state/`, out of Git.
- Keep automation and processing code under `src/` or `scripts/`.
- Keep template/private sync guardrails in `repo-governance/ownership.manifest.json`.
- Do not edit downstream repositories unless the task explicitly requires it.
- If a downstream repository must be edited, read its local `AGENTS.md` first and follow its conventions.

## Knowledge Foundation
- Run `python3 scripts/project_router.py context` for a live project briefing, or read `Knowledge/ContextPack.md` for orientation.
- Architecture decisions are recorded in `Knowledge/ADR/`.
- Scripts are documented with "why/when" context in `Knowledge/ScriptsReference.md`.

## Workflow Defaults
- Treat `.agents/skills/` as the canonical neutral reference layer for shared workflow rules.
- Keep `.codex/skills/` aligned with `.agents/skills/`, adding only Codex-specific notes when needed.
- Prefer the local skill `project-router-direct-sync` for direct access to the VoiceNotes service.
- Prefer the local skill `project-router-session-opener` at the beginning of a session.
- Prefer the local skill `project-router-triage-review` for routing analysis and user-facing review.
- Prefer the local skill `project-router-inbox-consumer` for consuming incoming packets from the router inbox.
- Prefer `python3 scripts/bootstrap_private_repo.py` when promoting a fresh template copy into a private operational repository.
- Prefer `python3 scripts/bootstrap_local.py` when setting up a new machine or validating starter hygiene.
- Prefer the repository entrypoint `python3 scripts/project_router_client.py ...` for direct VoiceNotes API access in project-facing docs and workflows.
- Prefer `python3 scripts/project_router.py scan-outboxes` when pulling project-router packets from downstream repositories.
- Prefer `python3 scripts/project_router.py doctor` before trusting a downstream `router/` surface.
- Prefer `python3 scripts/project_router.py migrate-source-layout --dry-run` before changing or auditing old local starter copies that still use the flat pre-source-aware layout.
- Prefer `python3 scripts/project_router.py discover` when the `pending_project` queue starts to accumulate notes.
- Prefer `python3 scripts/project_router.py compile` before any real dispatch so downstream projects receive a richer brief than the raw transcript.
- Use stable note IDs and collision-resistant filenames.
- Make the pipeline idempotent: repeated runs must not duplicate normalized notes or dispatch records.
- Keep the note model layered: `capture_kind`, `intent`, and `destination` must remain distinct fields.
- Keep compiled notes rich: include summary, facts, tasks, decisions, open questions, follow-ups, timeline, ambiguities, and evidence spans whenever available.
- Fail closed when machine-local config is missing or still uses placeholder paths.
- Validate with focused commands first, then broader checks if the repository grows more tooling later.
- Preserve note relationship metadata (`thread_id`, `continuation_of`, `related_note_ids`) when reviewing or dispatching related captures.
- Treat `data/review/...` as queue views. Canonical metadata changes should land in source-aware `data/normalized/...`, not only in review copies.

## Key Conventions
- Filenames: `{ISO_TIMESTAMP}--{SOURCE_NOTE_ID}.{ext}` — collision-resistant, immutable.
- Note ID validation: alphanumeric + dash + underscore only (`NOTE_ID_PATTERN`).
- Metadata model is layered: `capture_kind`, `intent`, and `destination` are distinct fields — never conflate them.
- Bilingual stopwords: English + Portuguese (supports downstream Portuguese-language projects).
- Re-normalization preserves user metadata: `user_keywords`, `thread_id`, `continuation_of`, `related_note_ids` survive re-triage.
- Errors use `SystemExit(message)` for validation failures, not exceptions.
- Classification is rule-based: recording_type mapping + keyword matching + sentence-level heuristics — no ML.
- Compiled notes must be rich: include summary, facts, tasks, decisions, open questions, follow-ups, timeline, ambiguities, and evidence spans whenever available.

## Current Commands
- `python3 scripts/bootstrap_private_repo.py`
- `python3 scripts/bootstrap_local.py`
- `python3 scripts/refresh_knowledge_local.py`
- `python3 scripts/project_router_client.py sync --output-dir ./data/raw/voicenotes`
- `python3 scripts/project_router.py status`
- `python3 scripts/project_router.py normalize`
- `python3 scripts/project_router.py triage`
- `python3 scripts/project_router.py compile`
- `python3 scripts/project_router.py review`
- `python3 scripts/project_router.py discover`
- `python3 scripts/project_router.py scan-outboxes`
- `python3 scripts/project_router.py doctor`
- `python3 scripts/project_router.py init-router-root --project <key> --router-root <path>`
- `python3 scripts/project_router.py adopt-router-root --project <key>`
- `python3 scripts/project_router.py migrate-source-layout --dry-run`
- `python3 scripts/project_router.py ingest --integration filesystem`
- `python3 scripts/project_router.py extract --source filesystem`
- `python3 scripts/project_router.py decide --note-id vn_123 --decision approve`
- `python3 scripts/project_router.py dispatch --dry-run`
- `python3 scripts/project_router.py dispatch --confirm-user-approval --note-id vn_123`
- `python3 scripts/project_router.py inbox-intake`
- `python3 scripts/project_router.py inbox-status`
- `python3 scripts/project_router.py inbox-ack --packet-id <id> --status <applied|blocked|rejected|in_progress>`
- `python3 scripts/check_agent_surface_parity.py`
- `python3 scripts/check_repo_ownership.py`
- `python3 scripts/check_sync_manifest_alignment.py`
- `python3 scripts/check_knowledge_structure.py`
- `python3 scripts/check_adr_related_links.py`
- `python3 scripts/check_managed_blocks.py`
- `python3 scripts/check_customization_contracts.py`
- `python3 scripts/project_router.py context`

<!-- customization-contract:begin -->
## Private AI Rules

Tracked AI surfaces are upstream shared_review base.
If Knowledge/local/AI/README.md exists, read it first for private cross-agent rules.
If Knowledge/local/AI/codex.md exists, read it next for Codex-specific additions.
Do not store private rules directly in this file.
<!-- customization-contract:end -->
