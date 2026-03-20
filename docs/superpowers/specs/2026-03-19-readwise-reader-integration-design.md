# Readwise Reader Integration Design

**Date:** 2026-03-19
**Status:** Approved
**Author:** Mario + Claude
**Related plan:** `Knowledge/runbooks/plans/readwise-source-integration.plan.md`

## Summary

Add Readwise Reader as a new data source for the Project Router pipeline. Documents saved in Reader (articles, PDFs, newsletters, tweets, etc.) flow through the same `sync → normalize → triage → compile → dispatch` pipeline as VoiceNotes captures, classified by keywords and routed to downstream project inboxes.

## Goals

- Each template user authenticates with their own Readwise access token
- Reader documents are synced incrementally (idempotent, no duplicates)
- All Reader metadata is preserved during normalization
- Zero external dependencies — stdlib only
- Existing pipeline commands remain backward compatible
- Feature is upstreamable to the shared template (not private-only)

## Non-Goals

- MCP-based interactive querying (can be added later as an independent enhancement)
- Standalone classic Readwise highlight ingestion (Reader documents are v1 scope; classic highlights are a follow-up once the source contract is stable)
- Real-time webhooks (batch sync is sufficient for the current workflow)
- Write-back actions to Readwise (save, move, tag, archive)
- Dependency on `@readwise/cli` npm package or MCP for runtime operation

---

## 1. Sync Client

### New files

- `scripts/readwise_client.py` — CLI entry point (thin wrapper)
- `src/project_router/readwise_client.py` — sync logic module

### Authentication

- **Primary env var:** `READWISE_ACCESS_TOKEN` in `.env.local`
- **Compatibility alias:** also honor `READWISE_TOKEN` if `READWISE_ACCESS_TOKEN` is unset
- **Validation:** `GET https://readwise.io/api/v2/auth/` → expects HTTP 204
- **Fail-closed:** `SystemExit` with clear message when token is missing or invalid
- Token is per-user, obtained at `https://readwise.io/access_token`

### API

- **Base URL:** `https://readwise.io/api/v3/`
- **List endpoint:** `GET /list/` with query params
- **Pagination:** `nextPageCursor` (null when exhausted), max 100 docs per page
- **Rate limit:** 20 requests/minute on `/list/` — respect `Retry-After` header with sleep+retry
- **Incremental sync:** `updatedAfter` parameter (ISO 8601)

### HTTP implementation

Uses `urllib.request` from stdlib. This is a deliberate divergence from VoiceNotes which uses `curl` via `subprocess.run`. The Reader API is standard REST with Bearer token auth — `urllib.request` is simpler and avoids the curl dependency.

```python
headers = {
    "Authorization": f"Token {access_token}",
    "Accept": "application/json",
}
```

### Sync state

