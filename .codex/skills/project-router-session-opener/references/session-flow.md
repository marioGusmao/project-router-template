# Session Flow

## Purpose

This skill exists to make the beginning of a VoiceNotes session predictable and safe.

## Safe Session Opener Sequence

1. `python3 scripts/project_router.py status`
2. Check whether `.env.local` exists.
3. Check whether `projects/registry.local.json` exists.
4. If `.env.local` exists, fetch fresh notes by default:
   - `python3 scripts/project_router_client.py sync --output-dir ./data/raw`
   - `python3 scripts/project_router.py normalize`
   - `python3 scripts/project_router.py triage`
   - `python3 scripts/project_router.py compile`
   - this refresh path should preserve manual approvals when the computed route does not change
5. Show pending packets:
   - `python3 scripts/project_router.py review`
6. If `review_pending_project` is not zero, inspect clusters:
   - `python3 scripts/project_router.py discover`
7. If the user asked to simulate downstream readiness without sending anything:
   - `python3 scripts/project_router.py dispatch --dry-run`

## Required Reporting Shape

After the refresh/review pass, report results in three note lists when applicable:

1. `Processed in pipeline`
   - every note refreshed through `normalize -> triage -> compile`
   - group by project before listing notes
   - use the routed project when present; otherwise use `unrouted`
   - include `source_note_id`, title, short summary, compiled path, and optional normalized path
2. `Not ready for downstream`
   - every note still ending in `needs_review`, `ambiguous`, or `pending_project`
   - include `source_note_id`, title, short summary, current status, and compiled path
3. `Ready for dry-run`
   - every note surfaced as a dispatch candidate by `dispatch --dry-run`
   - include `source_note_id`, title, short summary, proposed project, and compiled path

Do not rely on filenames alone. The user should be able to understand the note from title + short summary and open it directly from the report.

## Do Not Do During Session Opening

- Do not run `dispatch`.
- Do not approve decisions on the user's behalf.
- Do not run sync if `.env.local` is missing or invalid.

## After Session Opening

Typical next commands:

- Review one packet:
  - `python3 scripts/project_router.py review --note-id <source_note_id>`
- Rebuild one compiled package:
  - `python3 scripts/project_router.py compile --note-id <source_note_id>`
- Record a decision:
  - `python3 scripts/project_router.py decide --note-id <source_note_id> --decision approve`
  - `python3 scripts/project_router.py decide --note-id <source_note_id> --decision pending-project --thread-id <thread_id> --continuation-of <source_note_id>`
- Dispatch only after explicit confirmation and explicit note IDs:
  - `python3 scripts/project_router.py dispatch --confirm-user-approval --note-id <source_note_id>`
