---
name: project-router-session-opener
description: Start a Project Router session for VoiceNotes captures by checking local config, fetching new notes from VoiceNotes when local auth is available, updating the local triage queues, and surfacing the exact items that need review.
---

# Project Router Session Opener

Use this workflow at the start of a Project Router session for VoiceNotes captures.

## Mandatory Rules

- Never auto-dispatch.
- Never write to a downstream project during session opening.
- Treat `sync`, `normalize`, and `triage` as safe refresh steps.
- Treat `compile`, `review`, and `decide` as the decision-preparation layer.
- Treat `dispatch` as a later explicit step that requires user confirmation and exact `source_note_id` allowlists.
- Treat confirmation as note-specific by `source_note_id`.
- Compiled packages must be fresh before dispatch.
- When reporting session results, always include note lists with clickable paths, not only aggregate counts.

If the repository is unfamiliar, run `python3 scripts/project_router.py context` for a live project briefing, or read `Knowledge/ContextPack.md` for orientation.

## Session Opening Flow

1. Run `python3 scripts/project_router.py status`.
2. If the machine is new, run `python3 scripts/bootstrap_local.py`.
3. Confirm `.env.local` and `projects/registry.local.json` exist.
4. If `.env.local` exists, run:
   - `python3 scripts/project_router_client.py sync --output-dir ./data/raw/voicenotes`
   - `python3 scripts/project_router.py normalize`
   - `python3 scripts/project_router.py triage`
   - `python3 scripts/project_router.py compile`
5. Run `python3 scripts/project_router.py review`.
6. If `pending_project` is non-zero, run `python3 scripts/project_router.py discover`.
7. Stop there and ask the user what to approve, reject, or refine.

## Downstream Setup

If a project needs a new downstream scaffold, use `init-router-root`. If a project still uses legacy `inbox_path`, use `adopt-router-root` to migrate:

- `python3 scripts/project_router.py init-router-root --project <key> --router-root <path>`
- `python3 scripts/project_router.py adopt-router-root --project <key>`

## Output Format

Keep the opener summary short, then group notes into these sections when they exist:

- `Processed in pipeline`
- `Not ready for downstream`
- `Ready for dry-run`

For every listed note include `source_note_id`, title, short summary, and a clickable path to the compiled or normalized note.
