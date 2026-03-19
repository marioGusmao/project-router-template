---
name: project-router-session-opener
description: Start a Project Router session for VoiceNotes and Readwise captures by checking local config, fetching new notes when local auth is available, updating the local triage queues, and surfacing the exact items that need review.
---

# Project Router Session Opener

Use this workflow at the start of a Project Router session for VoiceNotes captures.

## Mandatory Rules

- Never auto-dispatch.
- Never write to a downstream project during session opening.
- Treat downstream repositories as read-only by default. Prefer the downstream repository's `project-router` inbox/outbox surfaces for cross-project communication.
- Treat `sync`, `normalize`, and `triage` as safe refresh steps.
- Treat `compile`, `review`, and `decide` as the decision-preparation layer.
- Treat `dispatch` as a later explicit step that requires user confirmation and exact `source_note_id` allowlists.
- Treat confirmation as note-specific by `source_note_id`.
- Compiled packages must be fresh before dispatch.
- When reporting session results, always include note lists with clickable paths, not only aggregate counts.

If the repository is unfamiliar, run `python3 scripts/project_router.py context` for a live project briefing, or read `Knowledge/ContextPack.md` for orientation.

## Session Opening Flow

1. If `private.meta.json` exists, run `python3 scripts/project_router.py template-update-status --check-remote`.
2. If the command reports `update_available`, ask the user whether they want to review/update the template before continuing. Do not auto-run the sync workflow or merge anything on the user's behalf.
3. Run `python3 scripts/project_router.py status`.
4. If the machine is new, run `python3 scripts/bootstrap_local.py`.
5. Confirm `.env.local` and `projects/registry.local.json` exist.
6. If `.env.local` exists and `VOICENOTES_API_KEY` is configured (not the placeholder), run:
   - `python3 scripts/project_router_client.py sync --output-dir ./data/raw/voicenotes`
   - `python3 scripts/project_router.py normalize --source voicenotes`
   - `python3 scripts/project_router.py triage --source voicenotes`
   - `python3 scripts/project_router.py compile --source voicenotes`
   If `VOICENOTES_API_KEY` is missing or still set to the placeholder, explain: "VoiceNotes sync skipped: VOICENOTES_API_KEY not configured in .env.local".
6b. If `READWISE_ACCESS_TOKEN` is configured in `.env.local` (not the placeholder value), run:
   - `python3 scripts/readwise_client.py sync --output-dir ./data/raw/readwise`
   - `python3 scripts/project_router.py normalize --source readwise`
   - `python3 scripts/project_router.py triage --source readwise`
   - `python3 scripts/project_router.py compile --source readwise`
   If `READWISE_ACCESS_TOKEN` is missing or still set to the placeholder, explain: "Readwise sync skipped: READWISE_ACCESS_TOKEN not configured in .env.local".
7. If filesystem inboxes are configured (check `registry.local.json` for `sources.filesystem_inboxes`), run:
   - `python3 scripts/project_router.py ingest --integration filesystem`
   - `python3 scripts/project_router.py normalize --source filesystem`
   - `python3 scripts/project_router.py extract` (list pending, then extract each)
   - `python3 scripts/project_router.py triage --source filesystem`
   - `python3 scripts/project_router.py compile --source filesystem`
8. Run `python3 scripts/project_router.py review`.
9. Check the review output for notes with `user_suggested_project` set. If any are found:
   - List each note: "Dashboard suggests rerouting {note_id} from '{project}' → '{suggested_project}'"
   - Ask the user: "Accept, reject, or skip each suggestion?"
   - For accepted suggestions: run `python3 scripts/project_router.py decide --note-id {id} --decision approve --final-project {suggested_project}`
   - For rejected suggestions: clear the suggestion fields from the note metadata
10. If `pending_project` is non-zero, run `python3 scripts/project_router.py discover`.
11. Check if the dashboard is running on port 8420. If not, start it in background with `python3 scripts/dashboard.py --no-browser &`. Then open the browser to http://localhost:8420.
12. Run `python3 scripts/project_router.py inbox-intake` to ingest any packets in `router/inbox/`.
13. Run `python3 scripts/project_router.py inbox-status` to check for open inbox packets.
14. Stop there and ask the user what to approve, reject, or refine.

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
