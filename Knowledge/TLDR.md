# TL;DR

Project Router Template is an **intake and classification layer** for VoiceNotes captures. It receives raw voice note JSON, classifies each note by project, intent, and type, then dispatches compiled briefs to downstream project inboxes.

**Pipeline:** `sync` -> `normalize` -> `triage` -> `compile` -> `review` -> `decide` -> `dispatch` (VoiceNotes source) or `ingest` -> `normalize` -> `extract` -> `triage` -> `compile` -> `dispatch` (filesystem source)

**Tech:** Pure Python 3.11+, zero external package dependencies, file-based storage. No database, no pip install.

**Template/private split:** The repository can run as a shareable template or as a private derived copy. The template surface stays neutral; a private copy holds secrets, routing paths, and customized registries. Sync between them is governed by `repo-governance/ownership.manifest.json`.

**Where to start:**

1. Run `python3 scripts/project_router.py status` to see current queue counts.
2. Run `python3 scripts/project_router.py context` for a project briefing (reflects current repo state including demo indicators and pending migrations).
3. Read `Knowledge/ContextPack.md` for a "where to find what" routing table.
4. Read `Knowledge/PipelineMap.md` for a concrete trace of a note through the full pipeline.
5. Read `CLAUDE.md` or `AGENTS.md` for safety rules and session defaults.
