# Template Roadmap

Milestones for the project-router-template upstream. Derived repos maintain their own roadmap in `Knowledge/local/Roadmap.md`.

## v0.1.0 (current)

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
- Knowledge/local/ for derived repo extensions

## Future

- Frozen vocabulary validation: enforce consistent term usage across agent surfaces
- ADR cross-reference checker: validate Related links between ADRs
- Machine-readable glossary: structured format for tooling consumption
- Stronger bootstrap migrations for older derived repos when the local scaffold changes
