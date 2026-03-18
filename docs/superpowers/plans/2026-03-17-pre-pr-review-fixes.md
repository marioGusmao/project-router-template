# Pre-PR Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix all bugs, documentation inconsistencies, error handling gaps, and protocol enforcement issues identified by review agents and manual audit before creating the PR for `feature/filesystem-inbox`.

**Architecture:** All fixes are in the existing single-module CLI (`src/project_router/cli.py`), its test file, and documentation files. No new files needed. Fixes are independent across chunks and can be parallelized.

**Tech Stack:** Python 3 stdlib only (core), pytest for tests, markdown for docs.

**Sources:** 4 automated review agents + manual P1/P2 audit findings.

---

## Chunk 1: Critical Code Bugs

### Task 1: Preserve extraction fields across re-normalization

**Files:**
- Modify: `src/project_router/cli.py:1694-1728` (PRESERVED_NORMALIZED_FIELDS + merge_normalized_metadata)
- Test: `tests/test_project_router.py`

- [ ] **Step 1: Write the failing test**

In `tests/test_project_router.py`, inside `FilesystemSourceTests`, add:

```python
def test_renormalize_preserves_completed_extraction(self) -> None:
    """Re-normalizing must not erase a completed AI extraction."""
    with temporary_repo_dir() as tmp:
        root = Path(tmp)
        prepare_repo(root)
        write_registry(root)
        # Configure filesystem inbox inline (no helper exists)
        inbox_path = root / "fs_inbox"
        inbox_path.mkdir(parents=True, exist_ok=True)
        local_reg = {
            "projects": {},
            "sources": {"filesystem_inboxes": {"default": {"inbox_path": str(inbox_path)}}},
        }
        (root / "projects" / "registry.local.json").write_text(json.dumps(local_reg), encoding="utf-8")
        (inbox_path / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
        with patch_cli_paths(root):
            with unittest.mock.patch("builtins.print"):
                cli.ingest_command(
                    type("Args", (), {"integration": "filesystem", "dry_run": False, "source": "filesystem"})()
                )
            # Find the normalized note
            norm_dir = root / "data" / "normalized" / "filesystem"
            notes = list(norm_dir.glob("*.md"))
            self.assertEqual(len(notes), 1)
            note_path = notes[0]
            metadata, body = cli.read_note(note_path)
            self.assertEqual(metadata["extraction_status"], "needs_extraction")
            # Simulate completed AI extraction
            metadata["extraction_status"] = "complete"
            metadata["extraction_method"] = "ai_assisted"
            cli.write_note(note_path, metadata, "# photo.png\n\nExtracted text from AI.\n")
            # Re-run normalize — extraction fields must survive
            with unittest.mock.patch("builtins.print"):
                cli.normalize_command(
                    type("Args", (), {"source": "filesystem", "note_ids": None})()
                )
            metadata2, body2 = cli.read_note(note_path)
            self.assertEqual(metadata2["extraction_status"], "complete")
            self.assertEqual(metadata2["extraction_method"], "ai_assisted")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_project_router.py -v -k "test_renormalize_preserves_completed_extraction"`
Expected: FAIL — `extraction_status` will be `needs_extraction` after re-normalize.

- [ ] **Step 3: Write minimal implementation**

In `src/project_router/cli.py`, add extraction fields to `PRESERVED_NORMALIZED_FIELDS` (line 1694):

```python
PRESERVED_NORMALIZED_FIELDS = {
    "project",
    "candidate_projects",
    "confidence",
    "routing_reason",
    "review_status",
    "requires_user_confirmation",
    "dispatched_at",
    "dispatched_to",
    "note_type",
    "status",
    "user_keywords",
    "thread_id",
    "continuation_of",
    "related_note_ids",
    "audio_local_path",
    "extraction_status",
    "extraction_method",
}
```

Then in `merge_normalized_metadata` (after line 1727, before `return`), add conditional preservation for `ai_extraction_hint` and `canonical_blob_ref`:

```python
    if existing.get("extraction_status") == "complete":
        for ek in ("ai_extraction_hint", "canonical_blob_ref"):
            if ek in existing:
                merged[ek] = existing[ek]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_project_router.py -v -k "test_renormalize_preserves_completed_extraction"`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: all 189+ tests pass

- [ ] **Step 6: Commit**

