#!/usr/bin/env python3
"""Sync managed blocks from upstream into local files, preserving content outside the blocks.

Used by the template-upstream-sync workflow for files that use the managed_blocks
customization model (README.md, README.pt-PT.md). Content inside matching
begin/end markers is replaced with the upstream version; content outside the
markers belongs to the derived repo and is preserved.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def replace_block(local_text: str, upstream_text: str, marker_name: str) -> str | None:
    """Replace the content of a managed block in local_text with the upstream version.

    Returns the updated text, or None if the marker is missing from either file.
    """
    start = f"<!-- {marker_name}:begin -->"
    end = f"<!-- {marker_name}:end -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)

    upstream_match = pattern.search(upstream_text)
    if not upstream_match:
        return None

    local_match = pattern.search(local_text)
    if not local_match:
        return None

    return pattern.sub(upstream_match.group(0), local_text, count=1)


def sync_managed_blocks(
    upstream_path: Path,
    local_path: Path,
    marker_names: list[str],
) -> bool:
    """Replace managed blocks in local_path with upstream versions.

    Returns True if any changes were made.
    """
    if not upstream_path.exists():
        print(f"SKIP: upstream {upstream_path} does not exist.", file=sys.stderr)
        return False
    if not local_path.exists():
        print(f"SKIP: local {local_path} does not exist.", file=sys.stderr)
        return False

    local_text = local_path.read_text(encoding="utf-8")
    upstream_text = upstream_path.read_text(encoding="utf-8")
    result = local_text

    for marker in marker_names:
        updated = replace_block(result, upstream_text, marker)
        if updated is not None:
            result = updated
        else:
            print(f"WARNING: marker {marker!r} missing from {upstream_path.name} or {local_path.name}.", file=sys.stderr)

    if result == local_text:
        return False

    local_path.write_text(result, encoding="utf-8")
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream-dir", required=True, type=Path, help="Path to the upstream template checkout.")
    parser.add_argument("--local-dir", required=True, type=Path, help="Path to the local repository root.")
    parser.add_argument(
        "--files",
        default="README.md,README.pt-PT.md",
        help="Comma-separated list of files to sync (default: README.md,README.pt-PT.md).",
    )
    parser.add_argument(
        "--markers",
        default="repository-mode,template-onboarding",
        help="Comma-separated list of managed block marker names (default: repository-mode,template-onboarding).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    files = [f.strip() for f in args.files.split(",") if f.strip()]
    markers = [m.strip() for m in args.markers.split(",") if m.strip()]
    changed: list[str] = []

    for filename in files:
        upstream = args.upstream_dir / filename
        local = args.local_dir / filename
        if sync_managed_blocks(upstream, local, markers):
            changed.append(filename)

    if changed:
        print(f"Updated managed blocks in: {', '.join(changed)}")
    else:
        print("No managed block changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
