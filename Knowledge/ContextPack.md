# Context Pack

This is a curated routing document for GitHub browsing -- a "where to find what" table for the project-router-template codebase.

For a live project briefing in the terminal, run `python3 scripts/project_router.py context`.

| Topic | Location | Notes |
|-------|----------|-------|
| Pipeline code | `src/project_router/cli.py` | Single-module CLI containing all pipeline stages |
| CLI entry point | `scripts/project_router.py` | Thin wrapper that calls `cli.main(argv)` |
| Sync client | `scripts/project_router_client.py` | Fetches from VoiceNotes API; requires `.env.local` |
| Project registry (shared) | `projects/registry.shared.json` | Committed: project metadata, keywords, thresholds |
| Project registry (local) | `projects/registry.local.json` | Gitignored: machine-local paths and overrides |
| Project registry (example) | `projects/registry.example.json` | Committed: starter template for the local overlay |
| Safety rules | `CLAUDE.md`, `AGENTS.md` | Critical invariants for dispatch, raw preservation, approval |
| Agent skills (canonical) | `.agents/skills/` | Neutral reference layer for shared workflow rules |
| Agent skills (Claude) | `.claude/skills/` | Claude-facing adaptations |
| Agent skills (Codex) | `.codex/skills/` | Codex-facing adaptations |
| Governance (ownership) | `repo-governance/ownership.manifest.json` | Template/private sync boundary |
| Governance (contracts) | `repo-governance/customization-contracts.json` | Per-surface sync model and overlay rules |
| Governance (parity) | `parity.manifest.json` | Agent surface parity tracking |
| Governance (validators) | `scripts/check_*.py` | Knowledge structure, ADR links, sync alignment, ownership, parity, managed blocks, contracts |
| Customization contract | `Knowledge/CustomizationContract.md` | Human-readable surface ownership table |
| Upgrade guide | `Knowledge/UpgradeGuide.md` | How to merge template sync PRs |
| Tests | `tests/test_project_router.py` | unittest + tempfile isolation |
| ADRs | `Knowledge/ADR/` | Architecture Decision Records (000--099 template) |
| Glossary | `Knowledge/Glossary.md` | ~25 terms across 6 categories |
| Pipeline map | `Knowledge/PipelineMap.md` | Concrete note trace through all stages |
| Scripts reference | `Knowledge/ScriptsReference.md` | Scripts grouped by purpose with prerequisites |
| Roadmap | `Knowledge/Roadmap.md` | Template milestones |
| Template promotion | `scripts/bootstrap_private_repo.py` | Promotes a derived copy into private operational repo |
| Local config bootstrap | `scripts/bootstrap_local.py` | Creates `.env.local` and `registry.local.json` |
| Design specs | `docs/superpowers/specs/` | Detailed implementation designs |
| Knowledge sync model | `Knowledge/README.md` | Explains Knowledge directory structure and sync rules |
| Changelog | `CHANGELOG.md` | Version history |