```bash
git add src/project_router/cli.py tests/test_project_router.py
git commit -m "fix: preserve extraction fields across re-normalization

PRESERVED_NORMALIZED_FIELDS now includes extraction_status and
extraction_method. canonical_blob_ref and ai_extraction_hint are
conditionally preserved when extraction_status is 'complete'."
```

---

### Task 2: Validate blob_ref and inbox_key against path traversal in dispatch

**Files:**
- Modify: `src/project_router/cli.py:2561-2571` (dispatch blob copy block)
- Test: `tests/test_project_router.py`

- [ ] **Step 1: Write the failing test**

In `tests/test_project_router.py`, inside `DispatchCommandTests`, add a helper-free filesystem-source dispatch test. The note must live in `data/normalized/filesystem/` (not voicenotes) and its compiled artifact in `data/compiled/filesystem/`:

```python
def test_dispatch_rejects_traversal_in_blob_ref(self) -> None:
    """blob_ref containing '..' must not resolve outside RAW_DIR."""
    with temporary_repo_dir() as tmp:
        root = Path(tmp)
        prepare_repo(root)
        write_registry(root)
        note_id = "fs_traversal"
        # Write a filesystem-source note in the correct source-aware directory
        note_path = root / "data" / "normalized" / "filesystem" / f"20260311T160000Z--{note_id}.md"
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_metadata = {
            "source": "filesystem",
            "source_note_id": note_id,
            "source_endpoint": "filesystem/default",
            "title": "Traversal test",
            "created_at": "2026-03-11T16:00:00Z",
            "status": "classified",
            "project": "home_renovation",
            "review_status": "approved",
            "canonical_path": str(note_path.relative_to(root)),
            "raw_payload_path": "data/raw/filesystem/default/manifests/20260311T160000Z--fs_traversal.manifest.json",
            "note_type": "project-idea",
            "canonical_blob_ref": "../../etc/passwd",
        }
        body = "# Traversal test\n\nBody.\n"
        cli.write_note(note_path, note_metadata, body)
        # Write compiled artifact
        compiled_path = root / "data" / "compiled" / "filesystem" / f"20260311T160000Z--{note_id}.md"
        compiled_path.parent.mkdir(parents=True, exist_ok=True)
        compiled_metadata = {
            "source": "filesystem",
            "source_note_id": note_id,
            "title": "Traversal test",
            "created_at": "2026-03-11T16:00:00Z",
            "compiled_at": "2026-03-11T16:05:00Z",
            "compiled_from_signature": cli.canonical_compile_signature(note_metadata, body),
            "brief_summary": "Summary",
        }
        cli.write_note(compiled_path, compiled_metadata, "# Traversal test\n\nCompiled.\n")
        # Create the fake blob target to make .exists() return True
        evil_target = root / "data" / "raw" / "filesystem" / "default" / ".." / ".." / "etc" / "passwd"
        evil_target.parent.mkdir(parents=True, exist_ok=True)
        evil_target.write_text("root:x:0:0", encoding="utf-8")
        with patch_cli_paths(root):
            with unittest.mock.patch("builtins.print") as mock_print:
                cli.dispatch_command(
                    type("Args", (), {"dry_run": False, "confirm_user_approval": True, "note_ids": [note_id], "source": "filesystem"})()
                )
        output = parse_print_json(mock_print)
        # The blob must NOT have been dispatched — traversal was blocked
        for c in output["candidates"]:
            self.assertNotIn("blob_dispatched", c)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_project_router.py -v -k "test_dispatch_rejects_traversal_in_blob_ref"`
Expected: FAIL — without the guard, the blob is copied from outside RAW_DIR.

- [ ] **Step 3: Write minimal implementation**

In `src/project_router/cli.py`, replace the blob dispatch block at lines 2561-2572 with a guarded version:

