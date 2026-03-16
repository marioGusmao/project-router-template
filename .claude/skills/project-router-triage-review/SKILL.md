---
name: project-router-triage-review
description: Analyze normalized VoiceNotes notes inside Project Router, propose project routing, surface ambiguity, and ask the user for confirmation before any note is written to another project.
---

# Project Router Triage Review

Use this workflow to review normalized notes in Project Router for VoiceNotes and recommend the next step.

## Mandatory Rules

- Never auto-dispatch.
- Never treat a high confidence score as permission to write.
- Treat confirmation as note-specific by `source_note_id`.
- Never dispatch a normalized note directly.
- Compiled packages must be fresh before dispatch.
- Always show the proposed destination, confidence, and short reasoning.
- Always ask the user to confirm exact `source_note_id` values before any downstream write.
- Prefer false negatives over wrong dispatches.

## Review Workflow

1. Read the normalized note and frontmatter.
2. Identify `capture_kind`, `intent`, probable target project, probable note type, confidence, and ambiguity.
3. Produce one of: `keep_in_review`, `needs_review`, `pending_project`, `propose_dispatch`.
4. Before any dispatch proposal, make sure there is a compiled package:
   - `python3 scripts/project_router.py compile`
   - `python3 scripts/project_router.py review`
   - `python3 scripts/project_router.py dispatch --dry-run`
5. If the outcome is `propose_dispatch`, stop and ask for confirmation.
6. If several notes point to a new theme, run `python3 scripts/project_router.py discover`.

## Safe Defaults

- If more than one destination is plausible, mark the note as ambiguous.
- If the transcript is too vague, keep it in review.
- If no current project fits, put the note in `pending_project`.
- Keep `capture_kind`, `intent`, and `destination` separate.
