# ADR-000: Use Architecture Decision Records

**Status:** accepted

**Date:** 2026-03-14

## Context

The project needs a structured way to record and discover architectural decisions. Design rationale was previously scattered across commit messages, comments, and tribal knowledge.

The project also has design specs under `docs/superpowers/specs/`. ADRs capture the **why** of decisions; design specs capture the **how** of implementations. Both are valuable and complementary.

## Decision

Use Architecture Decision Records (ADRs) in `Knowledge/ADR/`. Each decision gets a numbered markdown file following the template in `Knowledge/ADR/TEMPLATE.md`.

Template ADRs use numbers 000--099 and are template_owned (synced from upstream). Derived repo ADRs go in `Knowledge/local/ADR/` starting at 100, and are private_owned (never synced).

Keep ADRs alongside design specs -- they serve different purposes and complement each other.

## Consequences

- Architectural decisions are discoverable by browsing `Knowledge/ADR/`.
- New contributors can understand the rationale behind design choices.
- Design specs and ADRs complement each other: specs describe implementation, ADRs describe reasoning.
- The template/private numbering split prevents merge conflicts during upstream sync.
- Adding a new ADR requires choosing the next available number in the appropriate range.
