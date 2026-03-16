# Rename `project-router/` → `Router/` Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename the canonical router directory from `project-router/` to `Router/` and make inference content-based instead of name-based.

**Architecture:** Rename the physical directory, update `LOCAL_ROUTER_DIR`, change adopt inference to check for `router-contract.json` instead of hard-coded directory name, update `.gitignore` for inbox/outbox runtime artifacts, update all documentation and governance references.

**Tech Stack:** Python stdlib, git, JSON governance manifests

---

## Chunk 1: Code + Directory + Gitignore

### Task 1: Rename directory and update LOCAL_ROUTER_DIR

**Files:**
- Rename: `project-router/` → `Router/`
- Modify: `src/project_router/cli.py:39` — `LOCAL_ROUTER_DIR`
- Modify: `tests/test_project_router.py:79` — `patch_cli_paths` mock

- [ ] **Step 1: Rename the directory**

```bash
git mv project-router Router
```

- [ ] **Step 2: Update LOCAL_ROUTER_DIR in cli.py**

Change line 39:
```python
# Before
LOCAL_ROUTER_DIR = ROOT / "project-router"
# After
LOCAL_ROUTER_DIR = ROOT / "Router"
```

- [ ] **Step 3: Update patch_cli_paths in tests**

Change line 79:
```python
# Before
"LOCAL_ROUTER_DIR": root / "project-router",
# After
"LOCAL_ROUTER_DIR": root / "Router",
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_project_router.py -v -x`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "refactor: rename project-router/ → Router/"
```

### Task 2: Content-based inference in resolve_adoption_state

**Files:**
- Modify: `src/project_router/cli.py:2904` — `resolve_adoption_state`

- [ ] **Step 1: Write failing test**

In `tests/test_project_router.py`, add to `AdoptRouterRootTests`:
```python
def test_adopt_infers_from_custom_named_parent(self) -> None:
    """inbox_path inside a non-standard-named parent with router-contract.json → inferred."""
    with temporary_repo_dir() as tmp:
        root = Path(tmp)
        prepare_repo(root)
        router_root = root / "repos" / "home-renovation" / "MyRouter"
        inbox = router_root / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)
        # Place a contract so inference works
        (router_root / "router-contract.json").write_text(
            json.dumps({"schema_version": "1", "project_key": "home_renovation",
                         "default_language": "en", "supported_packet_types": ["insight"]}),
            encoding="utf-8",
        )
        shared = {
            "defaults": {"min_keyword_hits": 2},
            "projects": {"home_renovation": {"display_name": "Home Renovation", "language": "en",
                                              "note_type": "project-idea", "keywords": ["renovation"]}},
        }
        local = {"projects": {"home_renovation": {"inbox_path": str(inbox)}}}
        (root / "projects" / "registry.shared.json").write_text(json.dumps(shared), encoding="utf-8")
        (root / "projects" / "registry.local.json").write_text(json.dumps(local, indent=2), encoding="utf-8")
        with patch_cli_paths(root):
            with mock.patch("builtins.print") as mock_print:
                rc = cli.main(["adopt-router-root", "--project", "home_renovation", "--confirm"])
        self.assertEqual(rc, 0)
        report = parse_print_json(mock_print)
        self.assertEqual(report["target_router_root"], str(router_root))
```

- [ ] **Step 2: Run test — verify it fails**

Run: `python3 -m pytest tests/test_project_router.py -v -k "test_adopt_infers_from_custom_named_parent"`
Expected: FAIL (current code checks `parent.name == "project-router"`)

- [ ] **Step 3: Fix inference logic**

In `resolve_adoption_state`, replace the name-based check:
```python
# Before
elif project_rule.inbox_path and not has_placeholder_path(project_rule.inbox_path):
    if project_rule.inbox_path.parent.name == "project-router":
        target = project_rule.inbox_path.parent
    else:
        raise SystemExit(
            f"Cannot infer router root: inbox_path parent is '{project_rule.inbox_path.parent.name}', "
            f"expected 'project-router'. Use --router-root."
        )

# After
elif project_rule.inbox_path and not has_placeholder_path(project_rule.inbox_path):
    candidate_parent = project_rule.inbox_path.parent
    if (candidate_parent / "router-contract.json").exists():
        target = candidate_parent
    else:
        raise SystemExit(
            f"Cannot infer router root: no router-contract.json found in '{candidate_parent}'. "
            f"Use --router-root."
        )
```

- [ ] **Step 4: Update structural_preflight hint**

Change the `.git` error message:
```python
# Before
f"Did you mean '{target / 'project-router'}'?"
# After
f"Did you mean '{target / 'Router'}'?"
```

- [ ] **Step 5: Run tests**

Run: `python3 -m pytest tests/test_project_router.py -v -x`
Expected: All pass (including the new test and existing `test_adopt_unsafe_inference_aborts`)

- [ ] **Step 6: Update test_adopt_unsafe_inference_aborts assertion**

The error message changed from "expected 'project-router'" to "no router-contract.json". Update the assertion:
```python
# Before
self.assertIn("Cannot infer", str(ctx.exception))
# After — same assertion, message still starts with "Cannot infer"
self.assertIn("Cannot infer", str(ctx.exception))
```
(No change needed — assertion is broad enough.)

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "fix: content-based router root inference instead of name-based"
```

### Task 3: Update .gitignore for Router/

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add Router/ inbox/outbox gitignore rules**

