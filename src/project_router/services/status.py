"""Pipeline status and count helpers for Project Router.

Aggregates file counts across pipeline stages and computes the overall
status summary dict.  ``compute_pipeline_status`` is the reusable core
that ``status_command`` in cli.py delegates to.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import (
    COMPILED_DIR,
    DECISIONS_DIR,
    DISPATCHED_DIR,
    FILESYSTEM_SOURCE,
    INBOX_STATUS_DIR,
    KNOWN_SOURCES,
    LOCAL_ROUTER_DIR,
    NORMALIZED_DIR,
    OUTBOX_SCAN_STATE_PATH,
    PROCESSED_DIR,
    PROJECT_ROUTER_SOURCE,
    RAW_DIR,
    READWISE_SOURCE,
    VOICE_SOURCE,
)
from .notes import (
    list_markdown_files,
    list_raw_files,
    review_dir_for,
)


# ---------------------------------------------------------------------------
#  Directory listing helpers (filesystem / project_router sources)
# ---------------------------------------------------------------------------


def list_project_router_keys_for_artifacts(directory: Path) -> list[str]:
    if not directory.exists():
        return []
    return sorted(path.name for path in directory.iterdir() if path.is_dir())


def list_filesystem_inbox_keys() -> list[str]:
    """Return sorted inbox keys found under data/raw/filesystem/."""
    fs_root = RAW_DIR / FILESYSTEM_SOURCE
    if not fs_root.exists():
        return []
    return sorted(p.name for p in fs_root.iterdir() if p.is_dir())


def list_filesystem_manifests(directory: Path | None = None) -> list[Path]:
    """Walk filesystem manifest directories for .manifest.json files."""
    output: list[Path] = []
    if directory is not None:
        if directory.exists():
            output.extend(
                f for f in sorted(directory.iterdir())
                if f.is_file() and f.name.endswith(".manifest.json")
            )
        return output
    for inbox_key in list_filesystem_inbox_keys():
        manifests_dir = RAW_DIR / FILESYSTEM_SOURCE / inbox_key / "manifests"
        if manifests_dir.exists():
            output.extend(
                f for f in sorted(manifests_dir.iterdir())
                if f.is_file() and f.name.endswith(".manifest.json")
            )
    return sorted(output)


def iter_source_dirs(kind: str, sources: set[str]) -> list[Path]:
    # Lazy import to avoid circular dependency — raw_dir_for / normalized_dir_for
    # / compiled_dir_for are still defined in cli.py.
    from ..cli import raw_dir_for, normalized_dir_for, compiled_dir_for

    if kind == "raw":
        voice_dir = raw_dir_for(VOICE_SOURCE)
        project_root = RAW_DIR / PROJECT_ROUTER_SOURCE
    elif kind == "normalized":
        voice_dir = normalized_dir_for(VOICE_SOURCE)
        project_root = NORMALIZED_DIR / PROJECT_ROUTER_SOURCE
    elif kind == "compiled":
        voice_dir = compiled_dir_for(VOICE_SOURCE)
        project_root = COMPILED_DIR / PROJECT_ROUTER_SOURCE
    else:
        raise SystemExit(f"Unknown artifact kind '{kind}'.")
    output: list[Path] = []
    if VOICE_SOURCE in sources:
        output.append(voice_dir)
    if PROJECT_ROUTER_SOURCE in sources:
        output.extend(project_root / key for key in list_project_router_keys_for_artifacts(project_root))
    if FILESYSTEM_SOURCE in sources:
        if kind == "raw":
            for inbox_key in list_filesystem_inbox_keys():
                output.append(RAW_DIR / FILESYSTEM_SOURCE / inbox_key / "manifests")
        elif kind == "normalized":
            output.append(NORMALIZED_DIR / FILESYSTEM_SOURCE)
        elif kind == "compiled":
            output.append(COMPILED_DIR / FILESYSTEM_SOURCE)
    if READWISE_SOURCE in sources:
        if kind == "raw":
            output.append(RAW_DIR / READWISE_SOURCE)
        elif kind == "normalized":
            output.append(NORMALIZED_DIR / READWISE_SOURCE)
        elif kind == "compiled":
            output.append(COMPILED_DIR / READWISE_SOURCE)
    return output


# ---------------------------------------------------------------------------
#  Count helpers
# ---------------------------------------------------------------------------


def count_markdown(path: Path) -> int:
    return len(list_markdown_files(path))


def count_raw(path: Path) -> int:
    return len(list_raw_files(path))


def count_manifests(directory: Path | None = None) -> int:
    return len(list_filesystem_manifests(directory))


def _count_inbox_states() -> dict[str, int]:
    """Count inbox packets by status for the status command."""
    # Lazy import — extract_packet_id / load_inbox_packet_state live in cli.py
    from ..cli import extract_packet_id, load_inbox_packet_state

    counts: dict[str, int] = {}
    if INBOX_STATUS_DIR.exists():
        for state_path in INBOX_STATUS_DIR.glob("*.json"):
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
                status = state.get("status", "unknown")
                counts[status] = counts.get(status, 0) + 1
            except (json.JSONDecodeError, OSError):
                counts["error"] = counts.get("error", 0) + 1
    inbox = LOCAL_ROUTER_DIR / "inbox"
    unprocessed = 0
    if inbox.exists():
        for p in inbox.iterdir():
            if p.is_file() and p.suffix == ".md" and p.name != ".gitkeep":
                try:
                    pid = extract_packet_id(p)
                except SystemExit:
                    continue
                if load_inbox_packet_state(pid) is None:
                    unprocessed += 1
    if unprocessed:
        counts["unprocessed"] = unprocessed
    return counts


# ---------------------------------------------------------------------------
#  Pipeline status aggregation
# ---------------------------------------------------------------------------


def compute_pipeline_status(sources: set[str]) -> dict[str, Any]:
    """Build the pipeline status summary dict.

    This is the reusable core extracted from ``status_command``.
    ``sources`` should be a set of known source names (e.g. from
    ``parse_source_filter``).
    """
    # Lazy imports for helpers still in cli.py
    from ..cli import (
        compiled_dir_for,
        count_active_scan_state_errors,
        legacy_source_layout_operations,
        load_outbox_scan_state,
        normalized_dir_for,
        raw_dir_for,
    )

    voicenotes_raw = count_raw(raw_dir_for(VOICE_SOURCE)) if VOICE_SOURCE in sources else 0
    voicenotes_normalized = count_markdown(normalized_dir_for(VOICE_SOURCE)) if VOICE_SOURCE in sources else 0
    voicenotes_compiled = count_markdown(compiled_dir_for(VOICE_SOURCE)) if VOICE_SOURCE in sources else 0
    project_router_raw = sum(count_raw(path) for path in iter_source_dirs("raw", {PROJECT_ROUTER_SOURCE})) if PROJECT_ROUTER_SOURCE in sources else 0
    project_router_normalized = sum(count_markdown(path) for path in iter_source_dirs("normalized", {PROJECT_ROUTER_SOURCE})) if PROJECT_ROUTER_SOURCE in sources else 0
    project_router_compiled = sum(count_markdown(path) for path in iter_source_dirs("compiled", {PROJECT_ROUTER_SOURCE})) if PROJECT_ROUTER_SOURCE in sources else 0
    filesystem_raw = count_manifests() if FILESYSTEM_SOURCE in sources else 0
    filesystem_normalized = count_markdown(normalized_dir_for(FILESYSTEM_SOURCE)) if FILESYSTEM_SOURCE in sources else 0
    filesystem_compiled = count_markdown(compiled_dir_for(FILESYSTEM_SOURCE)) if FILESYSTEM_SOURCE in sources else 0
    readwise_raw = count_raw(raw_dir_for(READWISE_SOURCE)) if READWISE_SOURCE in sources else 0
    readwise_normalized = count_markdown(normalized_dir_for(READWISE_SOURCE)) if READWISE_SOURCE in sources else 0
    readwise_compiled = count_markdown(compiled_dir_for(READWISE_SOURCE)) if READWISE_SOURCE in sources else 0
    scan_state = load_outbox_scan_state() if PROJECT_ROUTER_SOURCE in sources else None
    legacy_backlog = len(legacy_source_layout_operations())

    summary: dict[str, Any] = {
        "sources": sorted(sources),
        "raw": {
            "voicenotes": voicenotes_raw,
            "project_router": project_router_raw,
            "filesystem": filesystem_raw,
            "readwise": readwise_raw,
        },
        "normalized": {
            "voicenotes": voicenotes_normalized,
            "project_router": project_router_normalized,
            "filesystem": filesystem_normalized,
            "readwise": readwise_normalized,
        },
        "compiled": {
            "voicenotes": voicenotes_compiled,
            "project_router": project_router_compiled,
            "filesystem": filesystem_compiled,
            "readwise": readwise_compiled,
        },
        "review": {
            "voicenotes": {
                "ambiguous": count_markdown(review_dir_for(VOICE_SOURCE, "ambiguous")) if VOICE_SOURCE in sources else 0,
                "pending_project": count_markdown(review_dir_for(VOICE_SOURCE, "pending_project")) if VOICE_SOURCE in sources else 0,
                "needs_review": count_markdown(review_dir_for(VOICE_SOURCE, "needs_review")) if VOICE_SOURCE in sources else 0,
            },
            "project_router": {
                "parse_errors": count_active_scan_state_errors(scan_state) if PROJECT_ROUTER_SOURCE in sources else 0,
                "pending_project": count_markdown(review_dir_for(PROJECT_ROUTER_SOURCE, "pending_project")) if PROJECT_ROUTER_SOURCE in sources else 0,
                "needs_review": count_markdown(review_dir_for(PROJECT_ROUTER_SOURCE, "needs_review")) if PROJECT_ROUTER_SOURCE in sources else 0,
            },
            "filesystem": {
                "parse_errors": count_markdown(review_dir_for(FILESYSTEM_SOURCE, "parse_errors")) if FILESYSTEM_SOURCE in sources else 0,
                "needs_extraction": count_markdown(review_dir_for(FILESYSTEM_SOURCE, "needs_extraction")) if FILESYSTEM_SOURCE in sources else 0,
                "ambiguous": count_markdown(review_dir_for(FILESYSTEM_SOURCE, "ambiguous")) if FILESYSTEM_SOURCE in sources else 0,
                "pending_project": count_markdown(review_dir_for(FILESYSTEM_SOURCE, "pending_project")) if FILESYSTEM_SOURCE in sources else 0,
                "needs_review": count_markdown(review_dir_for(FILESYSTEM_SOURCE, "needs_review")) if FILESYSTEM_SOURCE in sources else 0,
            },
            "readwise": {
                "ambiguous": count_markdown(review_dir_for(READWISE_SOURCE, "ambiguous")) if READWISE_SOURCE in sources else 0,
                "pending_project": count_markdown(review_dir_for(READWISE_SOURCE, "pending_project")) if READWISE_SOURCE in sources else 0,
                "needs_review": count_markdown(review_dir_for(READWISE_SOURCE, "needs_review")) if READWISE_SOURCE in sources else 0,
            },
        },
        "dispatched": sum(count_markdown(path) for path in DISPATCHED_DIR.glob("*") if path.is_dir()),
        "processed": count_markdown(PROCESSED_DIR),
        "decision_packets": len(list(DECISIONS_DIR.glob("*.json"))),
        "inbox": _count_inbox_states(),
        "legacy_backlog": legacy_backlog,
        "scan_state_path": str(OUTBOX_SCAN_STATE_PATH),
    }
    return summary
