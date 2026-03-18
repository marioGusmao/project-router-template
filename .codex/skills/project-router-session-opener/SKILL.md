---
name: project-router-session-opener
description: Start a Project Router session for VoiceNotes captures by checking local config, fetching new notes from VoiceNotes when local auth is available, updating the local triage queues, and surfacing the exact items that need review. Use at the beginning of a session when you want Codex to know the safe operating flow for this project without dispatching anything automatically.
---

# Project Router Session Opener

## Overview

Use this skill at the start of a Project Router session for VoiceNotes captures. It establishes the safe operating sequence for the repository and keeps the session focused on review, approval, and rule refinement rather than premature dispatch.

## Mandatory Rules

- Never dispatch automatically.
- Never write to a downstream project during session opening.
- Treat downstream repositories as read-only by default. Prefer the downstream repository's `project-router` inbox/outbox surfaces for cross-project communication.
- Treat `sync`, `normalize`, and `triage` as safe refresh steps.
- Treat `compile`, `review`, and `decide` as the decision-preparation layer.
- Treat `dispatch` as a later, explicit step that needs user confirmation and explicit `source_note_id` allowlists.
- Treat `normalize` as a refresh step that preserves approved/manual metadata when the underlying route has not changed.
- When reporting session results, always include note lists with clickable paths, not only aggregate counts.
- For every listed note, include `source_note_id`, title, a short summary, and at least one path the user can open.

If the repository is unfamiliar, run `python3 scripts/project_router.py context` for a live project briefing, or read `Knowledge/ContextPack.md` for orientation.

## Session Opening Flow

1. If `private.meta.json` exists, check the template version first:
   - `python3 scripts/project_router.py template-update-status --check-remote`
2. If the command reports `update_available`, ask the user whether they want to review/update the template before continuing. Do not auto-run the sync workflow or merge anything on the user's behalf.
3. Confirm the repository state with:
   - `python3 scripts/project_router.py status`
4. Confirm local config exists:
   - `.env.local`
   - `projects/registry.local.json`
5. If `.env.local` exists, fetch new notes from VoiceNotes as part of the default opener:
   - `python3 scripts/project_router_client.py sync --output-dir ./data/raw/voicenotes`
   - `python3 scripts/project_router.py normalize`
   - `python3 scripts/project_router.py triage`
   - `python3 scripts/project_router.py compile`
6. If filesystem inboxes are configured (check `registry.local.json` for `sources.filesystem_inboxes`), run:
   - `python3 scripts/project_router.py ingest --integration filesystem`
   - `python3 scripts/project_router.py normalize --source filesystem`
   - `python3 scripts/project_router.py extract` (list pending, then extract each)
   - `python3 scripts/project_router.py triage --source filesystem`
   - `python3 scripts/project_router.py compile --source filesystem`
7. Surface the decision queue with:
   - `python3 scripts/project_router.py review`
8. If `pending_project` is non-zero, analyze emerging themes with:
   - `python3 scripts/project_router.py discover`
9. Ingest and check router inbox packets:
   - `python3 scripts/project_router.py inbox-intake`
   - `python3 scripts/project_router.py inbox-status`
10. Stop there and ask the user what to approve, reject, or refine.

## Downstream Setup

If a project needs a new downstream scaffold, use `init-router-root`. If a project still uses legacy `inbox_path`, use `adopt-router-root` to migrate:

- `python3 scripts/project_router.py init-router-root --project <key> --router-root <path>`
- `python3 scripts/project_router.py adopt-router-root --project <key>`

## Default Behavior

If the user says “start the session” or invokes this skill without further detail:
- If `private.meta.json` exists, run `template-update-status --check-remote` first and surface any available update before the rest of the opener
- Run `status`
- Inspect whether local config files exist
- If `.env.local` exists, run `sync -> normalize -> triage -> compile`
- Show pending decision packets via `review`
- If `.env.local` is missing, skip sync and explain that the local VoiceNotes token is not configured on this machine

## Output Format

Keep the opener summary short:

```text
Session state:
- raw: 0
- normalized: 12
- pending decisions: 4

Config:
- .env.local present
- registry.local.json present

Next safe step:
- run sync/normalize/triage/compile
or
- review the 4 pending notes
```

After the short session state, always include these sections when notes exist:

- `Processed in pipeline`
  - Notes that were refreshed through `normalize -> triage -> compile`
  - Group this section by project first
  - Use the routed project when one exists; otherwise group under `unrouted`
  - For each note: `source_note_id`, title, short summary, link to compiled note, and optional link to normalized note
- `Not ready for downstream`
  - Notes still in `needs_review`, `ambiguous`, or `pending_project`
  - For each note: `source_note_id`, title, short summary, current status, and link to the compiled note
- `Ready for dry-run`
  - Notes that already qualify as dispatch candidates in `dispatch --dry-run`
  - For each note: `source_note_id`, title, short summary, proposed project, and link to the compiled note

If a section has no notes, say so explicitly instead of omitting it.

## References

- Read `references/session-flow.md` for the exact command sequence and the decision boundaries between refresh, review, and dispatch.