```python
            # For filesystem-source notes, also dispatch the original blob
            blob_ref = metadata.get("canonical_blob_ref")
            source = normalize_source_name(str(metadata.get("source") or VOICE_SOURCE)) or VOICE_SOURCE
            if source == FILESYSTEM_SOURCE and blob_ref:
                inbox_key = (metadata.get("source_endpoint") or "").replace("filesystem/", "") or "default"
                if not NOTE_ID_PATTERN.fullmatch(inbox_key):
                    print(f"warning: skipping blob dispatch for {source_note_id}: invalid inbox_key '{inbox_key}'", file=sys.stderr)
                else:
                    blob_source = RAW_DIR / FILESYSTEM_SOURCE / inbox_key / blob_ref
                    safe_root = (RAW_DIR / FILESYSTEM_SOURCE).resolve()
                    if not blob_source.resolve().is_relative_to(safe_root):
                        print(f"warning: skipping blob dispatch for {source_note_id}: blob_ref resolves outside raw directory", file=sys.stderr)
                    elif blob_source.exists():
                        blob_ext = blob_source.suffix
                        blob_dest = destination.parent / f"{destination.stem}{blob_ext}"
                        shutil.copy2(str(blob_source), str(blob_dest))
                        blob_mirror = mirror_path.parent / blob_dest.name
                        shutil.copy2(str(blob_source), str(blob_mirror))
                        candidates[-1]["blob_dispatched"] = str(blob_dest)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_project_router.py -v -k "test_dispatch_rejects_traversal_in_blob_ref"`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add src/project_router/cli.py tests/test_project_router.py
git commit -m "fix: validate blob_ref and inbox_key against path traversal in dispatch

