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

When updating a shared workflow:

1. Update `.agents/skills/` first.
2. Mirror the change into `.codex/skills/` and `.claude/skills/`.
3. Update `README.md`, `AGENTS.md`, or `CLAUDE.md` when the operating model changes.
4. Run `python3 scripts/check_agent_surface_parity.py`.
5. Run `python3 scripts/check_repo_ownership.py`.
