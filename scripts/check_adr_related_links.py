#!/usr/bin/env python3
"""Validate that ## Related sections in ADR files point to real files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ADR_REF_RE = re.compile(r"ADR-(\d{3,})")
MALFORMED_RE = re.compile(r"(?i)ADR[- ]?\d+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=["warn", "block"],
        default="warn",
        help="Exit mode: warn always exits 0; block exits non-zero on errors.",
    )
    return parser.parse_args()


def collect_adr_dirs() -> list[Path]:
    """Return ADR directories to scan (template and local when present)."""
    dirs: list[Path] = []
    template_adr = ROOT / "Knowledge" / "ADR"
    if template_adr.is_dir():
        dirs.append(template_adr)
    local_adr = ROOT / "Knowledge" / "local" / "ADR"
    if local_adr.is_dir():
        dirs.append(local_adr)
    return dirs


def adr_id_from_filename(name: str) -> str | None:
    """Extract ADR ID from a filename like '001-stdlib-only.md'."""
    m = re.match(r"^(\d{3,})-.*\.md$", name)
    return m.group(1) if m else None


def build_adr_index(adr_dirs: list[Path]) -> tuple[dict[str, Path], list[str]]:
    """Map ADR IDs (e.g. '001') to their file paths across all ADR trees.

    Returns (index, warnings) where warnings captures duplicate ID collisions.
    """
    index: dict[str, Path] = {}
    warnings: list[str] = []
    for adr_dir in adr_dirs:
        for entry in adr_dir.iterdir():
            if not entry.is_file() or entry.name == "TEMPLATE.md":
                continue
            adr_id = adr_id_from_filename(entry.name)
            if adr_id:
                if adr_id in index:
                    warnings.append(
                        f"duplicate ADR ID {adr_id} in {entry.name} and {index[adr_id].name}"
                    )
                index[adr_id] = entry
    return index, warnings


def validate_related_section(
    path: Path,
    own_id: str,
    adr_index: dict[str, Path],
) -> tuple[list[str], list[str]]:
    """Validate the ## Related section of a single ADR file.

    Returns (errors, warnings).
    """
    errors: list[str] = []
    warnings: list[str] = []

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    in_related = False
    for line in lines:
        stripped = line.strip()
        if stripped == "## Related":
            in_related = True
            continue
        if in_related and stripped.startswith("## "):
            break
        if not in_related:
            continue

        # Check for valid ADR references
        valid_matches = list(ADR_REF_RE.finditer(line))
        valid_refs = [match.group(1) for match in valid_matches]
        valid_spans = {match.span() for match in valid_matches}
        for ref_id in valid_refs:
            if ref_id == own_id:
                errors.append(f"{path.name}: self-reference ADR-{ref_id}")
            elif ref_id not in adr_index:
                errors.append(f"{path.name}: nonexistent target ADR-{ref_id}")

        # Malformed ADR mentions should still warn even when the line also
        # contains valid ADR references; skip exact valid-match spans.
        if stripped:
            for malformed_match in MALFORMED_RE.finditer(line):
                if malformed_match.span() in valid_spans:
                    continue
                warnings.append(
                    f"{path.name}: malformed ADR reference '{malformed_match.group(0)}'"
                )

    return errors, warnings


def main() -> int:
    args = parse_args()
    adr_dirs = collect_adr_dirs()
    if not adr_dirs:
        print("No ADR directories found.", file=sys.stderr)
        return 1

    adr_index, index_warnings = build_adr_index(adr_dirs)
    all_errors: list[str] = []
    all_warnings: list[str] = index_warnings[:]
    files_checked = 0

    for adr_dir in adr_dirs:
        for entry in sorted(adr_dir.iterdir()):
            if not entry.is_file() or entry.name == "TEMPLATE.md":
                continue
            own_id = adr_id_from_filename(entry.name)
            if not own_id:
                continue
            files_checked += 1
            errors, warnings = validate_related_section(entry, own_id, adr_index)
            all_errors.extend(errors)
            all_warnings.extend(warnings)

    for w in all_warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    for e in all_errors:
        print(f"ERROR: {e}", file=sys.stderr)

    if all_errors and args.mode == "block":
        return 1

    if not all_errors and not all_warnings:
        print(json.dumps({"status": "ok", "files_checked": files_checked}, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
