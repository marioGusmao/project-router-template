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

REQUIRED_FILES = [
    "Knowledge/TLDR.md",
    "Knowledge/ContextPack.md",
    "Knowledge/Glossary.md",
    "Knowledge/PipelineMap.md",
    "Knowledge/Roadmap.md",
    "Knowledge/ScriptsReference.md",
    "Knowledge/README.md",
    "Knowledge/ADR/TEMPLATE.md",
    "Knowledge/ADR/000-use-adr-for-decisions.md",
]

EXPECTED_SYNCED = {
    "Knowledge/README.md",
    "Knowledge/TLDR.md",
    "Knowledge/ContextPack.md",
    "Knowledge/Glossary.md",
    "Knowledge/PipelineMap.md",
    "Knowledge/Roadmap.md",
    "Knowledge/ScriptsReference.md",
    "Knowledge/ADR/TEMPLATE.md",
    "Knowledge/ADR/000-use-adr-for-decisions.md",
    "Knowledge/ADR/001-stdlib-only.md",
    "Knowledge/ADR/002-template-private-split.md",
    "Knowledge/ADR/003-knowledge-foundation.md",
    "Knowledge/ADR/004-fail-closed-dispatch.md",
    "Knowledge/ADR/005-safety-invariants.md",
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
        if parts and parts[0] == "local":
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
    return None


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Required files
    for rel in REQUIRED_FILES:
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

    # 4. Local scaffold (only when private.meta.json exists)
    if (ROOT / "private.meta.json").exists():
        local_required = [
            KNOWLEDGE / "local" / "README.md",
            KNOWLEDGE / "local" / "ADR",
            KNOWLEDGE / "local" / "Roadmap.md",
        ]
        for p in local_required:
            if not p.exists():
                errors.append(f"Local scaffold missing: {p.relative_to(ROOT).as_posix()}")

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

    # Report
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    payload = {
        "status": "ok",
        "required_present": len(REQUIRED_FILES),
        "unexpected_synced": unexpected_count,
        "adr_count": adr_count,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
