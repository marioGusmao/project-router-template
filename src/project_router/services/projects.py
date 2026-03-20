"""Project registry loading and helpers for Project Router.

Loading, merging, and querying the project registry (shared + local overlays).
All functions preserve original logic from cli.py — they are moved here for
reuse across modules without pulling in the full CLI surface.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import (
    REGISTRY_EXAMPLE_PATH,
    REGISTRY_LOCAL_PATH,
    REGISTRY_SHARED_PATH,
)


# ---------------------------------------------------------------------------
#  Data model
# ---------------------------------------------------------------------------


@dataclass
class ProjectRule:
    key: str
    display_name: str
    language: str
    inbox_path: Path | None
    router_root_path: Path | None
    note_type: str
    keywords: list[str]


# ---------------------------------------------------------------------------
#  JSON helpers
# ---------------------------------------------------------------------------


def read_registry_config(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse {path}: {exc}")
    except OSError as exc:
        raise SystemExit(f"Failed to read {path}: {exc}")


def read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Failed to parse {path}: {exc}") from exc
    except OSError as exc:
        raise SystemExit(f"Failed to read {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected a JSON object in {path}.")
    return payload


# ---------------------------------------------------------------------------
#  Path validation
# ---------------------------------------------------------------------------


def has_placeholder_path(path: Path) -> bool:
    return "/ABSOLUTE/PATH/" in str(path)


# ---------------------------------------------------------------------------
#  Registry merge
# ---------------------------------------------------------------------------


def merge_registry_configs(shared: dict[str, Any], local: dict[str, Any]) -> dict[str, Any]:
    defaults = dict(shared.get("defaults", {}))
    defaults.update(local.get("defaults", {}))

    shared_projects = shared.get("projects") or {}
    local_projects = local.get("projects") or {}
    merged_projects: dict[str, dict[str, Any]] = {}
    for key in sorted(set(shared_projects) | set(local_projects)):
        merged = dict(shared_projects.get(key) or {})
        merged.update(local_projects.get(key) or {})
        merged_projects[key] = merged

    shared_sources = shared.get("sources") or {}
    local_sources = local.get("sources") or {}
    merged_sources: dict[str, Any] = {}
    for key in sorted(set(shared_sources) | set(local_sources)):
        shared_val = shared_sources.get(key) or {}
        local_val = local_sources.get(key) or {}
        if isinstance(shared_val, dict) and isinstance(local_val, dict):
            merged_val = dict(shared_val)
            merged_val.update(local_val)
            merged_sources[key] = merged_val
        else:
            merged_sources[key] = local_val if local_val else shared_val

    return {
        "defaults": defaults,
        "projects": merged_projects,
        "sources": merged_sources,
    }


# ---------------------------------------------------------------------------
#  Registry loading
# ---------------------------------------------------------------------------


def load_registry(*, require_local: bool = False) -> tuple[dict[str, Any], dict[str, ProjectRule]]:
    if require_local and not REGISTRY_LOCAL_PATH.exists():
        raise SystemExit(
            "projects/registry.local.json is required for dispatch. "
            "Run: python3 scripts/bootstrap_local.py"
        )

    if REGISTRY_SHARED_PATH.exists():
        shared_config = read_registry_config(REGISTRY_SHARED_PATH)
        local_config = read_registry_config(REGISTRY_LOCAL_PATH) if REGISTRY_LOCAL_PATH.exists() else {}
        config = merge_registry_configs(shared_config, local_config)
        registry_path = REGISTRY_LOCAL_PATH if REGISTRY_LOCAL_PATH.exists() else REGISTRY_SHARED_PATH
    else:
        registry_path = REGISTRY_LOCAL_PATH if REGISTRY_LOCAL_PATH.exists() else REGISTRY_EXAMPLE_PATH
        config = read_registry_config(registry_path)

    defaults = config.get("defaults", {})
    projects: dict[str, ProjectRule] = {}
    for key, raw in (config.get("projects") or {}).items():
        inbox_path_raw = raw.get("inbox_path")
        router_root_path_raw = raw.get("router_root_path")
        projects[key] = ProjectRule(
            key=key,
            display_name=raw["display_name"],
            language=raw["language"],
            inbox_path=Path(inbox_path_raw) if inbox_path_raw else None,
            router_root_path=Path(router_root_path_raw) if router_root_path_raw else None,
            note_type=raw["note_type"],
            keywords=list(raw.get("keywords", [])),
        )
    return defaults, projects
