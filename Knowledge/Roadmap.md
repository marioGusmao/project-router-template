# Template Roadmap

Milestones for the project-router-template upstream. Derived repos maintain their own roadmap in `Knowledge/local/Roadmap.md`.

## v0.1.0

Core pipeline and governance foundation.

- Core pipeline stages: sync, normalize, triage, compile, review, decide, dispatch
- Safety rules: fail-closed dispatch, raw preservation, note-specific approval
- Governance tooling: ownership manifest, parity checks, repo ownership checks
- Template/private split: bootstrap_private_repo.py, ownership.manifest.json
- Project-router protocol: router-contract.json, inbox, outbox, conformance, doctor
- Agent surfaces: .agents/skills/, .claude/skills/, .codex/skills/ with parity enforcement
- Source-aware pipeline paths: voicenotes and project_router sources

## v0.2.0 (knowledge foundation)

Structured knowledge layer for onboarding and decision tracking.

- Knowledge directory: TLDR, ContextPack, Glossary, PipelineMap, Roadmap, ScriptsReference
- Architecture Decision Records (ADRs) with template/private numbering split
- `context` CLI subcommand for live project briefings
- Knowledge structure validator: check_knowledge_structure.py
- Sync-manifest consistency check: check_sync_manifest_alignment.py
- Knowledge/local/ for derived repo extensions

## v0.3.0 (governance hardening)

Extended governance validators and private scaffold seeds.

- ADR related-links validator: `check_adr_related_links.py` with `--mode warn/block`
- Private TLDR seed: `Knowledge/Templates/local/TLDR/README.md`

## Deferred Backlog

Items below are captured with enough implementation detail to be self-contained. Each entry records why it matters, what would trigger it, and what the implementation looks like.

### 1. Portability checker

