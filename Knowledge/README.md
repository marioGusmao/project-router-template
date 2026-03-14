# Knowledge Directory

This directory contains the project's structured knowledge layer: onboarding docs, architectural decisions, glossary, pipeline reference, roadmap, and seed files for derived repositories.

## Sync Model

Everything **outside** `local/` is **template-owned** and syncs from the upstream template repository. Do not modify these files in your derived repo -- they will be overwritten by the next template sync.

The template-owned scaffold for derived repositories lives in `Knowledge/Templates/local/`. `python3 scripts/bootstrap_private_repo.py` materializes that scaffold into `Knowledge/local/` inside a private-derived repo.

Use `python3 scripts/refresh_knowledge_local.py` to preview or backfill missing scaffold files in older derived repos after template updates.

Your derived content goes in `Knowledge/local/` after bootstrap:

| Location | Ownership | Syncs from template? |
|----------|-----------|----------------------|
| `Knowledge/*.md` | template_owned | Yes |
| `Knowledge/ADR/000-099` | template_owned | Yes |
| `Knowledge/Templates/local/` | template_owned | Yes |
| `Knowledge/local/` | private_owned | No |
| `Knowledge/local/ADR/100+` | private_owned | No |

## Extension Rules

1. **Never modify curated files outside `local/`** in a derived repo. Template sync will overwrite your changes.
2. **Template ADRs use numbers 000--099.** Your project-specific ADRs go in `Knowledge/local/ADR/` starting at 100.
3. **Your private roadmap** goes in `Knowledge/local/Roadmap.md`.
4. **Operational notes** (scratch, session logs, etc.) go in `Knowledge/local/notes/`.

## Quick Start

- Read `TLDR.md` for a 15-line project summary.
- Read `ContextPack.md` for a "where to find what" routing table.
- Read `Glossary.md` for term definitions.
- Read `PipelineMap.md` for a concrete trace of a note through the pipeline.
- Browse `ADR/` for architectural decision records.
