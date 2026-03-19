#!/usr/bin/env python3
"""Readwise Reader sync client — CLI entry point."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from project_router.readwise_client import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
