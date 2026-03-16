# Private AI Rules

This directory contains private cross-agent operating rules that override or extend the shared template surfaces (CLAUDE.md, AGENTS.md, skills).

## How It Works

- **CLAUDE.md** loads `claude.md` via `@import` in the `customization-contract` managed block.
- **AGENTS.md** references `codex.md` via prose instruction (Codex has no `@import`).
- This `README.md` is loaded by both surfaces for cross-agent rules.

## What Goes Here

| File | Audience | Purpose |
|------|----------|---------|
| `README.md` | All agents | Cross-agent private rules (loaded by both Claude and Codex) |
| `claude.md` | Claude Code | Claude-specific additions: extra safety rules, workflow tweaks, local preferences |
| `codex.md` | Codex | Codex-specific additions: agent configs, local workflow overrides |

## What Does NOT Go Here

- **Routing rules** belong in `projects/registry.shared.json` (committed) or `projects/registry.local.json` (local).
- **Machine paths** belong in `.env.local` or `projects/registry.local.json`.
- **Skills** can be added as extra directories under `.claude/skills/`, `.codex/skills/`, or `.agents/skills/` — they survive sync without needing to be here.
- **ADRs** belong in `Knowledge/local/ADR/`.

## Guidelines

- Keep rules concise and actionable.
- These files are `private_owned` — they never sync from the template upstream.
- Empty files are valid — they produce no effect until you add content.
