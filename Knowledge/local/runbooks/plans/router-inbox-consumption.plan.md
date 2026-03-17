# Router Inbox Consumption

## Status

- Overall: `implemented`
- Current phase: `P04` (complete)

## Summary

Enable the Project Router to consume items from its own `router/inbox/`, establishing the downstream consumption pattern that all projects with a `router/` interface will follow.

Three CLI commands (`inbox-intake`, `inbox-status`, `inbox-ack`) handle the lifecycle. `inbox-intake` validates and archives incoming packets — converting legacy compiled briefs to protocol-compliant packets automatically. `inbox-ack` closes items and emits response packets to `router/outbox/`. State lives in per-packet JSON files under `state/project_router/inbox_status/`.

The plan also formalises `router/archive/` as a `local_only` surface for preserving received originals, updates `router-contract.json` to declare `ack` as a supported packet type, and adds an AI skill to guide agents through consumption sessions.

## Execution Phases

- `P01` complete: governance and contract groundwork — `.gitignore`, `ownership.manifest.json`, `customization-contracts.json`, `router-contract.json`, `router/archive/.gitkeep`
- `P02` complete: CLI implementation — `inbox-intake` (with brief-to-packet conversion), `inbox-status`, `inbox-ack`, parser registration, `status` integration, `ensure_layout`, `write_scaffold_dirs`
- `P03` complete: skills, documentation, and session opener — skill in 3 surfaces, session opener update, `router/README.md` expansion, private AI overlay commands
- `P04` complete: tests, validation lane, and plan promotion — 13 unit tests, full governance lane green, live smoke test with 2 existing inbox items

## Implementation Record

### Files modified
- `.gitignore` — added `router/archive/*` and `!router/archive/.gitkeep`
- `repo-governance/ownership.manifest.json` — inserted `router/archive/**` rule before `router/**`
- `repo-governance/customization-contracts.json` — inserted `router/archive/**` surface before `router/**`
- `router/router-contract.json` — added `"ack"` to `supported_packet_types`
- `src/project_router/cli.py` — constants, ensure_layout, write_scaffold_dirs, 6 helpers, 3 commands, parser registration, status integration
- `tests/test_project_router.py` — prepare_repo, patch_cli_paths, 13 new tests in `InboxConsumptionTests`
- `.claude/skills/project-router-inbox-consumer/SKILL.md` — new skill
- `.agents/skills/project-router-inbox-consumer/SKILL.md` — new skill
- `.codex/skills/project-router-inbox-consumer/SKILL.md` — new skill
- `.claude/skills/project-router-session-opener/SKILL.md` — added inbox steps
- `.agents/skills/project-router-session-opener/SKILL.md` — added inbox steps
- `.codex/skills/project-router-session-opener/SKILL.md` — added inbox steps
- `router/README.md` — expanded with 5-surface structure and consumption lifecycle
- `Knowledge/local/AI/claude.md` — added inbox commands
- `Knowledge/local/AI/codex.md` — added inbox commands

### Files created
- `router/archive/.gitkeep`
