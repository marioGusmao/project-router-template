# Readwise Reader Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Readwise Reader as a pipeline data source so template users can sync saved articles into the normalize → triage → compile → dispatch flow.

**Architecture:** New sync client (`readwise_client.py`) fetches Reader documents via REST API with `urllib.request`. Source registration wires `readwise` through all per-source directory helpers, normalizer, and status counters. Session opener skills gain a conditional Readwise sync block.

**Tech Stack:** Python 3 stdlib only (`urllib.request`, `json`, `argparse`, `pathlib`). No external dependencies.

**Spec:** `docs/superpowers/specs/2026-03-19-readwise-reader-integration-design.md`

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `src/project_router/readwise_client.py` | Create | Sync client: auth, pagination, rate limits, raw storage, sync state |
| `scripts/readwise_client.py` | Create | CLI entry point (thin wrapper calling `readwise_client.main()`) |
| `src/project_router/services/paths.py` | Modify | `READWISE_SOURCE`, `READWISE_REVIEW_STATUSES`, alias in `normalize_source_name()` |
| `src/project_router/cli.py` | Modify | `ensure_layout()`, `raw_dir_for()`, `normalized_dir_for()`, `compiled_dir_for()`, `load_raw_recording()`, `normalize_command()` note_id extraction, `normalized_note_from_raw()` |
| `src/project_router/services/notes.py` | Modify | `review_dir_for()`, `review_queue_directories()` |
| `src/project_router/services/status.py` | Modify | `iter_source_dirs()`, `compute_pipeline_status()` |
| `.env.example` | Modify | Add `READWISE_ACCESS_TOKEN` placeholder |
| `CLAUDE.md` | Modify | Add Readwise to Session Defaults step 4b |
| `AGENTS.md` | Modify | Add Readwise to Session Defaults step 4b |
| `.agents/skills/project-router-session-opener/SKILL.md` | Modify | Add Readwise sync block after step 6 |
| `.claude/skills/project-router-session-opener/SKILL.md` | Modify | Add Readwise sync block after step 6 |
| `.codex/skills/project-router-session-opener/SKILL.md` | Modify | Add Readwise sync block after step 6 |
| `tests/test_project_router.py` | Modify | Add Readwise tests: normalize, directory helpers, status |

---

## Task 1: Source Constants and Aliases

**Files:**
- Modify: `src/project_router/services/paths.py:73-104`
- Test: `tests/test_project_router.py`

- [ ] **Step 1: Write failing test — source constant exists**

```python
# In tests/test_project_router.py, add at the bottom of the file:
class TestReadwiseSourceRegistration(unittest.TestCase):
    def test_readwise_source_in_known_sources(self):
        from src.project_router.services.paths import KNOWN_SOURCES, READWISE_SOURCE
        self.assertEqual(READWISE_SOURCE, "readwise")
        self.assertIn("readwise", KNOWN_SOURCES)

    def test_readwise_review_statuses_defined(self):
        from src.project_router.services.paths import READWISE_REVIEW_STATUSES
        self.assertEqual(READWISE_REVIEW_STATUSES, ("ambiguous", "needs_review", "pending_project"))

    def test_normalize_source_name_readwise_aliases(self):
        from src.project_router.services.paths import normalize_source_name
        self.assertEqual(normalize_source_name("readwise"), "readwise")
        self.assertEqual(normalize_source_name("reader"), "readwise")
        self.assertEqual(normalize_source_name("rw"), "readwise")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_project_router.py -v -k "TestReadwiseSourceRegistration"`
Expected: FAIL — `ImportError` for `READWISE_SOURCE`

- [ ] **Step 3: Implement source constants**

In `src/project_router/services/paths.py`, after the existing source constants (line 76):

```python
READWISE_SOURCE = "readwise"
KNOWN_SOURCES = frozenset({VOICE_SOURCE, PROJECT_ROUTER_SOURCE, FILESYSTEM_SOURCE, READWISE_SOURCE})
```

Add review statuses after `FILESYSTEM_REVIEW_STATUSES` (line 82):

```python
READWISE_REVIEW_STATUSES = ("ambiguous", "needs_review", "pending_project")
```

Add aliases in `normalize_source_name()` (inside the `aliases` dict, line ~96):

```python
"reader": READWISE_SOURCE,
"rw": READWISE_SOURCE,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_project_router.py -v -k "TestReadwiseSourceRegistration"`
Expected: PASS (3 tests)

