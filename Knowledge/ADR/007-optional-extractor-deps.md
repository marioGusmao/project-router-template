# ADR-007: Optional Extractor Dependencies

**Status:** accepted

**Date:** 2026-03-16

## Context

ADR-001 established a zero-dependency rule for the core pipeline. The filesystem source introduces content extraction from binary formats (PDF, DOCX) where stdlib-only approaches are insufficient. Without optional libraries, these files require AI-assisted extraction as a fallback, which adds latency and cost.

## Decision

Allow optional dependencies **only** in `src/project_router/extractors/` with graceful `ImportError` fallback. The core pipeline (`src/project_router/cli.py`) remains zero-dependency.

Optional dependencies are listed in `requirements-extractors.txt`:
- `pymupdf>=1.24.0` — PDF text extraction
- `python-docx>=1.1.0` — DOCX text extraction

When these are not installed, the corresponding extractors return `needs_ai_extraction=True` and the pipeline routes the note through the `needs_extraction` review queue for AI-assisted extraction.

## Consequences

- Core pipeline remains zero-dep: clone and run still works.
- Users who install optional deps get deterministic extraction for PDF/DOCX.
- Users without optional deps get a graceful fallback path via AI extraction.
- The `requirements-extractors.txt` file will migrate to `[project.optional-dependencies.extractors]` when `pyproject.toml` is added.
- No extractor may import an optional dependency at module level without a `try/except ImportError` guard.

## Related

- ADR-001: Standard library only (this ADR amends ADR-001 for the extractors boundary)