Append to `.gitignore`:
```
# Router inbox/outbox packets are runtime artifacts
Router/inbox/*
!Router/inbox/.gitkeep
Router/outbox/*
!Router/outbox/.gitkeep
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore && git commit -m "chore: gitignore Router/ inbox and outbox runtime artifacts"
```

### Task 4: Update help text and error messages in cli.py

**Files:**
- Modify: `src/project_router/cli.py` — argparse help strings and error messages

- [ ] **Step 1: Update references in cli.py**

Change these strings:
- Line ~3420: `"Missing project-router contract at {contract_path}"` → keep as-is (runtime message, path is dynamic)
- Line ~3968: `"Also scan this repository's local project-router/outbox if configured."` → `"Also scan this repository's local Router/outbox if configured."`
- Line ~3972: `"Validate a project-router contract and outbox surface."` → `"Validate a Router contract and outbox surface."`
- Line ~3973: `"Direct path to a project-router root for local validation."` → `"Direct path to a Router root for local validation."`
- Line ~3992: `"Create a downstream project-router scaffold."` → `"Create a downstream Router scaffold."`
- Line ~3994: `"Absolute path to the project-router directory."` → `"Absolute path to the Router directory."`

- [ ] **Step 2: Run tests**

Run: `python3 -m pytest tests/test_project_router.py -v -x`
Expected: All pass

- [ ] **Step 3: Commit**

```bash
git add src/project_router/cli.py && git commit -m "chore: update CLI help strings project-router → Router"
```

## Chunk 2: Documentation + Governance

### Task 5: Update governance manifests

**Files:**
- Modify: `repo-governance/ownership.manifest.json` — pattern `project-router/**` → `Router/**`
- Modify: `repo-governance/customization-contracts.json` — pattern `project-router/**` → `Router/**`
- Modify: `scripts/check_repo_ownership.py` — sample paths

- [ ] **Step 1: Update ownership.manifest.json**

Change `"pattern": "project-router/**"` → `"pattern": "Router/**"`

- [ ] **Step 2: Update customization-contracts.json**

Change `"pattern": "project-router/**"` → `"pattern": "Router/**"`

- [ ] **Step 3: Update check_repo_ownership.py**

Change sample paths:
```python
# Before
"project-router/router-contract.json",
"project-router/conformance/valid-packet.example.md",
# After
"Router/router-contract.json",
"Router/conformance/valid-packet.example.md",
```

- [ ] **Step 4: Run governance checks**

```bash
python3 scripts/check_repo_ownership.py
python3 scripts/check_customization_contracts.py
```
Expected: Both `"status": "ok"`

- [ ] **Step 5: Commit**

```bash
git add repo-governance/ scripts/check_repo_ownership.py && git commit -m "chore: update governance manifests project-router → Router"
```

### Task 6: Update documentation files

**Files:**
- Modify: `CLAUDE.md` — 3 references
- Modify: `AGENTS.md` — 1 reference
- Modify: `README.md` — 6 references
- Modify: `README.pt-PT.md` — 1 reference
- Modify: `Knowledge/ContextPack.md` — 1 reference
- Modify: `Knowledge/Glossary.md` — 1 reference (protocol description)
- Modify: `Knowledge/ScriptsReference.md` — 2 references
- Modify: `Knowledge/PipelineMap.md` — 1 reference
- Modify: `Knowledge/CustomizationContract.md` — 1 reference

- [ ] **Step 1: Batch replace `project-router/` → `Router/` in all docs**

For each file listed above, replace directory references. Keep "project-router protocol" as the protocol name where it refers to the concept, not the directory.

- [ ] **Step 2: Run governance checks**

```bash
python3 scripts/check_managed_blocks.py
python3 scripts/check_knowledge_structure.py --strict
```
Expected: Both ok

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md AGENTS.md README.md README.pt-PT.md Knowledge/ && git commit -m "docs: update directory references project-router → Router"
```

### Task 7: Update test helper paths

**Files:**
- Modify: `tests/test_project_router.py` — `write_registry` helper uses `"project-router"` in paths

- [ ] **Step 1: Update write_registry inbox_path and router_root_path**

The test helper `write_registry` creates paths like `root / "repos" / "home-renovation" / "project-router"`. These are temp test paths — they don't need to match the repo convention. However, `write_registry_legacy` and various tests use `"project-router"` in constructed paths. These are fine as-is because they test arbitrary paths, not the directory name convention. No changes needed to test paths.

- [ ] **Step 2: Run full test suite**

```bash
python3 -m pytest tests/test_project_router.py tests/test_template_governance.py -v
```
Expected: All pass

- [ ] **Step 3: Commit (if any changes)**

### Task 8: Final validation

- [ ] **Step 1: Run full validation**

```bash
python3 scripts/refresh_knowledge_local.py --apply-missing
python3 -m pytest tests/test_project_router.py tests/test_template_governance.py -v
python3 scripts/check_agent_surface_parity.py --pre-publish
python3 scripts/check_repo_ownership.py
python3 scripts/check_sync_manifest_alignment.py
python3 scripts/check_managed_blocks.py
python3 scripts/check_customization_contracts.py
python3 scripts/check_knowledge_structure.py --strict
python3 scripts/check_adr_related_links.py --mode block
```
Expected: All pass

- [ ] **Step 2: Push and update PR**

```bash
git push
```
