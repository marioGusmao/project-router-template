"""Note I/O helpers for Project Router.

Reading, writing, and manipulating markdown notes with YAML-style frontmatter.
All functions preserve original logic from cli.py — they are moved here for
reuse across modules without pulling in the full CLI surface.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .paths import (
    FILESYSTEM_REVIEW_STATUSES,
    FILESYSTEM_SOURCE,
    KNOWN_SOURCES,
    PROJECT_ROUTER_SOURCE,
    REVIEW_DIR,
    REVIEW_QUEUE_STATUSES,
    VOICE_SOURCE,
    normalize_source_name,
)


# ---------------------------------------------------------------------------
#  Scalar parsing / dumping
# ---------------------------------------------------------------------------


def parse_scalar(raw: str) -> Any:
    raw = raw.strip()
    if raw == "null":
        return None
    if raw == "true":
        return True
    if raw == "false":
        return False
    if raw.startswith("[") or raw.startswith("{") or raw.startswith('"'):
        return json.loads(raw)
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


def dump_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(str(value), ensure_ascii=False)


# ---------------------------------------------------------------------------
#  Note read / write
# ---------------------------------------------------------------------------


def read_note(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text

    lines = text.splitlines()
    metadata: dict[str, Any] = {}
    end_index = None
    for index in range(1, len(lines)):
        line = lines[index]
        if line == "---":
            end_index = index
            break
        if not line.strip():
            continue
        if ":" not in line:
            sys.stderr.write(f"Warning: {path} has unparseable frontmatter line: {line!r}\n")
            continue
        key, _, value = line.partition(":")
        metadata[key.strip()] = parse_scalar(value)

    if end_index is None:
        sys.stderr.write(f"Warning: {path} has unclosed frontmatter. Treating as plain text.\n")
        return {}, text

    body = "\n".join(lines[end_index + 1 :]).lstrip("\n")
    return metadata, body


def write_note(path: Path, metadata: dict[str, Any], body: str) -> None:
    ordered_keys = [
        "source",
        "source_project",
        "source_note_id",
        "source_item_type",
        "source_endpoint",
        "title",
        "created_at",
        "recorded_at",
        "recording_type",
        "duration",
        "tags",
        "capture_kind",
        "intent",
        "destination",
        "destination_reason",
        "user_keywords",
        "inferred_keywords",
        "source_language",
        "language_confidence",
        "matched_languages",
        "mixed_languages",
        "active_parser_languages",
        "transcript_format",
        "summary_available",
        "summary_source",
        "audio_available",
        "audio_local_path",
        "classification_basis",
        "derived_outputs",
        "thread_id",
        "continuation_of",
        "related_note_ids",
        "compiled_at",
        "compiled_version",
        "compiled_from_path",
        "compiled_from_signature",
        "compiled_from_status",
        "brief_summary",
        "entities",
        "facts",
        "tasks",
        "decisions",
        "open_questions",
        "follow_ups",
        "timeline",
        "ambiguities",
        "confidence_by_field",
        "evidence_spans",
        "status",
        "project",
        "candidate_projects",
        "confidence",
        "routing_reason",
        "review_status",
        "requires_user_confirmation",
        "content_hash",
        "canonical_path",
        "raw_payload_path",
        "dispatched_at",
        "dispatched_to",
        "note_type",
        "user_suggested_project",
        "user_suggestion_timestamp",
        "reviewer_notes",
    ]
    rendered: list[str] = []
    seen = set()
    for key in ordered_keys:
        if key in metadata:
            rendered.append(f"{key}: {dump_value(metadata[key])}")
            seen.add(key)
    for key in sorted(k for k in metadata if k not in seen):
        rendered.append(f"{key}: {dump_value(metadata[key])}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n" + "\n".join(rendered) + f"\n---\n\n{body.rstrip()}\n", encoding="utf-8")


# ---------------------------------------------------------------------------
#  Metadata helpers
# ---------------------------------------------------------------------------


def ensure_note_metadata_defaults(metadata: dict[str, Any]) -> dict[str, Any]:
    # Lazy import to avoid circular dependency: active_parser_profile_keys
    # depends on the language-profile loading infrastructure in classification.
    from .classification import active_parser_profile_keys

    metadata.setdefault("source", VOICE_SOURCE)
    metadata.setdefault("source_project", None)
    metadata.setdefault("tags", [])
    metadata.setdefault("capture_kind", None)
    metadata.setdefault("intent", None)
    metadata.setdefault("destination", None)
    metadata.setdefault("destination_reason", "")
    metadata.setdefault("user_keywords", [])
    metadata.setdefault("inferred_keywords", [])
    metadata.setdefault("source_language", "unknown")
    metadata.setdefault("language_confidence", 0.0)
    metadata.setdefault("matched_languages", [])
    metadata.setdefault("mixed_languages", False)
    metadata.setdefault("active_parser_languages", list(active_parser_profile_keys()))
    metadata.setdefault("summary_available", False)
    metadata.setdefault("summary_source", None)
    metadata.setdefault("audio_available", False)
    metadata.setdefault("audio_local_path", None)
    metadata.setdefault("classification_basis", [])
    metadata.setdefault("derived_outputs", [])
    metadata.setdefault("thread_id", None)
    metadata.setdefault("continuation_of", None)
    metadata.setdefault("related_note_ids", [])
    metadata.setdefault("candidate_projects", [])
    metadata.setdefault("dispatched_to", [])
    metadata.setdefault("content_hash", None)
    metadata.setdefault("user_suggested_project", None)
    metadata.setdefault("user_suggestion_timestamp", None)
    metadata.setdefault("reviewer_notes", None)
    return metadata


def apply_note_annotations(metadata: dict[str, Any], args: argparse.Namespace, note_id: str) -> None:
    metadata = ensure_note_metadata_defaults(metadata)
    if getattr(args, "user_keywords", None):
        merged = {str(value).strip().lower() for value in metadata.get("user_keywords", []) if str(value).strip()}
        merged.update(str(value).strip().lower() for value in args.user_keywords if str(value).strip())
        metadata["user_keywords"] = sorted(merged)
    if getattr(args, "related_note_ids", None):
        merged_ids = {str(value).strip() for value in metadata.get("related_note_ids", []) if str(value).strip()}
        merged_ids.update(str(value).strip() for value in args.related_note_ids if str(value).strip())
        merged_ids.discard(note_id)
        metadata["related_note_ids"] = sorted(merged_ids)
    if getattr(args, "thread_id", None):
        metadata["thread_id"] = args.thread_id
    if getattr(args, "continuation_of", None):
        continuation_of = str(args.continuation_of).strip()
        metadata["continuation_of"] = continuation_of or None
        if continuation_of and continuation_of != note_id:
            merged_ids = {str(value).strip() for value in metadata.get("related_note_ids", []) if str(value).strip()}
            merged_ids.add(continuation_of)
            metadata["related_note_ids"] = sorted(merged_ids)
    reviewer_notes = getattr(args, "reviewer_notes", None)
    if reviewer_notes is not None:
        metadata["reviewer_notes"] = reviewer_notes


# ---------------------------------------------------------------------------
#  Review directory helpers
# ---------------------------------------------------------------------------


def review_dir_for(source: str, status: str) -> Path:
    source = normalize_source_name(source) or source
    if source == VOICE_SOURCE:
        if status not in REVIEW_QUEUE_STATUSES:
            raise SystemExit(f"Unsupported review status '{status}'.")
        return REVIEW_DIR / VOICE_SOURCE / status
    if source == PROJECT_ROUTER_SOURCE:
        if status not in {"parse_errors", "needs_review", "pending_project"}:
            raise SystemExit(f"Unsupported review status '{status}'.")
        return REVIEW_DIR / PROJECT_ROUTER_SOURCE / status
    if source == FILESYSTEM_SOURCE:
        if status not in FILESYSTEM_REVIEW_STATUSES:
            raise SystemExit(f"Unsupported review status '{status}'.")
        return REVIEW_DIR / FILESYSTEM_SOURCE / status
    raise SystemExit(f"Unsupported source '{source}'.")


def review_queue_directories(sources: set[str]) -> list[Path]:
    output: list[Path] = []
    if VOICE_SOURCE in sources:
        output.extend(review_dir_for(VOICE_SOURCE, status) for status in REVIEW_QUEUE_STATUSES)
    if PROJECT_ROUTER_SOURCE in sources:
        output.extend(review_dir_for(PROJECT_ROUTER_SOURCE, status) for status in ("parse_errors", "needs_review", "pending_project"))
    if FILESYSTEM_SOURCE in sources:
        output.extend(review_dir_for(FILESYSTEM_SOURCE, status) for status in FILESYSTEM_REVIEW_STATUSES)
    return output


def remove_review_copies(note_name: str) -> None:
    for review_dir in review_queue_directories(KNOWN_SOURCES):
        review_copy = review_dir / note_name
        if review_copy.exists():
            review_copy.unlink()


# ---------------------------------------------------------------------------
#  Timestamp
# ---------------------------------------------------------------------------


def iso_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
#  File listing
# ---------------------------------------------------------------------------


def list_markdown_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(file for file in path.iterdir() if file.is_file() and file.suffix == ".md")


def list_raw_files(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted(
        file
        for file in path.iterdir()
        if file.is_file() and file.name != ".gitkeep" and file.suffix in {".json", ".md"}
    )