- **Why:** Prevents committing machine-local paths (`/Users/...`, `/home/...`) into tracked files. Critical for template repos designed to be shared.
- **Trigger:** Evidence of accidentally committed local paths, or before first public release.
- **Target artifacts:** `scripts/check_portability.py` (~140 lines), CI job.
- **Acceptance:** Scans `git ls-files` for local absolute paths. Allowlist-based exceptions. Exit 0 on clean, 1 on violations.
- **Not now:** No tracked local paths found in current repo state.
- **Implementation notes:** Core regex for POSIX (`/Users/`, `/home/`) and Windows (`C:\`) local paths. Default allowlist: `tests/**`, `scripts/check_portability.py`. Convention: `from __future__ import annotations`, `raise SystemExit(main())`, `argparse` with `--allowlist PATH`.

### 2. Auto-generated script catalog

- **Why:** Manual `ScriptsReference.md` maintenance grows burdensome; skill inventory not machine-discoverable.
- **Trigger:** `scripts/` grows past ~15 files or shared skills past ~6.
- **Target artifacts:** `scripts/generate_catalog.py` producing `Knowledge/generated/scripts-catalog.md`.
- **Acceptance:** Catalog reflects actual scripts/skills. `--check` mode for CI. AUTOGEN markers for safe re-generation.
- **Not now:** The repo is still below the trigger threshold, so manual reference maintenance is still manageable.
- **Implementation notes:** Use `ast.parse()` + `ast.get_docstring()` for docstring extraction (stdlib). Scan `scripts/*.py`. Skills: extract name from directory, description from first paragraph of SKILL.md. Output: `| Script | Description | Category |` table with AUTOGEN markers.

### 3. Wikilink validator

- **Why:** Prevents link rot across Knowledge/ documents.
- **Trigger:** Knowledge/ adopts `[[wikilink]]` syntax.
- **Target artifacts:** `scripts/check_knowledge_wikilinks.py` (~170 lines).
- **Acceptance:** Broken wikilinks detected with "did you mean?" suggestions. Fenced code blocks and inline code skipped. Local absolute markdown links flagged. Exit 0 on clean, 1 on broken links.
- **Not now:** Zero wikilinks exist in the project currently.
- **Implementation notes:** Core regex for `[[wikilinks]]`. Processing: detect fenced code toggles, strip inline code, scan for wikilinks. Target resolution: split on `|`, strip `#` anchors, append `.md` if needed. Similarity via `difflib.get_close_matches()`.

### 4. Obsidian vault configuration

- **Why:** Makes Knowledge/ browsable with graph view, backlinks, and outline.
- **Trigger:** Knowledge/ adopts wikilinks or a real vault workflow appears.
- **Target artifacts:** `Knowledge/.obsidian/app.json`, `appearance.json`, `core-plugins.json`. `workspace.json` is local-only, never committed.
- **Acceptance:** Vault opens correctly in Obsidian. Ownership rule added. `.gitignore` covers `workspace*.json`.
- **Not now:** No wikilinks exist; graph and backlinks would be empty.

### 5. Machine-readable glossary

- **Why:** Enable tooling to consume vocabulary programmatically. Foundation for frozen vocabulary validation.
- **Trigger:** A real consumer exists (e.g., frozen vocabulary validator or auto-documentation).
- **Target artifacts:** `Knowledge/Glossary.json` (JSON, not YAML per ADR-001), `scripts/check_glossary_sync.py`.
- **Acceptance:** Bidirectional sync validated. Every JSON term in Markdown and vice versa. Category assignments match.
- **Not now:** No consumer exists. 25 terms in one Markdown file is manageable.

### 6. Frozen vocabulary validation

- **Why:** Prevents terminology drift across 3 agent surfaces and documentation.
- **Trigger:** Combined ADR + TLDR count passes ~20, or multiple real TLDRs exist.
- **Target artifacts:** `scripts/check_frozen_vocabulary.py`.
- **Acceptance:** Pipeline stage names, review queue names, ownership classes validated against Glossary.json. Violations grouped by file. `--mode warn/block` pattern.
- **Not now:** Not enough surface area to drift.

### 7. Full ADR governance

- **Why:** Structured governance for a growing ADR corpus, including status lifecycle, required sections, and cross-reference integrity.
- **Trigger:** ADR count exceeds ~10 and related links alone are no longer sufficient.
- **Target artifacts:** `Knowledge/ADR/ADR-CROSS-REFERENCES.md`, upgraded `check_adr_related_links.py` with G1-G4 checks, `check_adr_supersession.py`.
- **Acceptance:** All 4 governance invariants enforced. Supersession chains validated. Cross-references bidirectional. `proposed` status defined with lifecycle contract.
- **Not now:** 6 ADRs with shallow cross-references. Adding full governance adds overhead without enough corpus to justify it.
- **Implementation notes:** G1: required sections (`## Context`, `## Decision`/`## Decisions`, `## Consequences`). G2: cross-references file. G3: README sequence counter. G4: approval queue matches proposed-status ADRs. Supersession validator: status/`superseded-by` consistency, reciprocal checks. Add reciprocal reference checking and document bidirectional rule.

### 8. Expanded private scaffolding

- **Why:** Derived repos benefit from consistent phased roadmaps.
- **Trigger:** Derived repos consistently adopt phased roadmaps.
- **Target artifacts:** New seeds under `Knowledge/Templates/local/` (roadmap phases, feature templates).
- **Acceptance:** Optional first, required after a sync cycle. `refresh_knowledge_local.py` handles backfill.
- **Not now:** Only one derived repo exists; workflow not yet proven.

### 9. Skills manifest

- **Why:** Deeper content validation beyond `parity.manifest.json`'s surface-level checks.
- **Trigger:** Skills exceed ~5.
- **Target artifacts:** `Knowledge/skills.manifest.json`, `scripts/check_skills_sync.py` (~280 lines).
- **Acceptance:** File existence, required sections, mirror rules, and edit parity enforced. Inventory validated against `AGENTS.md`. `--mode audit/enforce` with `--fail-on-severity` levels.
- **Not now:** 3 skills, parity manifest is sufficient.
