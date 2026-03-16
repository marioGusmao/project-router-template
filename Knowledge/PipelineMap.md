# Pipeline Map

A concrete trace of a single note through the full pipeline, showing every file that is created or modified at each stage.

## Example Note

- Source: VoiceNotes API
- Note ID: `vn_abc123`
- Timestamp: `2026-03-14T12:00:00Z`
- Filename stem: `20260314T120000Z--vn_abc123`

## Stage 1: Sync

**Command:** `python3 scripts/project_router_client.py sync --output-dir ./data/raw/voicenotes`

**Creates:**
```
data/raw/voicenotes/20260314T120000Z--vn_abc123.json
```

The raw JSON from the VoiceNotes API. This file is **canonical and immutable** -- never delete or overwrite it.

## Stage 2: Normalize

**Command:** `python3 scripts/project_router.py normalize --source voicenotes`

**Creates:**
```
data/normalized/voicenotes/20260314T120000Z--vn_abc123.md
```

Converts raw JSON into markdown with YAML frontmatter. The frontmatter contains `source_note_id`, timestamps, and any user-supplied metadata. The body contains the transcribed text.

## Stage 3: Triage

**Command:** `python3 scripts/project_router.py triage --source voicenotes`

**Modifies:**
```
data/normalized/voicenotes/20260314T120000Z--vn_abc123.md  (frontmatter updated)
```

Adds classification fields to the frontmatter: `destination` (target project), `intent` (task, reference, decision, etc.), `capture_kind` (voice_memo, quick_thought, etc.), and confidence metadata. Classification uses recording_type mapping + keyword matching + sentence-level heuristics from the shared registry.

## Stage 4: Compile

**Command:** `python3 scripts/project_router.py compile --source voicenotes`

**Creates:**
```
data/compiled/voicenotes/20260314T120000Z--vn_abc123.md
```

Generates an enriched project-ready brief. Adds extracted summary, facts, tasks, decisions, and other structured content. This is the artifact that gets dispatched -- never dispatch directly from `data/normalized/`.

## Stage 5: Review

**Command:** `python3 scripts/project_router.py review --source voicenotes`

**Creates:**
```
data/review/voicenotes/{status}/20260314T120000Z--vn_abc123.md
```

Where `{status}` is one of: `ambiguous`, `needs_review`, `pending_project`.

These are **queue view copies**, not the source of truth. The canonical metadata lives in the source-aware `data/normalized/` path.

## Stage 6: Decide

**Command:** `python3 scripts/project_router.py decide --note-id vn_abc123 --decision approve`

**Creates:**
```
state/decisions/vn_abc123.json
```

Records the user's decision (approve, reject, defer, reclassify) as a JSON packet. Decisions are keyed by `source_note_id`.

## Stage 7: Dispatch

**Command:** `python3 scripts/project_router.py dispatch --confirm-user-approval --note-id vn_abc123`

**Creates:**
```
data/dispatched/20260314T120000Z--vn_abc123.md
```

**Writes to downstream:**
```
{router_root_path}/project-router/inbox/20260314T120000Z--vn_abc123.md
```

Moves the compiled package to `data/dispatched/` and copies it into the downstream project's inbox. Requires explicit user approval. Fails closed if configuration is missing or invalid.

## Source-Aware Directory Structure

```
data/
  raw/
    voicenotes/          # Raw JSON from VoiceNotes API
    project_router/      # Raw from other project-router sources
      {project}/
  normalized/
    voicenotes/          # Normalized markdown (source of truth for metadata)
    project_router/
      {project}/
  compiled/
    voicenotes/          # Compiled briefs ready for dispatch
    project_router/
      {project}/
  review/
    voicenotes/          # Queue views (not source of truth)
      ambiguous/
      needs_review/
      pending_project/
    project_router/
      parse_errors/
      needs_review/
      pending_project/
  dispatched/            # Successfully dispatched packages
state/
  decisions/             # User decision packets (JSON)
```