blob_source.resolve() must be under RAW_DIR/filesystem/. inbox_key is
validated with NOTE_ID_PATTERN. Both guard against tampered metadata."
```

---

### Task 3: Remove dead --source argument from extract subcommand

**Files:**
- Modify: `src/project_router/cli.py` (extract subparser setup + extract_command)
- Test: `tests/test_project_router.py`

- [ ] **Step 1: Find and read the extract subparser setup**

Search for `"extract"` in the argparse setup section of `cli.py` (near the end of the file where subparsers are defined). Identify the line that calls `add_source_argument` on the extract subparser.

- [ ] **Step 2: Write a test that extract rejects --source**

```python
def test_extract_does_not_accept_source_argument(self) -> None:
    """extract is filesystem-only — --source should not be accepted."""
    result = subprocess.run(
        ["python3", str(REPO_ROOT / "scripts" / "project_router.py"), "extract", "--source", "voicenotes"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    self.assertNotEqual(result.returncode, 0)
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python3 -m pytest tests/test_project_router.py -v -k "test_extract_does_not_accept_source_argument"`
Expected: FAIL — currently the parser accepts `--source` without error.

- [ ] **Step 4: Remove add_source_argument from extract subparser**

In `cli.py`, find the extract subparser definition and remove the `add_source_argument(extract_parser)` call.

- [ ] **Step 5: Run test to verify it passes**

Run: `python3 -m pytest tests/test_project_router.py -v -k "test_extract_does_not_accept_source_argument"`
Expected: PASS — argparse now rejects `--source` for extract.

- [ ] **Step 6: Run full test suite**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add src/project_router/cli.py tests/test_project_router.py
git commit -m "fix: remove dead --source argument from extract subcommand

extract is filesystem-only by design. Accepting --source was misleading
since the value was silently ignored."
```

---

### Task 4: Return non-zero exit code from ingest_command on errors

**Files:**
- Modify: `src/project_router/cli.py:1056`
- Test: `tests/test_project_router.py`

- [ ] **Step 1: Write the failing test**

```python
def test_ingest_returns_nonzero_on_error(self) -> None:
    """ingest_command must return 1 when errors occur."""
    with temporary_repo_dir() as tmp:
        root = Path(tmp)
        prepare_repo(root)
        write_registry(root)
        inbox_path = root / "fs_inbox"
        inbox_path.mkdir(parents=True, exist_ok=True)
        local_reg = {
            "projects": {},
            "sources": {"filesystem_inboxes": {"default": {"inbox_path": str(inbox_path)}}},
        }
        (root / "projects" / "registry.local.json").write_text(json.dumps(local_reg), encoding="utf-8")
        (inbox_path / "broken.bin").write_bytes(b"data")
        with patch_cli_paths(root):
            # Mock ingest_file to raise OSError for any file
            with unittest.mock.patch.object(cli, "ingest_file", side_effect=OSError("disk error")):
                with unittest.mock.patch("builtins.print"):
                    rc = cli.ingest_command(
                        type("Args", (), {"integration": "filesystem", "dry_run": False, "source": "filesystem"})()
                    )
        self.assertEqual(rc, 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_project_router.py -v -k "test_ingest_returns_nonzero_on_error"`
Expected: FAIL — `rc` will be `0`.

- [ ] **Step 3: Write minimal implementation**

In `src/project_router/cli.py` line 1056, change:

```python
    return 0
```

to:

```python
    return 1 if results.get("errors", 0) > 0 else 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_project_router.py -v -k "test_ingest_returns_nonzero_on_error"`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add src/project_router/cli.py tests/test_project_router.py
git commit -m "fix: ingest_command returns non-zero exit code on errors

Previously always returned 0 even when all ingestions failed.
Now returns 1 when results['errors'] > 0."
```

---

### Task 5: Guard frontmatter parser against colon-free lines

**Files:**
- Modify: `src/project_router/cli.py:622-625`
- Test: `tests/test_project_router.py`

- [ ] **Step 1: Write the failing test**

In `ReadNoteTests`, add:

```python
def test_read_note_skips_lines_without_colon(self) -> None:
    """Frontmatter lines without ':' must be skipped, not inserted as garbage keys."""
    with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
        note = Path(tmp) / "note.md"
        note.write_text("---\ntitle: Test\n- list item\nstatus: ok\n---\nBody.\n", encoding="utf-8")
        metadata, body = cli.read_note(note)
        self.assertEqual(metadata["title"], "Test")
        self.assertEqual(metadata["status"], "ok")
        self.assertNotIn("- list item", metadata)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_project_router.py -v -k "test_read_note_skips_lines_without_colon"`
Expected: FAIL — `"- list item"` will be a key in metadata.

- [ ] **Step 3: Write minimal implementation**

In `src/project_router/cli.py`, replace lines 622-625:

```python
        if not line.strip():
            continue
        key, _, value = line.partition(":")
        metadata[key.strip()] = parse_scalar(value)
```

with:

```python
        if not line.strip():
            continue
        if ":" not in line:
            sys.stderr.write(f"Warning: {path} has unparseable frontmatter line: {line!r}\n")
            continue
        key, _, value = line.partition(":")
        metadata[key.strip()] = parse_scalar(value)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_project_router.py -v -k "test_read_note_skips_lines_without_colon"`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add src/project_router/cli.py tests/test_project_router.py
git commit -m "fix: skip frontmatter lines without colon instead of inserting garbage keys

Lines like '- list item' in frontmatter now emit a warning and are
skipped instead of being parsed as key=line, value=None."
```

---

### Task 5b: Enforce supported_packet_types in ack emission, validator, and doctor

**Files:**
- Modify: `src/project_router/cli.py:3149-3195` (validate_outbox_packet)
- Modify: `src/project_router/cli.py:3834-3859` (run_full_doctor_validation)
- Modify: `src/project_router/cli.py:4592-4630` (inbox_ack_command ack emission)
- Test: `tests/test_project_router.py`

The contract at `router/router-contract.json` declares `supported_packet_types` (e.g., `["improvement_proposal", "question", "insight", "ack"]`). But neither `validate_outbox_packet`, `run_full_doctor_validation`, nor `inbox_ack_command` consult this field to reject packets of unsupported types.

- [ ] **Step 1: Write failing test — validator rejects unsupported packet type**

In a new test (e.g., `InitRouterRootTests` or a dedicated class), add:

```python
def test_doctor_rejects_unsupported_packet_type(self) -> None:
    """doctor must flag packets whose type is not in supported_packet_types."""
    with temporary_repo_dir() as tmp:
        root = Path(tmp)
        prepare_repo(root)
        # Create a minimal router root with a restricted contract
        router_root = root / "downstream" / "router"
        (router_root / "inbox").mkdir(parents=True)
        (router_root / "outbox").mkdir(parents=True)
        (router_root / "conformance").mkdir(parents=True)
        for name in ("valid-packet.example.md", "invalid-packet.example.md"):
            (router_root / "conformance" / name).write_text("---\npacket_id: ex\n---\nExample\n", encoding="utf-8")
        contract = {"schema_version": "1", "project_key": "test_proj", "default_language": "en", "supported_packet_types": ["improvement_proposal"]}
        (router_root / "router-contract.json").write_text(json.dumps(contract), encoding="utf-8")
        # Write an ack packet (not in supported types)
        ack_meta = {"schema_version": "1", "packet_id": "ack_test", "created_at": "2026-03-17T10:00:00Z", "source_project": "test_proj", "packet_type": "ack", "title": "Ack", "language": "en", "status": "applied"}
        cli.write_note(router_root / "outbox" / "20260317T100000Z--ack_test.md", ack_meta, "# Ack\n\nBody.\n")
        with patch_cli_paths(root):
            result = cli.run_full_doctor_validation(router_root, "test_proj")
        self.assertEqual(result["status"], "error")
        self.assertTrue(any("supported_packet_types" in e or "unsupported" in e.lower() for e in result["errors"]))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_project_router.py -v -k "test_doctor_rejects_unsupported_packet_type"`
Expected: FAIL — doctor returns `"status": "ok"`.

- [ ] **Step 3: Add packet_type validation to validate_outbox_packet**

In `validate_outbox_packet` (cli.py:3149), accept a new keyword argument `supported_packet_types: list[str] | None = None` and add this check after the existing field validations (around line 3187):

```python
    packet_type = metadata.get("packet_type")
    if supported_packet_types is not None and packet_type and packet_type not in supported_packet_types:
        errors.append(f"{path.name}: packet_type '{packet_type}' is not in contract supported_packet_types {supported_packet_types}.")
```

- [ ] **Step 4: Thread supported_packet_types through run_full_doctor_validation**

In `run_full_doctor_validation` (cli.py:3850-3851), extract `supported_packet_types` from the contract and pass it to `parse_outbox_packet` → `validate_outbox_packet`. The call chain is:
1. `run_full_doctor_validation` calls `parse_outbox_packet(path, expected_project_key=..., strict=False)`
2. `parse_outbox_packet` calls `validate_outbox_packet(path, metadata, body, expected_project_key=..., strict=False)`

Add `supported_packet_types` parameter to both functions and thread it through:

In `run_full_doctor_validation`, before the packet loop:
```python
    supported_types = contract.get("supported_packet_types")
```

Then pass it: `parse_outbox_packet(path, expected_project_key=..., supported_packet_types=supported_types)`

- [ ] **Step 5: Guard inbox_ack_command against unsupported ack type**

In `inbox_ack_command` (cli.py:4592-4610), after reading the contract, check if "ack" is in `supported_packet_types`:

```python
        supported_types = contract.get("supported_packet_types", []) if contract_path.exists() else []
        if supported_types and "ack" not in supported_types:
            sys.stderr.write(f"Warning: local contract does not list 'ack' in supported_packet_types. Ack packet will still be written.\n")
```

This is a warning, not a hard block, since the ack is written to the local outbox and the downstream can decide to ignore it.

- [ ] **Step 6: Run test to verify it passes**

Run: `python3 -m pytest tests/test_project_router.py -v -k "test_doctor_rejects_unsupported_packet_type"`
Expected: PASS

- [ ] **Step 7: Run full test suite**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: all tests pass

- [ ] **Step 8: Commit**

```bash
git add src/project_router/cli.py tests/test_project_router.py
git commit -m "fix: enforce supported_packet_types in validator, doctor, and ack emission

validate_outbox_packet now rejects packets whose type is not in the
contract's supported_packet_types. run_full_doctor_validation threads
the contract types through. inbox_ack_command warns when 'ack' is not
a supported type."
```

---

### Task 5c: Add CHANGELOG entry for repo-governance changes (release-note gate)

**Files:**
- Modify: `CHANGELOG.md:5-7`

The publish gate `check_customization_contracts.py --changed-path repo-governance/**` fails because `repo-governance/**` has `migration_policy: "requires_release_note"` but the CHANGELOG `## Unreleased` section doesn't cover these changes.

- [ ] **Step 1: Add CHANGELOG entry**

Under `## Unreleased` in CHANGELOG.md, add entries covering the feature/filesystem-inbox branch changes:

```markdown
- Added filesystem source with ingestion protocol, modular extractors, and AI extraction workflow.
- Added router inbox consumption commands: `inbox-intake`, `inbox-status`, `inbox-ack`.
- Hardened dispatch with pre-validation of `--note-id`, ISO timestamps, and atomic batch rejection.
- Preserved manual review decisions (reject/approved) across triage reruns.
- Added tracked-file coverage gate to `check_customization_contracts.py`.
- Registered `Knowledge/runbooks/**` as local-only in ownership manifest and customization contracts.
- Gitignored `Knowledge/runbooks/plans/` as operational artifacts.
```

- [ ] **Step 2: Verify the gate passes**

Run: `python3 scripts/check_customization_contracts.py --changed-path repo-governance/customization-contracts.json --changed-path repo-governance/ownership.manifest.json --changed-path CHANGELOG.md`
Expected: no errors (CHANGELOG covers the changes)

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: add CHANGELOG entries for filesystem-inbox branch features

Satisfies the release-note gate for repo-governance/** changes."
```

---

## Chunk 2: Documentation Fixes

### Task 6: Fix CLAUDE.md architecture description

**Files:**
- Modify: `CLAUDE.md:98`

- [ ] **Step 1: Update the architecture paragraph**

Replace line 98:
```
**Single-module CLI:** All logic lives in `src/project_router/cli.py`. No external dependencies — stdlib only.
```

with:
```
**CLI module + extractors:** Core pipeline logic lives in `src/project_router/cli.py`. Modular content extractors live in `src/project_router/extractors/`. The core pipeline has zero external dependencies (stdlib only); extractors may use optional packages (`pymupdf`, `python-docx`) per ADR-007.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: fix CLAUDE.md architecture — acknowledge extractors subpackage"
```

---

### Task 7: Add inbox steps to Codex session-flow.md

**Files:**
- Modify: `.codex/skills/project-router-session-opener/references/session-flow.md:28-29`

- [ ] **Step 1: Add inbox steps before the "stop" step**

Insert after step 7 (`discover`) and before the current step 8 (`Stop there`):

```markdown
8. If router inbox packets exist, consume them:
   - `python3 scripts/project_router.py inbox-intake`
   - `python3 scripts/project_router.py inbox-status`
9. Stop there and ask the user what to approve, reject, or refine.
```

Remove the old step 8 that currently says "Stop there".

- [ ] **Step 2: Commit**

```bash
git add .codex/skills/project-router-session-opener/references/session-flow.md
git commit -m "docs: add inbox-intake/inbox-status to Codex session-flow.md"
```

---

### Task 8: Add filesystem to safety rule about review queues

**Files:**
- Modify: `CLAUDE.md:187`
- Modify: `AGENTS.md:24`

- [ ] **Step 1: Update CLAUDE.md safety rule**

Replace:
```
- **Send uncertain notes to the source-aware review queues** under `data/review/voicenotes/` or `data/review/project_router/` when no current project/rule exists yet
```

with:
```
- **Send uncertain notes to the source-aware review queues** under `data/review/voicenotes/`, `data/review/project_router/`, or `data/review/filesystem/` when no current project/rule exists yet
```

- [ ] **Step 2: Update AGENTS.md safety rule**

Replace:
```
- Send uncertain notes to the source-aware review queues under `data/review/voicenotes/` or `data/review/project_router/` when no current project/rule exists yet.
```

with:
```
- Send uncertain notes to the source-aware review queues under `data/review/voicenotes/`, `data/review/project_router/`, or `data/review/filesystem/` when no current project/rule exists yet.
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md AGENTS.md
git commit -m "docs: add data/review/filesystem/ to safety rule about review queues"
```

---

### Task 9: Fix README repository layouts — add filesystem dirs, fix runbooks path

**Files:**
- Modify: `README.md:41-77`
- Modify: `README.pt-PT.md:41-77`

- [ ] **Step 1: Update README.md layout**

In the `data/` section, add `filesystem/` entries under `raw/`, `normalized/`, `compiled/`, and `review/`. Fix `local/runbooks/plans/` to `runbooks/plans/` under `Knowledge/`.

The updated tree should include:
```text
data/
  raw/
    voicenotes/
    project_router/
    filesystem/
  normalized/
    voicenotes/
    project_router/
    filesystem/
  compiled/
    voicenotes/
    project_router/
    filesystem/
  review/
    voicenotes/
    project_router/
    filesystem/
  dispatched/
  processed/
Knowledge/
  ADR/
  Templates/
  local/
  runbooks/plans/
```

- [ ] **Step 2: Apply same changes to README.pt-PT.md**

Mirror the exact same structural changes.

- [ ] **Step 3: Commit**

```bash
git add README.md README.pt-PT.md
git commit -m "docs: add filesystem/ to README layouts, fix runbooks/plans/ path"
```

---

### Task 10: Add skill references to CLAUDE.md Workflow Preferences

**Files:**
- Modify: `CLAUDE.md:217-222`

- [ ] **Step 1: Add skill preferences**

After the existing workflow preferences (line 222), add:

```markdown
- Prefer the local skill `project-router-session-opener` at the beginning of a session
- Prefer the local skill `project-router-inbox-consumer` for consuming incoming packets from the router inbox
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add session-opener and inbox-consumer skill references to CLAUDE.md"
```

---

### Task 10b: Fix doctor command documentation — requires --project or --router-root

**Files:**
- Modify: `AGENTS.md:104`
- Modify: `.agents/README.md:18`
- Modify: `parity.manifest.json:19`
- Modify: `CLAUDE.md:220`

The docs list `python3 scripts/project_router.py doctor` as a standalone command, but the CLI requires `--project` or `--router-root`.

- [ ] **Step 1: Update AGENTS.md**

Change line 104 from:
```
- `python3 scripts/project_router.py doctor`
```
to:
```
- `python3 scripts/project_router.py doctor --project <key>`
```

- [ ] **Step 2: Update .agents/README.md**

Change line 18 from:
```
- same contract validation command `python3 scripts/project_router.py doctor`
```
to:
```
- same contract validation command `python3 scripts/project_router.py doctor --project <key>`
```

- [ ] **Step 3: Update parity.manifest.json**

Change the doctor entry from:
```json
"python3 scripts/project_router.py doctor"
```
to:
```json
"python3 scripts/project_router.py doctor --project"
```

- [ ] **Step 4: Update CLAUDE.md Workflow Preferences**

Change line 220 from:
```
- Prefer `python3 scripts/project_router.py doctor` before trusting a downstream `router/` surface
```
to:
```
- Prefer `python3 scripts/project_router.py doctor --project <key>` before trusting a downstream `router/` surface
```

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md .agents/README.md parity.manifest.json CLAUDE.md
git commit -m "docs: fix doctor command docs — requires --project or --router-root"
```

---

### Task 10c: Align CONTRIBUTING.md PR checklist with full governance lane

**Files:**
- Modify: `CONTRIBUTING.md:25-31`

CONTRIBUTING.md only lists 3 checks (parity, ownership, pytest) but README.md Publish Checklist lists the full 7-check governance lane plus additional manual verifications.

- [ ] **Step 1: Expand CONTRIBUTING.md checklist**

Replace the check block (lines 27-31):
```bash
python3 scripts/check_agent_surface_parity.py --pre-publish
python3 scripts/check_repo_ownership.py
python3 -m pytest tests/test_project_router.py -q
```

with:
```bash
python3 -m pytest tests/test_project_router.py -q
python3 scripts/check_agent_surface_parity.py --pre-publish
python3 scripts/check_repo_ownership.py
python3 scripts/check_sync_manifest_alignment.py
python3 scripts/check_knowledge_structure.py --strict
python3 scripts/check_adr_related_links.py --mode block
python3 scripts/check_managed_blocks.py
python3 scripts/check_customization_contracts.py
```

- [ ] **Step 2: Commit**

```bash
git add CONTRIBUTING.md
git commit -m "docs: align CONTRIBUTING.md checklist with full governance lane"
```

---

### Task 10d: Add downstream contract and read-only scan sections to README.pt-PT.md

**Files:**
- Modify: `README.pt-PT.md:158-159`

README.md has a "Local Project-Router Contract" section (lines 159-168) explaining the downstream contract structure and read-only scan model. README.pt-PT.md skips straight from registry to workflow.

- [ ] **Step 1: Add the missing section**

Insert after line 157 (`A classificação pode correr apenas com o registry partilhado. O dispatch real exige o overlay local.`) and before the `## Workflow` section:

```markdown

## Contrato Project-Router Local

Cada repositório participante deve expor:

- `router/router-contract.json`
- `router/inbox/`
- `router/outbox/`
- `router/conformance/`

O router central lê as pastas downstream `outbox/` em modo read-only via `scan-outboxes`. Nunca move nem reescreve ficheiros em repositórios downstream durante scan ou review.
```

- [ ] **Step 2: Commit**

```bash
git add README.pt-PT.md
git commit -m "docs: add downstream contract section to README.pt-PT.md"
```

---

### Task 10e: Fix runbooks/plans path in README layouts

The READMEs show `local/runbooks/plans/` under `Knowledge/local/` but the actual gitignored path is `Knowledge/runbooks/plans/` (not inside `local/`). This is already covered by Task 9 in Chunk 2 — ensure the fix there changes `local/runbooks/plans/` to `runbooks/plans/` under `Knowledge/` (not under `Knowledge/local/`).

No additional task needed — Task 9 already handles this.

---

## Chunk 3: Error Handling Improvements

### Task 11: Warn on corrupt ingest state instead of silent None

**Files:**
- Modify: `src/project_router/cli.py:839-842`

- [ ] **Step 1: Add stderr warning**

Replace:
```python
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
```

with:
```python
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        sys.stderr.write(f"Warning: corrupt ingest state {path}: {exc}\n")
        return None
```

- [ ] **Step 2: Commit**

```bash
git add src/project_router/cli.py
git commit -m "fix: warn on corrupt ingest state instead of silent None"
```

---

### Task 12: Narrow except Exception in ingest_command + warn on manifest SystemExit

**Files:**
- Modify: `src/project_router/cli.py:1047-1051` (ingest_command except block)
- Modify: `src/project_router/cli.py:865-869` (ingest_file manifest read)

- [ ] **Step 1: Narrow ingest_command exception handling**

Keep `except Exception` but add a comment explaining it is intentional — extractors (pymupdf, python-docx) can raise arbitrary exception types that re-raise through `ingest_file` lines 902-905. Narrowing to a fixed set would crash the entire ingest loop on unexpected extractor errors. Change only to add the explanatory comment:

```python
            except Exception as exc:  # Extractors may raise arbitrary types; log and continue
                results["errors"] += 1
                detail = {"file": str(item), "inbox": inbox_key, "error": f"{type(exc).__name__}: {exc}"}
                error_details.append(detail)
                print(f"error: failed to ingest {item}: {exc}", file=sys.stderr)
```

- [ ] **Step 2: Add warning in ingest_file for manifest read failure**

Replace lines 865-869:
```python
        try:
            existing_manifest = read_manifest(existing)
            same_content_as.append(existing_manifest.get("source_note_id", ""))
        except SystemExit:
            pass
```

with:
```python
        try:
            existing_manifest = read_manifest(existing)
            same_content_as.append(existing_manifest.get("source_note_id", ""))
        except SystemExit as exc:
            sys.stderr.write(f"Warning: could not read manifest {existing}: {exc}\n")
```

- [ ] **Step 3: Run full test suite**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: all tests pass

- [ ] **Step 4: Commit**

```bash
git add src/project_router/cli.py
git commit -m "fix: document intentional broad except in ingest, warn on manifest corruption

The broad except Exception in ingest_command is intentional — extractors
may raise arbitrary types. Added explanatory comment. Manifest read
failure in ingest_file now warns to stderr instead of silent pass."
```

---

### Task 13: Add error handling to read_registry_config

**Files:**
- Modify: `src/project_router/cli.py:522-523`

- [ ] **Step 1: Wrap with try/except**

Replace:
```python
def read_registry_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
```

with:
```python
def read_registry_config(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse {path}: {exc}")
    except OSError as exc:
        raise SystemExit(f"Failed to read {path}: {exc}")
```

- [ ] **Step 2: Run full test suite**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: all tests pass

- [ ] **Step 3: Commit**

```bash
git add src/project_router/cli.py
git commit -m "fix: add error handling to read_registry_config

Corrupt or unreadable registry files now produce a clear SystemExit
message instead of a raw Python traceback."
```

---

### Task 14: Simplify dispatch summary ternary

**Files:**
- Modify: `src/project_router/cli.py:2603`

- [ ] **Step 1: Simplify the expression**

Replace:
```python
        "dispatched": dispatched if args.confirm_user_approval else 0 if not args.dry_run else dispatched,
```

with:
```python
        "dispatched": dispatched,
```

The `dispatched` counter already reflects the correct value in all three modes: dry-run increments it to count would-be dispatches (line 2535), no-confirm stays 0 because notes are skipped before any increment, and confirm mode counts real dispatches. The ternary adds no value — it just re-derives what the counter already holds.

- [ ] **Step 2: Run full test suite**

Run: `python3 -m pytest tests/test_project_router.py -v`
Expected: all tests pass

- [ ] **Step 3: Commit**

```bash
git add src/project_router/cli.py
git commit -m "refactor: simplify dispatch summary ternary

dispatched already holds the right value: dry-run counts would-be
dispatches, no-confirm stays 0 (notes skipped), confirm counts real
dispatches. The ternary re-derived what the counter already held."
```

---

## Final Verification

- [ ] **Run full test suite**: `python3 -m pytest tests/test_project_router.py -v`
- [ ] **Run all governance checks**: `python3 scripts/check_agent_surface_parity.py && python3 scripts/check_knowledge_structure.py && python3 scripts/check_customization_contracts.py && python3 scripts/check_repo_ownership.py && python3 scripts/check_sync_manifest_alignment.py && python3 scripts/check_adr_related_links.py && python3 scripts/check_managed_blocks.py`
- [ ] **Review git log**: `git log main..HEAD --oneline` — should show original 7 commits + fix commits
