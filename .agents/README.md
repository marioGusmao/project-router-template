# Agent References

This directory is the canonical neutral reference layer for shared agent workflows in the Project Router starter.

Use it this way:

- keep the shared workflow contract in `.agents/skills/`
- adapt that contract into `.codex/skills/` and `.claude/skills/`
- allow platform-specific notes only when they do not weaken the shared safety rules

The goal is not byte-for-byte identity. The goal is behavioral parity:

- same safety boundaries
- same pipeline order
- same dispatch approval contract
- same repository entrypoints such as `python3 scripts/project_router_client.py`
- same read-only downstream scan command `python3 scripts/project_router.py scan-outboxes`
- same contract validation command `python3 scripts/project_router.py doctor`
- same promotion path for derived private repositories via `python3 scripts/bootstrap_private_repo.py`

## Knowledge Foundation

The `Knowledge/` directory provides onboarding docs and architectural decision records. See `Knowledge/ContextPack.md` for a routing guide to the codebase, or run `python3 scripts/project_router.py context` for a live project briefing. Validate Knowledge structure with `python3 scripts/check_knowledge_structure.py`.

## Additional Commands

- `python3 scripts/bootstrap_local.py` — set up local config
- `python3 scripts/refresh_knowledge_local.py` — preview or backfill the Knowledge/local scaffold
- `python3 scripts/project_router.py decide --note-id vn_123 --decision approve` — record a user decision
- `python3 scripts/project_router.py dispatch --confirm-user-approval --note-id vn_123` — real dispatch with explicit approval
- `python3 scripts/project_router.py migrate-source-layout --dry-run` — preview legacy migration
- `python3 scripts/check_agent_surface_parity.py` — validate agent surface parity
- `python3 scripts/check_repo_ownership.py` — validate ownership manifest
- `python3 scripts/check_sync_manifest_alignment.py` — validate sync manifest alignment
- `python3 scripts/check_adr_related_links.py` — validate ADR related links

When updating a shared workflow:

1. Update `.agents/skills/` first.
2. Mirror the change into `.codex/skills/` and `.claude/skills/`.
3. Update `README.md`, `AGENTS.md`, or `CLAUDE.md` when the operating model changes.
4. Run `python3 scripts/check_agent_surface_parity.py`.
5. Run `python3 scripts/check_repo_ownership.py`.
6. Run `python3 scripts/check_managed_blocks.py`.
7. Run `python3 scripts/check_customization_contracts.py`.
