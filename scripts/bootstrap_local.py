#!/usr/bin/env python3
"""Bootstrap local-only Project Router configuration for VoiceNotes without touching committed files."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE_PATH = ROOT / ".env.example"
ENV_LOCAL_PATH = ROOT / ".env.local"
REGISTRY_SHARED_PATH = ROOT / "projects" / "registry.shared.json"
REGISTRY_LOCAL_PATH = ROOT / "projects" / "registry.local.json"
CLAUDE_SETTINGS_EXAMPLE = ROOT / ".claude" / "settings.example.json"
CLAUDE_SETTINGS_LOCAL = ROOT / ".claude" / "settings.local.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Rewrite local bootstrap files when they already exist.")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def env_var_name(project_key: str) -> str:
    normalized = "".join(char if char.isalnum() else "_" for char in project_key.upper())
    return f"VN_ROUTER_ROOT_{normalized}"


def ensure_env_local(force: bool) -> str:
    if ENV_LOCAL_PATH.exists() and not force:
        return "kept existing .env.local"
    if not ENV_EXAMPLE_PATH.exists():
        return "skipped .env.local creation (.env.example missing)"
    ENV_LOCAL_PATH.write_text(ENV_EXAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    return "wrote .env.local from .env.example"


def ensure_claude_settings(force: bool) -> str:
    if CLAUDE_SETTINGS_LOCAL.exists() and not force:
        return "kept existing .claude/settings.local.json"
    if not CLAUDE_SETTINGS_EXAMPLE.exists():
        return "skipped .claude/settings.local.json creation (settings.example.json missing)"
    CLAUDE_SETTINGS_LOCAL.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_SETTINGS_LOCAL.write_text(CLAUDE_SETTINGS_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    return "wrote .claude/settings.local.json from settings.example.json"


def prompt_for_path(project_key: str, existing_value: str | None) -> str | None:
    prompt = f"Absolute router root path for {project_key}"
    if existing_value:
        prompt += f" [{existing_value}]"
    prompt += " (leave blank to keep inactive): "
    response = input(prompt).strip()
    if not response:
        return existing_value
    return response


def build_registry_local(force: bool) -> tuple[dict[str, Any] | None, list[str], str]:
    if not REGISTRY_SHARED_PATH.exists():
        raise SystemExit(f"Missing shared registry at {REGISTRY_SHARED_PATH}.")

    existing_local = read_json(REGISTRY_LOCAL_PATH) if REGISTRY_LOCAL_PATH.exists() else {}
    if REGISTRY_LOCAL_PATH.exists() and not force:
        return None, [], "kept existing projects/registry.local.json"

    shared_config = read_json(REGISTRY_SHARED_PATH)
    project_keys = sorted((shared_config.get("projects") or {}).keys())
    known_env_vars = {env_var_name(key) for key in project_keys}
    warnings = [
        f"Ignoring unknown environment variable {key}."
        for key in sorted(os.environ)
        if key.startswith("VN_ROUTER_ROOT_") and key not in known_env_vars
    ]

    projects_payload: dict[str, dict[str, str]] = {}
    for key in project_keys:
        existing_project = ((existing_local.get("projects") or {}).get(key) or {})
        existing_value = str(existing_project.get("router_root_path") or existing_project.get("inbox_path") or "").strip() or None
        env_value = str(os.environ.get(env_var_name(key)) or "").strip() or None
        selected = existing_value if existing_value and not force else env_value
        if selected is None and os.isatty(0):
            selected = prompt_for_path(key, existing_value if force else None)
        # Normalize: if the value ends in /inbox, it's either a legacy inbox_path
        # or a previously-corrupted router_root_path. Strip to get the real root.
        if selected:
            candidate = Path(selected)
            if candidate.name == "inbox":
                selected = str(candidate.parent)
        if selected:
            projects_payload[key] = {"router_root_path": selected}

    REGISTRY_LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"projects": projects_payload}
    REGISTRY_LOCAL_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload, warnings, "wrote projects/registry.local.json"


def main() -> int:
    args = parse_args()
    env_status = ensure_env_local(force=args.force)
    claude_settings_status = ensure_claude_settings(force=args.force)
    registry_payload, warnings, registry_status = build_registry_local(force=args.force)

    for warning in warnings:
        print(f"warning: {warning}")

    summary = {
        "env_local": env_status,
        "claude_settings": claude_settings_status,
        "registry_local": registry_status,
        "configured_projects": sorted((registry_payload or {}).get("projects", {}).keys()),
        "next_steps": [
            "python3 scripts/project_router.py status",
            "python3 scripts/project_router_client.py sync --output-dir ./data/raw/voicenotes",
        ],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
