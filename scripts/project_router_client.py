#!/usr/bin/env python3
"""Repository-neutral entrypoint for the Project Router sync client for VoiceNotes."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.project_router.sync_client import main as sync_main


def main() -> int:
    return sync_main()


if __name__ == "__main__":
    sys.exit(main())
