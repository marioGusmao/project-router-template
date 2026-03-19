# Project Router Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web dashboard for visual triage, project routing suggestions, and pipeline overview for the Project Router system.

**Architecture:** Shared service layer extracted from `cli.py` (5,300 lines) → Python stdlib `http.server` backend with SQLite read model → React + Vite + shadcn/ui frontend. The CLI becomes a thin dispatcher importing from services. Dashboard defaults to suggestion mode; canonical decisions require explicit confirmation.

**Tech Stack:** Python 3 stdlib (http.server, sqlite3, json), React 18, Vite, TypeScript, shadcn/ui, Tailwind CSS, Geist fonts.

**Spec:** `docs/superpowers/specs/2026-03-18-project-router-dashboard-design.md`

---

## Scope & Phasing

This plan has 4 phases, each producing testable, committable software:

| Phase | What | Depends on | Approx tasks |
|-------|------|-----------|-------------|
| **1** | CLI prerequisites (new fields, review output, governance) | Nothing | 5 |
| **2** | Service layer extraction from cli.py | Phase 1 | 10 |
| **3** | Dashboard backend (HTTP server + SQLite) + CLI integration | Phase 2 | 7 |
| **4** | Dashboard frontend (React app) | Phase 3 | 12 |

---

## File Structure

### Phase 1 — CLI changes (modify existing)

```
src/project_router/cli.py               # Add new fields to ordered_keys, defaults, review output
tests/test_project_router.py            # Add tests for new fields
repo-governance/customization-contracts.json  # Declare new surfaces
```

### Phase 2 — Service extraction (new + modify)

```
src/project_router/services/__init__.py
src/project_router/services/paths.py          # All path constants
src/project_router/services/notes.py           # read_note, write_note, parse_scalar, dump_value, etc.
src/project_router/services/projects.py        # Registry loading, merge
src/project_router/services/decisions.py       # Decision packet CRUD
src/project_router/services/classification.py  # route_note, classify_intent, extract_keywords
src/project_router/services/compilation.py     # compiled_note_path, compiled_artifact_state
src/project_router/services/status.py          # Pipeline counts
src/project_router/services/suggestions.py     # user_suggested_project persistence
src/project_router/cli.py                      # Refactored to import from services
tests/test_services.py                         # Unit tests for extracted services
tests/test_project_router.py                   # Regression — must still pass
```

### Phase 3 — Dashboard backend (new)

```
src/project_router/web/__init__.py
src/project_router/web/server.py         # stdlib http.server, routing, static serving
src/project_router/web/index.py          # SQLite read-model builder + queries
src/project_router/web/handlers.py       # API route handlers
scripts/dashboard.py                     # Entry point
dashboard/open-dashboard.command         # macOS launcher
tests/test_dashboard_api.py              # API endpoint tests
```

### Phase 4 — Dashboard frontend (new)

```
dashboard/frontend/package.json
dashboard/frontend/vite.config.ts
dashboard/frontend/tsconfig.json
dashboard/frontend/index.html
dashboard/frontend/.gitattributes
dashboard/frontend/src/main.tsx
dashboard/frontend/src/App.tsx
dashboard/frontend/src/lib/api.ts
dashboard/frontend/src/lib/utils.ts
dashboard/frontend/src/lib/keyboard.ts
dashboard/frontend/src/components/layout/Sidebar.tsx
dashboard/frontend/src/components/layout/MainLayout.tsx
dashboard/frontend/src/components/layout/CommandPalette.tsx
dashboard/frontend/src/components/layout/RefreshIndicator.tsx
dashboard/frontend/src/components/layout/UndoSnackbar.tsx
dashboard/frontend/src/components/layout/KeyboardHelp.tsx
dashboard/frontend/src/components/dashboard/StatusCards.tsx
dashboard/frontend/src/components/dashboard/RecentNotes.tsx
dashboard/frontend/src/components/notes/NotesTable.tsx
dashboard/frontend/src/components/notes/NoteDetail.tsx
dashboard/frontend/src/components/notes/NoteContent.tsx
dashboard/frontend/src/components/notes/ProjectSelector.tsx
dashboard/frontend/src/components/notes/NoteActions.tsx
dashboard/frontend/src/components/notes/CandidateCards.tsx
dashboard/frontend/src/components/notes/ClassificationPanel.tsx
dashboard/frontend/src/components/notes/CompilationPanel.tsx
dashboard/frontend/src/components/notes/MetadataPanel.tsx
dashboard/frontend/src/components/notes/HistoryPanel.tsx
dashboard/frontend/src/components/notes/BatchActionBar.tsx
dashboard/frontend/src/components/triage/TriageView.tsx
dashboard/frontend/src/components/triage/TriageSwimlane.tsx
dashboard/frontend/src/components/projects/ProjectList.tsx
dashboard/frontend/src/components/projects/ProjectDetail.tsx
dashboard/frontend/src/components/inbox/InboxView.tsx
dashboard/frontend/src/components/archive/ArchiveView.tsx
dashboard/frontend/src/components/preview/ImagePreview.tsx
dashboard/frontend/src/components/preview/PdfPreview.tsx
dashboard/frontend/src/components/preview/AudioPlayer.tsx
dashboard/frontend/src/components/preview/FilePreview.tsx
dashboard/frontend/src/hooks/useNotes.ts
dashboard/frontend/src/hooks/useProjects.ts
dashboard/frontend/src/hooks/useStatus.ts
dashboard/frontend/src/hooks/useKeyboard.ts
dashboard/frontend/src/hooks/useUndo.ts
```

---

## Phase 1: CLI Prerequisites

### Task 1: Add new frontmatter fields to CLI

**Files:**
- Modify: `src/project_router/cli.py` (lines 907-969 `ordered_keys`, lines 1486-1513 `ensure_note_metadata_defaults`)
- Test: `tests/test_project_router.py`

- [ ] **Step 1: Write test for new fields surviving write/read round-trip**

```python
def test_dashboard_suggestion_fields_round_trip(self):
    """user_suggested_project, user_suggestion_timestamp, reviewer_notes survive write/read."""
    root = temporary_repo_dir()
    prepare_repo(root)
    with patch_cli_paths(root):
        note_path = cli.NORMALIZED_DIR / "voicenotes" / "20260318T100000Z--test_suggest.md"
        metadata = cli.ensure_note_metadata_defaults({
            "source": "voicenotes",
            "source_note_id": "test_suggest",
            "title": "Test note",
            "status": "classified",
            "project": "home_renovation",
        })
        metadata["user_suggested_project"] = "garden"
        metadata["user_suggestion_timestamp"] = "2026-03-18T14:30:00Z"
        metadata["reviewer_notes"] = "Check: the routing seems wrong"
        cli.write_note(note_path, metadata, "Body text")
        loaded, body = cli.read_note(note_path)
        self.assertEqual(loaded["user_suggested_project"], "garden")
        self.assertEqual(loaded["user_suggestion_timestamp"], "2026-03-18T14:30:00Z")
        self.assertEqual(loaded["reviewer_notes"], "Check: the routing seems wrong")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_project_router.py -v -k "test_dashboard_suggestion_fields_round_trip"`
Expected: FAIL — fields not in ordered_keys, not preserved

- [ ] **Step 3: Add fields to ordered_keys and ensure_note_metadata_defaults**

In `cli.py`, add to `ordered_keys` list (after `note_type`, before the closing `]`):
```python
    "note_type",
    "user_suggested_project",
    "user_suggestion_timestamp",
    "reviewer_notes",
]
```

