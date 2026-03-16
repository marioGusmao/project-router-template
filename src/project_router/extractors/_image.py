"""Image metadata extractor with AI fallback flag."""

from __future__ import annotations

import struct
from pathlib import Path

from ._base import ExtractionResult, basic_file_metadata, guess_content_type
from ._registry import register


def _png_dimensions(path: Path) -> tuple[int, int] | None:
    """Read width/height from PNG IHDR chunk."""
    try:
        with open(path, "rb") as f:
            header = f.read(24)
            if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
                return None
            w, h = struct.unpack(">II", header[16:24])
            return w, h
    except OSError:
        return None


def _jpeg_dimensions(path: Path) -> tuple[int, int] | None:
    """Read width/height from JPEG SOF marker."""
    try:
        with open(path, "rb") as f:
            data = f.read(64 * 1024)
            if len(data) < 2 or data[:2] != b"\xff\xd8":
                return None
            i = 2
            while i < len(data) - 1:
                if data[i] != 0xFF:
                    break
                marker = data[i + 1]
                if marker in (0xC0, 0xC1, 0xC2):
                    if i + 9 < len(data):
                        h, w = struct.unpack(">HH", data[i + 5 : i + 9])
                        return w, h
                    return None
                if marker == 0xD9 or marker == 0xDA:
                    break
                if i + 3 < len(data):
                    length = struct.unpack(">H", data[i + 2 : i + 4])[0]
                    i += 2 + length
                else:
                    break
    except OSError:
        return None
    return None


def _gif_dimensions(path: Path) -> tuple[int, int] | None:
    """Read width/height from GIF header."""
    try:
        with open(path, "rb") as f:
            header = f.read(10)
            if len(header) < 10 or header[:4] != b"GIF8":
                return None
            w, h = struct.unpack("<HH", header[6:10])
            return w, h
    except OSError:
        return None


def _image_dimensions(path: Path) -> tuple[int, int] | None:
    """Attempt to read image dimensions using stdlib-only methods."""
    ext = path.suffix.lower()
    if ext == ".png":
        return _png_dimensions(path)
    if ext in (".jpg", ".jpeg"):
        return _jpeg_dimensions(path)
    if ext == ".gif":
        return _gif_dimensions(path)
    return None


@register([".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff", ".tif"])
def extract_image(path: Path) -> ExtractionResult:
    """Extract metadata from image files. Always flags needs_ai_extraction."""
    meta = basic_file_metadata(path)
    dims = _image_dimensions(path)
    if dims:
        meta["width"], meta["height"] = dims
    return ExtractionResult(
        content_type=guess_content_type(path),
        extraction_method="metadata_only",
        metadata=meta,
        needs_ai_extraction=True,
        ai_extraction_hint="Image file — deterministic text extraction not possible. Use multimodal AI to describe or transcribe the image content.",
    )
