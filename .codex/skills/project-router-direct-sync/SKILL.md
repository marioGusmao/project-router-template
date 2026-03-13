---
name: project-router-direct-sync
description: Sync, search, retrieve, and create VoiceNotes notes directly from Codex using the same OpenClaw-compatible API token, without requiring OpenClaw. Use when tasks involve pulling notes into local triage workflows, exporting canonical raw JSON payloads, reviewing recent notes, searching by theme, or creating text notes back in VoiceNotes.
---

# Project Router Direct Sync

## Overview

Use this skill to interact with VoiceNotes through Project Router from Codex via the OpenClaw-compatible integration token. Prefer the bundled script instead of ad-hoc `curl` so requests, canonical raw JSON export, Markdown rendering, and auth handling stay consistent.

## Prerequisites

- Ensure `VOICENOTES_API_KEY` is set in the shell environment.
- Keep this skill focused on direct VoiceNotes access. Do not assume OpenClaw is installed.
- If the task depends on project-specific routing or triage rules, inspect the target project before dispatching notes there.

## Workflow

1. Confirm `VOICENOTES_API_KEY` is present before calling the API.
2. Use the repository entrypoint `scripts/project_router_client.py` for all VoiceNotes operations.
3. Start with read-only operations:
   - `list` for recent or filtered notes
   - `search` for semantic lookup
   - `get` for a full transcript
4. When the goal is local processing, use `sync` to export canonical raw JSON payloads with stable filenames.
5. Use `create` only when the user explicitly wants a new note written back to VoiceNotes.

## Commands

Run from the repository root or pass absolute paths:

```bash
python3 scripts/project_router_client.py list --from 2026-03-01T00:00:00Z
python3 scripts/project_router_client.py search --query "home renovation idea"
python3 scripts/project_router_client.py get --id NTHiJljf --format markdown
python3 scripts/project_router_client.py sync --output-dir ./data/raw/voicenotes
python3 scripts/project_router_client.py create --text "Remember to review the warranty"
```

## Output Rules

- Prefer `sync` when notes need to become repository files.
- `sync` writes canonical raw JSON files that preserve the API payload under `recording`.
- `get --format markdown` is for ad-hoc reading, not canonical storage.
- Filenames are collision-resistant and immutable: `timestamp + note_id`.
- Re-running `sync` refreshes an existing raw file when the upstream payload changed and skips it when the payload is unchanged.

## References

- Read `references/openclaw-compat.md` when you need endpoint details, payload shapes, or compatibility notes from the original public OpenClaw skill.
