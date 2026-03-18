---
name: project-router-direct-sync
description: Sync, search, retrieve, and create VoiceNotes notes directly from the repository using the OpenClaw-compatible API token, without requiring OpenClaw.
---

# Project Router Direct Sync

Use this workflow to interact with VoiceNotes directly from the repository without depending on OpenClaw.

## Prerequisites

- Ensure `VOICENOTES_API_KEY` is available through `.env.local` or the shell environment.
- Prefer the neutral repository entrypoint `python3 scripts/project_router_client.py ...` instead of ad-hoc `curl`.
- If the task depends on routing or dispatch, review the repository safety rules before writing anywhere.
- Treat downstream repositories as read-only by default from this hub. If a synced note implies work in another repository, prefer that downstream repository's `project-router` inbox/outbox surfaces before suggesting direct edits.

## Workflow

1. Confirm `VOICENOTES_API_KEY` is present.
2. Start with read-only operations when possible.
3. Use `sync` when notes need to become canonical repository files.
4. Use `create` only when the user explicitly asks to write a note back to VoiceNotes.

## Commands

```bash
python3 scripts/project_router_client.py list --from 2026-03-01T00:00:00Z
python3 scripts/project_router_client.py search --query "home renovation idea"
python3 scripts/project_router_client.py get --id NTHiJljf --format markdown
python3 scripts/project_router_client.py sync --output-dir ./data/raw/voicenotes
python3 scripts/project_router_client.py create --text "Remember to review the warranty"
```

## Output Rules

- Prefer `sync` when notes need to become repository files.
- `sync` writes canonical raw JSON files.
- Re-running `sync` must stay idempotent and refresh changed upstream payloads.
