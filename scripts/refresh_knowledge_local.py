#!/usr/bin/env python3
"""Preview or refresh the Knowledge/local scaffold from Knowledge/Templates/local."""

from __future__ import annotations

import argparse
import json

from knowledge_local_scaffold import ROOT, compare_scaffold, materialize_scaffold


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply-missing",
        action="store_true",
        help="Create only missing scaffold files under Knowledge/local/.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite differing scaffold files from the template source.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    comparison = compare_scaffold(ROOT)

    payload: dict[str, object] = {
        "source_root": "Knowledge/Templates/local",
        "target_root": "Knowledge/local",
        "missing": sorted(item.rel_path for item in comparison if item.status == "missing"),
        "different": sorted(item.rel_path for item in comparison if item.status == "different"),
        "same": sorted(item.rel_path for item in comparison if item.status == "same"),
    }

    if args.apply_missing or args.overwrite:
        changes = materialize_scaffold(ROOT, overwrite=args.overwrite)
        payload.update(
            {
                "dry_run": False,
                "overwrite": args.overwrite,
                "created": changes["created"],
                "updated": changes["updated"],
                "skipped": changes["skipped"],
            }
        )
    else:
        payload["dry_run"] = True

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
