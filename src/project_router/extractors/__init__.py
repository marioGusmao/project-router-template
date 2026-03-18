"""Content extraction for ingested files.

Public API:
    extract(path) -> ExtractionResult
    SUPPORTED_EXTENSIONS -> frozenset[str]
"""

from __future__ import annotations

from pathlib import Path

from ._base import ExtractionResult, basic_file_metadata, guess_content_type
from ._registry import get_extractor, supported_extensions

# Import submodules to trigger registration.
from . import _text  # noqa: F401
from . import _pdf  # noqa: F401
from . import _image  # noqa: F401
from . import _office  # noqa: F401


def extract(path: Path) -> ExtractionResult:
    """Extract text content from a file using the registered extractor."""
    extractor = get_extractor(path)
    if extractor is None:
        return ExtractionResult(
            content_type=guess_content_type(path),
            extraction_method="unsupported",
            metadata=basic_file_metadata(path),
            needs_ai_extraction=True,
            ai_extraction_hint=f"No deterministic extractor for '{path.suffix}'. Use AI to read this file.",
        )
    return extractor(path)


SUPPORTED_EXTENSIONS: frozenset[str] = supported_extensions()

__all__ = [
    "extract",
    "ExtractionResult",
    "SUPPORTED_EXTENSIONS",
    "basic_file_metadata",
    "guess_content_type",
]
