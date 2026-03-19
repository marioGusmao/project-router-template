"""Compiled-note operations for Project Router.

Compilation helpers: text processing (transcript, sentences, entity/fact/task
extraction), artifact path resolution, compile-signature freshness checks, and
the main ``compile_note_artifact`` builder.  All functions preserve original
logic from cli.py — they are moved here for reuse across modules without
pulling in the full CLI surface.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .paths import VOICE_SOURCE
from .notes import (
    ensure_note_metadata_defaults,
    iso_now,
    read_note,
)
from .classification import (
    active_parser_terms,
    body_excerpt,
    contains_any_term,
)
from .decisions import (
    note_identity,
    relative_or_absolute,
    require_valid_note_id,
)


# ---------------------------------------------------------------------------
#  Generic helpers
# ---------------------------------------------------------------------------


def existing_artifact_path(directory: Path, note_id: str, suffix: str) -> Path | None:
    safe_note_id = require_valid_note_id(note_id)
    matches = sorted(
        path
        for path in directory.glob(f"*--{safe_note_id}{suffix}")
        if path.is_file()
    )
    if len(matches) > 1:
        rendered = ", ".join(str(path) for path in matches)
        raise SystemExit(f"Multiple canonical artifacts found for note '{safe_note_id}': {rendered}")
    return matches[0] if matches else None


def note_id_from_metadata(path: Path, metadata: dict[str, Any]) -> str:
    return require_valid_note_id(metadata.get("source_note_id") or path.stem)


# ---------------------------------------------------------------------------
#  Text processing helpers
# ---------------------------------------------------------------------------


def transcript_text(body: str) -> str:
    lines = body.strip().splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).strip()


def sentence_chunks(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    chunks = re.split(r"(?<=[.!?])\s+|\s*\n+\s*", compact)
    cleaned: list[str] = []
    for chunk in chunks:
        value = chunk.strip(" -")
        if len(value) >= 8:
            cleaned.append(value)
    return cleaned


def unique_preserve(values: list[str], *, limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for raw in values:
        value = raw.strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        output.append(value)
        if limit is not None and len(output) >= limit:
            break
    return output


# ---------------------------------------------------------------------------
#  Extraction helpers
# ---------------------------------------------------------------------------


def extract_entities(metadata: dict[str, Any], body: str) -> list[str]:
    entities: list[str] = []
    if metadata.get("project"):
        entities.append(f"project:{metadata['project']}")
    if metadata.get("note_type"):
        entities.append(f"type:{metadata['note_type']}")
    for tag in metadata.get("tags", []):
        cleaned = str(tag).strip()
        if cleaned:
            entities.append(f"tag:{cleaned}")
    for keyword in metadata.get("user_keywords", []):
        entities.append(f"user_keyword:{keyword}")
    for keyword in metadata.get("inferred_keywords", []):
        entities.append(f"inferred_keyword:{keyword}")
    title_tokens = re.findall(r"\b[A-ZÀ-Ý][A-Za-zÀ-ÿ0-9_-]{2,}\b", str(metadata.get("title") or "") + " " + body_excerpt(body, limit=320))
    entities.extend(title_tokens)
    return unique_preserve(entities, limit=12)


def extract_facts(metadata: dict[str, Any], sentences: list[str]) -> list[str]:
    facts: list[str] = []
    fact_terms = active_parser_terms("fact_terms")
    timeline_terms = active_parser_terms("timeline_terms")
    if metadata.get("created_at"):
        facts.append(f"captured_at: {metadata['created_at']}")
    if metadata.get("recorded_at") and metadata.get("recorded_at") != metadata.get("created_at"):
        facts.append(f"recorded_at: {metadata['recorded_at']}")
    if metadata.get("duration") not in (None, ""):
        raw_duration = metadata["duration"]
        try:
            duration_value = float(raw_duration)
        except (TypeError, ValueError):
            facts.append(f"duration_raw: {raw_duration}")
        else:
            if duration_value >= 1000:
                milliseconds = int(duration_value)
                seconds = round(duration_value / 1000, 2)
                facts.append(f"duration_ms: {milliseconds}")
                facts.append(f"duration_seconds_approx: {seconds}")
            else:
                facts.append(f"duration_seconds: {duration_value:g}")
    for sentence in sentences:
        lowered = sentence.lower()
        if re.search(r"\b\d[\d.,]*\b", sentence) or "202" in lowered or contains_any_term(lowered, fact_terms) or contains_any_term(lowered, timeline_terms):
            facts.append(sentence)
    return unique_preserve(facts, limit=8)


def extract_tasks(sentences: list[str]) -> list[str]:
    triggers = active_parser_terms("task_triggers")
    return unique_preserve([sentence for sentence in sentences if any(trigger in sentence.lower() for trigger in triggers)], limit=8)


def extract_decisions(sentences: list[str]) -> list[str]:
    triggers = active_parser_terms("decision_triggers")
    return unique_preserve([sentence for sentence in sentences if any(trigger in sentence.lower() for trigger in triggers)], limit=6)


def extract_open_questions(sentences: list[str]) -> list[str]:
    triggers = active_parser_terms("open_question_triggers")
    return unique_preserve([sentence for sentence in sentences if sentence.endswith("?") or any(trigger in sentence.lower() for trigger in triggers)], limit=6)


def extract_follow_ups(metadata: dict[str, Any], sentences: list[str]) -> list[str]:
    follow_ups: list[str] = []
    if metadata.get("continuation_of"):
        follow_ups.append(f"Continuation of note {metadata['continuation_of']}.")
    if metadata.get("related_note_ids"):
        follow_ups.append(f"Related notes: {', '.join(metadata['related_note_ids'])}.")
    triggers = active_parser_terms("follow_up_triggers")
    for sentence in sentences:
        if any(trigger in sentence.lower() for trigger in triggers):
            follow_ups.append(sentence)
    return unique_preserve(follow_ups, limit=8)


def extract_timeline(metadata: dict[str, Any], sentences: list[str]) -> list[str]:
    timeline: list[str] = []
    if metadata.get("created_at"):
        timeline.append(f"captured:{metadata['created_at']}")
    patterns = (
        r"\b20\d{2}-\d{2}-\d{2}\b",
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    )
    timeline_terms = active_parser_terms("timeline_terms")
    for sentence in sentences:
        lowered = sentence.lower()
        if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in patterns) or contains_any_term(lowered, timeline_terms):
            timeline.append(sentence)
    return unique_preserve(timeline, limit=6)


def compile_summary(metadata: dict[str, Any], sentences: list[str]) -> str:
    title = str(metadata.get("title") or f"Voice note {metadata.get('source_note_id')}")
    capture_kind = str(metadata.get("capture_kind") or "reference")
    intent = str(metadata.get("intent") or "reference")
    destination = str(metadata.get("destination") or metadata.get("project") or "unrouted")
    lead = f"{title} is a {capture_kind} note with {intent} intent currently targeting {destination}."
    supporting = " ".join(sentences[:2]).strip()
    return f"{lead} {supporting}".strip()


# ---------------------------------------------------------------------------
#  Build helpers
# ---------------------------------------------------------------------------


def build_confidence_by_field(
    metadata: dict[str, Any],
    *,
    facts: list[str],
    tasks: list[str],
    decisions: list[str],
    open_questions: list[str],
    follow_ups: list[str],
    timeline: list[str],
) -> dict[str, float]:
    base = float(metadata.get("confidence") or 0.0)
    return {
        "summary": round(max(0.45, min(0.95, 0.45 + (0.1 * min(3, len(facts))))), 2),
        "routing": round(base, 2),
        "facts": round(max(0.3, min(0.9, 0.3 + (0.08 * len(facts)))), 2),
        "tasks": round(max(0.25, min(0.9, 0.25 + (0.1 * len(tasks)))), 2),
        "decisions": round(max(0.25, min(0.9, 0.25 + (0.1 * len(decisions)))), 2),
        "open_questions": round(max(0.25, min(0.85, 0.25 + (0.1 * len(open_questions)))), 2),
        "follow_ups": round(max(0.25, min(0.85, 0.25 + (0.08 * len(follow_ups)))), 2),
        "timeline": round(max(0.25, min(0.85, 0.25 + (0.08 * len(timeline)))), 2),
    }


def build_evidence_spans(
    *,
    sentences: list[str],
    facts: list[str],
    tasks: list[str],
    decisions: list[str],
    open_questions: list[str],
    follow_ups: list[str],
) -> list[dict[str, str]]:
    spans: list[dict[str, str]] = []
    field_map = {
        "facts": facts,
        "tasks": tasks,
        "decisions": decisions,
        "open_questions": open_questions,
        "follow_ups": follow_ups,
    }
    for field, values in field_map.items():
        for value in values[:3]:
            excerpt = next((sentence for sentence in sentences if value[:48].lower() in sentence.lower()), value)
            spans.append({"field": field, "excerpt": excerpt[:240]})
    return spans


def build_ambiguities(metadata: dict[str, Any], *, open_questions: list[str], facts: list[str]) -> list[str]:
    ambiguities: list[str] = []
    if metadata.get("status") in {"pending_project", "needs_review", "ambiguous"}:
        ambiguities.append(str(metadata.get("destination_reason") or metadata.get("routing_reason") or "Routing still needs human confirmation."))
    if not facts:
        ambiguities.append("No strong factual extraction was found beyond the raw transcript.")
    if open_questions:
        ambiguities.append("The note contains unresolved questions that may affect downstream processing.")
    if metadata.get("audio_available") and not metadata.get("audio_local_path"):
        ambiguities.append("Audio is marked as available, but no local audio path is stored yet.")
    return unique_preserve(ambiguities, limit=6)


# ---------------------------------------------------------------------------
#  Formatting helpers
# ---------------------------------------------------------------------------


def format_bullet_section(title: str, values: list[str]) -> str:
    if not values:
        return f"## {title}\n\n- None extracted.\n"
    lines = "\n".join(f"- {value}" for value in values)
    return f"## {title}\n\n{lines}\n"


def format_evidence_section(spans: list[dict[str, str]]) -> str:
    if not spans:
        return "## Evidence spans\n\n- No direct evidence spans captured.\n"
    lines = "\n".join(f"- {item['field']}: {item['excerpt']}" for item in spans)
    return f"## Evidence spans\n\n{lines}\n"


# ---------------------------------------------------------------------------
#  Compiled filename and path
# ---------------------------------------------------------------------------


def compiled_filename_from_metadata(metadata: dict[str, Any]) -> str:
    # Lazy import: normalize_timestamp lives in cli.py (used by many
    # non-compilation functions as well) and cannot be extracted here
    # without pulling unrelated normalization infrastructure.
    from ..cli import normalize_timestamp

    timestamp = normalize_timestamp(str(metadata.get("created_at") or metadata.get("recorded_at") or "unknown-time"))
    note_id = require_valid_note_id(metadata.get("source_note_id"))
    return f"{timestamp}--{note_id}.md"


def compiled_note_path(metadata: dict[str, Any]) -> Path:
    # Lazy import: compiled_dir_for lives in cli.py (depends on
    # source-directory resolution infrastructure not yet extracted).
    from ..cli import compiled_dir_for

    source, source_project, note_id = note_identity(metadata)
    directory = compiled_dir_for(source, source_project)
    return existing_artifact_path(directory, note_id, ".md") or (directory / compiled_filename_from_metadata(metadata))


# ---------------------------------------------------------------------------
#  Compile signature and freshness
# ---------------------------------------------------------------------------


def canonical_compile_signature(metadata: dict[str, Any], body: str) -> str:
    canonical = {
        "title": metadata.get("title"),
        "created_at": metadata.get("created_at"),
        "recorded_at": metadata.get("recorded_at"),
        "recording_type": metadata.get("recording_type"),
        "duration": metadata.get("duration"),
        "tags": metadata.get("tags", []),
        "capture_kind": metadata.get("capture_kind"),
        "intent": metadata.get("intent"),
        "destination": metadata.get("destination"),
        "destination_reason": metadata.get("destination_reason"),
        "user_keywords": metadata.get("user_keywords", []),
        "inferred_keywords": metadata.get("inferred_keywords", []),
        "summary_available": metadata.get("summary_available", False),
        "summary_source": metadata.get("summary_source"),
        "audio_available": metadata.get("audio_available", False),
        "audio_local_path": metadata.get("audio_local_path"),
        "classification_basis": metadata.get("classification_basis", []),
        "derived_outputs": metadata.get("derived_outputs", []),
        "thread_id": metadata.get("thread_id"),
        "continuation_of": metadata.get("continuation_of"),
        "related_note_ids": metadata.get("related_note_ids", []),
        "status": metadata.get("status"),
        "project": metadata.get("project"),
        "candidate_projects": metadata.get("candidate_projects", []),
        "confidence": metadata.get("confidence"),
        "routing_reason": metadata.get("routing_reason"),
        "review_status": metadata.get("review_status"),
        "requires_user_confirmation": metadata.get("requires_user_confirmation"),
        "note_type": metadata.get("note_type"),
        "body": body,
    }
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compiled_artifact_state(metadata: dict[str, Any], body: str) -> tuple[Path, bool, dict[str, Any] | None, str | None]:
    path = compiled_note_path(metadata)
    if not path.exists():
        return path, False, None, None
    compiled_metadata, _ = read_note(path)
    current_signature = canonical_compile_signature(metadata, body)
    is_fresh = compiled_metadata.get("compiled_from_signature") == current_signature
    return path, is_fresh, compiled_metadata, current_signature


# ---------------------------------------------------------------------------
#  Main compilation
# ---------------------------------------------------------------------------


def compile_note_artifact(metadata: dict[str, Any], body: str, note_path: Path) -> tuple[Path, dict[str, Any], str]:
    metadata = ensure_note_metadata_defaults(dict(metadata))
    compile_signature = canonical_compile_signature(metadata, body)
    transcript = transcript_text(body)
    sentences = sentence_chunks(transcript)
    entities = extract_entities(metadata, transcript)
    facts = extract_facts(metadata, sentences)
    tasks = extract_tasks(sentences)
    decisions = extract_decisions(sentences)
    open_questions = extract_open_questions(sentences)
    follow_ups = extract_follow_ups(metadata, sentences)
    timeline = extract_timeline(metadata, sentences)
    brief_summary = compile_summary(metadata, sentences)
    confidence_by_field = build_confidence_by_field(
        metadata,
        facts=facts,
        tasks=tasks,
        decisions=decisions,
        open_questions=open_questions,
        follow_ups=follow_ups,
        timeline=timeline,
    )
    evidence_spans = build_evidence_spans(
        sentences=sentences,
        facts=facts,
        tasks=tasks,
        decisions=decisions,
        open_questions=open_questions,
        follow_ups=follow_ups,
    )
    ambiguities = build_ambiguities(metadata, open_questions=open_questions, facts=facts)
    compiled_metadata = {
        "source": metadata.get("source", VOICE_SOURCE),
        "source_note_id": metadata.get("source_note_id"),
        "title": metadata.get("title"),
        "created_at": metadata.get("created_at"),
        "capture_kind": metadata.get("capture_kind"),
        "intent": metadata.get("intent"),
        "destination": metadata.get("destination"),
        "destination_reason": metadata.get("destination_reason"),
        "status": metadata.get("status"),
        "project": metadata.get("project"),
        "note_type": metadata.get("note_type"),
        "confidence": metadata.get("confidence"),
        "review_status": metadata.get("review_status"),
        "tags": metadata.get("tags", []),
        "user_keywords": metadata.get("user_keywords", []),
        "inferred_keywords": metadata.get("inferred_keywords", []),
        "source_language": metadata.get("source_language"),
        "language_confidence": metadata.get("language_confidence"),
        "matched_languages": metadata.get("matched_languages", []),
        "mixed_languages": metadata.get("mixed_languages", False),
        "active_parser_languages": metadata.get("active_parser_languages", []),
        "thread_id": metadata.get("thread_id"),
        "continuation_of": metadata.get("continuation_of"),
        "related_note_ids": metadata.get("related_note_ids", []),
        "summary_available": metadata.get("summary_available", False),
        "summary_source": metadata.get("summary_source"),
        "audio_available": metadata.get("audio_available", False),
        "audio_local_path": metadata.get("audio_local_path"),
        "classification_basis": metadata.get("classification_basis", []),
        "derived_outputs": metadata.get("derived_outputs", []),
        "canonical_path": relative_or_absolute(note_path),
        "raw_payload_path": metadata.get("raw_payload_path"),
        "compiled_at": iso_now(),
        "compiled_version": 1,
        "compiled_from_path": relative_or_absolute(note_path),
        "compiled_from_signature": compile_signature,
        "compiled_from_status": metadata.get("status"),
        "brief_summary": brief_summary,
        "entities": entities,
        "facts": facts,
        "tasks": tasks,
        "decisions": decisions,
        "open_questions": open_questions,
        "follow_ups": follow_ups,
        "timeline": timeline,
        "ambiguities": ambiguities,
        "confidence_by_field": confidence_by_field,
        "evidence_spans": evidence_spans,
    }
    compiled_title = str(metadata.get("title") or f"Voice note {metadata.get('source_note_id')}")
    compiled_body = (
        f"# {compiled_title}\n\n"
        f"## Project-ready brief\n\n{brief_summary}\n\n"
        f"{format_bullet_section('Entities', entities)}\n"
        f"{format_bullet_section('Facts', facts)}\n"
        f"{format_bullet_section('Tasks', tasks)}\n"
        f"{format_bullet_section('Decisions', decisions)}\n"
        f"{format_bullet_section('Open questions', open_questions)}\n"
        f"{format_bullet_section('Follow-ups', follow_ups)}\n"
        f"{format_bullet_section('Timeline', timeline)}\n"
        f"{format_bullet_section('Ambiguities', ambiguities)}\n"
        f"## Confidence by field\n\n```json\n{json.dumps(confidence_by_field, indent=2, ensure_ascii=False)}\n```\n\n"
        f"{format_evidence_section(evidence_spans)}\n"
        f"## Source transcript\n\n{transcript or '(empty transcript)'}\n"
    )
    return compiled_note_path(metadata), compiled_metadata, compiled_body
