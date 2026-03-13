#!/usr/bin/env python3
"""Validate shared agent surface parity for the Project Router starter."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "parity.manifest.json"
REGISTRY_SHARED_PATH = ROOT / "projects" / "registry.shared.json"
SURFACE_SCAN_FILES = [
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "CLAUDE.md",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pre-publish", action="store_true", help="Run extra checks for template publication hygiene.")
    return parser.parse_args()


def load_manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line.strip()]


def report_failure(errors: list[str]) -> int:
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1


def main() -> int:
    manifest = load_manifest()
    errors: list[str] = []

    required_skills = [str(item) for item in manifest.get("required_skills", [])]
    surface_files = {key: [ROOT / entry for entry in value] for key, value in manifest.get("surface_files", {}).items()}
    required_commands = [str(item) for item in manifest.get("required_commands", [])]
    required_phrases = [str(item) for item in manifest.get("required_phrases", [])]
    forbidden_path_fragments = [str(item) for item in manifest.get("forbidden_path_fragments", [])]

    agent_skill_dir = ROOT / ".agents" / "skills"
    codex_skill_dir = ROOT / ".codex" / "skills"
    claude_skill_dir = ROOT / ".claude" / "skills"
    for skill_id in required_skills:
        agent_path = agent_skill_dir / skill_id / "SKILL.md"
        codex_path = codex_skill_dir / skill_id / "SKILL.md"
        claude_path = claude_skill_dir / skill_id / "SKILL.md"
        if not agent_path.exists():
            errors.append(f"Missing reference agent skill surface: {agent_path.relative_to(ROOT)}")
        if not codex_path.exists():
            errors.append(f"Missing Codex skill surface: {codex_path.relative_to(ROOT)}")
        if not claude_path.exists():
            errors.append(f"Missing Claude skill surface: {claude_path.relative_to(ROOT)}")

    for surface_name, files in surface_files.items():
        for path in files:
            if not path.exists():
                errors.append(f"Missing {surface_name} surface file: {path.relative_to(ROOT)}")

    corpora: dict[str, str] = {}
    for surface_name, files in surface_files.items():
        texts: list[str] = []
        for path in files:
            if path.exists():
                texts.append(read_text(path))
        corpora[surface_name] = "\n".join(texts)

    for surface_name, corpus in corpora.items():
        for phrase in required_phrases:
            if phrase not in corpus:
                errors.append(f"{surface_name} surface missing required phrase: {phrase}")
        for command in required_commands:
            if command not in corpus:
                errors.append(f"{surface_name} surface missing required command: {command}")

    docs_corpus = "\n".join(read_text(path) for path in SURFACE_SCAN_FILES if path.exists())
    docs_corpus += "\n" + "\n".join(corpora.values())
    for fragment in forbidden_path_fragments:
        if fragment in docs_corpus:
            errors.append(f"Forbidden internal client path reference found: {fragment}")

    if args := parse_args():
        if args.pre_publish:
            if REGISTRY_SHARED_PATH.exists():
                registry = json.loads(REGISTRY_SHARED_PATH.read_text(encoding="utf-8"))
                for project_key, raw in (registry.get("projects") or {}).items():
                    if "inbox_path" in raw:
                        errors.append(f"Shared registry project '{project_key}' must not define inbox_path.")
                    if "router_root_path" in raw:
                        errors.append(f"Shared registry project '{project_key}' must not define router_root_path.")

            secret_patterns = [
                re.compile(r"VOICENOTES_API_KEY\s*=\s*(?!replace-with-your-voicenotes-token)"),
                re.compile(r"sk-[A-Za-z0-9]{20,}"),
                re.compile(r"ghp_[A-Za-z0-9]{20,}"),
            ]
            for path in tracked_files():
                if not path.exists() or path.is_dir():
                    continue
                text = read_text(path)
                for pattern in secret_patterns:
                    if pattern.search(text):
                        errors.append(f"Tracked file appears to contain a secret-like value: {path.relative_to(ROOT)}")
                        break

    if errors:
        return report_failure(errors)

    print(
        json.dumps(
            {
                "status": "ok",
                "required_skills": required_skills,
                "checked_surfaces": sorted(surface_files.keys()),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
