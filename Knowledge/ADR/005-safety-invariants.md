# ADR-005: Safety Invariants

**Status:** accepted

**Date:** 2026-03-14

## Context

The pipeline handles user notes that flow through multiple stages before reaching downstream projects. Each stage transforms or enriches the data. Several invariants must hold across the entire pipeline to prevent data loss, unauthorized dispatch, or corrupted state.

These invariants apply to both human operators and AI agents working with the pipeline.

## Decision

Three core safety invariants:

### 1. Compile Before Dispatch

Never dispatch a normalized note directly. Always compile first, then dispatch from the compiled artifact.

**Why:** Normalized notes contain raw transcription with basic frontmatter. Compiled notes contain enriched summaries, extracted facts, tasks, and decisions. Downstream projects expect the compiled format. Dispatching uncompiled notes would break downstream processing.

### 2. Note-Specific Approval

Real dispatch must name exact `source_note_id` values via `--note-id`. No batch-all shortcuts exist.

**Why:** Each note may route to a different project. Blanket approval could send notes to unintended destinations. The user must review and approve each note individually (or name specific IDs they have reviewed).

### 3. Raw Preservation

Never delete or overwrite canonical raw JSON in `data/raw/`. It is the source of truth.

**Why:** Raw JSON is the immutable record of what the VoiceNotes API returned. If any pipeline stage introduces a bug, the raw data allows full re-processing. Deleting raw data makes recovery impossible.

## Consequences

- Pipeline stages are strictly ordered: sync -> normalize -> triage -> compile -> review -> decide -> dispatch.
- Dispatch is intentionally difficult without explicit approval -- this is a feature, not a bug.
- Raw data survives any pipeline bug, enabling full re-processing from scratch.
- AI agents must follow the same invariants -- no shortcuts for automation.
- The `review` command exists specifically to support the approval workflow.
- Re-running any stage is safe (idempotent) and never destroys prior data.

## Related

- ADR-004: Fail-closed dispatch (implements invariant #1 and #2 at the dispatch stage)
