"""Decision packet CRUD and identity helpers for Project Router.

Building, loading, saving, and querying decision packets, plus identity/slug
functions.  All functions preserve original logic from cli.py — they are moved
here for reuse across modules without pulling in the full CLI surface.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .paths import (
    DECISIONS_DIR,
    KNOWN_SOURCES,
    NOTE_ID_PATTERN,
    ROOT,
    VOICE_SOURCE,
    normalize_source_name,
)
from .notes import (
    ensure_note_metadata_defaults,
    iso_now,
    read_note,
)
from .classification import (
    body_excerpt,
    extract_keywords,
)


# ---------------------------------------------------------------------------
#  String / path utilities
# ---------------------------------------------------------------------------


def slugify(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:60]


def require_valid_note_id(raw: Any, *, field: str = "source_note_id") -> str:
    note_id = str(raw or "").strip()
    if not note_id:
        raise SystemExit(f"{field} is required.")
    if not NOTE_ID_PATTERN.fullmatch(note_id):
        raise SystemExit(f"Invalid {field} '{note_id}'. Only letters, numbers, underscores, and hyphens are allowed.")
    return note_id


def relative_or_absolute(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def source_project_key(metadata: dict[str, Any]) -> str | None:
    value = metadata.get("source_project")
    if value in (None, "", "null"):
        return None
    return str(value)


# ---------------------------------------------------------------------------
#  Note identity
# ---------------------------------------------------------------------------


def note_identity(metadata: dict[str, Any]) -> tuple[str, str | None, str]:
    source = normalize_source_name(str(metadata.get("source") or VOICE_SOURCE)) or VOICE_SOURCE
    source_project = source_project_key(metadata)
    note_id = require_valid_note_id(metadata.get("source_note_id"))
    return source, source_project, note_id


def identity_slug(source: str, source_project: str | None, note_id: str) -> str:
    parts = [normalize_source_name(source) or source]
    if source_project:
        parts.append(source_project)
    parts.append(note_id)
    return "--".join(slugify(part) or part for part in parts)


# ---------------------------------------------------------------------------
#  Decision packet path helpers
# ---------------------------------------------------------------------------


def decision_packet_path_for_metadata(metadata: dict[str, Any]) -> Path:
    source, source_project, note_id = note_identity(metadata)
    return DECISIONS_DIR / f"{identity_slug(source, source_project, note_id)}.json"


def decision_packet_paths_for_note_id(source_note_id: str) -> list[Path]:
    safe_note_id = require_valid_note_id(source_note_id)
    return sorted(path for path in DECISIONS_DIR.glob("*.json") if path.is_file() and path.stem.endswith(f"--{safe_note_id}"))


def resolve_unique_decision_packet_path(source_note_id: str, *, sources: set[str] | None = None) -> Path:
    matches = decision_packet_paths_for_note_id(source_note_id)
    if sources is not None:
        matches = [path for path in matches if normalize_source_name(str(load_decision_packet_by_path(path).get("source") or VOICE_SOURCE)) in sources]
    if not matches:
        raise SystemExit(f"No decision packet found for {source_note_id}.")
    if len(matches) > 1:
        rendered = ", ".join(str(path) for path in matches)
        raise SystemExit(f"Multiple decision packets found for {source_note_id}. Narrow the source scope first: {rendered}")
    return matches[0]


# ---------------------------------------------------------------------------
#  Decision packet I/O
# ---------------------------------------------------------------------------


def load_decision_packet_for_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    path = decision_packet_path_for_metadata(metadata)
    if not path.exists():
        return {"reviews": []}
    return json.loads(path.read_text(encoding="utf-8"))


def load_decision_packet_by_path(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"reviews": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_decision_packet_for_metadata(metadata: dict[str, Any], packet: dict[str, Any]) -> None:
    path = decision_packet_path_for_metadata(metadata)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
#  Candidate scores
# ---------------------------------------------------------------------------


def candidate_scores(details: dict[str, float]) -> list[dict[str, Any]]:
    confidence = details.get("confidence")
    items = []
    for project, score in sorted(((k, v) for k, v in details.items() if k != "confidence"), key=lambda item: item[1], reverse=True):
        items.append({"project": project, "score": score})
    if confidence is not None:
        for item in items:
            if item["project"] == items[0]["project"]:
                item["confidence"] = confidence
                break
    return items


# ---------------------------------------------------------------------------
#  Build decision packet
# ---------------------------------------------------------------------------


def build_decision_packet(
    note_path: Path,
    metadata: dict[str, Any],
    body: str,
    *,
    route: str,
    details: dict[str, float],
    reason: str,
) -> dict[str, Any]:
    source_note_id = str(metadata.get("source_note_id") or note_path.stem)
    packet = load_decision_packet_for_metadata(metadata)
    candidates = candidate_scores(details)
    proposed_project = metadata.get("project")
    proposed_type = metadata.get("note_type")
    action = "propose_dispatch" if route not in ("ambiguous", "needs_review", "pending_project") else route
    packet.update(
        {
            "source_note_id": source_note_id,
            "source": metadata.get("source", VOICE_SOURCE),
            "source_project": metadata.get("source_project"),
            "canonical_path": relative_or_absolute(note_path),
            "raw_payload_path": metadata.get("raw_payload_path"),
            "title": metadata.get("title"),
            "created_at": metadata.get("created_at"),
            "tags": metadata.get("tags", []),
            "capture_kind": metadata.get("capture_kind"),
            "intent": metadata.get("intent"),
            "destination": metadata.get("destination"),
            "destination_reason": metadata.get("destination_reason"),
            "user_keywords": metadata.get("user_keywords", []),
            "inferred_keywords": metadata.get("inferred_keywords", []),
            "source_language": metadata.get("source_language"),
            "language_confidence": metadata.get("language_confidence"),
            "matched_languages": metadata.get("matched_languages", []),
            "mixed_languages": metadata.get("mixed_languages", False),
            "active_parser_languages": metadata.get("active_parser_languages", []),
            "summary_available": metadata.get("summary_available", False),
            "summary_source": metadata.get("summary_source"),
            "audio_available": metadata.get("audio_available", False),
            "audio_local_path": metadata.get("audio_local_path"),
            "classification_basis": metadata.get("classification_basis", []),
            "derived_outputs": metadata.get("derived_outputs", []),
            "thread": {
                "thread_id": metadata.get("thread_id"),
                "continuation_of": metadata.get("continuation_of"),
                "related_note_ids": metadata.get("related_note_ids", []),
            },
            "proposal": {
                "status": metadata.get("status"),
                "review_status": metadata.get("review_status", "pending"),
                "proposed_project": proposed_project,
                "proposed_type": proposed_type,
                "confidence": metadata.get("confidence", 0.0),
                "reason": reason,
                "candidates": candidates,
                "action": action,
                "requires_user_confirmation": metadata.get("requires_user_confirmation", True),
                "excerpt": body_excerpt(body),
                "updated_at": iso_now(),
            },
        }
    )
    packet.setdefault("reviews", [])
    return packet


# ---------------------------------------------------------------------------
#  Build review entry
# ---------------------------------------------------------------------------


def _raw_payload_path_from_packet(packet: dict[str, Any]) -> str | None:
    return packet.get("raw_payload_path")


def build_review_entry(packet: dict[str, Any], packet_path: Path) -> dict[str, Any]:
    # Lazy imports for functions not yet extracted from cli.py
    from ..cli import compiled_artifact_state, compiled_note_path

    proposal = packet.get("proposal", {})
    compiled = packet.get("compiled") or {}
    note_metadata: dict[str, Any] = {}
    note_body = ""
    canonical_path_raw = packet.get("canonical_path")
    canonical_path = str(ROOT / canonical_path_raw) if canonical_path_raw and not Path(canonical_path_raw).is_absolute() else canonical_path_raw
    if canonical_path and Path(canonical_path).exists():
        note_metadata, note_body = read_note(Path(canonical_path))
        note_metadata = ensure_note_metadata_defaults(note_metadata)
        if not note_metadata.get("inferred_keywords"):
            note_metadata["inferred_keywords"] = extract_keywords(note_metadata, note_body)
    thread = packet.get("thread") or {}
    note_status = note_metadata.get("status") or proposal.get("status")
    note_project = note_metadata.get("project")
    note_type = note_metadata.get("note_type")
    note_review_status = note_metadata.get("review_status") or proposal.get("review_status")
    note_confidence = note_metadata.get("confidence") if "confidence" in note_metadata else proposal.get("confidence")
    compiled_path = compiled.get("path") or (str(compiled_note_path(note_metadata)) if note_metadata.get("source_note_id") else None)
    compiled_summary = compiled.get("brief_summary")
    compiled_is_fresh = None
    compiled_ready = False
    if canonical_path and Path(canonical_path).exists():
        compiled_artifact_path, fresh, compiled_metadata, _ = compiled_artifact_state(note_metadata, note_body)
        compiled_ready = compiled_metadata is not None
        if compiled_artifact_path.exists():
            compiled_path = str(compiled_artifact_path)
            compiled_is_fresh = fresh
        if compiled_metadata:
            compiled_summary = compiled_metadata.get("brief_summary") or compiled_summary
    note_action = "propose_dispatch" if note_status == "classified" and note_project else note_status
    if note_status == "classified" and note_project:
        if not compiled_ready:
            note_action = "compile_required"
        elif compiled_is_fresh is False:
            note_action = "recompile_required"
    return {
        "source_note_id": packet.get("source_note_id"),
        "title": note_metadata.get("title") or packet.get("title"),
        "project": note_project if note_project is not None else proposal.get("proposed_project"),
        "type": note_type if note_type is not None else proposal.get("proposed_type"),
        "confidence": note_confidence,
        "action": note_action,
        "review_status": note_review_status,
        "capture_kind": note_metadata.get("capture_kind") or packet.get("capture_kind"),
        "intent": note_metadata.get("intent") or packet.get("intent"),
        "destination": note_metadata.get("destination") or packet.get("destination"),
        "destination_reason": note_metadata.get("destination_reason") or packet.get("destination_reason"),
        "user_keywords": note_metadata.get("user_keywords", []) or packet.get("user_keywords", []),
        "inferred_keywords": note_metadata.get("inferred_keywords", []) or packet.get("inferred_keywords", []),
        "summary_available": note_metadata.get("summary_available", packet.get("summary_available", False)),
        "audio_available": note_metadata.get("audio_available", packet.get("audio_available", False)),
        "classification_basis": note_metadata.get("classification_basis", []) or packet.get("classification_basis", []),
        "thread_id": note_metadata.get("thread_id") or thread.get("thread_id"),
        "continuation_of": note_metadata.get("continuation_of") or thread.get("continuation_of"),
        "related_note_ids": note_metadata.get("related_note_ids", []) or thread.get("related_note_ids", []),
        "compiled_summary": compiled_summary,
        "compiled_ready": compiled_ready,
        "compiled_is_fresh": compiled_is_fresh,
        "normalized_path": canonical_path,
        "compiled_path": compiled_path,
        "raw_payload_path": _raw_payload_path_from_packet(packet),
        "decision_packet_path": str(packet_path),
        "user_suggested_project": note_metadata.get("user_suggested_project"),
        "user_suggestion_timestamp": note_metadata.get("user_suggestion_timestamp"),
        "reviewer_notes": note_metadata.get("reviewer_notes"),
    }


# ---------------------------------------------------------------------------
#  Pending review counts
# ---------------------------------------------------------------------------


def count_pending_review_entries(*, sources: set[str]) -> dict[str, int]:
    counts = {source: 0 for source in sources}
    for path in sorted(DECISIONS_DIR.glob("*.json")):
        packet = load_decision_packet_by_path(path)
        source = normalize_source_name(str(packet.get("source") or VOICE_SOURCE)) or VOICE_SOURCE
        if source not in sources:
            continue
        entry = build_review_entry(packet, path)
        if entry.get("review_status") != "pending" and entry.get("action") not in {"compile_required", "recompile_required"}:
            continue
        counts[source] = counts.get(source, 0) + 1
    return counts


# ---------------------------------------------------------------------------
#  Normalized note lookup
# ---------------------------------------------------------------------------


def find_normalized_note_paths(note_id: str, *, sources: set[str] | None = None) -> list[Path]:
    # Lazy import: iter_normalized_files_by_source depends on general
    # source-directory iteration infrastructure that lives in cli.py.
    from ..cli import iter_normalized_files_by_source

    matches: list[Path] = []
    for path in iter_normalized_files_by_source(sources or set(KNOWN_SOURCES)):
        metadata, _ = read_note(path)
        if str(metadata.get("source_note_id")) == note_id:
            matches.append(path)
    return matches


def resolve_unique_normalized_note_path(note_id: str, *, sources: set[str] | None = None) -> Path:
    matches = find_normalized_note_paths(note_id, sources=sources)
    if not matches:
        raise SystemExit(f"No normalized note found for {note_id}.")
    if len(matches) > 1:
        rendered = ", ".join(str(path) for path in matches)
        raise SystemExit(f"Multiple normalized notes found for {note_id}. Narrow the source scope first: {rendered}")
    return matches[0]