File: `state/readwise_sync_state.json` (provider-specific, separate from VoiceNotes' `state/sync_state.json`)

```json
{
  "last_synced_at": "2026-03-19T10:00:00Z",
  "last_synced_ids": ["rw_12345", "rw_12346"]
}
```

**Important divergence from VoiceNotes:** The checkpoint tracks `updated_at` (not `created_at`) because the Readwise `updatedAfter` parameter returns documents **modified** after a timestamp. A document that gains new highlights or notes will reappear in subsequent syncs. The VoiceNotes client tracks `created_at` because its API filters by creation time. The merge logic shape is the same (watermark + ID dedup), but the semantic watermark key differs.

### Note ID prefix

The `rw_` prefix is applied at **sync time** in the raw filename, mirroring how the filesystem source bakes `fs_` into the note ID at ingest. The prefix persists through normalization as `source_note_id: "rw_{doc_id}"`. This differs from VoiceNotes which uses raw IDs without a prefix.

### Raw filename and idempotent overwrite

Path: `data/raw/readwise/{created_at_timestamp}--rw_{doc_id}.json`

The filename timestamp uses the document's **`created_at`** (stable, immutable) — not `updated_at`. This ensures the filename never changes when a document is edited in Reader. When an incremental sync re-fetches an updated document (because `updated_at` > checkpoint), the sync client:

1. Looks up the existing raw file by `rw_{doc_id}` suffix using `existing_export_path()` (same glob pattern as VoiceNotes)
2. Compares the new payload against the existing file
3. **Overwrites in-place** if the payload changed, or skips if identical

This preserves the repository's one-canonical-raw-copy model: one `source_note_id` = one raw file, always at the same path. The `updated_at` timestamp is only used as the **sync checkpoint watermark**, never in filenames.

```json
{
  "source": "readwise",
  "source_endpoint": "reader/list",
  "source_item_type": "reader_document",
  "synced_at": "2026-03-19T10:00:00Z",
  "document": {
    "id": "01abc123",
    "title": "Article Title",
    "author": "Author Name",
    "url": "https://reader.readwise.io/...",
    "source_url": "https://original-article.com/...",
    "category": "article",
    "location": "archive",
    "tags": {"tag1": "tag_id_1", "tag2": "tag_id_2"},
    "notes": "User notes...",
    "summary": "Auto-generated summary...",
    "word_count": 1234,
    "reading_progress": 0.75,
    "site_name": "Example.com",
    "image_url": "https://...",
    "published_date": "2026-03-01",
    "created_at": "2026-03-15T08:00:00Z",
    "updated_at": "2026-03-18T14:30:00Z",
    "saved_at": "2026-03-15T08:00:00Z",
    "last_moved_at": "2026-03-16T10:00:00Z",
    "first_opened_at": "2026-03-15T09:00:00Z",
    "last_opened_at": "2026-03-18T14:00:00Z",
    "parent_id": null,
    "reading_time": 8
  }
}
```

### CLI commands

```bash
# Incremental sync (uses checkpoint)
python3 scripts/readwise_client.py sync --output-dir ./data/raw/readwise

# First sync with time window
python3 scripts/readwise_client.py sync --output-dir ./data/raw/readwise --window-days 30

# Full history
python3 scripts/readwise_client.py sync --output-dir ./data/raw/readwise --full-history

# Filter by category
python3 scripts/readwise_client.py sync --output-dir ./data/raw/readwise --category article

# Filter by location
python3 scripts/readwise_client.py sync --output-dir ./data/raw/readwise --location archive
```

CLI flags mirror VoiceNotes where applicable: `--window-days`, `--full-history`, `--max-pages`, `--overwrite`, `--state-file`, `--no-checkpoint`.

Additional Reader-specific filters: `--category` (article, email, pdf, epub, tweet, video), `--location` (new, later, archive, feed), `--tag`.

---

## 2. Source Registration

### `src/project_router/services/paths.py`

```python
READWISE_SOURCE = "readwise"
KNOWN_SOURCES = frozenset({VOICE_SOURCE, PROJECT_ROUTER_SOURCE, FILESYSTEM_SOURCE, READWISE_SOURCE})

# Review queue statuses for Readwise (same as VoiceNotes)
READWISE_REVIEW_STATUSES = ("ambiguous", "needs_review", "pending_project")
```

### Source name aliases in `normalize_source_name()`

```python
"reader": READWISE_SOURCE,
"rw": READWISE_SOURCE,
```

### Directory helpers requiring new branches

The `--source` CLI argument auto-updates via `KNOWN_SOURCES`, but the following functions use explicit per-source `if/elif` chains and **will crash** without a Readwise branch:

| Function | File | Expected directory |
|---|---|---|
| `raw_dir_for()` | `cli.py` | `data/raw/readwise/` |
| `normalized_dir_for()` | `cli.py` | `data/normalized/readwise/` |
| `compiled_dir_for()` | `cli.py` | `data/compiled/readwise/` |
| `review_dir_for()` | `services/notes.py` | `data/review/readwise/{status}/` |
| `review_queue_directories()` | `services/notes.py` | iterate `READWISE_REVIEW_STATUSES` |
| `iter_source_dirs()` | `services/status.py` | yield readwise raw/normalized/compiled dirs |
| `compute_pipeline_status()` | `services/status.py` | count rows for readwise source |
| `ensure_layout()` | `cli.py` | create readwise directories at startup |

Each needs a simple `if source == READWISE_SOURCE:` returning the appropriate path under the standard layout.

---

## 3. Normalizer

### New branch in `normalized_note_from_raw()` (`cli.py`)

Added as `elif source == READWISE_SOURCE:` following the existing pattern.

### Field mapping: Reader → normalized metadata

| Reader field | Metadata field | Notes |
|---|---|---|
| `id` | `source_note_id` | Prefixed as `rw_{id}` (applied at sync time) |
| — | `source_item_type` | `"reader_document"` (fixed value for v1) |
| `title` | `title` | |
| `category` | `reader_category` (new) | `article`, `email`, `pdf`, `epub`, `tweet`, `video` |
| `source_url` | `source_url` (new) | Original article/doc URL |
| `author` | `author` (new) | |
| `tags` | `tags` | Converted from `{tag: id}` object to `["tag1", "tag2"]` list |
| `location` | `reader_location` (new) | `new`, `later`, `archive`, `feed` |
| `notes` | Included in body | User's personal notes |
| `summary` | `summary_available: True`, `summary_source: "reader"` | |
| `word_count` | `word_count` (new) | |
| `reading_progress` | `reading_progress` (new) | 0.0–1.0 |
| `created_at` | `created_at` | |
| `updated_at` | `recorded_at` | Best proxy for "when last active" |
| `site_name` | `site_name` (new) | |
| `published_date` | `published_date` (new) | |

New fields are additive — they don't affect existing pipeline logic which only depends on the base metadata set.

### Normalized body format

```markdown
# {title}

**Source:** {source_url}
**Author:** {author}
**Category:** {category}

{summary if available}

## Notes
{user notes if present}

## Highlights
{list of highlights if present}
```

### Highlights strategy (v1: filter out child highlights at sync time)

The Reader API models highlights as separate documents with `parent_id` set to the parent document. In v1, **child highlights are excluded from the pipeline entirely:**

1. **During sync:** Documents with a non-null `parent_id` are **skipped** — they are not written to `data/raw/readwise/`
2. **Only top-level documents enter the pipeline** — `source_item_type` remains `"reader_document"` for all synced items, consistent with the non-goal of standalone highlight ingestion
3. **No highlight-specific normalization, triage, or dispatch logic** — the queue and dispatch surface stays 1:1 with saved articles/documents

This keeps v1 scope clean: one saved Reader article = one pipeline item. A future enhancement can opt into child highlight ingestion (either aggregated under parents or as standalone notes) once the base source contract is stable.

---

## 4. Bootstrap and Configuration

### `.env.example`

Add one line:

```
READWISE_ACCESS_TOKEN=replace-with-your-readwise-token
```

### `scripts/bootstrap_local.py`

No code changes needed — the script copies `.env.example` → `.env.local` verbatim, so the Readwise placeholder is included automatically.

### Session opener skill

Add a conditional block after the VoiceNotes sync in all three skill surfaces (`.agents/`, `.claude/`, `.codex/`):

```
If READWISE_ACCESS_TOKEN is configured in .env.local:
  python3 scripts/readwise_client.py sync --output-dir ./data/raw/readwise
  python3 scripts/project_router.py normalize --source readwise
  python3 scripts/project_router.py triage --source readwise
  python3 scripts/project_router.py compile --source readwise
```

If the token is missing or still set to the placeholder value, **skip with an explicit explanation** (e.g., "Readwise sync skipped: READWISE_ACCESS_TOKEN not configured in .env.local"). This matches the existing session opener behavior for VoiceNotes, which tells the operator why sync was skipped rather than silently hiding misconfiguration.

### CLAUDE.md and AGENTS.md session defaults

The "Session Defaults" sections in both files must be updated to reference Readwise alongside VoiceNotes. Add a new step between the VoiceNotes sync (step 4) and the filesystem ingest (step 5):

```
4b. If READWISE_ACCESS_TOKEN exists in .env.local, use:
   - python3 scripts/readwise_client.py sync --output-dir ./data/raw/readwise
   - python3 scripts/project_router.py normalize --source readwise
   - python3 scripts/project_router.py triage --source readwise
   - python3 scripts/project_router.py compile --source readwise
```

---

## 5. Files Changed

### New files

| File | Purpose | Ownership class |
|---|---|---|
| `scripts/readwise_client.py` | CLI entry point (thin wrapper) | `template_owned` |
| `src/project_router/readwise_client.py` | Sync client logic | `template_owned` |

### Edited files

| File | Change |
|---|---|
| `src/project_router/services/paths.py` | `READWISE_SOURCE` constant, `READWISE_REVIEW_STATUSES`, alias in `normalize_source_name()` |
| `src/project_router/cli.py` | New `elif` branch in `normalized_note_from_raw()`, `raw_dir_for()`, `normalized_dir_for()`, `compiled_dir_for()`, `ensure_layout()` |
| `src/project_router/services/notes.py` | New branch in `review_dir_for()`, `review_queue_directories()` |
| `src/project_router/services/status.py` | New branch in `iter_source_dirs()`, `compute_pipeline_status()` |
| `.env.example` | Add `READWISE_ACCESS_TOKEN` placeholder |
| `CLAUDE.md` | Add Readwise sync to Session Defaults |
| `AGENTS.md` | Add Readwise sync to Session Defaults |
| `.agents/skills/project-router-session-opener/SKILL.md` | Add Readwise sync block |
| `.claude/skills/project-router-session-opener/SKILL.md` | Add Readwise sync block |
| `.codex/skills/project-router-session-opener/SKILL.md` | Add Readwise sync block |
| `repo-governance/customization-contracts.json` | Declare new files with ownership class |
| `tests/test_project_router.py` | Tests for Readwise normalization, sync state, directory helpers |

### Unchanged

- `triage_command`, `compile_command`, `dispatch_command` — source-agnostic (no per-source branches)
- `projects/registry.shared.json` — keyword classification works as-is
- `scripts/bootstrap_local.py` — no code changes (`.env.example` copy handles it)
- All existing tests — no breakage

---

## 6. Constraints

- **Zero external dependencies** — uses `urllib.request` from stdlib
- **Rate limit compliance** — 20 req/min on `/list/`, respect `Retry-After` with sleep+retry
- **Idempotent** — re-running sync overwrites-in-place if payload changed, skips if identical; one `source_note_id` = one canonical raw file (filename uses stable `created_at`, not mutable `updated_at`)
- **First sync requires explicit scope** — `--window-days`, `--from/--to`, or `--full-history` (same safety as VoiceNotes)
- **No auto-dispatch** — Readwise documents follow the same review → decide → dispatch flow
- **Read-only** — sync never calls save/move/tag/archive endpoints on Readwise

---

## 7. Testing Strategy

- Unit tests for `normalized_note_from_raw()` with mock Readwise raw payloads
- Unit tests for sync state merge logic (using `updated_at` watermark)
- Unit tests for note ID prefixing (`rw_` applied at sync time)
- Unit tests for Reader tag format conversion (object → list)
- Unit tests for directory helpers returning correct readwise paths
- Unit tests for status command including readwise counts
- Integration test: raw Readwise JSON → normalize → verify metadata fields
- Regression pass: existing VoiceNotes and filesystem tests remain green
- No network calls in tests — mock raw payloads in temp directories

---

## 8. Governance and Validation

Before merging, run the full governance check suite:

```bash
python3 scripts/check_customization_contracts.py
python3 scripts/check_repo_ownership.py
python3 scripts/check_sync_manifest_alignment.py
python3 scripts/check_knowledge_structure.py
python3 scripts/check_agent_surface_parity.py --pre-publish
python3 -m pytest tests/test_project_router.py -v -k "readwise or sync or normalize or status"
python3 scripts/project_router.py status
python3 scripts/project_router.py context
```

---

## 9. Upstream Delivery

This is a private-derived repository. The reusable implementation must be upstreamed to `marioGusmao/project-router-template`:

1. Implement and validate locally in a feature branch
2. Create upstream PR to the shared template repository
3. Ensure all new files are declared in `customization-contracts.json` as `template_owned`
4. Verify downstream adoption: a fresh derived repo can enable Readwise via normal template sync + `.env.local` token setup
5. No private-only patches should be required for ordinary template users

---

## 10. Risks and Rollback

| Risk | Mitigation | Rollback |
|---|---|---|
| New source crashes existing pipeline commands | Every per-source switch gets a readwise branch; full regression tests | Remove `readwise` from `KNOWN_SOURCES` and delete source-specific wiring |
| Rate limit sensitivity on Reader API | Respect `Retry-After`, cap `--max-pages`, sleep between requests | Reduce default sync window or disable auto-sync in session opener |
| Child highlights doubling the queue | v1 filters out child highlights at sync time (`parent_id != null` → skip) | Already scoped out of v1 |
| Scope creep to classic highlights | Explicitly deferred; ship Reader documents first | Track as separate follow-up issue |
| Private-only implementation never reaches template users | P06 upstream delivery is an explicit phase, not optional | Hold at upstream review stage if boundaries aren't clean |
