# ADR-001: Standard Library Only

**Status:** accepted

**Date:** 2026-03-14

## Context

The router needs to run anywhere Python 3.11+ is available without requiring package installation. Users should be able to clone the repo and run the pipeline immediately. Dependency management adds friction and potential conflicts, especially when the router runs alongside other projects on the same machine.

## Decision

Zero external package dependencies. All code uses Python standard library only.

- HTTP client uses `urllib` instead of `requests`.
- JSON handling uses the built-in `json` module.
- Testing uses `unittest` (stdlib) rather than requiring `pytest` as a dependency (though `pytest` can run the unittest-based tests if available).
- Argument parsing uses `argparse`.
- File operations use `pathlib` and `os`.

## Consequences

- No `pip install` step needed. Clone and run.
- No dependency conflicts with other projects on the same machine.
- No virtual environment required (though still recommended practice).
- Some features require more verbose code than third-party libraries would provide (e.g., `urllib` vs `requests`).
- New contributors familiar with popular packages may need to adjust to stdlib equivalents.
- Testing can use either `python3 -m unittest` or `python3 -m pytest` (pytest discovers unittest tests).

## Related

- ADR-004: Fail-closed dispatch (also motivated by simplicity and safety)
- ADR-007: Optional extractor dependencies (amends this ADR for the extractors boundary)
