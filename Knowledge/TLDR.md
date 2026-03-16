# TL;DR

Project Router Template is an **intake and classification layer** for VoiceNotes captures. It receives raw voice note JSON, classifies each note by project, intent, and type, then dispatches compiled briefs to downstream project inboxes.

**Pipeline:** `sync` -> `normalize` -> `triage` -> `compile` -> `review` -> `decide` -> `dispatch`

**Tech:** Pure Python 3.11+, zero external package dependencies, file-based storage. No database, no pip install.

**Template/private split:** This is a shareable GitHub template repository. Fork or derive your own private copy for real operational use. The template stays neutral; your private repo holds secrets, routing paths, and customized registries. Sync governed by `repo-governance/ownership.manifest.json`.

**Where to start:**

1. Run `python3 scripts/project_router.py status` to see current queue counts.
2. Run `python3 scripts/project_router.py context` for a project briefing (reflects current repo state including demo indicators and pending migrations).
3. Read `Knowledge/ContextPack.md` for a "where to find what" routing table.
4. Read `Knowledge/PipelineMap.md` for a concrete trace of a note through the full pipeline.
5. Read `CLAUDE.md` or `AGENTS.md` for safety rules and session defaults.
