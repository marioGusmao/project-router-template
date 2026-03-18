#!/usr/bin/env python3
"""Validate Knowledge directory structure and ownership classification."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "Knowledge"
MANIFEST_PATH = ROOT / "repo-governance" / "ownership.manifest.json"

TEMPLATE_REQUIRED_FILES = [
    "Knowledge/README.md",
    "Knowledge/TLDR.md",
    "Knowledge/ContextPack.md",
    "Knowledge/CustomizationContract.md",
    "Knowledge/Glossary.md",
    "Knowledge/PipelineMap.md",
    "Knowledge/Roadmap.md",
    "Knowledge/ScriptsReference.md",
    "Knowledge/UpgradeGuide.md",
    "Knowledge/ADR/TEMPLATE.md",
    "Knowledge/ADR/000-use-adr-for-decisions.md",
    "Knowledge/ADR/001-stdlib-only.md",
    "Knowledge/ADR/002-template-private-split.md",
    "Knowledge/ADR/003-knowledge-foundation.md",
    "Knowledge/ADR/004-fail-closed-dispatch.md",
    "Knowledge/ADR/005-safety-invariants.md",
    "Knowledge/ADR/006-template-upgrade-process.md",
    "Knowledge/ADR/007-optional-extractor-deps.md",
    "Knowledge/Templates/local/README.md",
    "Knowledge/Templates/local/Roadmap.md",
    "Knowledge/Templates/local/ADR/README.md",
    "Knowledge/Templates/local/notes/README.md",
    "Knowledge/Templates/local/TLDR/README.md",
    "Knowledge/Templates/local/AI/README.md",
    "Knowledge/Templates/local/AI/claude.md",
    "Knowledge/Templates/local/AI/codex.md",
]

EXPECTED_SYNCED = {
    "Knowledge/README.md",
    "Knowledge/TLDR.md",
    "Knowledge/ContextPack.md",
    "Knowledge/CustomizationContract.md",
    "Knowledge/Glossary.md",
    "Knowledge/PipelineMap.md",
    "Knowledge/Roadmap.md",
    "Knowledge/ScriptsReference.md",
    "Knowledge/UpgradeGuide.md",
    "Knowledge/ADR/TEMPLATE.md",
    "Knowledge/ADR/000-use-adr-for-decisions.md",
    "Knowledge/ADR/001-stdlib-only.md",
    "Knowledge/ADR/002-template-private-split.md",
    "Knowledge/ADR/003-knowledge-foundation.md",
    "Knowledge/ADR/004-fail-closed-dispatch.md",
    "Knowledge/ADR/005-safety-invariants.md",
    "Knowledge/ADR/006-template-upgrade-process.md",
    "Knowledge/ADR/007-optional-extractor-deps.md",
    "Knowledge/Templates/local/README.md",
    "Knowledge/Templates/local/Roadmap.md",
    "Knowledge/Templates/local/ADR/README.md",
    "Knowledge/Templates/local/notes/README.md",
    "Knowledge/Templates/local/TLDR/README.md",
    "Knowledge/Templates/local/AI/README.md",
    "Knowledge/Templates/local/AI/claude.md",
    "Knowledge/Templates/local/AI/codex.md",
}

DERIVED_REQUIRED_FILES = [
    "Knowledge/local/README.md",
    "Knowledge/local/Roadmap.md",
    "Knowledge/local/ADR/README.md",
    "Knowledge/local/TLDR/README.md",
    "Knowledge/local/notes/README.md",
    "Knowledge/local/AI/README.md",
    "Knowledge/local/AI/claude.md",
    "Knowledge/local/AI/codex.md",
]

DERIVED_METADATA_FILES = [
    "private.meta.json",
    "template-base.json",
]

PRIVATE_MODE_MARKERS = {
    "README.md": "private operational Project Router repo",
    "AGENTS.md": "Current mode: private derived repository.",
    "CLAUDE.md": "Current role: private derived repository.",
}

ADR_ID_RE = re.compile(r"^(\d{3})-.*\.md$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Treat unexpected synced files as errors.")
    return parser.parse_args()


def collect_knowledge_files() -> list[str]:
    """Return all files under Knowledge/ as repo-relative POSIX paths, excluding local/."""
    results: list[str] = []
    if not KNOWLEDGE.is_dir():
        return results
    for p in sorted(KNOWLEDGE.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT).as_posix()
        parts = p.relative_to(KNOWLEDGE).parts
        if parts and parts[0] in ("local", "runbooks"):
            continue
        results.append(rel)
    return results


def classify_path(path: str, rules: list[dict[str, str]]) -> dict[str, str] | None:
    normalized = path[2:] if path.startswith("./") else path
    normalized = normalized.rstrip("/")
    for rule in rules:
        pattern = str(rule["pattern"]).rstrip("/")
        if fnmatch.fnmatch(normalized, pattern):
            return rule
        if pattern.endswith("/**") and normalized == pattern[:-3].rstrip("/"):
            return rule
    return None


def repo_declares_private_derived() -> bool:
    for rel, marker in PRIVATE_MODE_MARKERS.items():
        path = ROOT / rel
        if path.exists() and marker in path.read_text(encoding="utf-8"):
            return True
    return False


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Required files
    for rel in TEMPLATE_REQUIRED_FILES:
        if not (ROOT / rel).exists():
            errors.append(f"Required file missing: {rel}")

    # 2. Unexpected synced files
    unexpected_count = 0
    for rel in collect_knowledge_files():
        if rel not in EXPECTED_SYNCED:
            unexpected_count += 1
            msg = f"Unexpected file in synced Knowledge path: {rel}"
            if args.strict:
                errors.append(msg)
            else:
                warnings.append(msg)

    # 3. ADR numbering fence (IDs must be 000-099)
    adr_dir = KNOWLEDGE / "ADR"
    adr_count = 0
    if adr_dir.is_dir():
        for entry in sorted(adr_dir.iterdir()):
            m = ADR_ID_RE.match(entry.name)
            if m:
                adr_count += 1
                adr_id = int(m.group(1))
                if adr_id >= 100:
                    errors.append(f"ADR ID out of range (>=100): {entry.name}")

    # 4. Private-derived metadata + local scaffold
    if (ROOT / "private.meta.json").exists() or repo_declares_private_derived():
        for rel in DERIVED_METADATA_FILES:
            if not (ROOT / rel).exists():
                errors.append(f"Private-derived metadata missing: {rel}")
        for rel in DERIVED_REQUIRED_FILES:
            if not (ROOT / rel).exists():
                errors.append(f"Local scaffold missing: {rel}")

    # 5. Ownership classification safety test
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        rules = manifest.get("rules") or []
        test_path = "Knowledge/local/README.md"
        rule = classify_path(test_path, rules)
        if rule is None or rule.get("ownership") != "private_owned":
            actual = rule.get("ownership") if rule else "unclassified"
            errors.append(
                f"Ownership safety: {test_path} should be private_owned, got {actual}"
            )
        seed_path = "Knowledge/Templates/local/README.md"
        seed_rule = classify_path(seed_path, rules)
        if seed_rule is None or seed_rule.get("ownership") != "template_owned":
            actual = seed_rule.get("ownership") if seed_rule else "unclassified"
            errors.append(
                f"Ownership safety: {seed_path} should be template_owned, got {actual}"
            )

    # Report
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    payload = {
        "status": "ok",
        "required_present": len(TEMPLATE_REQUIRED_FILES),
        "unexpected_synced": unexpected_count,
        "adr_count": adr_count,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
