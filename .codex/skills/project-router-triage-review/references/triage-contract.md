# Triage Contract

## Queue Intent

- `data/raw/voicenotes/` and `data/raw/project_router/`: source-aware raw inputs
- `data/normalized/voicenotes/` and `data/normalized/project_router/`: canonical local notes ready for analysis
- `data/compiled/voicenotes/` and `data/compiled/project_router/`: project-ready compiled briefs derived from canonical notes
- `data/review/voicenotes/ambiguous/`: multiple plausible destinations for VoiceNotes captures
- `data/review/*/needs_review/`: insufficient confidence or vague content
- `data/review/*/pending_project/`: notes that do not fit any configured project yet
- `data/review/project_router/parse_errors/`: invalid downstream project-router packets recorded locally
- `data/dispatched/`: mirror of notes already written to downstream inboxes

The canonical source remains in `data/normalized/...`. Review queues are views over that canonical note. The compiled package is a parallel artifact and must be fresh relative to the canonical note before any dispatch.

## Confirmation Policy

- A classified note is still only a proposal.
- Downstream dispatch requires explicit user confirmation in the active conversation.
- Downstream repositories are read-only by default from this hub; if follow-up work is needed, prefer the downstream repository's `project-router` inbox/outbox surfaces before suggesting direct edits.
- Until the user confirms, the skill should only recommend an action.

## Reporting Contract

- Every user-facing triage report must include note-level lists, not only counts.
- Notes shown as processed must include:
  - `source_note_id`
  - title
  - short summary
  - clickable compiled path when available
  - optional normalized path when useful
  - and must be grouped by project, using `unrouted` when no project is assigned yet
- Notes shown as not ready for downstream must include:
  - `source_note_id`
  - title
  - short summary
  - current status (`needs_review`, `ambiguous`, or `pending_project`)
  - clickable compiled path
- Notes shown as ready for dry-run must include:
  - `source_note_id`
  - title
  - short summary
  - proposed project
  - clickable compiled path
- If a category is empty, say it is empty explicitly.

## Review Questions

- Does the note clearly belong to one project?
- Is there enough evidence to justify that routing?
- Should this note stay in review instead of being dispatched?
- If dispatched later, what exact downstream inbox path should receive it?
- If the note implies follow-up work in another repository, should that request go through the downstream `project-router` inbox instead of a direct edit?
