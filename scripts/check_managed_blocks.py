#!/usr/bin/env python3
"""Validate that all managed block markers exist in matched begin/end pairs."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Map of files to the managed block marker names they must contain.
REQUIRED_BLOCKS: dict[str, list[str]] = {
    "README.md": ["repository-mode", "template-onboarding"],
    "README.pt-PT.md": ["repository-mode", "template-onboarding"],
    "AGENTS.md": ["repository-mode", "customization-contract"],
    "CLAUDE.md": ["repository-mode", "customization-contract"],
}

BEGIN_PATTERN = re.compile(r"<!--\s+(\S+?):begin\s+-->")
END_PATTERN = re.compile(r"<!--\s+(\S+?):end\s+-->")


def validate_file(rel_path: str, required_markers: list[str]) -> list[str]:
    path = ROOT / rel_path
    errors: list[str] = []

    if not path.exists():
        errors.append(f"{rel_path}: file does not exist")
        return errors

    text = path.read_text(encoding="utf-8")
    found_begins = set(BEGIN_PATTERN.findall(text))
    found_ends = set(END_PATTERN.findall(text))

    for marker in required_markers:
        if marker not in found_begins:
            errors.append(f"{rel_path}: missing <!-- {marker}:begin -->")
        if marker not in found_ends:
            errors.append(f"{rel_path}: missing <!-- {marker}:end -->")

    # Check for duplicate markers.
    begin_list = BEGIN_PATTERN.findall(text)
    end_list = END_PATTERN.findall(text)
    for marker in set(begin_list):
        if begin_list.count(marker) > 1:
            errors.append(f"{rel_path}: duplicate <!-- {marker}:begin --> found ({begin_list.count(marker)} occurrences)")
    for marker in set(end_list):
        if end_list.count(marker) > 1:
            errors.append(f"{rel_path}: duplicate <!-- {marker}:end --> found ({end_list.count(marker)} occurrences)")

    # Check for orphaned markers (begin without end or vice versa) across all found markers.
    all_markers = found_begins | found_ends
    for marker in all_markers:
        if marker in found_begins and marker not in found_ends:
            errors.append(f"{rel_path}: <!-- {marker}:begin --> has no matching end marker")
        if marker in found_ends and marker not in found_begins:
            errors.append(f"{rel_path}: <!-- {marker}:end --> has no matching begin marker")

    return errors


def main() -> int:
    errors: list[str] = []
    checked: dict[str, list[str]] = {}

    for rel_path, markers in REQUIRED_BLOCKS.items():
        file_errors = validate_file(rel_path, markers)
        errors.extend(file_errors)
        checked[rel_path] = markers

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {"status": "ok", "checked_files": checked},
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