- [ ] **Step 5: Run full test suite for regressions**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: All existing tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/project_router/services/paths.py tests/test_project_router.py
git commit -m "feat: register readwise as a known source with aliases and review statuses"
```

---

## Task 2: Directory Helpers

**Files:**
- Modify: `src/project_router/cli.py:129-210`
- Modify: `src/project_router/services/notes.py:251-276`
- Modify: `src/project_router/services/status.py:75-104`
- Test: `tests/test_project_router.py`

- [ ] **Step 1: Write failing tests — directory helpers return correct paths**

```python
class TestReadwiseDirectoryHelpers(unittest.TestCase):
    def test_raw_dir_for_readwise(self):
        from src.project_router.services.paths import RAW_DIR
        result = cli.raw_dir_for("readwise")
        self.assertEqual(result, RAW_DIR / "readwise")

    def test_normalized_dir_for_readwise(self):
        from src.project_router.services.paths import NORMALIZED_DIR
        result = cli.normalized_dir_for("readwise")
        self.assertEqual(result, NORMALIZED_DIR / "readwise")

    def test_compiled_dir_for_readwise(self):
        from src.project_router.services.paths import COMPILED_DIR
        result = cli.compiled_dir_for("readwise")
        self.assertEqual(result, COMPILED_DIR / "readwise")

    def test_review_dir_for_readwise(self):
        from src.project_router.services.paths import REVIEW_DIR
        from src.project_router.services.notes import review_dir_for
        result = review_dir_for("readwise", "ambiguous")
        self.assertEqual(result, REVIEW_DIR / "readwise" / "ambiguous")

    def test_review_dir_for_readwise_rejects_invalid_status(self):
        from src.project_router.services.notes import review_dir_for
        with self.assertRaises(SystemExit):
            review_dir_for("readwise", "parse_errors")

    def test_review_queue_directories_includes_readwise(self):
        from src.project_router.services.notes import review_queue_directories
        dirs = review_queue_directories({"readwise"})
        self.assertEqual(len(dirs), 3)  # ambiguous, needs_review, pending_project

    def test_iter_source_dirs_readwise(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            from src.project_router.services.status import iter_source_dirs
            dirs = iter_source_dirs("raw", {"readwise"})
            self.assertEqual(len(dirs), 1)
            self.assertTrue(str(dirs[0]).endswith("readwise"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_project_router.py -v -k "TestReadwiseDirectoryHelpers"`
Expected: FAIL — `SystemExit("Unsupported source 'readwise'.")`

- [ ] **Step 3: Add readwise branch to `raw_dir_for()`**

In `src/project_router/cli.py`, before the final `raise SystemExit` in `raw_dir_for()` (line ~184):

```python
    if source == READWISE_SOURCE:
        return RAW_DIR / READWISE_SOURCE
```

Add `READWISE_SOURCE` to the imports from paths at the top of cli.py.

- [ ] **Step 4: Add readwise branch to `normalized_dir_for()`**

In `src/project_router/cli.py`, before the final `raise SystemExit` in `normalized_dir_for()` (line ~197):

```python
    if source == READWISE_SOURCE:
        return NORMALIZED_DIR / READWISE_SOURCE
```

- [ ] **Step 5: Add readwise branch to `compiled_dir_for()`**

In `src/project_router/cli.py`, before the final `raise SystemExit` in `compiled_dir_for()` (line ~210):

```python
    if source == READWISE_SOURCE:
        return COMPILED_DIR / READWISE_SOURCE
```

- [ ] **Step 6: Add readwise directories to `ensure_layout()`**

In `src/project_router/cli.py`, inside the `ensure_layout()` tuple (after the filesystem review dirs, before `DISPATCHED_DIR`):

```python
        RAW_DIR / READWISE_SOURCE,
        NORMALIZED_DIR / READWISE_SOURCE,
        COMPILED_DIR / READWISE_SOURCE,
        REVIEW_DIR / READWISE_SOURCE / "ambiguous",
        REVIEW_DIR / READWISE_SOURCE / "needs_review",
        REVIEW_DIR / READWISE_SOURCE / "pending_project",
```

- [ ] **Step 7: Add readwise branch to `review_dir_for()` in notes.py**

In `src/project_router/services/notes.py`, before the final `raise SystemExit` in `review_dir_for()` (line ~265):

```python
    if source == READWISE_SOURCE:
        if status not in READWISE_REVIEW_STATUSES:
            raise SystemExit(f"Unsupported review status '{status}'.")
        return REVIEW_DIR / READWISE_SOURCE / status
```

Add `READWISE_SOURCE, READWISE_REVIEW_STATUSES` to the imports from paths at the top of notes.py.

- [ ] **Step 8: Add readwise branch to `review_queue_directories()` in notes.py**

In `src/project_router/services/notes.py`, before `return output` in `review_queue_directories()` (line ~276):

```python
    if READWISE_SOURCE in sources:
        output.extend(review_dir_for(READWISE_SOURCE, status) for status in READWISE_REVIEW_STATUSES)
```

- [ ] **Step 9: Add readwise branch to `iter_source_dirs()` in status.py**

In `src/project_router/services/status.py`, after the filesystem block in `iter_source_dirs()` (line ~103):

```python
    if READWISE_SOURCE in sources:
        if kind == "raw":
            output.append(RAW_DIR / READWISE_SOURCE)
        elif kind == "normalized":
            output.append(NORMALIZED_DIR / READWISE_SOURCE)
        elif kind == "compiled":
            output.append(COMPILED_DIR / READWISE_SOURCE)
```

Add `READWISE_SOURCE` to the imports from paths at the top of status.py.

- [ ] **Step 10: Add readwise branch to `load_raw_recording()` in cli.py**

In `src/project_router/cli.py`, inside `load_raw_recording()` after the `PROJECT_ROUTER_SOURCE` check (line ~1096), before the `"recording" in payload` check:

```python
        if payload.get("source") == READWISE_SOURCE:
            return payload, "readwise-json"
```

Without this, Readwise raw JSON files fall through to the VoiceNotes fallback and get misinterpreted.

- [ ] **Step 11: Add readwise branch to `normalize_command()` note_id extraction**

In `src/project_router/cli.py`, inside `normalize_command()` after the `FILESYSTEM_SOURCE` elif (line ~1446), before the `else:` fallback:

```python
        elif detected_source == READWISE_SOURCE:
            document = raw_payload.get("document") or {}
            note_id = document.get("id")
            if note_id:
                note_id = f"rw_{note_id}"
```

Without this, Readwise notes would try `raw_payload.get("recording")` which is `None`, making `note_id` be `None` and the note silently skipped.

- [ ] **Step 12: Update `prepare_repo()` in tests**

In `tests/test_project_router.py`, add readwise directories to `prepare_repo()` (after the filesystem entries, before `dispatched`):

```python
        root / "data" / "raw" / "readwise",
        root / "data" / "normalized" / "readwise",
        root / "data" / "compiled" / "readwise",
        root / "data" / "review" / "readwise" / "ambiguous",
        root / "data" / "review" / "readwise" / "needs_review",
        root / "data" / "review" / "readwise" / "pending_project",
```

- [ ] **Step 13: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_project_router.py -v -k "TestReadwiseDirectoryHelpers"`
Expected: PASS (7 tests)

- [ ] **Step 14: Run full test suite for regressions**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: All tests PASS

- [ ] **Step 15: Commit**

```bash
git add src/project_router/cli.py src/project_router/services/notes.py src/project_router/services/status.py tests/test_project_router.py
git commit -m "feat: wire readwise through directory helpers, raw loader, note_id extraction, and review queues"
```

---

## Task 3: Status Command — Readwise Counts

**Files:**
- Modify: `src/project_router/services/status.py:159-231`
- Test: `tests/test_project_router.py`

- [ ] **Step 1: Write failing test — status includes readwise counts**

```python
class TestReadwiseStatus(unittest.TestCase):
    def test_status_includes_readwise_counts(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            from src.project_router.services.status import compute_pipeline_status
            result = compute_pipeline_status({"readwise"})
            self.assertIn("readwise", result["raw"])
            self.assertIn("readwise", result["normalized"])
            self.assertIn("readwise", result["compiled"])
            self.assertIn("readwise", result["review"])
            self.assertEqual(result["raw"]["readwise"], 0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_project_router.py -v -k "TestReadwiseStatus"`
Expected: FAIL — `KeyError: 'readwise'`

- [ ] **Step 3: Add readwise rows to `compute_pipeline_status()`**

In `src/project_router/services/status.py`, inside `compute_pipeline_status()`:

After the filesystem count lines (line ~184), add:

```python
    readwise_raw = count_raw(raw_dir_for(READWISE_SOURCE)) if READWISE_SOURCE in sources else 0
    readwise_normalized = count_markdown(normalized_dir_for(READWISE_SOURCE)) if READWISE_SOURCE in sources else 0
    readwise_compiled = count_markdown(compiled_dir_for(READWISE_SOURCE)) if READWISE_SOURCE in sources else 0
```

In the `summary` dict, add `"readwise"` keys to each section:

```python
        "raw": {
            ...existing...,
            "readwise": readwise_raw,
        },
        "normalized": {
            ...existing...,
            "readwise": readwise_normalized,
        },
        "compiled": {
            ...existing...,
            "readwise": readwise_compiled,
        },
        "review": {
            ...existing...,
            "readwise": {
                "ambiguous": count_markdown(review_dir_for(READWISE_SOURCE, "ambiguous")) if READWISE_SOURCE in sources else 0,
                "pending_project": count_markdown(review_dir_for(READWISE_SOURCE, "pending_project")) if READWISE_SOURCE in sources else 0,
                "needs_review": count_markdown(review_dir_for(READWISE_SOURCE, "needs_review")) if READWISE_SOURCE in sources else 0,
            },
        },
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_project_router.py -v -k "TestReadwiseStatus"`
Expected: PASS

- [ ] **Step 5: Run full test suite for regressions**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/project_router/services/status.py tests/test_project_router.py
git commit -m "feat: add readwise counts to pipeline status output"
```

---

## Task 4: Normalizer — Readwise Raw → Normalized Markdown

**Files:**
- Modify: `src/project_router/cli.py:1132-1301` (in `normalized_note_from_raw()` — insert after filesystem branch ~line 1252, before VoiceNotes fallback ~line 1254)
- Test: `tests/test_project_router.py`

- [ ] **Step 1: Write failing test — normalize a Readwise raw payload**

```python
class TestReadwiseNormalize(unittest.TestCase):
    def _readwise_raw_payload(self, **overrides):
        doc = {
            "id": "abc123",
            "title": "Test Article",
            "author": "Jane Doe",
            "url": "https://reader.readwise.io/abc123",
            "source_url": "https://example.com/article",
            "category": "article",
            "location": "archive",
            "tags": {"python": "tag_1", "testing": "tag_2"},
            "notes": "My notes on this",
            "summary": "A test article summary.",
            "word_count": 500,
            "reading_progress": 0.8,
            "site_name": "Example",
            "published_date": "2026-03-01",
            "created_at": "2026-03-15T08:00:00Z",
            "updated_at": "2026-03-18T14:30:00Z",
            "parent_id": None,
        }
        doc.update(overrides)
        return {
            "source": "readwise",
            "source_endpoint": "reader/list",
            "source_item_type": "reader_document",
            "synced_at": "2026-03-19T10:00:00Z",
            "document": doc,
        }

    def test_normalize_readwise_creates_markdown(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            raw_path = root / "data" / "raw" / "readwise" / "20260315T080000Z--rw_abc123.json"
            raw_path.write_text(json.dumps(self._readwise_raw_payload()), encoding="utf-8")
            result = cli.main(["normalize", "--source", "readwise"])
            self.assertEqual(result, 0)
            normalized_dir = root / "data" / "normalized" / "readwise"
            md_files = list(normalized_dir.glob("*.md"))
            self.assertEqual(len(md_files), 1)

    def test_normalize_readwise_metadata_fields(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            raw_path = root / "data" / "raw" / "readwise" / "20260315T080000Z--rw_abc123.json"
            raw_path.write_text(json.dumps(self._readwise_raw_payload()), encoding="utf-8")
            cli.main(["normalize", "--source", "readwise"])
            normalized_dir = root / "data" / "normalized" / "readwise"
            md_file = list(normalized_dir.glob("*.md"))[0]
            metadata, body = cli.read_note(md_file)
            self.assertEqual(metadata["source"], "readwise")
            self.assertEqual(metadata["source_note_id"], "rw_abc123")
            self.assertEqual(metadata["source_item_type"], "reader_document")
            self.assertEqual(metadata["title"], "Test Article")
            self.assertEqual(metadata["author"], "Jane Doe")
            self.assertEqual(metadata["source_url"], "https://example.com/article")
            self.assertIn("python", metadata["tags"])
            self.assertIn("testing", metadata["tags"])
            self.assertEqual(metadata["reader_location"], "archive")
            self.assertEqual(metadata["reader_category"], "article")
            self.assertTrue(metadata["summary_available"])
            self.assertEqual(metadata["summary_source"], "reader")

    def test_normalize_readwise_tags_converted_from_object(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            raw_path = root / "data" / "raw" / "readwise" / "20260315T080000Z--rw_abc123.json"
            raw_path.write_text(json.dumps(self._readwise_raw_payload()), encoding="utf-8")
            cli.main(["normalize", "--source", "readwise"])
            md_file = list((root / "data" / "normalized" / "readwise").glob("*.md"))[0]
            metadata, _ = cli.read_note(md_file)
            self.assertIsInstance(metadata["tags"], list)
            self.assertIn("python", metadata["tags"])

    def test_normalize_readwise_body_includes_title_and_summary(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            raw_path = root / "data" / "raw" / "readwise" / "20260315T080000Z--rw_abc123.json"
            raw_path.write_text(json.dumps(self._readwise_raw_payload()), encoding="utf-8")
            cli.main(["normalize", "--source", "readwise"])
            md_file = list((root / "data" / "normalized" / "readwise").glob("*.md"))[0]
            _, body = cli.read_note(md_file)
            self.assertIn("# Test Article", body)
            self.assertIn("A test article summary.", body)
            self.assertIn("My notes on this", body)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_project_router.py -v -k "TestReadwiseNormalize"`
Expected: FAIL — no readwise branch in `normalized_note_from_raw()`

- [ ] **Step 3: Implement the readwise normalizer branch**

In `src/project_router/cli.py`, inside `normalized_note_from_raw()`, add a new branch after the filesystem block (`elif source == FILESYSTEM_SOURCE:`) and before the VoiceNotes fallback (`recording = dict(raw_payload.get("recording") or {})`):

```python
    if source == READWISE_SOURCE:
        document = dict(raw_payload.get("document") or {})
        raw_id = str(document.get("id") or "").strip()
        note_id = require_valid_note_id(f"rw_{raw_id}" if raw_id else "")
        title = document.get("title") or f"Readwise {raw_id}"
        created_at = document.get("created_at")
        note_dir = normalized_dir_for(READWISE_SOURCE)
        normalized_path = existing_artifact_path(note_dir, note_id, ".md") or (
            note_dir / f"{normalize_timestamp(created_at)}--{note_id}.md"
        )

        # Convert tags from {name: id} object to list of names
        raw_tags = document.get("tags") or {}
        tags = sorted(raw_tags.keys()) if isinstance(raw_tags, dict) else list(raw_tags)

        has_summary = bool(document.get("summary"))
        metadata = {
            "source": READWISE_SOURCE,
            "source_project": None,
            "source_note_id": note_id,
            "source_item_type": raw_payload.get("source_item_type", "reader_document"),
            "source_endpoint": raw_payload.get("source_endpoint", "reader/list"),
            "title": title,
            "created_at": created_at,
            "recorded_at": document.get("updated_at"),
            "recording_type": None,
            "duration": None,
            "tags": tags,
            "capture_kind": None,
            "intent": None,
            "destination": None,
            "destination_reason": "",
            "user_keywords": [],
            "inferred_keywords": [],
            "transcript_format": "markdown",
            "summary_available": has_summary,
            "summary_source": "reader" if has_summary else None,
            "audio_available": False,
            "audio_local_path": None,
            "classification_basis": [],
            "derived_outputs": [],
            "thread_id": None,
            "continuation_of": None,
            "related_note_ids": [],
            "status": "normalized",
            "project": None,
            "candidate_projects": [],
            "confidence": 0.0,
            "routing_reason": "",
            "review_status": "pending",
            "requires_user_confirmation": True,
            "content_hash": None,
            "canonical_path": relative_or_absolute(normalized_path),
            "raw_payload_path": relative_or_absolute(raw_path),
            "dispatched_to": [],
            "author": document.get("author"),
            "source_url": document.get("source_url"),
            "reader_category": document.get("category"),
            "reader_location": document.get("location"),
            "word_count": document.get("word_count"),
            "reading_progress": document.get("reading_progress"),
            "site_name": document.get("site_name"),
            "published_date": document.get("published_date"),
        }

        # Build body
        parts = [f"# {title}\n"]
        source_url = document.get("source_url")
        author = document.get("author")
        category = document.get("category")
        if source_url:
            parts.append(f"**Source:** {source_url}")
        if author:
            parts.append(f"**Author:** {author}")
        if category:
            parts.append(f"**Category:** {category}")
        if parts[-1] != f"# {title}\n":
            parts.append("")  # blank line after metadata block

        summary = document.get("summary")
        if summary:
            parts.append(summary.strip())
            parts.append("")

        notes = document.get("notes")
        if notes and notes.strip():
            parts.append("## Notes")
            parts.append(notes.strip())
            parts.append("")

        body = "\n".join(parts) + "\n"
        return normalized_path, enrich_note_metadata(metadata, body), body
```

Also ensure `READWISE_SOURCE` is imported from paths at the top of cli.py (it should already be if Task 2 was done).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_project_router.py -v -k "TestReadwiseNormalize"`
Expected: PASS (4 tests)

- [ ] **Step 5: Run full test suite for regressions**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/project_router/cli.py tests/test_project_router.py
git commit -m "feat: normalize Readwise Reader raw payloads into source-aware markdown"
```

---

## Task 5: Sync Client

**Files:**
- Create: `src/project_router/readwise_client.py`
- Create: `scripts/readwise_client.py`
- Test: `tests/test_project_router.py`

- [ ] **Step 1: Write failing tests — sync client helpers**

```python
class TestReadwiseSyncClient(unittest.TestCase):
    def test_require_readwise_token_raises_when_missing(self):
        import os
        from src.project_router.readwise_client import require_access_token
        for key in ("READWISE_ACCESS_TOKEN", "READWISE_TOKEN"):
            os.environ.pop(key, None)
        with self.assertRaises(SystemExit):
            require_access_token()

    def test_require_readwise_token_primary(self):
        import os
        from src.project_router.readwise_client import require_access_token
        os.environ["READWISE_ACCESS_TOKEN"] = "test_token"
        try:
            self.assertEqual(require_access_token(), "test_token")
        finally:
            del os.environ["READWISE_ACCESS_TOKEN"]

    def test_require_readwise_token_alias(self):
        import os
        from src.project_router.readwise_client import require_access_token
        os.environ.pop("READWISE_ACCESS_TOKEN", None)
        os.environ["READWISE_TOKEN"] = "alias_token"
        try:
            self.assertEqual(require_access_token(), "alias_token")
        finally:
            del os.environ["READWISE_TOKEN"]

    def test_readwise_note_filename_uses_created_at_and_rw_prefix(self):
        from src.project_router.readwise_client import readwise_note_filename
        doc = {"id": "abc123", "created_at": "2026-03-15T08:00:00Z"}
        result = readwise_note_filename(doc)
        self.assertIn("rw_abc123", result)
        self.assertTrue(result.endswith(".json"))
        # Filename must use created_at, not updated_at
        self.assertIn("20260315", result)

    def test_readwise_raw_export_payload_structure(self):
        from src.project_router.readwise_client import raw_export_payload
        doc = {"id": "abc123", "title": "Test", "parent_id": None}
        result = raw_export_payload(doc)
        self.assertEqual(result["source"], "readwise")
        self.assertEqual(result["source_endpoint"], "reader/list")
        self.assertEqual(result["source_item_type"], "reader_document")
        self.assertIn("synced_at", result)
        self.assertEqual(result["document"], doc)

    def test_should_skip_child_highlight(self):
        from src.project_router.readwise_client import should_skip_document
        parent_doc = {"id": "abc", "parent_id": None}
        child_doc = {"id": "def", "parent_id": "abc"}
        self.assertFalse(should_skip_document(parent_doc))
        self.assertTrue(should_skip_document(child_doc))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_project_router.py -v -k "TestReadwiseSyncClient"`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Create the sync client module**

Create `src/project_router/readwise_client.py`:

```python
"""Readwise Reader sync client — fetches documents via the Reader API v3."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


BASE_URL = "https://readwise.io/api/v3"
AUTH_URL = "https://readwise.io/api/v2/auth/"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = REPO_ROOT / "state" / "readwise_sync_state.json"
NOTE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_local_env() -> None:
    load_env_file(REPO_ROOT / ".env")
    load_env_file(REPO_ROOT / ".env.local")


def require_access_token() -> str:
    load_local_env()
    token = os.environ.get("READWISE_ACCESS_TOKEN") or os.environ.get("READWISE_TOKEN")
    if not token or token == "replace-with-your-readwise-token":
        raise SystemExit(
            "READWISE_ACCESS_TOKEN is not set. "
            "Get your token at https://readwise.io/access_token and add it to .env.local"
        )
    return token


def require_valid_note_id(raw: Any, *, field: str = "source_note_id") -> str:
    note_id = str(raw or "").strip()
    if not note_id:
        raise SystemExit(f"{field} is required.")
    if not NOTE_ID_PATTERN.fullmatch(note_id):
        raise SystemExit(f"Invalid {field} '{note_id}'.")
    return note_id


def normalize_timestamp(value: str | None) -> str:
    if not value:
        return "unknown-time"
    return value.replace(":", "").replace("-", "").replace(".000000", "").replace("+00:00", "Z")


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def should_skip_document(doc: dict[str, Any]) -> bool:
    """Skip child highlights (non-null parent_id) in v1."""
    return doc.get("parent_id") is not None


def readwise_note_filename(doc: dict[str, Any]) -> str:
    raw_id = str(doc.get("id") or "").strip()
    note_id = require_valid_note_id(f"rw_{raw_id}")
    timestamp = normalize_timestamp(doc.get("created_at"))
    return f"{timestamp}--{note_id}.json"


def raw_export_payload(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "readwise",
        "source_endpoint": "reader/list",
        "source_item_type": "reader_document",
        "synced_at": iso_now(),
        "document": doc,
    }


def existing_export_path(output_dir: Path, note_id: str) -> Path | None:
    safe_id = require_valid_note_id(note_id)
    matches = sorted(p for p in output_dir.glob(f"*--{safe_id}.json") if p.is_file())
    if len(matches) > 1:
        rendered = ", ".join(str(p) for p in matches)
        raise SystemExit(f"Multiple raw exports for '{safe_id}': {rendered}")
    return matches[0] if matches else None


def same_document_payload(path: Path, doc: dict[str, Any]) -> bool:
    if not path.exists():
        return False
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return existing.get("source") == "readwise" and existing.get("document") == doc


def request_json(url: str, token: str) -> Any:
    req = urllib.request.Request(url, headers={
        "Authorization": f"Token {token}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            retry_after = int(exc.headers.get("Retry-After", "60"))
            print(f"Rate limited. Waiting {retry_after}s...", file=sys.stderr)
            time.sleep(retry_after)
            return request_json(url, token)
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"HTTP {exc.code} from Readwise: {body}") from exc


def validate_token(token: str) -> None:
    req = urllib.request.Request(AUTH_URL, headers={"Authorization": f"Token {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status != 204:
                raise SystemExit(f"Token validation returned HTTP {resp.status}.")
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Invalid Readwise token (HTTP {exc.code}).") from exc


def load_sync_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"last_synced_at": None, "last_synced_ids": []}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        "last_synced_at": raw.get("last_synced_at"),
        "last_synced_ids": list(raw.get("last_synced_ids") or []),
    }


def save_sync_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def merge_sync_state(existing: dict[str, Any], newest_updated_at: str | None, newest_ids: list[str]) -> dict[str, Any]:
    last = existing.get("last_synced_at")
    last_ids = list(existing.get("last_synced_ids") or [])
    if newest_updated_at and (not last or newest_updated_at > last):
        last = newest_updated_at
        last_ids = newest_ids
    elif newest_updated_at and newest_updated_at == last:
        for nid in newest_ids:
            if nid not in last_ids:
                last_ids.append(nid)
    return {"last_synced_at": last, "last_synced_ids": last_ids}


def iso_days_ago(days: int) -> str:
    if days <= 0:
        raise SystemExit("--window-days must be greater than 0.")
    now = datetime.fromisoformat(iso_now().replace("Z", "+00:00"))
    return (now - timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def command_sync(args: argparse.Namespace) -> int:
    token = require_access_token()
    validate_token(token)

    state = load_sync_state(args.state_file)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.full_history and (args.updated_after or args.window_days is not None):
        raise SystemExit("--full-history cannot be combined with --updated-after or --window-days.")
    if args.window_days is not None and args.updated_after:
        raise SystemExit("--window-days cannot be combined with --updated-after.")

    updated_after = args.updated_after
    if args.window_days is not None:
        updated_after = iso_days_ago(args.window_days)
    elif args.full_history:
        updated_after = None
    elif not args.no_checkpoint and not updated_after:
        updated_after = state.get("last_synced_at")
    if not updated_after and not args.full_history and (args.no_checkpoint or not state.get("last_synced_at")):
        raise SystemExit(
            "First sync requires an explicit scope. "
            "Use --window-days <N>, --updated-after <ISO>, or --full-history."
        )

    page_cursor = None
    pages_fetched = 0
    written = 0
    updated = 0
    skipped = 0
    skipped_highlights = 0
    newest_updated_at = state.get("last_synced_at")
    newest_ids: list[str] = list(state.get("last_synced_ids") or []) if newest_updated_at else []

    while pages_fetched < args.max_pages:
        params = []
        if updated_after:
            params.append(f"updatedAfter={updated_after}")
        if args.category:
            params.append(f"category={args.category}")
        if args.location:
            params.append(f"location={args.location}")
        for tag in (args.tags or []):
            params.append(f"tag={tag}")
        if page_cursor:
            params.append(f"pageCursor={page_cursor}")
        url = f"{BASE_URL}/list/" + ("?" + "&".join(params) if params else "")
        payload = request_json(url, token)
        results = payload.get("results") or []
        pages_fetched += 1

        for doc in results:
            if should_skip_document(doc):
                skipped_highlights += 1
                continue

            raw_id = str(doc.get("id") or "").strip()
            note_id = f"rw_{raw_id}"
            doc_updated_at = doc.get("updated_at")
            if doc_updated_at and (not newest_updated_at or doc_updated_at > newest_updated_at):
                newest_updated_at = doc_updated_at
                newest_ids = [note_id]
            elif doc_updated_at and doc_updated_at == newest_updated_at and note_id not in newest_ids:
                newest_ids.append(note_id)

            filename = readwise_note_filename(doc)
            path = existing_export_path(output_dir, note_id) or (output_dir / filename)
            existed_before = path.exists()
            if path.exists() and not args.overwrite and same_document_payload(path, doc):
                skipped += 1
                continue
            rendered = json.dumps(raw_export_payload(doc), indent=2, ensure_ascii=False) + "\n"
            path.write_text(rendered, encoding="utf-8")
            if existed_before:
                updated += 1
            else:
                written += 1

        page_cursor = payload.get("nextPageCursor")
        if not page_cursor:
            break

    if not args.no_checkpoint:
        updated_state = merge_sync_state(state, newest_updated_at, newest_ids)
        save_sync_state(args.state_file, updated_state)

    summary = {
        "output_dir": str(output_dir),
        "written": written,
        "updated": updated,
        "skipped": skipped,
        "skipped_highlights": skipped_highlights,
        "pages_fetched": pages_fetched,
        "max_pages": args.max_pages,
        "effective_updated_after": updated_after,
        "checkpoint_enabled": not args.no_checkpoint,
        "state_file": str(args.state_file),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_p = subparsers.add_parser("sync", help="Sync Readwise Reader documents to canonical raw JSON.")
    sync_p.add_argument("--output-dir", required=True, help="Directory for raw JSON exports.")
    sync_p.add_argument("--updated-after", help="ISO 8601 date: only docs updated after this.")
    sync_p.add_argument("--window-days", type=int, help="Fetch docs updated in the last N days.")
    sync_p.add_argument("--full-history", action="store_true", help="Fetch all documents.")
    sync_p.add_argument("--category", help="Filter: article, email, pdf, epub, tweet, video.")
    sync_p.add_argument("--location", help="Filter: new, later, archive, feed.")
    sync_p.add_argument("--tag", dest="tags", action="append", help="Tag filter; repeatable (up to 5).")
    sync_p.add_argument("--max-pages", type=int, default=10, help="Max API pages to fetch.")
    sync_p.add_argument("--overwrite", action="store_true", help="Rewrite existing files.")
    sync_p.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH, help="Sync checkpoint file.")
    sync_p.add_argument("--no-checkpoint", action="store_true", help="Ignore/skip sync checkpoint.")
    sync_p.set_defaults(func=command_sync)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Create the CLI entry point**

Create `scripts/readwise_client.py`:

```python
#!/usr/bin/env python3
"""Readwise Reader sync client — CLI entry point."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from project_router.readwise_client import main

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_project_router.py -v -k "TestReadwiseSyncClient"`
Expected: PASS (6 tests)

- [ ] **Step 6: Run full test suite for regressions**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add src/project_router/readwise_client.py scripts/readwise_client.py tests/test_project_router.py
git commit -m "feat: add Readwise Reader sync client with incremental fetch and child-highlight filtering"
```

---

## Task 6: Bootstrap and Docs

**Files:**
- Modify: `.env.example`
- Modify: `CLAUDE.md`
- Modify: `AGENTS.md`
- Modify: `.agents/skills/project-router-session-opener/SKILL.md`
- Modify: `.claude/skills/project-router-session-opener/SKILL.md`
- Modify: `.codex/skills/project-router-session-opener/SKILL.md`

- [ ] **Step 1: Add Readwise token to `.env.example`**

Append to `.env.example`:

```
READWISE_ACCESS_TOKEN=replace-with-your-readwise-token
```

- [ ] **Step 2: Update session opener skills (all 3 surfaces)**

In each of `.agents/`, `.claude/`, `.codex/` `skills/project-router-session-opener/SKILL.md`, add a new step 6b after step 6 and before step 7:

```markdown
6b. If `READWISE_ACCESS_TOKEN` is configured in `.env.local` (not the placeholder value), run:
   - `python3 scripts/readwise_client.py sync --output-dir ./data/raw/readwise`
   - `python3 scripts/project_router.py normalize --source readwise`
   - `python3 scripts/project_router.py triage --source readwise`
   - `python3 scripts/project_router.py compile --source readwise`
   If `READWISE_ACCESS_TOKEN` is missing or still set to the placeholder, explain: "Readwise sync skipped: READWISE_ACCESS_TOKEN not configured in .env.local".
```

Also update the frontmatter `description` to mention Readwise alongside VoiceNotes.

- [ ] **Step 3: Update CLAUDE.md Session Defaults**

In `CLAUDE.md`, add step 4b after step 4:

```markdown
4b. If `READWISE_ACCESS_TOKEN` exists in `.env.local`, use:
   - `python3 scripts/readwise_client.py sync --output-dir ./data/raw/readwise`
   - `python3 scripts/project_router.py normalize --source readwise`
   - `python3 scripts/project_router.py triage --source readwise`
   - `python3 scripts/project_router.py compile --source readwise`
```

Also add `python3 scripts/readwise_client.py sync --output-dir ./data/raw/readwise` to the Commands section.

- [ ] **Step 4: Update AGENTS.md Session Defaults**

Mirror the same step 4b addition in `AGENTS.md`.

- [ ] **Step 5: Commit**

```bash
git add .env.example CLAUDE.md AGENTS.md .agents/skills/project-router-session-opener/SKILL.md .claude/skills/project-router-session-opener/SKILL.md .codex/skills/project-router-session-opener/SKILL.md
git commit -m "docs: add Readwise Reader to bootstrap, session opener, and agent instructions"
```

---

## Task 7: Governance and Full Validation

**Files:**
- Modify: `repo-governance/customization-contracts.json` (if needed)
- No new files

- [ ] **Step 1: Check if new files need contract declarations**

Run: `python3 scripts/check_customization_contracts.py`

The new files (`scripts/readwise_client.py`, `src/project_router/readwise_client.py`) should be covered by existing glob patterns (`scripts/**` → `template_owned`, `src/**` → `template_owned`). If the check fails, add explicit entries.

- [ ] **Step 2: Run full governance suite**

```bash
python3 scripts/check_customization_contracts.py
python3 scripts/check_repo_ownership.py
python3 scripts/check_sync_manifest_alignment.py
python3 scripts/check_knowledge_structure.py
python3 scripts/check_agent_surface_parity.py --pre-publish
```

Expected: All checks PASS. If parity check flags the session-opener skill diff, verify all 3 surfaces have the same Readwise block.

- [ ] **Step 3: Run full test suite**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: All tests PASS (existing + new Readwise tests)

- [ ] **Step 4: Run pipeline smoke test**

```bash
python3 scripts/project_router.py status
python3 scripts/project_router.py context
```

Expected: Status shows `readwise` counts (all zeros). Context includes readwise in sources list.

- [ ] **Step 5: Fix any issues found, then commit**

```bash
git add -A  # only if governance checks required fixes
git commit -m "chore: pass governance checks for Readwise Reader integration"
```

---

## Task 8: Integration Smoke Test (Manual)

This task requires a real Readwise token. Skip if no token is available.

- [ ] **Step 1: Configure token**

Add real `READWISE_ACCESS_TOKEN` to `.env.local`.

- [ ] **Step 2: Run first sync with bounded window**

```bash
python3 scripts/readwise_client.py sync --output-dir ./data/raw/readwise --window-days 7
```

Expected: JSON summary with `written > 0`, files in `data/raw/readwise/`.

- [ ] **Step 3: Run full pipeline**

```bash
python3 scripts/project_router.py normalize --source readwise
python3 scripts/project_router.py triage --source readwise
python3 scripts/project_router.py compile --source readwise
python3 scripts/project_router.py status
python3 scripts/project_router.py review --source readwise
```

Expected: Status shows non-zero readwise counts. Review shows classified notes.

- [ ] **Step 4: Verify idempotent re-sync**

```bash
python3 scripts/readwise_client.py sync --output-dir ./data/raw/readwise
```

Expected: `written: 0`, `skipped: N` — no new files created.

- [ ] **Step 5: Commit any state/data artifacts to .gitignore verification**

Verify `data/` and `state/` are in `.gitignore`. No raw data should be committed.