In `ensure_note_metadata_defaults`, add:
```python
    metadata.setdefault("user_suggested_project", None)
    metadata.setdefault("user_suggestion_timestamp", None)
    metadata.setdefault("reviewer_notes", None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_project_router.py -v -k "test_dashboard_suggestion_fields_round_trip"`
Expected: PASS

- [ ] **Step 5: Run full test suite for regression**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: All existing tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/project_router/cli.py tests/test_project_router.py
git commit -m "feat: add dashboard suggestion fields to note frontmatter"
```

---

### Task 2: Add apply_note_annotations support for reviewer_notes

**Files:**
- Modify: `src/project_router/cli.py` (line ~3190 `apply_note_annotations`)
- Test: `tests/test_project_router.py`

- [ ] **Step 1: Write test for reviewer_notes annotation**

```python
def test_apply_annotations_reviewer_notes(self):
    """apply_note_annotations sets reviewer_notes from args."""
    metadata = cli.ensure_note_metadata_defaults({"source_note_id": "test1"})
    args = argparse.Namespace(
        user_keywords=None, related_note_ids=None,
        thread_id=None, continuation_of=None,
        reviewer_notes="Routing seems wrong",
    )
    cli.apply_note_annotations(metadata, args, "test1")
    self.assertEqual(metadata["reviewer_notes"], "Routing seems wrong")
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `python3 -m pytest tests/test_project_router.py -v -k "test_apply_annotations_reviewer_notes"`

- [ ] **Step 3: Add reviewer_notes handling to apply_note_annotations**

In `apply_note_annotations`, after the `continuation_of` block, add:
```python
    reviewer_notes = getattr(args, "reviewer_notes", None)
    if reviewer_notes is not None:
        metadata["reviewer_notes"] = reviewer_notes
```

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/project_router/cli.py tests/test_project_router.py
git commit -m "feat: add reviewer_notes to apply_note_annotations"
```

---

### Task 3: Add suggestion fields to build_review_entry output

**Files:**
- Modify: `src/project_router/cli.py` (line ~3087 `build_review_entry`)
- Test: `tests/test_project_router.py`

- [ ] **Step 1: Write test for suggestion fields in review output**

```python
def test_review_entry_includes_suggestion_fields(self):
    """build_review_entry includes user_suggested_project and reviewer_notes."""
    root = temporary_repo_dir()
    prepare_repo(root)
    write_registry(root)
    with patch_cli_paths(root):
        note_path = cli.NORMALIZED_DIR / "voicenotes" / "20260318T100000Z--vn_review_suggest.md"
        metadata = cli.ensure_note_metadata_defaults({
            "source": "voicenotes",
            "source_note_id": "vn_review_suggest",
            "title": "Review test",
            "status": "classified",
            "project": "home_renovation",
            "user_suggested_project": "garden",
            "user_suggestion_timestamp": "2026-03-18T14:30:00Z",
            "reviewer_notes": "Check routing",
        })
        cli.write_note(note_path, metadata, "Body")
        packet = cli.build_decision_packet(note_path, metadata, "Body",
                                           route="home_renovation",
                                           details={"home_renovation": 3, "confidence": 0.8},
                                           reason="test")
        cli.save_decision_packet_for_metadata(metadata, packet)
        entry = cli.build_review_entry(packet, cli.decision_packet_path_for_metadata(metadata))
        self.assertEqual(entry["user_suggested_project"], "garden")
        self.assertEqual(entry["user_suggestion_timestamp"], "2026-03-18T14:30:00Z")
        self.assertEqual(entry["reviewer_notes"], "Check routing")
```

- [ ] **Step 2: Run test — expect FAIL (fields not in output)**

- [ ] **Step 3: Add fields to build_review_entry return dict**

In `build_review_entry`, in the return dict (around line 3123-3150), add after `"decision_packet_path"`:
```python
        "user_suggested_project": note_metadata.get("user_suggested_project"),
        "user_suggestion_timestamp": note_metadata.get("user_suggestion_timestamp"),
        "reviewer_notes": note_metadata.get("reviewer_notes"),
```

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Full regression**

Run: `python3 -m pytest tests/test_project_router.py -v`

- [ ] **Step 6: Commit**

```bash
git add src/project_router/cli.py tests/test_project_router.py
git commit -m "feat: include suggestion fields in review command output"
```

---

### Task 4: Add decide_command clearing of suggestion fields on approve

**Files:**
- Modify: `src/project_router/cli.py` (line ~3223 `decide_command`)
- Test: `tests/test_project_router.py`

- [ ] **Step 1: Write test for suggestion clearing on approve**

```python
def test_decide_approve_clears_suggestion(self):
    """decide approve clears user_suggested_project and timestamp."""
    root = temporary_repo_dir()
    prepare_repo(root)
    write_registry(root)
    with patch_cli_paths(root):
        note_path = cli.NORMALIZED_DIR / "voicenotes" / "20260318T100000Z--vn_clear_suggest.md"
        metadata = cli.ensure_note_metadata_defaults({
            "source": "voicenotes",
            "source_note_id": "vn_clear_suggest",
            "title": "Clear test",
            "status": "needs_review",
            "project": None,
            "user_suggested_project": "home_renovation",
            "user_suggestion_timestamp": "2026-03-18T14:30:00Z",
        })
        cli.write_note(note_path, metadata, "Body")
        packet = cli.build_decision_packet(note_path, metadata, "Body",
                                           route="needs_review", details={}, reason="test")
        cli.save_decision_packet_for_metadata(metadata, packet)
        args = argparse.Namespace(
            decision="approve", final_project="home_renovation", final_type=None,
            note_id="vn_clear_suggest", source=None,
            user_keywords=None, related_note_ids=None,
            thread_id=None, continuation_of=None, reviewer_notes=None,
        )
        cli.decide_command(args)
        loaded, _ = cli.read_note(note_path)
        self.assertIsNone(loaded.get("user_suggested_project"))
        self.assertIsNone(loaded.get("user_suggestion_timestamp"))
        self.assertEqual(loaded["project"], "home_renovation")
        self.assertEqual(loaded["status"], "classified")
```

- [ ] **Step 2: Run test — expect FAIL**

- [ ] **Step 3: Add clearing logic to decide_command approve branch**

In `decide_command`, inside the `if decision == "approve":` block (after setting review_status), add:
```python
        metadata["user_suggested_project"] = None
        metadata["user_suggestion_timestamp"] = None
