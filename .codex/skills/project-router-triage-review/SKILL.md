---
name: project-router-triage-review
description: Analyze normalized VoiceNotes notes inside Project Router, propose project routing, surface ambiguity, and ask the user for confirmation before any note is written to another project. Use when reviewing captured notes, deciding whether a note belongs in a downstream inbox, or refining triage rules without dispatching automatically.
---

# Project Router Triage Review

## Overview

Use this skill to review normalized notes in Project Router for VoiceNotes and recommend the next step. This skill is analysis-only by default. It must not send, move, or dispatch a note to any downstream project without explicit user confirmation in the current conversation.

## Mandatory Rule

- Never dispatch automatically.
- Never treat a high confidence score as permission to write.
- Always show the proposed destination, confidence, and short reasoning.
- Always ask the user to confirm before any downstream write.
- Treat confirmation as note-specific by `source_note_id`, not as a global approval for the whole queue.
- When presenting review results, never rely on filenames alone.
- For every note you mention, include title, a short summary, and a clickable path to open the compiled note when available.

## Review Workflow

1. Read the normalized note and its frontmatter.
2. Identify:
   - capture kind
   - intent
   - probable target project
   - probable note type
   - confidence
   - ambiguity or missing context
3. Produce one of these outcomes:
   - `keep_in_review`
   - `needs_review`
   - `pending_project`
   - `propose_dispatch`
4. Before any dispatch proposal, make sure there is a compiled package with a concise summary, extracted tasks, decisions, open questions, and evidence spans:
   - `python3 scripts/project_router.py compile --note-id <source_note_id>`
5. If the outcome is `propose_dispatch`, stop and ask for confirmation. Do not write the note yet.
6. If multiple pending notes appear to describe the same theme, run `python3 scripts/project_router.py discover` and use the suggested buckets and relationships before proposing a new project or rule.

## Expected Output

Keep the recommendation short and operational:

```text
Proposed project: home_renovation
Confidence: 0.92
Reason: matched renovation and contractor planning language
Next step: ask user whether to dispatch to the Home Renovation inbox
```

When the user confirms, restate the exact `source_note_id` values being approved before any real dispatch command is run.

When reporting multiple notes, always group them into these sections:

- `Processed in pipeline`
  - group notes by project first
  - use the routed project when present; otherwise group under `unrouted`
- `Not ready for downstream`
- `Ready for dry-run`

For `Not ready for downstream`, always include the current status (`needs_review`, `ambiguous`, or `pending_project`) together with title, short summary, and link.

## Safe Defaults

- If more than one destination is plausible, mark the note as ambiguous.
- If the transcript is too vague, keep it in review.
- If no current project or rule fits yet, put the note in `pending_project` for later analysis.
- Use `user_keywords`, `thread_id`, `continuation_of`, and `related_note_ids` to preserve context across follow-up notes.
- Keep `capture_kind`, `intent`, and `destination` separate. A note can be a `meeting_recording` with `decision_log` intent and still stay in `pending_project`.
- Prefer reviewing the compiled package when available, because it is the best representation of what a downstream project will receive.
- Prefer false negatives over wrong dispatches.
- If the user has not confirmed, leave the note in this repository only.

## References

- Read `references/triage-contract.md` for the local queue model and confirmation rules.
