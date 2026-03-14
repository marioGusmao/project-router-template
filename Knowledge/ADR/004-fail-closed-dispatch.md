# ADR-004: Fail-Closed Dispatch

**Status:** accepted

**Date:** 2026-03-14

## Context

Dispatch writes files into downstream project inboxes. These are real filesystem writes to directories that may be managed by other tools, agents, or workflows. Misconfiguration could:

- Send notes to the wrong project.
- Write to nonexistent or placeholder paths, causing silent data loss.
- Dispatch stale or uncompiled notes, breaking downstream expectations.
- Dispatch notes the user never approved, violating trust.

## Decision

Fail closed on every dispatch precondition:

1. **Missing `registry.local.json`**: Blocks all dispatch. Cannot dispatch without local configuration.
2. **Missing `router_root_path`**: Skips that project candidate with an explicit warning. Does not fall back to guessing.
3. **Invalid or placeholder paths**: Blocks dispatch for that project. Paths must be absolute and point to existing directories.
4. **Stale compiled packages**: Blocks dispatch if the compiled artifact is older than the canonical normalized note.
5. **Missing user approval**: Blocks dispatch. Approval must name exact `source_note_id` values via `--note-id`. No batch-all shortcut.
6. **Missing `--confirm-user-approval` flag**: Blocks dispatch. The flag itself is a safety gate.

Every skip produces an explicit reason in the output. No silent failures.

## Consequences

- No silent failures -- every blocked dispatch explains why.
- Users must actively configure `registry.local.json` with real paths before dispatch works.
- More verbose error output, but much safer.
- Dispatch is intentionally difficult without explicit, per-note approval.
- Dry-run mode (`--dry-run`) lets users preview dispatch targets without risk.

## Related

- ADR-005: Safety invariants (the broader safety contract that includes dispatch)
- ADR-001: Stdlib only (simplicity motivation is shared)
