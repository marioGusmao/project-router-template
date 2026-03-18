"""Core types and utilities for content extractors."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExtractionResult:
    """Result of extracting text content from a file."""

    text: str = ""
    content_type: str = "application/octet-stream"
    extraction_method: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)
    needs_ai_extraction: bool = False
    ai_extraction_hint: str = ""
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


def basic_file_metadata(path: Path) -> dict[str, Any]:
    """Return basic file stat information."""
    try:
        stat = path.stat()
        return {
            "size_bytes": stat.st_size,
            "mtime": stat.st_mtime,
            "mode": oct(stat.st_mode & 0o777),
        }
    except OSError as exc:
        return {"error": str(exc)}


MIME_BY_EXTENSION: dict[str, str] = {
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".json": "application/json",
    ".html": "text/html",
    ".htm": "text/html",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def guess_content_type(path: Path) -> str:
    return MIME_BY_EXTENSION.get(path.suffix.lower(), "application/octet-stream")
