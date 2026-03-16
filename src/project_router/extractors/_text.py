"""Stdlib-only extractors for text-based file formats."""

from __future__ import annotations

import csv
import html as html_module
import io
import json
import re
from pathlib import Path

from ._base import ExtractionResult, basic_file_metadata, guess_content_type
from ._registry import register


def _strip_html(text: str) -> str:
    """Strip HTML tags and unescape entities."""
    if not text:
        return ""
    plain = html_module.unescape(text)
    plain = plain.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    plain = re.sub(r"</p\s*>", "\n\n", plain, flags=re.IGNORECASE)
    plain = re.sub(r"<[^>]+>", "", plain)
    return plain.strip()


@register([".md", ".txt"])
def extract_plaintext(path: Path) -> ExtractionResult:
    """Extract text from markdown or plain text files."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            text = path.read_text(encoding="latin-1")
        except OSError as exc:
            return ExtractionResult(
                content_type=guess_content_type(path),
                extraction_method="stdlib_read",
                metadata=basic_file_metadata(path),
                error=str(exc),
            )
    except OSError as exc:
        return ExtractionResult(
            content_type=guess_content_type(path),
            extraction_method="stdlib_read",
            metadata=basic_file_metadata(path),
            error=str(exc),
        )
    return ExtractionResult(
        text=text,
        content_type=guess_content_type(path),
        extraction_method="stdlib_read",
        metadata=basic_file_metadata(path),
    )


@register([".csv"])
def extract_csv(path: Path) -> ExtractionResult:
    """Extract text from CSV files as readable rows."""
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            raw = path.read_text(encoding="latin-1")
        except OSError as exc:
            return ExtractionResult(
                content_type="text/csv",
                extraction_method="stdlib_csv",
                metadata=basic_file_metadata(path),
                error=str(exc),
            )
    except OSError as exc:
        return ExtractionResult(
            content_type="text/csv",
            extraction_method="stdlib_csv",
            metadata=basic_file_metadata(path),
            error=str(exc),
        )
    try:
        reader = csv.reader(io.StringIO(raw))
        rows = list(reader)
        text = "\n".join(", ".join(row) for row in rows)
    except csv.Error as exc:
        return ExtractionResult(
            text=raw,
            content_type="text/csv",
            extraction_method="stdlib_csv_fallback",
            metadata=basic_file_metadata(path),
            warnings=[f"CSV parse error: {exc}"],
        )
    return ExtractionResult(
        text=text,
        content_type="text/csv",
        extraction_method="stdlib_csv",
        metadata={**basic_file_metadata(path), "row_count": len(rows)},
    )


@register([".json"])
def extract_json(path: Path) -> ExtractionResult:
    """Extract text from JSON files as pretty-printed content."""
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        text = json.dumps(data, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        return ExtractionResult(
            content_type="application/json",
            extraction_method="stdlib_json",
            metadata=basic_file_metadata(path),
            error=str(exc),
        )
    return ExtractionResult(
        text=text,
        content_type="application/json",
        extraction_method="stdlib_json",
        metadata=basic_file_metadata(path),
    )


@register([".html", ".htm"])
def extract_html(path: Path) -> ExtractionResult:
    """Extract text from HTML files by stripping tags."""
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            raw = path.read_text(encoding="latin-1")
        except OSError as exc:
            return ExtractionResult(
                content_type="text/html",
                extraction_method="stdlib_html_strip",
                metadata=basic_file_metadata(path),
                error=str(exc),
            )
    except OSError as exc:
        return ExtractionResult(
            content_type="text/html",
            extraction_method="stdlib_html_strip",
            metadata=basic_file_metadata(path),
            error=str(exc),
        )
    text = _strip_html(raw)
    return ExtractionResult(
        text=text,
        content_type="text/html",
        extraction_method="stdlib_html_strip",
        metadata=basic_file_metadata(path),
    )