```

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Full regression + commit**

```bash
git add src/project_router/cli.py tests/test_project_router.py
git commit -m "feat: clear suggestion fields on decide approve"
```

---

### Task 5: Governance — declare new surfaces in customization contracts

**Files:**
- Modify: `repo-governance/customization-contracts.json`

- [ ] **Step 1: Read current customization contracts**

Read `repo-governance/customization-contracts.json` to understand the structure.

- [ ] **Step 2: Add dashboard surface declarations**

Add entries for:
- `dashboard/**` → `private_owned`
- `src/project_router/services/**` → `shared_review`
- `src/project_router/web/**` → `shared_review`
- `scripts/dashboard.py` → `shared_review`
- `tests/test_services.py` → `shared_review`
- `tests/test_dashboard_api.py` → `shared_review`

- [ ] **Step 3: Run governance check**

Run: `python3 scripts/check_customization_contracts.py`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add repo-governance/customization-contracts.json
git commit -m "chore: declare dashboard surfaces in customization contracts"
```

---

## Phase 2: Service Layer Extraction

The core principle: extract functions from `cli.py` into service modules, make `cli.py` import from them, and verify all existing tests still pass. Each task extracts one module.

**Critical rule:** After EACH extraction task, run `python3 -m pytest tests/test_project_router.py -v` and verify ALL existing tests pass. Service extraction must be invisible to CLI behavior.

**Re-export strategy for test compatibility:** When `cli.py` does `from project_router.services.paths import ROOT`, the name `ROOT` becomes an attribute of `cli`. Existing test patches like `mock.patch("project_router.cli.ROOT", root)` patch the *binding* in `cli`, which works because Python patches the name in the target module. However, if code inside `services/notes.py` references `services.paths.ROOT` directly, that binding is NOT patched by `mock.patch("project_router.cli.ROOT")`. **Solution:** `patch_cli_paths` must patch at BOTH levels — `cli.ROOT` AND `services.paths.ROOT` — to cover code in both modules. Each extraction task must verify this.

### Task 6: Extract paths.py — shared constants

**Files:**
- Create: `src/project_router/services/__init__.py`
- Create: `src/project_router/services/paths.py`
- Modify: `src/project_router/cli.py`

- [ ] **Step 1: Create services package**

Create `src/project_router/services/__init__.py` (empty file).

- [ ] **Step 2: Create paths.py with all path constants**

Move lines 21-57 from `cli.py` into `services/paths.py`. Keep `NOTE_ID_PATTERN`, source constants, and review queue status constants. The file should import `Path`, `re`, and `frozenset`.

```python
"""Shared path constants for the Project Router pipeline."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]  # Note: 3 levels up from services/paths.py
# ... all constants ...
```

**Important:** `ROOT` changes from `parents[2]` to `parents[3]` because `paths.py` is one directory deeper than `cli.py`.

- [ ] **Step 3: Update cli.py to import from paths.py**

Replace the constant definitions in `cli.py` with:
```python
from project_router.services.paths import (
    ROOT, DATA_DIR, RAW_DIR, NORMALIZED_DIR, COMPILED_DIR, REVIEW_DIR,
    DISPATCHED_DIR, PROCESSED_DIR, STATE_DIR, DECISIONS_DIR, DISCOVERIES_DIR,
    PROJECT_ROUTER_STATE_DIR, OUTBOX_SCAN_STATE_PATH, OUTBOX_SCAN_LOCK_PATH,
    REGISTRY_LOCAL_PATH, REGISTRY_SHARED_PATH, REGISTRY_EXAMPLE_PATH,
    ENV_LOCAL_PATH, ENV_PATH, DISCOVERY_REPORT_PATH, LOCAL_ROUTER_DIR,
    LOCAL_ROUTER_ARCHIVE_DIR, INBOX_STATUS_DIR, TEMPLATE_BASE_PATH,
    PRIVATE_META_PATH, TEMPLATE_META_PATH, VERSION_PATH,
    NOTE_ID_PATTERN, VOICE_SOURCE, PROJECT_ROUTER_SOURCE, FILESYSTEM_SOURCE,
    KNOWN_SOURCES, REVIEW_QUEUE_STATUSES, FILESYSTEM_REVIEW_STATUSES,
    AMBIGUOUS_DIR, NEEDS_REVIEW_DIR, PENDING_PROJECT_DIR,
)
```

- [ ] **Step 4: Run full test suite**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: ALL tests pass. `patch_cli_paths` in tests patches `cli.ROOT`, `cli.DATA_DIR`, etc. — since cli.py now imports these, the patches need to target the correct module. Check if patches still work; if not, update `patch_cli_paths` to also patch `services.paths.*`.

- [ ] **Step 5: Update patch_cli_paths to patch both modules**

`patch_cli_paths` must patch every constant at BOTH levels. For each constant (ROOT, DATA_DIR, etc.), add a second patch line:
```python
# Existing: patches the cli module binding
stack.enter_context(mock.patch("project_router.cli.ROOT", root))
# New: patches the services.paths module binding (used by service layer code)
stack.enter_context(mock.patch("project_router.services.paths.ROOT", root))
# ... repeat for ALL path constants that are extracted
```

This ensures code in `services/notes.py` that does `from project_router.services.paths import NORMALIZED_DIR` sees the test path, not the real one. Every extracted constant needs both patches.

- [ ] **Step 6: Verify all tests pass + commit**

```bash
git add src/project_router/services/ src/project_router/cli.py tests/test_project_router.py
git commit -m "refactor: extract path constants to services/paths.py"
```

---

### Task 7: Extract notes.py — note I/O

**Files:**
- Create: `src/project_router/services/notes.py`
- Modify: `src/project_router/cli.py`

- [ ] **Step 1: Create notes.py with core note I/O functions**

Move these functions from `cli.py` to `services/notes.py`:
- `parse_scalar` (line 845)
- `read_note` (line 863)
- `dump_value` (line 892)
- `write_note` (line 906) — including the `ordered_keys` list
- `ensure_note_metadata_defaults` (line 1486)
- `apply_note_annotations` (line 3190)
- `remove_review_copies` (line 999)
- `iso_now` (line 1006)
- `list_markdown_files` (line 983)
- `list_raw_files` (line 989)

Import dependencies from `services.paths` as needed.

- [ ] **Step 2: Update cli.py imports**

Replace moved functions with imports:
```python
from project_router.services.notes import (
    parse_scalar, read_note, dump_value, write_note,
    ensure_note_metadata_defaults, apply_note_annotations,
    remove_review_copies, iso_now, list_markdown_files, list_raw_files,
)
```

- [ ] **Step 3: Write unit test for notes.py**

Create `tests/test_services.py` with a basic round-trip test:
```python
from project_router.services.notes import read_note, write_note, parse_scalar, dump_value

class TestNotesService(unittest.TestCase):
    def test_parse_scalar_types(self):
        self.assertIsNone(parse_scalar("null"))
        self.assertTrue(parse_scalar("true"))
        self.assertEqual(parse_scalar("42"), 42)
        self.assertEqual(parse_scalar('"hello"'), "hello")
        self.assertEqual(parse_scalar("[1, 2]"), [1, 2])
```

- [ ] **Step 4: Run ALL tests**

Run: `python3 -m pytest tests/ -v`
Expected: Both `test_project_router.py` and `test_services.py` pass.

- [ ] **Step 5: Commit**

```bash
git add src/project_router/services/notes.py tests/test_services.py src/project_router/cli.py
git commit -m "refactor: extract note I/O to services/notes.py"
```

---

### Task 8: Extract projects.py — registry loading

**Files:**
- Create: `src/project_router/services/projects.py`
- Modify: `src/project_router/cli.py`
- Modify: `tests/test_services.py`

- [ ] **Step 1: Move registry functions**

Move to `services/projects.py`:
- `ProjectRule` dataclass (line 279)
- `load_registry` (line 812)
- `read_registry_config` (line 601)
- `read_json_if_exists` (line 610)
- `has_placeholder_path` (line 556)
- Helper functions used by load_registry

- [ ] **Step 2: Update cli.py imports**

- [ ] **Step 3: Write smoke test for projects service**

Add to `tests/test_services.py`:
```python
class TestProjectsService(unittest.TestCase):
    def test_load_registry_returns_projects(self):
        root = temporary_repo_dir()
        prepare_repo(root)
        write_registry(root)
        with patch_cli_paths(root):
            from project_router.services.projects import load_registry
            defaults, projects = load_registry()
            self.assertIn("home_renovation", projects)
            self.assertEqual(projects["home_renovation"].display_name, "Home Renovation")
```

- [ ] **Step 4: Run full test suite — all pass**

- [ ] **Step 5: Commit**

```bash
git add src/project_router/services/projects.py src/project_router/cli.py tests/test_services.py
git commit -m "refactor: extract registry loading to services/projects.py"
```

---

### Task 9: Extract classification.py — routing logic

**Files:**
- Create: `src/project_router/services/classification.py`
- Modify: `src/project_router/cli.py`
- Modify: `tests/test_services.py`

- [ ] **Step 1: Move routing functions**

Move to `services/classification.py`:
- `route_note` (line 2530)
- `classify_intent` (line 1588)
- `classify_capture_kind` (line 1555)
- `extract_keywords` (line 1466)
- `keyword_tokens` (line 1459)
- `note_keyword_set` (line 1516)
- `body_excerpt` (line 1454)
- `enrich_note_metadata` (line 1608)
- `detect_note_languages` (line 227)
- Language profile loading functions (lines 98-219)

- [ ] **Step 2: Update cli.py imports**

- [ ] **Step 3: Write smoke test for classification service**

```python
class TestClassificationService(unittest.TestCase):
    def test_route_note_pending_project(self):
        from project_router.services.classification import route_note
        metadata = {"title": "Random unrelated note", "tags": [], "user_keywords": [], "inferred_keywords": []}
        defaults = {"min_keyword_hits": 2}
        projects = {}  # empty registry = no matches
        route, details, reason = route_note("Some body text", metadata, defaults, projects)
        self.assertEqual(route, "pending_project")
```

- [ ] **Step 4: Run full test suite — all pass**

- [ ] **Step 5: Commit**

```bash
git add src/project_router/services/classification.py src/project_router/cli.py tests/test_services.py
git commit -m "refactor: extract routing logic to services/classification.py"
```

---

### Task 10: Extract decisions.py — decision packet CRUD

**Files:**
- Create: `src/project_router/services/decisions.py`
- Modify: `src/project_router/cli.py`

- [ ] **Step 1: Move decision functions**

Move to `services/decisions.py`:
- `decision_packet_path_for_metadata` (line 1400)
- `decision_packet_paths_for_note_id` (line 1405)
- `resolve_unique_decision_packet_path` (line 1410)
- `load_decision_packet_for_metadata` (line 1422)
- `load_decision_packet_by_path` (line 1429)
- `save_decision_packet_for_metadata` (line 1435)
- `build_decision_packet` (line 1665)
- `build_review_entry` (line 3087)
- `candidate_scores` (line 1441)

- [ ] **Step 2: Update cli.py imports, run tests, commit**

```bash
git commit -m "refactor: extract decision packets to services/decisions.py"
```

---

### Task 11: Extract compilation.py — compiled note operations

**Files:**
- Create: `src/project_router/services/compilation.py`
- Modify: `src/project_router/cli.py`

- [ ] **Step 1: Move compilation functions**

Move to `services/compilation.py`:
- `compiled_note_path` (line 2219)
- `compiled_artifact_state` (line 2425)
- `compile_note_artifact` (line 2239) and all extract_* helpers
- `compile_summary` (line 2149)
- `build_confidence_by_field`, `build_evidence_spans`, `build_ambiguities`
- `transcript_text`, `sentence_chunks`, `unique_preserve`
- `format_bullet_section`, `format_evidence_section`

- [ ] **Step 2: Update cli.py imports, run tests, commit**

```bash
git commit -m "refactor: extract compilation to services/compilation.py"
```

---

### Task 12: Extract status.py — pipeline counts

**Files:**
- Create: `src/project_router/services/status.py`
- Modify: `src/project_router/cli.py`

- [ ] **Step 1: Move status functions**

Move to `services/status.py`:
- `count_markdown` (line 4679)
- `count_raw` (line 4683)
- `count_manifests` (line 4687)
- `_count_inbox_states` (line 4753)
- Status aggregation logic from `status_command` (extract as `compute_pipeline_status()`)

- [ ] **Step 2: Update cli.py — status_command calls compute_pipeline_status()**

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "refactor: extract pipeline counts to services/status.py"
```

---

### Task 13: Create suggestions.py — suggestion persistence

**Files:**
- Create: `src/project_router/services/suggestions.py`
- Test: `tests/test_services.py`

- [ ] **Step 1: Write test for suggestion write/clear**

```python
class TestSuggestionsService(unittest.TestCase):
    def test_write_suggestion(self):
        root = temporary_repo_dir()
        prepare_repo(root)
        with patch_cli_paths(root):
            note_path = cli.NORMALIZED_DIR / "voicenotes" / "20260318T100000Z--vn_sug.md"
            metadata = cli.ensure_note_metadata_defaults({
                "source": "voicenotes", "source_note_id": "vn_sug", "title": "Test",
            })
            cli.write_note(note_path, metadata, "Body")
            from project_router.services.suggestions import write_suggestion, clear_suggestion
            write_suggestion(note_path, "home_renovation")
            loaded, _ = cli.read_note(note_path)
            self.assertEqual(loaded["user_suggested_project"], "home_renovation")
            self.assertIsNotNone(loaded["user_suggestion_timestamp"])
            clear_suggestion(note_path)
            loaded2, _ = cli.read_note(note_path)
            self.assertIsNone(loaded2["user_suggested_project"])
            self.assertIsNone(loaded2["user_suggestion_timestamp"])
```

- [ ] **Step 2: Implement suggestions.py**

```python
"""Operator suggestion persistence for the dashboard."""
import json
from pathlib import Path
from project_router.services.notes import read_note, write_note, iso_now


def write_suggestion(note_path: Path, suggested_project: str) -> dict:
    """Write user_suggested_project to note AND log to decision packet. Returns updated metadata."""
    metadata, body = read_note(note_path)
    metadata["user_suggested_project"] = suggested_project
    metadata["user_suggestion_timestamp"] = iso_now()
    write_note(note_path, metadata, body)
    # Log to decision packet for history trail
    _log_suggestion_to_packet(metadata, suggested_project)
    return metadata


def clear_suggestion(note_path: Path) -> dict:
    """Clear suggestion fields. Returns updated metadata."""
    metadata, body = read_note(note_path)
    metadata["user_suggested_project"] = None
    metadata["user_suggestion_timestamp"] = None
    write_note(note_path, metadata, body)
    return metadata


def _log_suggestion_to_packet(metadata: dict, suggested_project: str) -> None:
    """Append suggestion entry to decision packet reviews array."""
    from project_router.services.decisions import (
        load_decision_packet_for_metadata, save_decision_packet_for_metadata,
    )
    packet = load_decision_packet_for_metadata(metadata)
    packet.setdefault("reviews", [])
    packet.setdefault("source_note_id", metadata.get("source_note_id"))
    packet.setdefault("source", metadata.get("source"))
    packet.setdefault("source_project", metadata.get("source_project"))
    packet["reviews"].append({
        "reviewed_at": iso_now(),
        "decision": "suggestion",
        "suggested_project": suggested_project,
        "previous_project": metadata.get("project"),
        "provenance": "dashboard",
    })
    save_decision_packet_for_metadata(metadata, packet)
```

This ensures the History tab in the detail panel can show the full suggestion trail (multiple suggestions, accept/reject outcomes) by reading the decision packet's `reviews` array — not just the single `user_suggested_project` field in frontmatter.

- [ ] **Step 3: Run tests, commit**

```bash
git add src/project_router/services/suggestions.py tests/test_services.py
git commit -m "feat: add suggestions service for dashboard write operations"
```

---

### Task 14: Verify full extraction + regression

- [ ] **Step 1: Run complete test suite**

Run: `python3 -m pytest tests/ -v`
Expected: ALL tests pass (both test_project_router.py and test_services.py)

- [ ] **Step 2: Run governance checks**

```bash
python3 scripts/check_customization_contracts.py
python3 scripts/check_repo_ownership.py
```

- [ ] **Step 3: Verify CLI still works end-to-end**

```bash
python3 scripts/project_router.py status
python3 scripts/project_router.py review --source voicenotes
```

- [ ] **Step 4: Commit any final adjustments**

```bash
git commit -m "refactor: complete service layer extraction — all tests green"
```

---

## Phase 3: Dashboard Backend

### Task 15: Create SQLite read-model builder (index.py)

**Files:**
- Create: `src/project_router/web/__init__.py`
- Create: `src/project_router/web/index.py`
- Test: `tests/test_dashboard_api.py`

- [ ] **Step 1: Write test for index build + query**

```python
class TestDashboardIndex(unittest.TestCase):
    def test_build_index_and_query_notes(self):
        root = temporary_repo_dir()
        prepare_repo(root)
        write_registry(root)
        with patch_cli_paths(root):
            # Create a normalized note
            note_path = cli.NORMALIZED_DIR / "voicenotes" / "20260318T100000Z--vn_idx.md"
            metadata = cli.ensure_note_metadata_defaults({
                "source": "voicenotes", "source_note_id": "vn_idx",
                "title": "Index test", "status": "classified", "project": "home_renovation",
            })
            cli.write_note(note_path, metadata, "Body text")
            # Build index
            from project_router.web.index import DashboardIndex
            db_path = root / "state" / "dashboard.db"
            idx = DashboardIndex(db_path)
            result = idx.rebuild()
            self.assertGreaterEqual(result["notes_count"], 1)
            # Query
            notes = idx.query_notes()
            self.assertEqual(len(notes), 1)
            self.assertEqual(notes[0]["source_note_id"], "vn_idx")
```

- [ ] **Step 2: Implement DashboardIndex class**

The `DashboardIndex` class:
- `__init__(db_path)` — opens/creates SQLite database
- `rebuild()` — drops and recreates tables, scans filesystem using service layer functions, populates tables, returns `{"notes_count": N, "errors": [...]}`
- `query_notes(source, status=None, project=None, search=None, page=1, per_page=50)` — returns list of note dicts. `source` filters by source; `status` accepts comma-separated values for multi-status queries (e.g., `"ambiguous,needs_review,pending_project,needs_extraction,parse_errors"`)
- `get_note(note_id, source)` — **source is required**. Returns single note dict or None. Raises error if note_id+source combination is ambiguous (duplicate source_note_id within same source across source_projects).
- `query_status()` — returns pipeline counts dict including all source-specific queues
- `query_projects()` — returns project list with note counts
- `update_note(note_id, source)` — incremental update for single note
- `query_related_notes(note_id, source)` — returns notes sharing `thread_id`, `continuation_of`, or `related_note_ids`
- `query_archive(project=None, search=None, date_from=None, date_to=None)` — merges: `data/dispatched/{project}/` + `data/processed/` + `router/archive/{project}/` (downstream router archives). Returns items with `stage` field: `"dispatched"`, `"processed"`, or `"router_archive"`. Non-note artifacts from router archives include packet metadata (source_project, packet_type, timestamps).
- `query_triage_items()` — returns ALL items needing operator attention across ALL sources and queue types:
  - `voicenotes`: ambiguous, needs_review, pending_project
  - `project_router`: parse_errors, needs_review, pending_project
  - `filesystem`: parse_errors, needs_extraction, ambiguous, needs_review, pending_project
  - Cross-source: classified notes with `user_suggested_project != null` (suggested reassignment)
  Each item includes `source`, `queue_type`, and `source_project` for correct grouping.

**Note ID resolution contract:** Every read and write operation that targets a specific note requires `(note_id, source)` pair. `source` is never optional in the index API. The HTTP layer may default `source` from the note's own metadata when unambiguous, but the index always receives it explicitly. For `project_router` source, `source_project` is additionally required when multiple projects could have the same `source_note_id`.

Uses `services.notes.read_note`, `services.status.compute_pipeline_status`, `services.projects.load_registry`.

- [ ] **Step 3: Run test, iterate until passing**

- [ ] **Step 4: Commit**

```bash
git add src/project_router/web/ tests/test_dashboard_api.py
git commit -m "feat: add SQLite read-model builder for dashboard"
```

---

### Task 16: Create HTTP server with API routing (server.py)

**Files:**
- Create: `src/project_router/web/server.py`
- Test: `tests/test_dashboard_api.py`

- [ ] **Step 1: Write test for API status endpoint**

```python
import json
import threading
import urllib.request

class TestDashboardServer(unittest.TestCase):
    def test_status_endpoint(self):
        root = temporary_repo_dir()
        prepare_repo(root)
        write_registry(root)
        with patch_cli_paths(root):
            from project_router.web.server import create_server
            server = create_server(port=0, static_dir=None)  # port=0 = random free port
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()
            try:
                url = f"http://localhost:{port}/api/status"
                with urllib.request.urlopen(url) as resp:
                    data = json.loads(resp.read())
                    self.assertIn("normalized", data)
            finally:
                server.shutdown()
```

- [ ] **Step 2: Implement server.py**

Stdlib `http.server.HTTPServer` + custom `BaseHTTPRequestHandler`:
- Route matching: simple prefix-based routing on `self.path`
- JSON response helper: `self.send_json(data, status=200)`
- Error helper: `self.send_error_json(message, code, status=400)`
- Static file serving: serve from `dist/` directory for non-`/api/` paths
- `create_server(port, static_dir, dev=False)` factory function

- [ ] **Step 3: Run test, commit**

```bash
git commit -m "feat: add stdlib HTTP server for dashboard API"
```

---

### Task 17: Implement API route handlers (handlers.py)

**Files:**
- Create: `src/project_router/web/handlers.py`
- Modify: `src/project_router/web/server.py`
- Test: `tests/test_dashboard_api.py`

- [ ] **Step 1: Write tests for each endpoint**

Test at minimum: `GET /api/status`, `GET /api/notes`, `GET /api/notes/:id`, `GET /api/projects`, `POST /api/notes/:id/suggest`, `POST /api/refresh`.

- [ ] **Step 2: Implement handlers**

Each handler is a function that receives parsed request data and returns a dict:
- `handle_status(index)` → status dict
- `handle_notes_list(index, params)` → paginated notes
- `handle_note_detail(index, note_id, params)` → full note with body
- `handle_note_compiled(index, note_id, params)` → compiled version
- `handle_note_related(index, note_id)` → related notes
- `handle_projects_list(index)` → projects with counts
- `handle_project_detail(index, key)` → project metadata
- `handle_project_notes(index, key, params)` → project's notes
- `handle_decisions(index)` → decision packets
- `handle_archive(index, params)` → dispatched + processed
- `handle_inbox(index)` → inbox packets
- `handle_suggest(index, note_id, body)` → write suggestion. Body MUST include `source`. Logs suggestion to decision packet `reviews` array with `{"decision": "suggestion", "suggested_project": ..., "timestamp": ..., "provenance": "dashboard"}`.
- `handle_status_change(index, note_id, body)` → change status with full source-specific side effects. Body MUST include `source`. Validates target status is valid for the note's source (e.g., rejects `needs_extraction` for voicenotes). Uses confirmation dialog in UI.
- `handle_annotate(index, note_id, body)` → add reviewer notes/keywords. Body MUST include `source`.
- `handle_approve(index, note_id, body)` → canonical decision. Body MUST include `source`. Sets `destination: <project_key>` (not "classified"). Clears suggestion fields. Logs to decision packet. Uses confirmation dialog in UI.
- `handle_undo(undo_buffer, action_id)` → revert. **Only for Tier 1 actions (suggest, annotate)**. Restores snapshotted frontmatter fields only. The handler MUST reject undo for Tier 2 actions (status, approve) — these are not undoable because they mutate review copies and decision packets beyond what a frontmatter snapshot can restore.
- `handle_batch(index, body)` → batch operations. Body MUST include `source` per note or a global `source`. **Only `suggest` and `annotate` actions allowed in batch.** Handler MUST reject `status` and `approve` with `{"error": "Status and approve actions require individual confirmation", "code": "BATCH_NOT_ALLOWED"}`.
- `handle_refresh(index)` → rebuild index

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "feat: implement dashboard API route handlers"
```

---

### Task 18: Create entry point script (dashboard.py)

**Files:**
- Create: `scripts/dashboard.py`
- Create: `dashboard/open-dashboard.command`

- [ ] **Step 1: Create dashboard.py**

```python
#!/usr/bin/env python3
"""Launch the Project Router Dashboard."""
import argparse
import socket
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def is_dashboard_running(port: int) -> bool:
    if not is_port_in_use(port):
        return False
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://localhost:{port}/api/status", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser(description="Project Router Dashboard")
    parser.add_argument("--port", type=int, default=8420)
    parser.add_argument("--dev", action="store_true", help="Enable CORS for development")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if is_dashboard_running(args.port):
        print(f"Dashboard already running at http://localhost:{args.port}")
        if not args.no_browser:
            webbrowser.open(f"http://localhost:{args.port}")
        return
    elif is_port_in_use(args.port):
        print(f"Port {args.port} is in use by another process.", file=sys.stderr)
        sys.exit(1)

    static_dir = ROOT / "dashboard" / "frontend" / "dist"
    if not static_dir.exists():
        static_dir = None
        print("Warning: frontend not built. API-only mode.", file=sys.stderr)

    from project_router.web.server import create_server
    server = create_server(port=args.port, static_dir=static_dir, dev=args.dev)
    print(f"Serving dashboard at http://localhost:{args.port}")
    if not args.no_browser:
        webbrowser.open(f"http://localhost:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create macOS launcher**

`dashboard/open-dashboard.command`:
```bash
#!/bin/bash
cd "$(dirname "$0")/.."
python3 scripts/dashboard.py
```

- [ ] **Step 3: Make launcher executable and test manually**

```bash
chmod +x dashboard/open-dashboard.command
python3 scripts/dashboard.py --no-browser &
curl -s http://localhost:8420/api/status | python3 -m json.tool
kill %1
```

- [ ] **Step 4: Commit**

```bash
git add scripts/dashboard.py dashboard/open-dashboard.command
git commit -m "feat: add dashboard entry point and macOS launcher"
```

---

### Task 19: Implement file serving for previews

**Files:**
- Modify: `src/project_router/web/handlers.py`
- Test: `tests/test_dashboard_api.py`

- [ ] **Step 1: Add file serving handler**

The `handle_note_file(note_id, filename)` handler:
- Resolves note to find its raw payload path
- For filesystem source: serves from `data/raw/filesystem/{inbox_key}/artifacts/`
- For voicenotes: extracts audio URL from raw JSON, returns redirect or 404
- Sets correct Content-Type based on file extension
- Returns file bytes, not JSON

- [ ] **Step 2: Test with a fixture file, commit**

```bash
git commit -m "feat: add file preview serving for dashboard"
```

---

### Task 20: Add CLI --dashboard flag and inbox.py service

**Files:**
- Modify: `src/project_router/cli.py` (add --dashboard argument to triage + review subparsers)
- Create: `src/project_router/services/inbox.py`
- Test: `tests/test_services.py`

- [ ] **Step 1: Extract inbox.py service**

Move inbox packet read functions from `cli.py` to `services/inbox.py`:
- `load_inbox_packet_state`, `save_inbox_packet_state`, `list_inbox_packets`
- `_count_inbox_states`

- [ ] **Step 2: Add --dashboard flag to triage and review subparsers**

In `build_parser()`, add to triage and review subparsers:
```python
parser_triage.add_argument("--dashboard", action="store_true", help="Open dashboard after triage")
parser_review.add_argument("--dashboard", action="store_true", help="Open dashboard after review")
```

In `triage_command` and `review_command`, at the end (before return), add:
```python
    if getattr(args, "dashboard", False):
        _ensure_dashboard_running(view="triage")  # or "notes" for review
```

Implement `_ensure_dashboard_running(view, port=8420)`:
```python
def _ensure_dashboard_running(view: str = "", port: int = 8420) -> None:
    import socket, subprocess, webbrowser
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("localhost", port)) != 0:
            # Start dashboard in background
            subprocess.Popen(
                [sys.executable, str(ROOT / "scripts" / "dashboard.py"), "--no-browser", "--port", str(port)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            import time; time.sleep(1)  # Brief wait for server startup
    webbrowser.open(f"http://localhost:{port}/{view}")
```

- [ ] **Step 3: Run tests, commit**

```bash
git add src/project_router/services/inbox.py src/project_router/cli.py tests/test_services.py
git commit -m "feat: add --dashboard flag to CLI and extract inbox service"
```

---

### Task 21: Update documentation and session opener

**Files:**
- Modify: `Knowledge/ScriptsReference.md` (add dashboard.py documentation)
- Modify: `.claude/skills/project-router-session-opener/` (add dashboard auto-start step)

- [ ] **Step 1: Add dashboard.py to ScriptsReference.md**

Add entry documenting: purpose, usage (`python3 scripts/dashboard.py`), flags (`--port`, `--dev`, `--no-browser`), and relationship to CLI `--dashboard` flag.

- [ ] **Step 2: Update session opener skill with suggestion consumption flow**

Add two steps to the session opener skill:

**Auto-start step:** After pipeline runs, check if dashboard is running → if not, start in background → open browser.

**Suggestion consumption step:** After running `review`, the session opener MUST check for notes with `user_suggested_project != null` in the review output. If found:
1. List each note with suggestion: "Dashboard suggests rerouting {note_id} from '{current_project}' → '{suggested_project}' (reviewer notes: '{notes}')"
2. Ask the user: "Accept, reject, or skip each suggestion?"
3. For accepted: run `decide --note-id {id} --decision approve --final-project {suggested}`
4. For rejected: clear suggestion fields via `decide --note-id {id} --decision reject` (or a new `clear-suggestion` action)
5. For skipped: leave as-is for next session

This closes the dashboard → chat round-trip. The key contract: **the session opener skill always checks review output for pending suggestions before asking the user what to do next.** Without this step, suggestions written in the dashboard sit forever unprocessed.

- [ ] **Step 2b: Update triage-review skill with suggestion awareness**

The `project-router-triage-review` skill must also include suggestion consumption: when presenting notes for review, highlight notes with `user_suggested_project` and present the suggestion as the first option.

- [ ] **Step 3: Run governance checks**

```bash
python3 scripts/check_agent_surface_parity.py --pre-publish
python3 scripts/check_knowledge_structure.py
python3 scripts/check_customization_contracts.py
```

- [ ] **Step 4: Commit**

```bash
git add Knowledge/ScriptsReference.md .claude/skills/
git commit -m "docs: add dashboard documentation and update session opener"
```

---

## Phase 4: Dashboard Frontend

### Task 22: Scaffold React + Vite project

**Files:**
- Create: `dashboard/frontend/` (entire scaffold)

- [ ] **Step 1: Initialize Vite + React + TypeScript project**

```bash
cd dashboard/frontend
npm create vite@latest . -- --template react-ts
npm install
```

- [ ] **Step 2: Install dependencies**

```bash
npm install -D tailwindcss @tailwindcss/vite
npx shadcn@latest init
```

Configure:
- `vite.config.ts`: add proxy for `/api` → `http://localhost:8420`
- `tailwind.config.js`: content paths
- Dark mode: `className` strategy

- [ ] **Step 3: Install shadcn/ui components**

```bash
npx shadcn@latest add button badge table input select dialog dropdown-menu
npx shadcn@latest add tabs card separator scroll-area tooltip command
npx shadcn@latest add sheet popover sonner checkbox
```

- [ ] **Step 4: Add Geist fonts**

```bash
npm install geist
```

Configure in `main.tsx` or CSS.

- [ ] **Step 5: Create .gitattributes for dist/**

```
dist/** binary
```

- [ ] **Step 6: Verify dev server starts**

```bash
npm run dev
```

- [ ] **Step 7: Commit**

```bash
git add dashboard/frontend/
git commit -m "feat: scaffold React + Vite + shadcn/ui frontend"
```

---

### Task 23: Build layout shell (Sidebar + MainLayout)

**Files:**
- Create: `dashboard/frontend/src/components/layout/Sidebar.tsx`
- Create: `dashboard/frontend/src/components/layout/MainLayout.tsx`
- Create: `dashboard/frontend/src/lib/api.ts`
- Modify: `dashboard/frontend/src/App.tsx`

- [ ] **Step 1: Create API client**

`lib/api.ts`: fetch wrapper with base URL, JSON parsing, error handling.

- [ ] **Step 2: Create Sidebar**

Fixed left sidebar with navigation links: Home, Notes, Triage, Projects, Inbox, Archive. Active state styling. Dark theme with zinc palette.

- [ ] **Step 3: Create MainLayout**

Layout wrapper: sidebar + main content area with header (filters/search + refresh indicator).

- [ ] **Step 4: Set up React Router**

```bash
npm install react-router-dom
```

Routes: `/`, `/notes`, `/triage`, `/projects`, `/projects/:key`, `/inbox`, `/archive`

- [ ] **Step 5: Verify navigation works, commit**

```bash
git commit -m "feat: add dashboard layout shell with sidebar navigation"
```

---

### Task 24: Build Dashboard home view (StatusCards + RecentNotes)

**Files:**
- Create: `dashboard/frontend/src/components/dashboard/StatusCards.tsx`
- Create: `dashboard/frontend/src/components/dashboard/RecentNotes.tsx`
- Create: `dashboard/frontend/src/hooks/useStatus.ts`

- [ ] **Step 1: Create useStatus hook**

Fetches `GET /api/status`, returns data + loading + error state.

- [ ] **Step 2: Create StatusCards**

Grid of cards showing pipeline counts. Color-coded badges. Oldest item age per queue ("Triage: 5 notes, oldest 4 days").

- [ ] **Step 3: Create RecentNotes**

Small table showing last 10 notes. Links to note detail.

- [ ] **Step 4: Create remaining home widgets**

- **ReviewSummary** — text summary covering ALL queue types across ALL sources: "5 notes to triage: 2 pending project, 1 ambiguous, 1 needs review, 1 parse error. 2 filesystem files awaiting extraction. 1 suggested reassignment pending."
- **ProjectDistribution** — simple bar or list showing notes per project (from `/api/projects`)
- **InboxStatus** — unprocessed packet count with link to `/inbox` (from `/api/inbox`)
- **ThreadGroups** — count of `thread_id` groups awaiting triage (from `/api/notes?status=pending_project,ambiguous,needs_review` grouped by thread_id)

- [ ] **Step 5: Wire up to Home route, verify with running backend**

```bash
# Terminal 1:
python3 scripts/dashboard.py --no-browser --dev
# Terminal 2:
cd dashboard/frontend && npm run dev
# Open http://localhost:5173
```

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add dashboard home view with status cards"
```

---

### Task 25: Build Notes view (NotesTable + filters + pagination)

**Files:**
- Create: `dashboard/frontend/src/components/notes/NotesTable.tsx`
- Create: `dashboard/frontend/src/hooks/useNotes.ts`

- [ ] **Step 1: Create useNotes hook**

Fetches `GET /api/notes` with filter params, pagination state.

- [ ] **Step 2: Create NotesTable**

shadcn Table with columns: checkbox, title, status badge, project, confidence (color-banded), source, age, compiled icon. Filter bar on top: status, source, project dropdowns + text search. Column sorting. Pagination controls.

- [ ] **Step 3: Add thread grouping**

Notes sharing a `thread_id` are visually grouped with a subtle connector line/indent. Expandable group header shows thread context and count. Uses `GET /api/notes?thread_id=X` to fetch thread members.

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add notes table view with filters, pagination, and thread grouping"
```

---

### Task 26: Build NoteDetail split panel

**Files:**
- Create: `dashboard/frontend/src/components/notes/NoteDetail.tsx`
- Create: `dashboard/frontend/src/components/notes/NoteContent.tsx`
- Create: `dashboard/frontend/src/components/notes/ProjectSelector.tsx`
- Create: `dashboard/frontend/src/components/notes/NoteActions.tsx`
- Create: `dashboard/frontend/src/components/notes/CandidateCards.tsx`
- Create: `dashboard/frontend/src/components/notes/ClassificationPanel.tsx`
- Create: `dashboard/frontend/src/components/notes/CompilationPanel.tsx`
- Create: `dashboard/frontend/src/components/notes/MetadataPanel.tsx`
- Create: `dashboard/frontend/src/components/notes/HistoryPanel.tsx`

- [ ] **Step 1: Create NoteDetail**

Split panel (40% right) with progressive disclosure. Header always visible. Collapsible sections.

- [ ] **Step 2: Create ProjectSelector**

Dropdown with type-to-search. Shows current project + suggestion. "Suggest This" writes to API.

- [ ] **Step 3: Create NoteActions**

Action bar: suggest, status change (with confirmation dialog), approve (with confirmation), add notes, add keywords.

- [ ] **Step 4: Create CandidateCards**

Visual comparison cards for candidate projects. Score bars with confidence coloring. "Suggest This" button per card.

- [ ] **Step 5: Create remaining panels**

ClassificationPanel, CompilationPanel (with freshness indicator), MetadataPanel, HistoryPanel.

- [ ] **Step 6: Create NoteContent**

Markdown renderer (use `react-markdown` or similar). File preview integration.

```bash
npm install react-markdown
```

- [ ] **Step 7: Wire split view into NotesTable, commit**

```bash
git commit -m "feat: add note detail split panel with all sections"
```

---

### Task 27: Build Triage view with swimlanes

**Files:**
- Create: `dashboard/frontend/src/components/triage/TriageView.tsx`
- Create: `dashboard/frontend/src/components/triage/TriageSwimlane.tsx`

- [ ] **Step 1: Create TriageSwimlane**

Collapsible section with count in header. Note cards inside with excerpt, candidates, quick actions.

- [ ] **Step 2: Create TriageView**

Swimlanes covering ALL source-specific queues:
1. **Suggested Reassignment** — classified notes with `user_suggested_project != null` (any source)
2. **Parse Errors** — `project_router` and `filesystem` parse failures needing manual intervention
3. **Needs Extraction** — `filesystem` notes awaiting text extraction (read-only, extraction done via CLI)
4. **Pending Project** — no project match (any source)
5. **Ambiguous** — multiple project matches (voicenotes + filesystem; project_router routes these to needs_review)
6. **Needs Review** — flagged for human review (any source)

Each swimlane shows the source icon per item. Swimlanes with zero items are hidden by default. Uses `query_triage_items()` from DashboardIndex. Priority sort within each. Batch selection. Opens detail panel on click.

For parse_errors and needs_extraction, the action bar shows source-appropriate actions only: parse_errors can be re-triaged or dismissed; needs_extraction shows "Extract via CLI" instruction (no dashboard write action available for these states).

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: add triage view with collapsible swimlanes"
```

---

### Task 28: Build Projects view

**Files:**
- Create: `dashboard/frontend/src/components/projects/ProjectList.tsx`
- Create: `dashboard/frontend/src/components/projects/ProjectDetail.tsx`
- Create: `dashboard/frontend/src/hooks/useProjects.ts`

- [ ] **Step 1: Create ProjectList**

Card grid showing projects with display_name, language, keywords, note counts, contract health indicator.

- [ ] **Step 2: Create ProjectDetail**

Route `/projects/:key`. Project metadata, contract health, tabbed note lists (Active / In Review / Archived). Includes note relationship timeline: `thread_id`, `continuation_of`, `related_note_ids` visualized as a vertical timeline of connected notes using `GET /api/notes/:id/related`.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: add projects view with detail pages and relationship graph"
```

---

### Task 29: Build Inbox and Archive views

**Files:**
- Create: `dashboard/frontend/src/components/inbox/InboxView.tsx`
- Create: `dashboard/frontend/src/components/archive/ArchiveView.tsx`

- [ ] **Step 1: Create InboxView**

Table of inbox packets. Status badges. Read-only detail expansion.

- [ ] **Step 2: Create ArchiveView**

Table of dispatched + processed notes. Project + date filters. Read-only.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: add inbox and archive views"
```

---

### Task 30: Build file preview components

**Files:**
- Create: `dashboard/frontend/src/components/preview/ImagePreview.tsx`
- Create: `dashboard/frontend/src/components/preview/PdfPreview.tsx`
- Create: `dashboard/frontend/src/components/preview/AudioPlayer.tsx`
- Create: `dashboard/frontend/src/components/preview/FilePreview.tsx`

- [ ] **Step 1: Create preview components**

ImagePreview: `<img>` tag with max-width. PdfPreview: `<embed>` or `<iframe>`. AudioPlayer: HTML5 `<audio>`. FilePreview: router that picks correct component based on file extension.

- [ ] **Step 2: Integrate into NoteContent, commit**

```bash
git commit -m "feat: add file preview components for dashboard"
```

---

### Task 31: Add keyboard shortcuts + command palette

**Files:**
- Create: `dashboard/frontend/src/lib/keyboard.ts`
- Create: `dashboard/frontend/src/hooks/useKeyboard.ts`
- Create: `dashboard/frontend/src/components/layout/CommandPalette.tsx`
- Create: `dashboard/frontend/src/components/layout/KeyboardHelp.tsx`

- [ ] **Step 1: Create keyboard manager**

Global key listener. Suppresses shortcuts when in text inputs. Maps keys to actions.

- [ ] **Step 2: Create CommandPalette**

Cmd+K dialog using shadcn Command component. Jump to views, search notes, refresh.

- [ ] **Step 3: Create KeyboardHelp**

`?` shortcut overlay showing all available shortcuts.

- [ ] **Step 4: Wire J/K/P/A/S/X/Z/Enter into Notes and Triage views**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add keyboard shortcuts and command palette"
```

---

### Task 32: Add undo snackbar + batch actions + stale indicator

**Files:**
- Create: `dashboard/frontend/src/components/layout/UndoSnackbar.tsx`
- Create: `dashboard/frontend/src/components/layout/RefreshIndicator.tsx`
- Create: `dashboard/frontend/src/components/notes/BatchActionBar.tsx`
- Create: `dashboard/frontend/src/hooks/useUndo.ts`

- [ ] **Step 1: Create UndoSnackbar**

Toast at bottom with countdown. Calls undo API. Uses sonner or custom toast.

- [ ] **Step 2: Create RefreshIndicator**

Header indicator: "Index: 2m ago" with color-coded dot. Click triggers refresh.

- [ ] **Step 3: Create BatchActionBar**

Floating toolbar when items selected. Only `suggest` and `annotate` actions available in batch — status change and approve buttons are disabled/hidden (per spec: these require per-note confirmation). Tooltip explains: "Status and approve actions require individual confirmation."

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add undo, batch actions, and stale data indicator"
```

---

### Task 33: Build frontend + final integration test

- [ ] **Step 1: Build the frontend**

```bash
cd dashboard/frontend
npm run build
```

- [ ] **Step 2: Test full stack locally**

```bash
python3 scripts/dashboard.py --no-browser
# Open http://localhost:8420 — should serve built frontend
```

Verify: dashboard loads, status shows, notes table populates, triage swimlanes render, project detail works, file previews work, keyboard shortcuts work.

- [ ] **Step 3: Commit dist/**

```bash
git add dashboard/frontend/dist/
git commit -m "build: commit compiled frontend assets"
```

- [ ] **Step 4: Final commit with all remaining files**

```bash
git add -A
git commit -m "feat: complete Project Router Dashboard v1"
```

---

## Validation Checklist

After all phases:

```bash
# CLI regression
python3 -m pytest tests/test_project_router.py -v

# Service tests
python3 -m pytest tests/test_services.py -v

# Dashboard API tests
python3 -m pytest tests/test_dashboard_api.py -v

# Governance
python3 scripts/check_customization_contracts.py
python3 scripts/check_repo_ownership.py
python3 scripts/check_agent_surface_parity.py --pre-publish
python3 scripts/check_knowledge_structure.py

# Frontend build verification
cd dashboard/frontend && npm run build && cd ../..

# Manual end-to-end
python3 scripts/project_router.py status
python3 scripts/dashboard.py --no-browser &
curl -s http://localhost:8420/api/status | python3 -m json.tool
curl -s "http://localhost:8420/api/notes?per_page=5" | python3 -m json.tool
curl -s http://localhost:8420/api/projects | python3 -m json.tool
kill %1

# CLI --dashboard flag
python3 scripts/project_router.py review --source voicenotes --dashboard
```
