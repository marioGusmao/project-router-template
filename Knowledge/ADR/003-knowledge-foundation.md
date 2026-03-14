# ADR-003: Knowledge Foundation

**Status:** accepted

**Date:** 2026-03-14

## Context

New humans and AI agents need to onboard quickly. Before this decision:

- Architectural decisions were undocumented -- rationale lived in commit messages or was lost entirely.
- Scripts lacked "why and when" context -- only raw command signatures were documented.
- There was no structured glossary, so terms like "capture_kind" vs "intent" vs "destination" were easy to confuse.
- The pipeline flow required reading ~2000 lines of `cli.py` to understand.

## Decision

Add a committed `Knowledge/` directory with:

- **TLDR.md**: 15-line project summary for fast orientation.
- **ContextPack.md**: "Where to find what" routing table for GitHub browsing.
- **Glossary.md**: ~25 terms across 6 categories with precise definitions.
- **PipelineMap.md**: Concrete trace of a note through every pipeline stage.
- **Roadmap.md**: Template milestones and planned work.
- **ScriptsReference.md**: Scripts grouped by purpose with "why and when" context.
- **ADR/**: Architecture Decision Records (000--099 for template).

The canonical seed scaffold for derived repos lives in `Knowledge/Templates/local/` (template_owned, synced from upstream).

Derived content lives in `Knowledge/local/` (private_owned):

- `Knowledge/local/ADR/`: Project-specific ADRs starting at 100.
- `Knowledge/local/Roadmap.md`: Project-specific roadmap.
- `Knowledge/local/notes/`: Operational scratch notes.

All synced Knowledge files are `template_owned`. A `context` CLI subcommand generates live project briefings from current state.

## Consequences

- Faster onboarding for both humans and AI agents.
- Architectural decisions are discoverable and searchable.
- Knowledge syncs safely from template to derived repos via the ownership model.
- Private bootstrap can backfill `Knowledge/local/` from one committed scaffold source.
- Derived repos extend in `local/` without merge conflicts.
- Maintaining knowledge docs adds a small overhead when pipeline changes occur.
- The `context` command provides always-accurate live briefings, complementing the static docs.
- ADR cross-references are validated by `check_adr_related_links.py`, catching broken links and self-references.
- The private scaffold seed includes `Knowledge/Templates/local/TLDR/README.md`, seeding an optional project-specific TLDR directory in derived repos.

## Related

- ADR-002: Template/private split (Knowledge uses the same ownership model)
