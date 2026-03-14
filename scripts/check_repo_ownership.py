#!/usr/bin/env python3
"""Validate repository ownership rules and template-sync path safety."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "repo-governance" / "ownership.manifest.json"
REQUIRED_CLASSES = {"template_owned", "private_owned", "shared_review", "local_only"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["validate", "template-sync"], default="validate")
    parser.add_argument("--path", action="append", default=[], help="Path to classify relative to the repository root.")
    return parser.parse_args()


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def classify_path(path: str, rules: list[dict[str, str]]) -> dict[str, str] | None:
    normalized = path[2:] if path.startswith("./") else path
    normalized = normalized.rstrip("/")
    for rule in rules:
        pattern = str(rule["pattern"]).rstrip("/")
        if fnmatch.fnmatch(normalized, pattern):
            return rule
    return None


def visible_repo_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted({line.strip() for line in result.stdout.splitlines() if line.strip()})


def main() -> int:
    args = parse_args()
    manifest = load_manifest()
    errors: list[str] = []

    classes = set((manifest.get("classes") or {}).keys())
    missing_classes = REQUIRED_CLASSES - classes
    if missing_classes:
        errors.append(f"Ownership manifest is missing classes: {', '.join(sorted(missing_classes))}")

    rules = manifest.get("rules") or []
    if not rules:
        errors.append("Ownership manifest must define at least one rule.")

    for rule in rules:
        ownership = rule.get("ownership")
        if ownership not in REQUIRED_CLASSES:
            errors.append(f"Unknown ownership class in rule {rule!r}")

    required_paths = [
        "src/project_router/cli.py",
        "scripts/project_router_client.py",
        "README.md",
        "AGENTS.md",
        "CLAUDE.md",
        ".agents/skills/project-router-triage-review/SKILL.md",
        ".codex/skills/project-router-triage-review/SKILL.md",
        ".claude/skills/project-router-triage-review/SKILL.md",
        "projects/registry.shared.json",
        "projects/registry.example.json",
        "project-router/router-contract.json",
        "project-router/conformance/valid-packet.example.md",
        ".env.local",
        "data/raw/voicenotes",
        "data/raw/project_router",
        "state/project_router/outbox_scan_state.json",
        "Knowledge/TLDR.md",
        "Knowledge/ContextPack.md",
        "Knowledge/Glossary.md",
        "Knowledge/PipelineMap.md",
        "Knowledge/ScriptsReference.md",
        "Knowledge/Roadmap.md",
        "Knowledge/README.md",
        "Knowledge/ADR/TEMPLATE.md",
        "Knowledge/ADR/000-use-adr-for-decisions.md",
        "Knowledge/local/README.md",
    ]
    for path in required_paths:
        if classify_path(path, rules) is None:
            errors.append(f"Ownership manifest does not classify required path: {path}")

    for path in visible_repo_files():
        if classify_path(path, rules) is None:
            errors.append(f"Ownership manifest does not classify repository file: {path}")

    if args.mode == "template-sync":
        blocked_classes = {"private_owned", "local_only"}
        for path in args.path:
            rule = classify_path(path, rules)
            if rule is None:
                errors.append(f"Unclassified path in template-sync mode: {path}")
                continue
            if rule["ownership"] in blocked_classes:
                errors.append(
                    f"Template sync must not touch {path} ({rule['ownership']}, policy={rule.get('sync_policy', 'n/a')})"
                )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if args.mode == "template-sync":
        payload = {path: classify_path(path, rules) for path in args.path}
    else:
        payload = {
            "status": "ok",
            "classified_examples": {
                path: classify_path(path, rules) for path in required_paths
            },
        }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
