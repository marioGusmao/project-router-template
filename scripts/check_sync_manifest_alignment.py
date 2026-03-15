#!/usr/bin/env python3
"""Validate template-upstream-sync paths against the ownership manifest."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from check_repo_ownership import classify_path, load_manifest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "template-upstream-sync.yml"
ALLOWED_SYNC_POLICIES = {"template_sync", "review_required"}


SYNC_ARRAY_NAMES = {"paths", "overwrite_paths", "ai_files", "extensible_paths", "diff_paths"}


def extract_sync_paths(text: str) -> list[str]:
    """Extract all paths from known bash sync array assignments in the workflow.

    Recognises arrays named: paths, overwrite_paths, ai_files,
    extensible_paths, diff_paths. Collects their non-comment entries.
    """
    in_array = False
    paths: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        # Match e.g. "overwrite_paths=(" or "paths=("
        if not in_array:
            for name in SYNC_ARRAY_NAMES:
                if stripped == f"{name}=(" or stripped.startswith(f"{name}=("):
                    in_array = True
                    break
            continue
        if stripped == ")":
            in_array = False
            continue
        if not stripped or stripped.startswith("#"):
            continue
        paths.append(stripped)
    return list(dict.fromkeys(paths))  # deduplicate, preserve order


def main() -> int:
    if not WORKFLOW_PATH.exists():
        print(f"ERROR: Workflow file not found: {WORKFLOW_PATH}", file=sys.stderr)
        return 1
    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    sync_paths = extract_sync_paths(workflow_text)
    manifest = load_manifest()
    rules = manifest.get("rules") or []

    errors: list[str] = []
    classification: dict[str, dict[str, str] | None] = {}

    for path in sync_paths:
        rule = classify_path(path, rules)
        classification[path] = rule
        if rule is None:
            errors.append(f"Unclassified sync path: {path}")
            continue
        sync_policy = rule.get("sync_policy")
        if sync_policy not in ALLOWED_SYNC_POLICIES:
            errors.append(
                f"Blocked sync path {path}: ownership={rule.get('ownership', 'unknown')} sync_policy={sync_policy or 'missing'}"
            )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "status": "ok",
                "workflow": str(WORKFLOW_PATH.relative_to(ROOT)),
                "sync_paths": sync_paths,
                "classified": classification,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
