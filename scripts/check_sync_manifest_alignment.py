#!/usr/bin/env python3
"""Validate template-upstream-sync paths against the manifest and contract registry."""

from __future__ import annotations

import fnmatch
import json
import sys
from pathlib import Path

from check_repo_ownership import classify_path, load_manifest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "template-upstream-sync.yml"
CONTRACTS_PATH = ROOT / "repo-governance" / "customization-contracts.json"
ALLOWED_SYNC_POLICIES = {"template_sync", "review_required"}


SYNC_ARRAY_NAMES = {"paths", "overwrite_paths", "ai_files", "extensible_paths", "diff_paths"}


def load_contracts() -> dict:
    return json.loads(CONTRACTS_PATH.read_text(encoding="utf-8"))


def classify_contract_path(path: str, surfaces: list[dict]) -> dict | None:
    normalized = path[2:] if path.startswith("./") else path
    normalized = normalized.rstrip("/")
    for surface in surfaces:
        pattern = str(surface["pattern"]).rstrip("/")
        if fnmatch.fnmatch(normalized, pattern):
            return surface
        if pattern.endswith("/**") and normalized == pattern[:-3].rstrip("/"):
            return surface
    return None


def extract_sync_paths(text: str) -> list[str]:
    """Extract all paths from known bash sync array assignments in the workflow."""
    in_array = False
    paths: list[str] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
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
    return list(dict.fromkeys(paths))


def main() -> int:
    if not WORKFLOW_PATH.exists():
        print(f"ERROR: Workflow file not found: {WORKFLOW_PATH}", file=sys.stderr)
        return 1
    if not CONTRACTS_PATH.exists():
        print(f"ERROR: Contract registry not found: {CONTRACTS_PATH}", file=sys.stderr)
        return 1

    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    sync_paths = extract_sync_paths(workflow_text)
    manifest = load_manifest()
    manifest_rules = manifest.get("rules") or []
    surfaces = load_contracts().get("surfaces", [])

    errors: list[str] = []
    manifest_classified: dict[str, dict[str, str] | None] = {}
    contract_classified: dict[str, dict | None] = {}

    for path in sync_paths:
        manifest_rule = classify_path(path, manifest_rules)
        contract_rule = classify_contract_path(path, surfaces)
        manifest_classified[path] = manifest_rule
        contract_classified[path] = contract_rule

        if manifest_rule is None:
            errors.append(f"Unclassified sync path in ownership manifest: {path}")
        elif manifest_rule.get("sync_policy") not in ALLOWED_SYNC_POLICIES:
            errors.append(
                f"Blocked sync path {path}: ownership={manifest_rule.get('ownership', 'unknown')} "
                f"sync_policy={manifest_rule.get('sync_policy') or 'missing'}"
            )

        if contract_rule is None:
            errors.append(f"Sync path missing from customization contract registry: {path}")
            continue

        if contract_rule.get("sync_policy") not in ALLOWED_SYNC_POLICIES:
            errors.append(
                f"Blocked sync path in customization contract registry: {path} "
                f"(ownership={contract_rule.get('ownership', 'unknown')}, "
                f"sync_policy={contract_rule.get('sync_policy') or 'missing'})"
            )

        if manifest_rule is None:
            continue
        if manifest_rule.get("ownership") != contract_rule.get("ownership"):
            errors.append(
                f"Ownership mismatch for {path}: manifest={manifest_rule.get('ownership')} "
                f"registry={contract_rule.get('ownership')}"
            )
        if manifest_rule.get("sync_policy") != contract_rule.get("sync_policy"):
            errors.append(
                f"sync_policy mismatch for {path}: manifest={manifest_rule.get('sync_policy')} "
                f"registry={contract_rule.get('sync_policy')}"
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
                "manifest_classified": manifest_classified,
                "contract_classified": contract_classified,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
