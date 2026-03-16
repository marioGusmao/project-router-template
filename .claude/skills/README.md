# Claude Skills

These files mirror the repository workflows that already exist for Codex under `.codex/skills/`.

The goal is contract parity, not byte-for-byte identity:

- keep the same safety boundaries
- keep the same routing and review flow
- allow tool-specific notes when needed

Use repository-neutral entrypoints such as `python3 scripts/project_router_client.py ...` when a workflow needs direct access to the VoiceNotes API through Project Router.
