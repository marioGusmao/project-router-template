# Session Flow

## Purpose

This skill exists to make the beginning of a VoiceNotes session predictable and safe.
For a broader orientation, see `Knowledge/ContextPack.md`.

## Safe Session Opener Sequence

1. If `private.meta.json` exists, run `python3 scripts/project_router.py template-update-status --check-remote`.
2. If the command reports `update_available`, ask the user whether they want to review/update the template before continuing. Do not auto-run the sync workflow or merge anything.
3. `python3 scripts/project_router.py status`
4. If the machine is new, run `python3 scripts/bootstrap_local.py`.
5. Check whether `.env.local` and `projects/registry.local.json` exist.
6. If `.env.local` exists, fetch fresh notes by default:
   - `python3 scripts/project_router_client.py sync --output-dir ./data/raw/voicenotes`
   - `python3 scripts/project_router.py normalize`
   - `python3 scripts/project_router.py triage`
   - `python3 scripts/project_router.py compile`
   - this refresh path should preserve manual approvals when the computed route does not change
7. If filesystem inboxes are configured (check `registry.local.json` for `sources.filesystem_inboxes`), run:
   - `python3 scripts/project_router.py ingest --integration filesystem`
   - `python3 scripts/project_router.py normalize --source filesystem`
   - `python3 scripts/project_router.py extract` (list pending, then extract each)
   - `python3 scripts/project_router.py triage --source filesystem`
   - `python3 scripts/project_router.py compile --source filesystem`
8. Show pending packets:
   - `python3 scripts/project_router.py review`
9. If `pending_project` is not zero, inspect clusters:
   - `python3 scripts/project_router.py discover`
10. If router inbox packets exist, consume them:
   - `python3 scripts/project_router.py inbox-intake`
   - `python3 scripts/project_router.py inbox-status`
11. Stop there and ask the user what to approve, reject, or refine.

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

- Do not run `dispatch` or `dispatch --dry-run`.
- Do not approve decisions on the user's behalf.
- Do not jump from a downstream finding to direct edits in that repository. Treat downstream repositories as read-only by default and prefer their `project-router` inbox/outbox surfaces first.
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
- Preview dispatch targets (after session opening, not during):
  - `python3 scripts/project_router.py dispatch --dry-run`
- Dispatch only after explicit confirmation and explicit note IDs:
  - `python3 scripts/project_router.py dispatch --confirm-user-approval --note-id <source_note_id>`
