#!/usr/bin/env python3
"""Restore the local customization-contract block into AI files after upstream overwrite.

Used by the template-upstream-sync workflow. The workflow flow is:
  1. Pass 0.5 backs up CLAUDE.md/AGENTS.md to a temp directory
  2. Pass 1 overwrites them with upstream content via rsync
  3. Pass 2 (this script) reads the contract block from the backup
     and splices it into the now-upstream-overwritten local file

This ensures upstream changes (Safety Rules, Commands, etc.) arrive automatically
while the customization-contract block (containing @import or prose references
to private overlays) is preserved from the pre-overwrite backup.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


MARKER_NAME = "customization-contract"
START_MARKER = f"<!-- {MARKER_NAME}:begin -->"
END_MARKER = f"<!-- {MARKER_NAME}:end -->"
BLOCK_PATTERN = re.compile(
    re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
    re.DOTALL,
)


def extract_contract_block(text: str) -> str | None:
    """Extract the customization-contract block from text, or None if absent."""
    match = BLOCK_PATTERN.search(text)
    return match.group(0) if match else None


def restore_contract_block(backup_path: Path, local_path: Path) -> bool:
    """Restore the customization-contract block from backup into the local file.

    The local file has already been overwritten with upstream content by rsync.
    The backup contains the pre-overwrite local file with the private contract block.

    Returns True if any changes were made.
    """
    if not backup_path.exists():
        print(f"SKIP: backup {backup_path} does not exist.", file=sys.stderr)
        return False
    if not local_path.exists():
        print(f"SKIP: local {local_path} does not exist.", file=sys.stderr)
        return False

    backup_text = backup_path.read_text(encoding="utf-8")
    local_text = local_path.read_text(encoding="utf-8")

    # Extract the private contract block from the pre-overwrite backup.
    private_block = extract_contract_block(backup_text)
    if not private_block:
        # No private contract block in the backup — nothing to restore.
        return False

    # Check if the now-upstream local file has a contract block placeholder.
    upstream_block = extract_contract_block(local_text)

    if upstream_block:
        # Replace upstream's contract block with the private one.
        result = BLOCK_PATTERN.sub(lambda _: private_block, local_text, count=1)
    else:
        # Upstream lacks a contract block — append the private one.
        result = local_text.rstrip() + "\n\n" + private_block + "\n"

    if result == local_text:
        return False

    local_path.write_text(result, encoding="utf-8")
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup-dir", required=True, type=Path, help="Path to the pre-overwrite backup directory.")
    parser.add_argument("--local-dir", required=True, type=Path, help="Path to the local repository root.")
    parser.add_argument(
        "--files",
        default="CLAUDE.md,AGENTS.md",
        help="Comma-separated list of AI files to restore (default: CLAUDE.md,AGENTS.md).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    files = [f.strip() for f in args.files.split(",") if f.strip()]
    changed: list[str] = []

    for filename in files:
        backup = args.backup_dir / filename
        local = args.local_dir / filename
        if restore_contract_block(backup, local):
            changed.append(filename)

    if changed:
        print(f"Restored contract blocks from backup: {', '.join(changed)}")
    else:
        print("No contract block changes needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
