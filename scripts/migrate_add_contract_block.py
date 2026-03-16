#!/usr/bin/env python3
"""Insert customization-contract managed blocks into CLAUDE.md and AGENTS.md when missing.

Idempotent: re-runs are no-ops if blocks already exist. Designed for old derived
repos that were promoted before the customization-contract marker was introduced.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKER_NAME = "customization-contract"

CLAUDE_BLOCK = """\
<!-- customization-contract:begin -->
## Private AI Rules

Tracked AI surfaces (this file, AGENTS.md, skills) are upstream shared_review base.
Private operating rules live in Knowledge/local/AI/:

@Knowledge/local/AI/README.md
@Knowledge/local/AI/claude.md

Do not store private rules directly in this file — they will be overwritten during template sync.
<!-- customization-contract:end -->"""

AGENTS_BLOCK = """\
<!-- customization-contract:begin -->
## Private AI Rules

Tracked AI surfaces are upstream shared_review base.
If Knowledge/local/AI/README.md exists, read it first for private cross-agent rules.
If Knowledge/local/AI/codex.md exists, read it next for Codex-specific additions.
Do not store private rules directly in this file.
<!-- customization-contract:end -->"""


def has_marker(text: str) -> bool:
    start = f"<!-- {MARKER_NAME}:begin -->"
    end = f"<!-- {MARKER_NAME}:end -->"
    return start in text and end in text


def insert_block(path: Path, block: str) -> bool:
    """Append the managed block at the end of the file. Returns True if inserted."""
    if not path.exists():
        print(f"SKIP: {path.name} does not exist.", file=sys.stderr)
        return False

    text = path.read_text(encoding="utf-8")
    if has_marker(text):
        return False

    updated = text.rstrip() + "\n\n" + block + "\n"
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    inserted: list[str] = []

    claude_path = ROOT / "CLAUDE.md"
    agents_path = ROOT / "AGENTS.md"

    if insert_block(claude_path, CLAUDE_BLOCK):
        inserted.append("CLAUDE.md")
    if insert_block(agents_path, AGENTS_BLOCK):
        inserted.append("AGENTS.md")

    if inserted:
        print(f"Inserted customization-contract block into: {', '.join(inserted)}")
    else:
        print("All customization-contract blocks already present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
