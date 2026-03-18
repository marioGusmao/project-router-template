"""Office document extractors with optional python-docx dependency."""

from __future__ import annotations

from pathlib import Path

from ._base import ExtractionResult, basic_file_metadata
from ._registry import register

try:
    import docx  # noqa: F401

    _HAS_DOCX = True
except ImportError:
    _HAS_DOCX = False


@register([".docx"])
def extract_docx(path: Path) -> ExtractionResult:
    """Extract text from DOCX files using python-docx if available."""
    meta = basic_file_metadata(path)
    if not _HAS_DOCX:
        return ExtractionResult(
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            extraction_method="unavailable",
            metadata=meta,
            needs_ai_extraction=True,
            ai_extraction_hint="python-docx not installed. Install python-docx>=1.1.0 for deterministic DOCX extraction, or use AI to read this file.",
        )
    try:
        import docx

        doc = docx.Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n\n".join(paragraphs)
        meta["paragraph_count"] = len(paragraphs)
        if not text:
            return ExtractionResult(
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                extraction_method="python_docx",
                metadata=meta,
                needs_ai_extraction=True,
                ai_extraction_hint="DOCX opened successfully but no text extracted. Use AI to read this file.",
            )
        return ExtractionResult(
            text=text,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            extraction_method="python_docx",
            metadata=meta,
        )
    except (MemoryError, RecursionError):
        raise
    except Exception as exc:
        return ExtractionResult(
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            extraction_method="python_docx",
            metadata=meta,
            error=str(exc),
            needs_ai_extraction=True,
            ai_extraction_hint=f"DOCX extraction failed: {exc}. Use AI to read this file.",
        )
