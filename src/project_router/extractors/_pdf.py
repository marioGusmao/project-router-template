"""PDF extractor with optional PyMuPDF dependency."""

from __future__ import annotations

from pathlib import Path

from ._base import ExtractionResult, basic_file_metadata
from ._registry import register

try:
    import pymupdf  # noqa: F401

    _HAS_PYMUPDF = True
except ImportError:
    _HAS_PYMUPDF = False


@register([".pdf"])
def extract_pdf(path: Path) -> ExtractionResult:
    """Extract text from PDF files using PyMuPDF if available."""
    meta = basic_file_metadata(path)
    if not _HAS_PYMUPDF:
        return ExtractionResult(
            content_type="application/pdf",
            extraction_method="unavailable",
            metadata=meta,
            needs_ai_extraction=True,
            ai_extraction_hint="PyMuPDF not installed. Install pymupdf>=1.24.0 for deterministic PDF extraction, or use AI to read this file.",
        )
    try:
        import pymupdf

        doc = pymupdf.open(str(path))
        pages: list[str] = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        text = "\n\n".join(pages).strip()
        meta["page_count"] = len(pages)
        if not text:
            return ExtractionResult(
                content_type="application/pdf",
                extraction_method="pymupdf",
                metadata=meta,
                needs_ai_extraction=True,
                ai_extraction_hint="PDF opened successfully but no text extracted (may be scanned/image-only). Use AI to read this file.",
            )
        return ExtractionResult(
            text=text,
            content_type="application/pdf",
            extraction_method="pymupdf",
            metadata=meta,
        )
    except Exception as exc:
        return ExtractionResult(
            content_type="application/pdf",
            extraction_method="pymupdf",
            metadata=meta,
            error=str(exc),
            needs_ai_extraction=True,
            ai_extraction_hint=f"PDF extraction failed: {exc}. Use AI to read this file.",
        )
