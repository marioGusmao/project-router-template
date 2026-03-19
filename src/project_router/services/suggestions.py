"""Operator suggestion persistence for the dashboard."""
from __future__ import annotations

from pathlib import Path

from .notes import read_note, write_note, iso_now


def write_suggestion(note_path: Path, suggested_project: str) -> dict:
    """Write user_suggested_project to note AND log to decision packet."""
    metadata, body = read_note(note_path)
    metadata["user_suggested_project"] = suggested_project
    metadata["user_suggestion_timestamp"] = iso_now()
    write_note(note_path, metadata, body)
    _log_suggestion_to_packet(metadata, suggested_project)
    return metadata


def clear_suggestion(note_path: Path) -> dict:
    """Clear suggestion fields."""
    metadata, body = read_note(note_path)
    metadata["user_suggested_project"] = None
    metadata["user_suggestion_timestamp"] = None
    write_note(note_path, metadata, body)
    return metadata


def _log_suggestion_to_packet(metadata: dict, suggested_project: str) -> None:
    """Append suggestion entry to decision packet reviews array."""
    from .decisions import load_decision_packet_for_metadata, save_decision_packet_for_metadata

    packet = load_decision_packet_for_metadata(metadata)
    packet.setdefault("reviews", [])
    packet.setdefault("source_note_id", metadata.get("source_note_id"))
    packet.setdefault("source", metadata.get("source"))
    packet.setdefault("source_project", metadata.get("source_project"))
    packet["reviews"].append({
        "reviewed_at": iso_now(),
        "decision": "suggestion",
        "suggested_project": suggested_project,
        "previous_project": metadata.get("project"),
        "provenance": "dashboard",
    })
    save_decision_packet_for_metadata(metadata, packet)
