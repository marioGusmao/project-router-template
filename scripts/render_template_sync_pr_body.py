#!/usr/bin/env python3
"""Render a template-sync PR body, optionally including diff-only review content."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-tag", required=True, help="Upstream release tag (for example v0.2.0).")
    parser.add_argument("--release-url", required=True, help="Upstream release URL.")
    parser.add_argument("--diff-file", required=True, type=Path, help="Path to the diff-only output file.")
    parser.add_argument("--output", required=True, type=Path, help="Path to the markdown body file to write.")
    return parser.parse_args(argv)


def render_body(*, release_tag: str, release_url: str, diff_text: str) -> str:
    body = f"Template upstream update from [{release_tag}]({release_url}).\n"
    if diff_text.strip():
        body += (
            "\n## Diff-only review\n\n"
            "The following shared-review paths were not overwritten and require manual review:\n\n"
            "```diff\n"
            f"{diff_text.rstrip()}\n"
            "```\n"
        )
    return body


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    diff_text = ""
    if args.diff_file.exists():
        diff_text = args.diff_file.read_text(encoding="utf-8")
    body = render_body(
        release_tag=args.release_tag,
        release_url=args.release_url,
        diff_text=diff_text,
    )
    args.output.write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
