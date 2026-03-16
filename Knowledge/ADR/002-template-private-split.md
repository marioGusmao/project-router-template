# ADR-002: Template/Private Repository Split

**Status:** accepted

**Date:** 2026-03-14

## Context

Users need a clean public starting point without their private notes, routing paths, or project-specific configuration. But they also need to customize routing rules, project registries, and agent skills for their own projects.

A single-repo model would force users to either maintain a fork (with constant merge conflicts) or keep everything private (losing the benefit of a shared template).

## Decision

Use the GitHub template repository model:

- **Template repo** (this repo): The shareable upstream. Contains common workflow, routing rules, agent guidance, and governance tooling. Stays neutral and project-agnostic.
- **Derived repos** (private): Operational homes. Created via GitHub's "Use this template" or manual clone. Hold secrets, machine-local paths, customized registries, and private routing packs.

Sync from template to derived repo is governed by:

- `repo-governance/ownership.manifest.json`: Declares which files are `template_owned` (synced), `private_owned` (never synced), `shared_review` (synced but may need local review), or `local_only` (gitignored).
- `template-upstream-sync.yml`: Workflow configuration for automated sync.
- `scripts/bootstrap_private_repo.py`: Promotion script that sets up a derived repo with sync metadata.

## Consequences

- Template stays neutral and shareable. No private data leaks.
- Private repos can customize freely without merge conflicts on owned files.
- Sync is governed and safe -- ownership manifest prevents accidental overwrites.
- Users must run `bootstrap_private_repo.py` once to set up sync in a derived repo.
- Two registries to maintain: `registry.shared.json` (template) and `registry.local.json` (local).
- See also `docs/superpowers/specs/` for detailed design documents.

## Related

- ADR-003: Knowledge foundation builds on this split model
- ADR-006: Template upgrade process and customization contract
