# Glossary

## Pipeline Stages

- **normalize**: Converts raw JSON captures into markdown files with YAML frontmatter. Source-aware: output goes to `data/normalized/{source}/`.
- **triage**: Classifies normalized notes by destination project, intent, and capture kind. Updates frontmatter in place.
- **compile**: Generates project-ready briefs from triaged notes with summary, extracted facts, tasks, and decisions. Output goes to `data/compiled/{source}/`.
- **dispatch**: Writes compiled packages to downstream project inboxes. Requires explicit user approval per note. Moves to `data/dispatched/`.
- **review**: Copies notes into status-based queue directories (`data/review/{source}/{status}/`) for inspection. Queue views only, not the source of truth.
- **discover**: Clusters notes marked `pending_project` to identify potential new project destinations.
- **scan-outboxes**: Read-only ingestion of downstream project `outbox/` directories. Never mutates downstream content.

## Note Model Fields

- **source_note_id**: Unique identifier for the original capture (e.g., `vn_abc123`). Alphanumeric + dash + underscore only.
- **capture_kind**: What type of capture this is (e.g., `voice_memo`, `quick_thought`, `meeting_note`). Derived from recording type mapping.
- **intent**: What the user intended (e.g., `task`, `reference`, `decision`, `brainstorm`). Classified by sentence-level heuristics.
- **destination**: Target project identifier (e.g., `home_renovation`). Set during triage from keyword matching and rules.
- **thread_id**: Groups related notes into a conversation thread. Preserved across re-normalization.
- **continuation_of**: Links a note to a prior note it continues. Preserved across re-normalization.
- **related_note_ids**: Cross-references to other notes. Preserved across re-normalization.
- **user_keywords**: User-supplied tags or keywords. Preserved across re-normalization.

## Review Queues

- **ambiguous**: Notes where triage could not confidently assign a single destination. Requires human disambiguation.
- **needs_review**: Notes that were classified but have low confidence or unusual characteristics. Flagged for human verification.
- **pending_project**: Notes that reference a project not yet in the registry. Candidates for `discover` clustering.

## Infrastructure

- **registry overlay**: Three-layer project configuration. `registry.shared.json` (committed, common metadata) + `registry.local.json` (gitignored, machine-local paths) + `registry.example.json` (committed, starter template). Classification runs from shared alone; dispatch requires local.
- **router_root_path**: Absolute filesystem path to a downstream project's root directory. Defined in `registry.local.json`. Must be absolute; placeholder paths trigger validation errors.
- **project-router protocol**: The interface downstream projects expose: `router/router-contract.json` (capabilities and schema), `router/inbox/` (receives dispatched notes), `router/outbox/` (emits status back), `router/conformance/` (validation artifacts).

## Ownership and Governance

- **template_owned**: Files that sync from the template upstream. Do not modify in derived repos.
- **private_owned**: Files that belong to the derived repo. Never synced from template.
- **shared_review**: Files that sync from template but may require local review after sync.
- **local_only**: Files that exist only on the local machine (gitignored). E.g., `.env.local`, `registry.local.json`.
- **ownership.manifest.json**: Located at `repo-governance/ownership.manifest.json`. Defines which files are template_owned vs private_owned.
- **parity.manifest.json**: Tracks alignment between agent surfaces (`.agents/skills/`, `.claude/skills/`, `.codex/skills/`).

## Protocol

- **router-contract.json**: Downstream project's declaration of supported note types, schema versions, and routing capabilities.
- **inbox/**: Directory where the router deposits compiled note packages for a downstream project.
- **outbox/**: Directory where downstream projects emit status updates or responses. Read-only from the router's perspective.
- **conformance/**: Directory for validation artifacts that verify a downstream project meets the protocol.
- **doctor command**: `python3 scripts/project_router.py doctor --project <name>` validates a downstream project's protocol compliance.
- **adoption journal**: JSON record written to `state/project_router/adoptions/{project_key}.json` after `adopt-router-root --confirm`, capturing detected inputs, chosen target, operations executed, config diff, doctor result, and follow-up items.
- **router root adoption**: The process of migrating a project from legacy `inbox_path` to the `router_root_path` convention via `adopt-router-root`. Creates or repairs the downstream scaffold, rewrites the local registry, and runs doctor validation.
