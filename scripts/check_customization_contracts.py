#!/usr/bin/env python3
"""Validate the customization contract registry against repo state and changed paths.

Checks:
1. Registry ↔ ownership manifest consistency (ownership + sync_policy)
2. Agent load rules: @import present in CLAUDE.md, prose present in AGENTS.md
3. Bootstrap sources exist in Knowledge/Templates
4. Private overlay paths are not in syncable directories
5. Contract block markers exist where required
6. No reject files or unresolved git conflict markers exist
7. Changed paths touching requires_release_note surfaces also touch CHANGELOG.md
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

from check_repo_ownership import classify_path, load_manifest


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_PATH = ROOT / "repo-governance" / "customization-contracts.json"

VALID_OWNERSHIPS = {"template_owned", "private_owned", "shared_review", "local_only"}
VALID_SYNC_POLICIES = {"template_sync", "review_required", "blocked"}
VALID_CUSTOMIZATION_MODELS = {
    "overwrite",
    "full_overwrite_preserve_contract",
    "managed_blocks",
    "extensible_directory",
    "diff_only",
    "skip",
}
VALID_AGENT_LOAD_RULES = {"@import", "prose", None}
VALID_MIGRATION_POLICIES = {"silent_ok", "review_required", "requires_release_note"}

CONTRACT_MARKER = "customization-contract"
CONFLICT_START_RE = re.compile(r"^<<<<<<< ", re.MULTILINE)
CONFLICT_END_RE = re.compile(r"^>>>>>>> ", re.MULTILINE)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--changed-path",
        action="append",
        default=[],
        help="Repository-relative changed path. Repeat for multiple paths.",
    )
    parser.add_argument(
        "--changed-path-file",
        type=Path,
        help="Optional file containing newline-delimited repository-relative changed paths.",
    )
    return parser.parse_args(argv)


def load_contracts() -> dict:
    return json.loads(CONTRACTS_PATH.read_text(encoding="utf-8"))


def normalize_path(path: str) -> str:
    normalized = path[2:] if path.startswith("./") else path
    return normalized.rstrip("/")


def classify_contract_path(path: str, surfaces: list[dict]) -> dict | None:
    normalized = normalize_path(path)
    for surface in surfaces:
        pattern = str(surface["pattern"]).rstrip("/")
        if fnmatch.fnmatch(normalized, pattern):
            return surface
        if pattern.endswith("/**") and normalized == pattern[:-3].rstrip("/"):
            return surface
    return None


def visible_repo_files() -> list[str]:
    try:
        repo_root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        if Path(repo_root).resolve() != ROOT.resolve():
            raise subprocess.CalledProcessError(returncode=1, cmd=["git", "rev-parse", "--show-toplevel"])
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return sorted({line.strip() for line in result.stdout.splitlines() if line.strip()})
    except (FileNotFoundError, subprocess.CalledProcessError):
        results: list[str] = []
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts:
                continue
            results.append(path.relative_to(ROOT).as_posix())
        return sorted(set(results))


def read_changed_paths(args: argparse.Namespace) -> list[str]:
    changed = {normalize_path(path) for path in args.changed_path if path and path.strip()}
    if args.changed_path_file:
        for raw_line in args.changed_path_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line:
                changed.add(normalize_path(line))
    return sorted(changed)


def check_schema(surfaces: list[dict]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "pattern",
        "ownership",
        "sync_policy",
        "customization_model",
        "private_overlay",
        "bootstrap_source",
        "agent_load_rule",
        "migration_policy",
        "validator_hooks",
    }
    for surface in surfaces:
        pattern = surface.get("pattern", "<missing>")
        missing = required_fields - set(surface.keys())
        if missing:
            errors.append(f"{pattern}: missing fields: {', '.join(sorted(missing))}")
        if surface.get("ownership") not in VALID_OWNERSHIPS:
            errors.append(f"{pattern}: invalid ownership: {surface.get('ownership')}")
        if surface.get("sync_policy") not in VALID_SYNC_POLICIES:
            errors.append(f"{pattern}: invalid sync_policy: {surface.get('sync_policy')}")
        if surface.get("customization_model") not in VALID_CUSTOMIZATION_MODELS:
            errors.append(f"{pattern}: invalid customization_model: {surface.get('customization_model')}")
        if surface.get("agent_load_rule") not in VALID_AGENT_LOAD_RULES:
            errors.append(f"{pattern}: invalid agent_load_rule: {surface.get('agent_load_rule')}")
        if surface.get("migration_policy") not in VALID_MIGRATION_POLICIES:
            errors.append(f"{pattern}: invalid migration_policy: {surface.get('migration_policy')}")
    return errors


def check_manifest_consistency(surfaces: list[dict], manifest_rules: list[dict]) -> list[str]:
    errors: list[str] = []
    for surface in surfaces:
        pattern = surface["pattern"]
        test_path = pattern.removesuffix("/**").removesuffix("/*").rstrip("/")
        if not test_path:
            continue
        rule = classify_path(test_path, manifest_rules)
        if rule is None and "**" in pattern:
            rule = classify_path(pattern.replace("/**", "/PLACEHOLDER.md"), manifest_rules)
        if rule is None:
            errors.append(f"{pattern}: not classified in ownership manifest")
            continue
        if rule["ownership"] != surface["ownership"]:
            errors.append(
                f"{pattern}: ownership mismatch — registry={surface['ownership']}, "
                f"manifest={rule['ownership']}"
            )
        manifest_sync = rule.get("sync_policy", "")
        if manifest_sync != surface["sync_policy"]:
            errors.append(
                f"{pattern}: sync_policy mismatch — registry={surface['sync_policy']}, "
                f"manifest={manifest_sync}"
            )
    return errors


def check_agent_load_rules(surfaces: list[dict]) -> list[str]:
    errors: list[str] = []
    for surface in surfaces:
        load_rule = surface.get("agent_load_rule")
        overlay = surface.get("private_overlay")
        if not load_rule or not overlay:
            continue
        path = ROOT / surface["pattern"]
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if load_rule == "@import":
            if f"@{overlay}" not in text:
                errors.append(f"{surface['pattern']}: missing @import reference to {overlay}")
        elif load_rule == "prose":
            overlay_stem = Path(overlay).name
            if overlay_stem not in text:
                errors.append(f"{surface['pattern']}: missing prose reference to {overlay_stem}")
    return errors


def check_bootstrap_sources(surfaces: list[dict]) -> list[str]:
    errors: list[str] = []
    for surface in surfaces:
        source = surface.get("bootstrap_source")
        if not source:
            continue
        source_path = ROOT / source
        if not source_path.exists():
            errors.append(f"{surface['pattern']}: bootstrap_source {source} does not exist")
    return errors


def check_overlay_not_syncable(surfaces: list[dict], manifest_rules: list[dict]) -> list[str]:
    errors: list[str] = []
    syncable_policies = {"template_sync", "review_required"}
    for surface in surfaces:
        overlay = surface.get("private_overlay")
        if not overlay:
            continue
        rule = classify_path(overlay, manifest_rules)
        if rule and rule.get("sync_policy") in syncable_policies:
            errors.append(
                f"{surface['pattern']}: private_overlay {overlay} is in a syncable path "
                f"(ownership={rule['ownership']}, sync_policy={rule['sync_policy']})"
            )
    return errors


def check_contract_markers(surfaces: list[dict]) -> list[str]:
    errors: list[str] = []
    for surface in surfaces:
        if surface.get("customization_model") != "full_overwrite_preserve_contract":
            continue
        path = ROOT / surface["pattern"]
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        start = f"<!-- {CONTRACT_MARKER}:begin -->"
        end = f"<!-- {CONTRACT_MARKER}:end -->"
        if start not in text:
            errors.append(f"{surface['pattern']}: missing {start}")
        if end not in text:
            errors.append(f"{surface['pattern']}: missing {end}")
    return errors


def check_repo_artifacts(files: list[str]) -> list[str]:
    errors: list[str] = []
    for rel_path in files:
        if rel_path.endswith(".rej"):
            errors.append(f"{rel_path}: reject artifact must be resolved before merge")
            continue
        path = ROOT / rel_path
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if CONFLICT_START_RE.search(text) or CONFLICT_END_RE.search(text):
            errors.append(f"{rel_path}: contains unresolved git conflict markers")
    return errors


def check_release_note_requirements(changed_paths: list[str], surfaces: list[dict]) -> list[str]:
    if not changed_paths or "CHANGELOG.md" in changed_paths:
        return []
    requires_notes = sorted(
        {
            surface["pattern"]
            for path in changed_paths
            if (surface := classify_contract_path(path, surfaces))
            and surface.get("migration_policy") == "requires_release_note"
        }
    )
    if not requires_notes:
        return []
    return [
        "Changed paths require a CHANGELOG.md update: " + ", ".join(requires_notes)
    ]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not CONTRACTS_PATH.exists():
        print(f"ERROR: Contract registry not found: {CONTRACTS_PATH}", file=sys.stderr)
        return 1

    contracts = load_contracts()
    surfaces = contracts.get("surfaces", [])
    manifest = load_manifest()
    manifest_rules = manifest.get("rules", [])
    changed_paths = read_changed_paths(args)

    errors: list[str] = []
    errors.extend(check_schema(surfaces))
    errors.extend(check_manifest_consistency(surfaces, manifest_rules))
    errors.extend(check_agent_load_rules(surfaces))
    errors.extend(check_bootstrap_sources(surfaces))
    errors.extend(check_overlay_not_syncable(surfaces, manifest_rules))
    errors.extend(check_contract_markers(surfaces))
    errors.extend(check_repo_artifacts(visible_repo_files()))
    errors.extend(check_release_note_requirements(changed_paths, surfaces))

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "status": "ok",
                "surfaces_checked": len(surfaces),
                "schema_version": contracts.get("schema_version", "unknown"),
                "changed_paths_checked": len(changed_paths),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
