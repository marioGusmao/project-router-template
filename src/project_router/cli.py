"""Minimal CLI for Project Router for VoiceNotes."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
NORMALIZED_DIR = DATA_DIR / "normalized"
COMPILED_DIR = DATA_DIR / "compiled"
AMBIGUOUS_DIR = DATA_DIR / "review" / "ambiguous"
NEEDS_REVIEW_DIR = DATA_DIR / "review" / "needs_review"
PENDING_PROJECT_DIR = DATA_DIR / "review" / "pending_project"
DISPATCHED_DIR = DATA_DIR / "dispatched"
PROCESSED_DIR = DATA_DIR / "processed"
STATE_DIR = ROOT / "state"
DECISIONS_DIR = STATE_DIR / "decisions"
DISCOVERIES_DIR = STATE_DIR / "discoveries"
REGISTRY_LOCAL_PATH = ROOT / "projects" / "registry.local.json"
REGISTRY_SHARED_PATH = ROOT / "projects" / "registry.shared.json"
REGISTRY_EXAMPLE_PATH = ROOT / "projects" / "registry.example.json"
ENV_LOCAL_PATH = ROOT / ".env.local"
ENV_PATH = ROOT / ".env"
DISCOVERY_REPORT_PATH = DISCOVERIES_DIR / "pending_project_latest.json"
NOTE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

STOPWORDS = {
    "a",
    "about",
    "after",
    "again",
    "agora",
    "acho",
    "algo",
    "ainda",
    "alguma",
    "algumas",
    "algum",
    "alguns",
    "and",
    "antes",
    "ao",
    "apenas",
    "aqui",
    "assim",
    "ate",
    "até",
    "can",
    "capture",
    "coisa",
    "coisas",
    "com",
    "como",
    "da",
    "das",
    "de",
    "delas",
    "deles",
    "depois",
    "do",
    "dos",
    "e",
    "ela",
    "elas",
    "ele",
    "eles",
    "em",
    "entre",
    "entao",
    "então",
    "era",
    "essa",
    "essas",
    "esse",
    "esses",
    "esta",
    "está",
    "estao",
    "estas",
    "este",
    "estes",
    "eu",
    "faz",
    "fazer",
    "fica",
    "ficar",
    "foi",
    "for",
    "from",
    "gente",
    "have",
    "isso",
    "isto",
    "ja",
    "já",
    "just",
    "last",
    "mais",
    "me",
    "mesmo",
    "meu",
    "minha",
    "meeting",
    "meia",
    "muita",
    "muitas",
    "muito",
    "muitos",
    "nao",
    "nas",
    "need",
    "new",
    "no",
    "nos",
    "nota",
    "note",
    "notes",
    "num",
    "numa",
    "não",
    "nós",
    "o",
    "os",
    "ora",
    "ou",
    "over",
    "para",
    "pela",
    "pelas",
    "pelo",
    "pelos",
    "por",
    "porque",
    "pra",
    "quando",
    "quanto",
    "que",
    "sei",
    "sem",
    "ser",
    "seu",
    "space",
    "speaker",
    "sua",
    "sobre",
    "sim",
    "tambem",
    "também",
    "tem",
    "tenho",
    "ter",
    "test",
    "teste",
    "the",
    "this",
    "todo",
    "tudo",
    "uhum",
    "um",
    "uma",
    "umas",
    "uns",
    "voice",
    "voicenotes",
    "vai",
    "ver",
    "vou",
    "welcome",
    "with",
    "you",
    "your",
}


@dataclass
class ProjectRule:
    key: str
    display_name: str
    language: str
    inbox_path: Path | None
    note_type: str
    auto_dispatch_threshold: float
    keywords: list[str]


def ensure_layout() -> None:
    for path in (
        RAW_DIR,
        NORMALIZED_DIR,
        COMPILED_DIR,
        AMBIGUOUS_DIR,
        NEEDS_REVIEW_DIR,
        PENDING_PROJECT_DIR,
        DISPATCHED_DIR,
        PROCESSED_DIR,
        DECISIONS_DIR,
        DISCOVERIES_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def load_local_env() -> None:
    load_env_file(ENV_PATH)
    load_env_file(ENV_LOCAL_PATH)


def has_placeholder_path(path: Path) -> bool:
    return "/ABSOLUTE/PATH/" in str(path)


def require_valid_note_id(raw: Any, *, field: str = "source_note_id") -> str:
    note_id = str(raw or "").strip()
    if not note_id:
        raise SystemExit(f"{field} is required.")
    if not NOTE_ID_PATTERN.fullmatch(note_id):
        raise SystemExit(f"Invalid {field} '{note_id}'. Only letters, numbers, underscores, and hyphens are allowed.")
    return note_id


def ensure_safe_inbox_path(path: Path, *, project_key: str, registry_path: Path) -> None:
    if has_placeholder_path(path):
        raise SystemExit(f"Project '{project_key}' still has a placeholder inbox path in {registry_path}.")
    if not path.is_absolute():
        raise SystemExit(f"Project '{project_key}' must use an absolute inbox path in {registry_path}.")
    if ".." in path.parts:
        raise SystemExit(f"Project '{project_key}' contains an unsafe inbox path in {registry_path}.")


def read_registry_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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

    return {
        "defaults": defaults,
        "projects": merged_projects,
    }


def load_registry(*, require_local: bool = False) -> tuple[dict[str, Any], dict[str, ProjectRule]]:
    if require_local and not REGISTRY_LOCAL_PATH.exists():
        raise SystemExit("projects/registry.local.json is required for dispatch. Copy the example and set real local inbox paths first.")

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
        projects[key] = ProjectRule(
            key=key,
            display_name=raw["display_name"],
            language=raw["language"],
            inbox_path=Path(inbox_path_raw) if inbox_path_raw else None,
            note_type=raw["note_type"],
            auto_dispatch_threshold=float(raw.get("auto_dispatch_threshold", defaults.get("auto_dispatch_threshold", 0.9))),
            keywords=list(raw.get("keywords", [])),
        )
    return defaults, projects


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
        key, _, value = line.partition(":")
        metadata[key.strip()] = parse_scalar(value)

    if end_index is None:
        return {}, text

    body = "\n".join(lines[end_index + 1 :]).lstrip("\n")
    return metadata, body


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


def write_note(path: Path, metadata: dict[str, Any], body: str) -> None:
    ordered_keys = [
        "source",
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
        "canonical_path",
        "raw_payload_path",
        "dispatched_at",
        "dispatched_to",
        "note_type",
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


def remove_review_copies(note_name: str) -> None:
    for review_dir in (AMBIGUOUS_DIR, NEEDS_REVIEW_DIR, PENDING_PROJECT_DIR):
        review_copy = review_dir / note_name
        if review_copy.exists():
            review_copy.unlink()


def iso_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def decision_packet_path(source_note_id: str) -> Path:
    safe_note_id = require_valid_note_id(source_note_id)
    return DECISIONS_DIR / f"{safe_note_id}.json"


def load_decision_packet(source_note_id: str) -> dict[str, Any]:
    path = decision_packet_path(source_note_id)
    if not path.exists():
        return {"reviews": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_decision_packet(packet: dict[str, Any]) -> None:
    path = decision_packet_path(str(packet["source_note_id"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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


def body_excerpt(body: str, limit: int = 240) -> str:
    compact = re.sub(r"\s+", " ", body).strip()
    return compact[:limit]


def keyword_tokens(text: str) -> list[str]:
    lowered = text.lower()
    tokens = re.findall(r"[a-z0-9à-ÿ][a-z0-9à-ÿ_-]{2,}", lowered)
    return [token for token in tokens if token not in STOPWORDS and not token.isdigit()]


def extract_keywords(metadata: dict[str, Any], body: str, *, limit: int = 8) -> list[str]:
    counter: Counter[str] = Counter()
    capture_kind = metadata.get("capture_kind") or classify_capture_kind(metadata, body)[0]
    title_tokens = keyword_tokens(str(metadata.get("title") or ""))
    body_source = body_excerpt(body, limit=600) if capture_kind in {"meeting_recording", "meeting_summary"} else body
    body_tokens = keyword_tokens(body_source)
    tag_tokens = [str(tag).strip().lower() for tag in metadata.get("tags", []) if str(tag).strip()]

    for token in title_tokens:
        counter[token] += 4 if capture_kind in {"meeting_recording", "meeting_summary"} else 3
    for token in body_tokens:
        counter[token] += 1
    for token in tag_tokens:
        if token not in STOPWORDS:
            counter[token] += 4

    return [token for token, _ in counter.most_common(limit)]


def ensure_note_metadata_defaults(metadata: dict[str, Any]) -> dict[str, Any]:
    metadata.setdefault("tags", [])
    metadata.setdefault("capture_kind", None)
    metadata.setdefault("intent", None)
    metadata.setdefault("destination", None)
    metadata.setdefault("destination_reason", "")
    metadata.setdefault("user_keywords", [])
    metadata.setdefault("inferred_keywords", [])
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
    return metadata


def note_keyword_set(metadata: dict[str, Any]) -> set[str]:
    values = []
    values.extend(str(tag).strip().lower() for tag in metadata.get("tags", []))
    values.extend(str(tag).strip().lower() for tag in metadata.get("user_keywords", []))
    values.extend(str(tag).strip().lower() for tag in metadata.get("inferred_keywords", []))
    return {value for value in values if value and value not in STOPWORDS}


def extract_signal_list(metadata: dict[str, Any], body: str) -> list[str]:
    signals: list[str] = []
    recording_type = metadata.get("recording_type")
    if recording_type is not None:
        signals.append(f"recording_type:{recording_type}")
    for tag in metadata.get("tags", []):
        cleaned = str(tag).strip().lower()
        if cleaned:
            signals.append(f"tag:{cleaned}")
    title = str(metadata.get("title") or "").lower()
    if "summary" in title or "resumo" in title:
        signals.append("title:summary")
    if "follow-up" in title or "follow up" in title or "seguimento" in title or "continuação" in title:
        signals.append("title:follow_up")
    if "calendar" in title or "calend" in title:
        signals.append("title:calendar")
    if "idea" in title or "ideia" in title or "project" in title or "projeto" in title:
        signals.append("title:project_idea")
    if "task" in title or "tarefa" in title:
        signals.append("title:task")
    if "buy" in title or "bought" in title or "comprei" in title or "garantia" in title or "warranty" in title:
        signals.append("title:purchase")
    compact_body = body.lower()
    if "speaker 1" in compact_body or "speaker 2" in compact_body:
        signals.append("body:speaker_markers")
    if "[00:" in body:
        signals.append("body:timestamps")
    return signals


def classify_capture_kind(metadata: dict[str, Any], body: str) -> tuple[str, list[str]]:
    signals = extract_signal_list(metadata, body)
    signal_set = set(signals)
    title = str(metadata.get("title") or "").lower()
    compact_body = body.lower()

    if "tag:meeting" in signal_set or "recording_type:2" in signal_set or "body:speaker_markers" in signal_set:
        if "title:summary" in signal_set:
            return "meeting_summary", signals
        return "meeting_recording", signals
    if any(token in title for token in ("automation", "integration", "codex", "obsidian", "idea", "ideia", "project", "projeto")):
        return "project_idea", signals
    if "title:calendar" in signal_set or "calendar" in compact_body or "calend" in compact_body:
        return "calendar_change", signals
    if "title:purchase" in signal_set or "comprei" in compact_body or "garantia" in compact_body or "warranty" in compact_body:
        return "purchase_record", signals
    if "title:task" in signal_set or "tenho que" in compact_body or "tenho de" in compact_body or "todo:" in compact_body:
        return "task_capture", signals
    if "title:project_idea" in signal_set or "ideia" in compact_body or "project idea" in compact_body:
        return "project_idea", signals
    if "journal" in title or "diário" in title or "journal" in compact_body:
        return "journal", signals
    if metadata.get("recording_type") == 3:
        return "voice_memo", signals
    return "reference", signals


def classify_intent(metadata: dict[str, Any]) -> str:
    if metadata.get("continuation_of") or metadata.get("related_note_ids"):
        return "follow_up"

    capture_kind = metadata.get("capture_kind")
    if capture_kind in {"task_capture", "calendar_change", "purchase_record", "project_idea"}:
        return "actionable"
    if capture_kind in {"meeting_recording", "meeting_summary"}:
        return "decision_log"
    return "reference"


def derive_outputs(capture_kind: str) -> list[str]:
    if capture_kind == "meeting_recording":
        return ["summary", "decisions", "tasks", "open_questions", "follow_ups"]
    if capture_kind == "meeting_summary":
        return ["decisions", "tasks", "open_questions", "follow_ups"]
    return []


def enrich_note_metadata(metadata: dict[str, Any], body: str) -> dict[str, Any]:
    metadata = ensure_note_metadata_defaults(metadata)
    capture_kind, signals = classify_capture_kind(metadata, body)
    metadata["capture_kind"] = capture_kind
    metadata["classification_basis"] = signals
    metadata["derived_outputs"] = derive_outputs(capture_kind)
    metadata["intent"] = classify_intent(metadata)
    metadata.setdefault("summary_available", False)
    metadata.setdefault("summary_source", None)
    metadata.setdefault("audio_available", False)
    metadata.setdefault("audio_local_path", None)
    return metadata


def parse_note_datetime(value: str | None) -> Any:
    if not value:
        return None
    from datetime import datetime

    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def relationship_score(left: dict[str, Any], right: dict[str, Any]) -> tuple[int, list[str]]:
    shared = sorted(note_keyword_set(left) & note_keyword_set(right))
    return len(shared), shared


def format_discovery_bucket(keywords: list[str]) -> str:
    if not keywords:
        return "unclassified-bucket"
    return "-".join(keywords[:3])


def note_sort_key(item: dict[str, Any]) -> str:
    created_dt = item.get("created_dt")
    if created_dt is not None:
        return created_dt.isoformat()
    metadata = item.get("metadata", {})
    return str(metadata.get("created_at") or metadata.get("recorded_at") or "")


def is_system_note(metadata: dict[str, Any], body: str) -> bool:
    title = str(metadata.get("title") or "").lower()
    note_id = str(metadata.get("source_note_id") or "").lower()
    compact_body = body.lower()
    return (
        title == "welcome to voicenotes"
        or note_id.startswith("welcome_")
        or ("capture your thoughts" in compact_body and "meeting" in compact_body and "recording" in compact_body)
    )


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
    packet = load_decision_packet(source_note_id)
    candidates = candidate_scores(details)
    proposed_project = metadata.get("project")
    proposed_type = metadata.get("note_type")
    action = "propose_dispatch" if route not in ("ambiguous", "needs_review", "pending_project") else route
    packet.update(
        {
            "source_note_id": source_note_id,
            "canonical_path": str(note_path),
            "title": metadata.get("title"),
            "created_at": metadata.get("created_at"),
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


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    import html as html_module

    plain = html_module.unescape(text)
    plain = plain.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    plain = re.sub(r"</p\s*>", "\n\n", plain, flags=re.IGNORECASE)
    plain = re.sub(r"<[^>]+>", "", plain)
    return plain.strip()


def normalize_timestamp(value: str | None) -> str:
    if not value:
        return "unknown-time"
    return value.replace(":", "").replace("-", "").replace(".000000", "").replace("+00:00", "Z")


def normalized_filename_from_recording(recording: dict[str, Any]) -> str:
    note_id = require_valid_note_id(recording.get("id") or recording.get("uuid"))
    timestamp = normalize_timestamp(recording.get("created_at") or recording.get("recorded_at"))
    return f"{timestamp}--{note_id}.md"


def compiled_filename_from_metadata(metadata: dict[str, Any]) -> str:
    timestamp = normalize_timestamp(str(metadata.get("created_at") or metadata.get("recorded_at") or "unknown-time"))
    note_id = require_valid_note_id(metadata.get("source_note_id"))
    return f"{timestamp}--{note_id}.md"


def load_raw_recording(path: Path) -> tuple[dict[str, Any], str]:
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "recording" in payload:
            return payload, "json"
        # tolerate direct recording payloads too
        return {"source": "voicenotes", "source_endpoint": "recordings", "recording": payload}, "json"

    metadata, body = read_note(path)
    return (
        {
            "source": metadata.get("source", "voicenotes"),
            "source_endpoint": "legacy-markdown-raw",
            "recording": {
                "id": metadata.get("source_note_id"),
                "title": metadata.get("title"),
                "created_at": metadata.get("created_at"),
                "recorded_at": metadata.get("recorded_at"),
                "recording_type": metadata.get("recording_type"),
                "duration": metadata.get("duration"),
                "tags": metadata.get("tags", []),
                "transcript": body,
            },
        },
        "legacy-markdown",
    )


def normalized_note_from_raw(raw_path: Path, raw_payload: dict[str, Any], raw_format: str) -> tuple[Path, dict[str, Any], str]:
    recording = dict(raw_payload.get("recording") or {})
    note_id = require_valid_note_id(recording.get("id") or recording.get("uuid"))
    title = recording.get("title") or f"VoiceNotes {recording.get('id') or recording.get('uuid')}"
    normalized_path = existing_artifact_path(NORMALIZED_DIR, note_id, ".md") or (NORMALIZED_DIR / normalized_filename_from_recording(recording))
    transcript = recording.get("transcript")
    metadata = {
        "source": raw_payload.get("source", "voicenotes"),
        "source_note_id": note_id,
        "source_item_type": recording.get("type", "note"),
        "source_endpoint": raw_payload.get("source_endpoint", "recordings"),
        "title": title,
        "created_at": recording.get("created_at"),
        "recorded_at": recording.get("recorded_at"),
        "recording_type": recording.get("recording_type"),
        "duration": recording.get("duration"),
        "tags": recording.get("tags") or [],
        "capture_kind": None,
        "intent": None,
        "destination": None,
        "destination_reason": "",
        "user_keywords": [],
        "inferred_keywords": [],
        "transcript_format": "html" if raw_format == "json" else "markdown",
        "summary_available": False,
        "summary_source": None,
        "audio_available": False,
        "audio_local_path": None,
        "classification_basis": [],
        "derived_outputs": [],
        "thread_id": None,
        "continuation_of": None,
        "related_note_ids": [],
        "status": "normalized",
        "project": None,
        "candidate_projects": [],
        "confidence": 0.0,
        "routing_reason": "",
        "review_status": "pending",
        "requires_user_confirmation": True,
        "canonical_path": str(normalized_path),
        "raw_payload_path": str(raw_path),
        "dispatched_to": [],
    }
    body = f"# {title}\n\n{strip_html(transcript)}\n"
    return normalized_path, enrich_note_metadata(metadata, body), body


PRESERVED_NORMALIZED_FIELDS = {
    "project",
    "candidate_projects",
    "confidence",
    "routing_reason",
    "review_status",
    "requires_user_confirmation",
    "dispatched_at",
    "dispatched_to",
    "note_type",
    "status",
    "user_keywords",
    "thread_id",
    "continuation_of",
    "related_note_ids",
    "audio_local_path",
}


def merge_normalized_metadata(existing: dict[str, Any], fresh: dict[str, Any]) -> dict[str, Any]:
    merged = dict(fresh)
    for key in PRESERVED_NORMALIZED_FIELDS:
        if key in existing:
            merged[key] = existing[key]
    if "destination" in existing and existing.get("status") == "dispatched":
        merged["destination"] = existing["destination"]
    if "summary_available" in existing and existing.get("summary_available"):
        merged["summary_available"] = existing["summary_available"]
        merged["summary_source"] = existing.get("summary_source")
    if "audio_available" in existing and existing.get("audio_available"):
        merged["audio_available"] = existing["audio_available"]
    if "classification_basis" in existing and existing.get("classification_basis"):
        # keep prior manual/source hints if they exceed the current payload
        merged["classification_basis"] = sorted(set(merged.get("classification_basis", [])) | set(existing.get("classification_basis", [])))
    return ensure_note_metadata_defaults(merged)


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
        if re.search(r"\b\d[\d.,]*\b", sentence) or any(token in lowered for token in ("€", "eur", "days", "meses", "months", "ano", "year", "202", "tomorrow", "amanhã", "hoje")):
            facts.append(sentence)
    return unique_preserve(facts, limit=8)


def extract_tasks(sentences: list[str]) -> list[str]:
    triggers = (
        "preciso",
        "preciso de",
        "tenho que",
        "tenho de",
        "need to",
        "to do",
        "todo",
        "follow up",
        "follow-up",
        "fazer",
        "enviar",
        "ligar",
        "marcar",
        "schedule",
        "book",
        "remember",
        "lembrar",
    )
    return unique_preserve([sentence for sentence in sentences if any(trigger in sentence.lower() for trigger in triggers)], limit=8)


def extract_decisions(sentences: list[str]) -> list[str]:
    triggers = ("decid", "ficou", "agreed", "vamos", "we will", "resolved", "decisão")
    return unique_preserve([sentence for sentence in sentences if any(trigger in sentence.lower() for trigger in triggers)], limit=6)


def extract_open_questions(sentences: list[str]) -> list[str]:
    triggers = ("não sei", "nao sei", "dúvida", "duvida", "question", "perceber", "confirmar", "verify", "validar")
    return unique_preserve([sentence for sentence in sentences if sentence.endswith("?") or any(trigger in sentence.lower() for trigger in triggers)], limit=6)


def extract_follow_ups(metadata: dict[str, Any], sentences: list[str]) -> list[str]:
    follow_ups: list[str] = []
    if metadata.get("continuation_of"):
        follow_ups.append(f"Continuation of note {metadata['continuation_of']}.")
    if metadata.get("related_note_ids"):
        follow_ups.append(f"Related notes: {', '.join(metadata['related_note_ids'])}.")
    triggers = ("follow up", "follow-up", "next step", "próximo", "proximo", "depois", "later", "continuar", "continuação", "continuação")
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
        r"\b(?:today|tomorrow|yesterday|hoje|amanhã|amanha|ontem|next week|esta semana)\b",
    )
    for sentence in sentences:
        lowered = sentence.lower()
        if any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in patterns):
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


def compiled_note_path(metadata: dict[str, Any]) -> Path:
    note_id = require_valid_note_id(metadata.get("source_note_id"))
    return existing_artifact_path(COMPILED_DIR, note_id, ".md") or (COMPILED_DIR / compiled_filename_from_metadata(metadata))


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
        "source": metadata.get("source", "voicenotes"),
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
        "thread_id": metadata.get("thread_id"),
        "continuation_of": metadata.get("continuation_of"),
        "related_note_ids": metadata.get("related_note_ids", []),
        "summary_available": metadata.get("summary_available", False),
        "summary_source": metadata.get("summary_source"),
        "audio_available": metadata.get("audio_available", False),
        "audio_local_path": metadata.get("audio_local_path"),
        "classification_basis": metadata.get("classification_basis", []),
        "derived_outputs": metadata.get("derived_outputs", []),
        "canonical_path": str(note_path),
        "raw_payload_path": metadata.get("raw_payload_path"),
        "compiled_at": iso_now(),
        "compiled_version": 1,
        "compiled_from_path": str(note_path),
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


def compile_command(args: argparse.Namespace) -> int:
    ensure_layout()
    note_filter = set(args.note_ids or [])
    written = 0
    updated = 0
    skipped = 0
    for note_path in list_markdown_files(NORMALIZED_DIR):
        metadata, body = read_note(note_path)
        metadata = ensure_note_metadata_defaults(metadata)
        source_note_id = str(metadata.get("source_note_id") or "")
        if note_filter and source_note_id not in note_filter:
            skipped += 1
            continue
        if metadata.get("status") == "dispatched":
            skipped += 1
            continue
        artifact_path, artifact_metadata, artifact_body = compile_note_artifact(metadata, body, note_path)
        packet = load_decision_packet(source_note_id)
        packet.setdefault("source_note_id", source_note_id)
        packet.setdefault("canonical_path", str(note_path))
        packet.setdefault("title", metadata.get("title"))
        if artifact_path.exists():
            existing_metadata, existing_body = read_note(artifact_path)
            preserved_compiled_at = existing_metadata.get("compiled_at")
            artifact_metadata["compiled_at"] = preserved_compiled_at or artifact_metadata["compiled_at"]
            if existing_metadata == artifact_metadata and existing_body == artifact_body:
                packet["compiled"] = {
                    "path": str(artifact_path),
                    "compiled_at": artifact_metadata.get("compiled_at"),
                    "brief_summary": artifact_metadata.get("brief_summary"),
                    "entities": artifact_metadata.get("entities", []),
                    "tasks": artifact_metadata.get("tasks", []),
                    "decisions": artifact_metadata.get("decisions", []),
                    "open_questions": artifact_metadata.get("open_questions", []),
                    "ambiguities": artifact_metadata.get("ambiguities", []),
                }
                save_decision_packet(packet)
                skipped += 1
                continue
            artifact_metadata["compiled_at"] = iso_now()
            write_note(artifact_path, artifact_metadata, artifact_body)
            packet["compiled"] = {
                "path": str(artifact_path),
                "compiled_at": artifact_metadata.get("compiled_at"),
                "brief_summary": artifact_metadata.get("brief_summary"),
                "entities": artifact_metadata.get("entities", []),
                "tasks": artifact_metadata.get("tasks", []),
                "decisions": artifact_metadata.get("decisions", []),
                "open_questions": artifact_metadata.get("open_questions", []),
                "ambiguities": artifact_metadata.get("ambiguities", []),
            }
            save_decision_packet(packet)
            updated += 1
            continue
        write_note(artifact_path, artifact_metadata, artifact_body)
        packet["compiled"] = {
            "path": str(artifact_path),
            "compiled_at": artifact_metadata.get("compiled_at"),
            "brief_summary": artifact_metadata.get("brief_summary"),
            "entities": artifact_metadata.get("entities", []),
            "tasks": artifact_metadata.get("tasks", []),
            "decisions": artifact_metadata.get("decisions", []),
            "open_questions": artifact_metadata.get("open_questions", []),
            "ambiguities": artifact_metadata.get("ambiguities", []),
        }
        save_decision_packet(packet)
        written += 1
    print(json.dumps({"compiled_written": written, "compiled_updated": updated, "skipped": skipped, "note_ids": sorted(note_filter)}, indent=2, ensure_ascii=False))
    return 0


def compiled_artifact_state(metadata: dict[str, Any], body: str) -> tuple[Path, bool, dict[str, Any] | None, str | None]:
    path = compiled_note_path(metadata)
    if not path.exists():
        return path, False, None, None
    compiled_metadata, _ = read_note(path)
    current_signature = canonical_compile_signature(metadata, body)
    is_fresh = compiled_metadata.get("compiled_from_signature") == current_signature
    return path, is_fresh, compiled_metadata, current_signature


def normalize_command(_: argparse.Namespace) -> int:
    ensure_layout()
    written = 0
    updated = 0
    skipped = 0
    for raw_file in list_raw_files(RAW_DIR):
        raw_payload, raw_format = load_raw_recording(raw_file)
        recording = raw_payload.get("recording") or {}
        note_id = recording.get("id") or recording.get("uuid")
        if not note_id:
            skipped += 1
            continue

        normalized_path, metadata, body = normalized_note_from_raw(raw_file, raw_payload, raw_format)
        if normalized_path.exists():
            existing_metadata, existing_body = read_note(normalized_path)
            merged_metadata = merge_normalized_metadata(existing_metadata, metadata)
            if merged_metadata == existing_metadata and body == existing_body:
                skipped += 1
                continue
            write_note(normalized_path, merged_metadata, body)
            updated += 1
            continue

        write_note(normalized_path, metadata, body)
        written += 1

    print(json.dumps({"normalized_written": written, "normalized_updated": updated, "skipped": skipped}, indent=2))
    return 0


def slugify(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:60]


def note_id_from_metadata(path: Path, metadata: dict[str, Any]) -> str:
    return require_valid_note_id(metadata.get("source_note_id") or path.stem)


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


def route_note(body: str, metadata: dict[str, Any], defaults: dict[str, Any], projects: dict[str, ProjectRule]) -> tuple[str, dict[str, float], str]:
    routing_parts = [
        str(metadata.get("title") or ""),
        " ".join(str(tag) for tag in metadata.get("tags", [])),
        " ".join(str(tag) for tag in metadata.get("user_keywords", [])),
        " ".join(str(tag) for tag in metadata.get("inferred_keywords", [])),
    ]
    if metadata.get("capture_kind") not in {"meeting_recording", "meeting_summary"}:
        routing_parts.append(body_excerpt(body, limit=600))
    combined = " ".join(filter(None, routing_parts)).lower()
    score_map: dict[str, float] = {}
    for key, project in projects.items():
        hits = 0
        for keyword in project.keywords:
            if keyword.lower() in combined:
                hits += 1
        if hits:
            score_map[key] = float(hits)

    if not score_map:
        return "pending_project", {}, "No configured project keywords matched this note. Keep it pending until a project or routing rule exists."

    ranked = sorted(score_map.items(), key=lambda item: item[1], reverse=True)
    top_project, top_score = ranked[0]
    min_keyword_hits = int(defaults.get("min_keyword_hits", 2))
    if top_score < min_keyword_hits:
        return "needs_review", score_map, "Some keywords matched, but not enough evidence to route safely."

    ties = [project for project, score in ranked if score == top_score]
    if len(ties) > 1:
        return "ambiguous", score_map, f"Multiple projects matched equally: {', '.join(ties)}."

    total = sum(score_map.values())
    confidence = round(top_score / total if total else 0.0, 2)
    basis = str(metadata.get("capture_kind") or "note")
    reason = f"Matched {int(top_score)} routing keywords for {top_project} using {basis} signals."
    return top_project, {"confidence": confidence, **score_map}, reason


def triage_command(args: argparse.Namespace) -> int:
    ensure_layout()
    defaults, projects = load_registry()
    triaged = 0
    for note_path in list_markdown_files(NORMALIZED_DIR):
        metadata, body = read_note(note_path)
        metadata = ensure_note_metadata_defaults(metadata)
        if metadata.get("status") == "dispatched":
            continue

        metadata["inferred_keywords"] = extract_keywords(metadata, body)
        metadata = enrich_note_metadata(metadata, body)
        previous_status = metadata.get("status")
        previous_project = metadata.get("project")
        previous_review_status = metadata.get("review_status")
        route, details, reason = route_note(body, metadata, defaults, projects)
        score_map = {k: v for k, v in details.items() if k != "confidence"}
        confidence = float(details.get("confidence", 0.0))
        metadata["candidate_projects"] = sorted(score_map, key=score_map.get, reverse=True)
        metadata["routing_reason"] = reason
        metadata["confidence"] = confidence
        metadata["destination"] = route
        metadata["destination_reason"] = reason

        preserve_manual_review = False
        if route in ("ambiguous", "needs_review", "pending_project"):
            preserve_manual_review = previous_status == route and previous_review_status not in (None, "pending")
        else:
            preserve_manual_review = previous_status == "classified" and previous_project == route and previous_review_status not in (None, "pending")

        if preserve_manual_review:
            metadata["review_status"] = previous_review_status
            metadata["requires_user_confirmation"] = previous_review_status != "approved"
        else:
            metadata["review_status"] = "pending"
            metadata["requires_user_confirmation"] = True

        if route in ("ambiguous", "needs_review", "pending_project"):
            metadata["status"] = route
            metadata["project"] = None
            metadata["intent"] = classify_intent(metadata)
            metadata.pop("note_type", None)
            write_note(note_path, metadata, body)
            remove_review_copies(note_path.name)
            if route == "ambiguous":
                target_dir = AMBIGUOUS_DIR
            elif route == "pending_project":
                target_dir = PENDING_PROJECT_DIR
            else:
                target_dir = NEEDS_REVIEW_DIR
            write_note(target_dir / note_path.name, metadata, body)
        else:
            metadata["status"] = "classified"
            metadata["project"] = route
            metadata["note_type"] = projects[route].note_type
            metadata["intent"] = classify_intent(metadata)
            write_note(note_path, metadata, body)
            remove_review_copies(note_path.name)
        save_decision_packet(build_decision_packet(note_path, metadata, body, route=route, details=details, reason=reason))
        triaged += 1

    print(json.dumps({"triaged": triaged, "mode": "all" if args.all else "default"}, indent=2))
    return 0


def build_dispatch_note(
    metadata: dict[str, Any],
    compiled_metadata: dict[str, Any],
    compiled_body: str,
    project: ProjectRule,
    canonical_path: Path,
    compiled_path: Path,
) -> tuple[str, str]:
    title = metadata.get("title") or compiled_metadata.get("title") or f"VoiceNotes {metadata.get('source_note_id')}"
    dispatch_metadata = {
        "source": "voicenotes",
        "source_note_id": metadata.get("source_note_id"),
        "created_at": metadata.get("created_at"),
        "project": project.key,
        "classification": metadata.get("note_type", project.note_type),
        "capture_kind": metadata.get("capture_kind"),
        "intent": metadata.get("intent"),
        "confidence": metadata.get("confidence"),
        "user_keywords": metadata.get("user_keywords", []),
        "inferred_keywords": metadata.get("inferred_keywords", []),
        "thread_id": metadata.get("thread_id"),
        "continuation_of": metadata.get("continuation_of"),
        "related_note_ids": metadata.get("related_note_ids", []),
        "status": "por_triar" if project.language.lower() == "pt-pt" else "to_review",
        "canonical_path": str(canonical_path),
        "compiled_path": str(compiled_path),
        "raw_payload_path": metadata.get("raw_payload_path"),
        "tags": metadata.get("tags", []),
        "compiled_at": compiled_metadata.get("compiled_at"),
        "brief_summary": compiled_metadata.get("brief_summary"),
        "entities": compiled_metadata.get("entities", []),
        "facts": compiled_metadata.get("facts", []),
        "tasks": compiled_metadata.get("tasks", []),
        "decisions": compiled_metadata.get("decisions", []),
        "open_questions": compiled_metadata.get("open_questions", []),
        "follow_ups": compiled_metadata.get("follow_ups", []),
        "timeline": compiled_metadata.get("timeline", []),
        "ambiguities": compiled_metadata.get("ambiguities", []),
        "confidence_by_field": compiled_metadata.get("confidence_by_field", {}),
        "evidence_spans": compiled_metadata.get("evidence_spans", []),
    }
    return title, frontmatter_text(dispatch_metadata, compiled_body)


def frontmatter_text(metadata: dict[str, Any], body: str) -> str:
    rendered = [f"{key}: {dump_value(value)}" for key, value in metadata.items()]
    return f"---\n" + "\n".join(rendered) + f"\n---\n\n{body.rstrip()}\n"


def dispatch_filename(metadata: dict[str, Any], title: str) -> str:
    created = str(metadata.get("created_at") or "unknown-time").replace(":", "").replace("-", "")
    note_id = require_valid_note_id(metadata.get("source_note_id"))
    return f"{created}--{note_id}.md"


def resolve_dispatch_destination(project: ProjectRule, metadata: dict[str, Any]) -> tuple[Path | None, str | None]:
    if project.inbox_path is None:
        return None, f"no local inbox_path for project '{project.key}'"

    try:
        ensure_safe_inbox_path(project.inbox_path, project_key=project.key, registry_path=REGISTRY_LOCAL_PATH)
    except SystemExit as exc:
        return None, str(exc)

    title = metadata.get("title") or f"VoiceNotes {metadata.get('source_note_id')}"
    return project.inbox_path / dispatch_filename(metadata, title), None


def dispatch_command(args: argparse.Namespace) -> int:
    ensure_layout()
    _, projects = load_registry(require_local=True)
    dispatched = 0
    skipped = 0
    candidates: list[dict[str, Any]] = []
    approved_note_ids = set(args.note_ids or [])

    if args.confirm_user_approval and not approved_note_ids:
        raise SystemExit("Real dispatch requires at least one --note-id after the user confirms those exact notes.")

    for note_path in list_markdown_files(NORMALIZED_DIR):
        metadata, body = read_note(note_path)
        project_key = metadata.get("project")
        if metadata.get("status") != "classified" or not project_key:
            skipped += 1
            continue
        if metadata.get("review_status") != "approved":
            skipped += 1
            continue

        project = projects.get(project_key)
        if not project:
            skipped += 1
            continue

        source_note_id = require_valid_note_id(metadata.get("source_note_id"))
        compiled_path, compiled_fresh, compiled_metadata, _ = compiled_artifact_state(metadata, body)
        compiled_ready = compiled_metadata is not None
        destination, destination_error = resolve_dispatch_destination(project, metadata)
        mirror_path = DISPATCHED_DIR / project.key / destination.name if destination is not None else None
        candidates.append(
            {
                "note": str(note_path),
                "source_note_id": source_note_id,
                "compiled_path": str(compiled_path),
                "compiled_ready": compiled_ready,
                "compiled_fresh": compiled_fresh,
                "destination": str(destination) if destination is not None else None,
                "project": project.key,
                "confidence": metadata.get("confidence"),
                "review_status": metadata.get("review_status"),
                "skip_reason": destination_error,
            }
        )

        if destination_error is not None:
            skipped += 1
            continue
        if not compiled_ready:
            candidates[-1]["skip_reason"] = "compiled package missing"
            skipped += 1
            continue
        if not compiled_fresh:
            candidates[-1]["skip_reason"] = "compiled package is stale"
            skipped += 1
            continue

        if args.dry_run:
            dispatched += 1
            continue

        if not args.confirm_user_approval:
            candidates[-1]["skip_reason"] = "user confirmation required"
            continue
        if source_note_id not in approved_note_ids:
            candidates[-1]["skip_reason"] = "source_note_id not included in approved allowlist"
            skipped += 1
            continue

        assert compiled_metadata is not None
        assert destination is not None
        assert mirror_path is not None
        _, compiled_body = read_note(compiled_path)
        title, content = build_dispatch_note(metadata, compiled_metadata, compiled_body, project, note_path, compiled_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        mirror_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(destination, mirror_path)

        metadata["status"] = "dispatched"
        metadata["dispatched_at"] = "manual-run"
        metadata["dispatched_to"] = [str(destination)]
        metadata["requires_user_confirmation"] = False
        write_note(note_path, metadata, body)
        packet = load_decision_packet(source_note_id)
        packet.setdefault("source_note_id", source_note_id)
        packet.setdefault("canonical_path", str(note_path))
        packet.setdefault("title", metadata.get("title"))
        packet.setdefault("created_at", metadata.get("created_at"))
        packet["dispatch"] = {
            "destination": str(destination),
            "dispatched_at": metadata["dispatched_at"],
            "compiled_path": str(compiled_path),
        }
        save_decision_packet(packet)
        dispatched += 1

    summary = {
        "candidates": candidates,
        "dispatched": dispatched if args.confirm_user_approval else 0 if not args.dry_run else dispatched,
        "skipped": skipped,
        "dry_run": args.dry_run,
        "confirmation_required": not args.dry_run and not args.confirm_user_approval,
        "approved_note_ids": sorted(approved_note_ids),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def pending_project_notes() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for note_path in list_markdown_files(NORMALIZED_DIR):
        metadata, body = read_note(note_path)
        metadata = ensure_note_metadata_defaults(metadata)
        if metadata.get("status") != "pending_project":
            continue
        if not metadata.get("inferred_keywords"):
            metadata["inferred_keywords"] = extract_keywords(metadata, body)
            write_note(note_path, metadata, body)
        if not metadata.get("capture_kind"):
            metadata = enrich_note_metadata(metadata, body)
            write_note(note_path, metadata, body)
        review_path = PENDING_PROJECT_DIR / note_path.name
        review_metadata, review_body = read_note(review_path) if review_path.exists() else ({}, "")
        if not review_path.exists() or review_metadata != metadata or review_body != body:
            write_note(review_path, metadata, body)
        items.append(
            {
                "note_path": note_path,
                "review_path": review_path,
                "metadata": metadata,
                "body": body,
                "keywords": sorted(note_keyword_set(metadata)),
                "created_dt": parse_note_datetime(str(metadata.get("created_at") or metadata.get("recorded_at") or "")),
            }
        )
    return items


def cluster_pending_notes(items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    remaining = list(range(len(items)))
    clusters: list[list[dict[str, Any]]] = []

    while remaining:
        seed_index = remaining.pop(0)
        cluster_indexes = [seed_index]
        changed = True
        while changed:
            changed = False
            for candidate_index in remaining[:]:
                for existing_index in cluster_indexes:
                    score, _ = relationship_score(items[candidate_index]["metadata"], items[existing_index]["metadata"])
                    if score >= 2:
                        cluster_indexes.append(candidate_index)
                        remaining.remove(candidate_index)
                        changed = True
                        break
        clusters.append([items[index] for index in cluster_indexes])

    clusters.sort(key=lambda cluster: (-len(cluster), str(cluster[0]["metadata"].get("created_at") or "")))
    return clusters


def cluster_keywords(cluster: list[dict[str, Any]]) -> list[str]:
    counter: Counter[str] = Counter()
    for item in cluster:
        for keyword in item["keywords"]:
            counter[keyword] += 1
    return [keyword for keyword, _ in counter.most_common(6)]


def cluster_relationship_suggestions(cluster: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(cluster, key=note_sort_key)
    suggestions: list[dict[str, Any]] = []
    for index in range(1, len(ordered)):
        current = ordered[index]
        previous = ordered[index - 1]
        score, shared_keywords = relationship_score(current["metadata"], previous["metadata"])
        if score < 2:
            continue
        suggestions.append(
            {
                "source_note_id": current["metadata"].get("source_note_id"),
                "possible_continuation_of": previous["metadata"].get("source_note_id"),
                "shared_keywords": shared_keywords,
            }
        )
    return suggestions


def discover_command(_: argparse.Namespace) -> int:
    ensure_layout()
    items = pending_project_notes()
    ignored_items = [item for item in items if is_system_note(item["metadata"], item["body"])]
    candidate_items = [item for item in items if not is_system_note(item["metadata"], item["body"])]
    clusters = cluster_pending_notes(candidate_items)
    report_clusters = []
    singleton_notes = []
    cluster_index = 0
    for cluster in clusters:
        if len(cluster) < 2:
            item = cluster[0]
            singleton_notes.append(
                {
                    "source_note_id": item["metadata"].get("source_note_id"),
                    "title": item["metadata"].get("title"),
                    "capture_kind": item["metadata"].get("capture_kind"),
                    "intent": item["metadata"].get("intent"),
                    "keywords": item["keywords"],
                    "normalized_path": str(item["note_path"]),
                    "review_path": str(item["review_path"]) if item["review_path"].exists() else None,
                    "decision_packet_path": str(decision_packet_path(str(item["metadata"].get("source_note_id")))),
                }
            )
            continue
        cluster_index += 1
        keywords = cluster_keywords(cluster)
        bucket = format_discovery_bucket(keywords)
        report_clusters.append(
            {
                "cluster_id": f"pending-{cluster_index}",
                "suggested_bucket": bucket,
                "suggested_keywords": keywords,
                "note_count": len(cluster),
                "suggested_relationships": cluster_relationship_suggestions(cluster),
                "notes": [
                    {
                        "source_note_id": item["metadata"].get("source_note_id"),
                        "title": item["metadata"].get("title"),
                        "created_at": item["metadata"].get("created_at"),
                        "capture_kind": item["metadata"].get("capture_kind"),
                        "intent": item["metadata"].get("intent"),
                        "keywords": item["keywords"],
                        "normalized_path": str(item["note_path"]),
                        "review_path": str(item["review_path"]) if item["review_path"].exists() else None,
                        "decision_packet_path": str(decision_packet_path(str(item["metadata"].get("source_note_id")))),
                    }
                    for item in sorted(cluster, key=note_sort_key)
                ],
            }
        )

    report = {
        "generated_at": iso_now(),
        "pending_project_notes": len(items),
        "ignored_system_notes": [
            {
                "source_note_id": item["metadata"].get("source_note_id"),
                "title": item["metadata"].get("title"),
                "normalized_path": str(item["note_path"]),
            }
            for item in sorted(ignored_items, key=note_sort_key)
        ],
        "clusters": report_clusters,
        "singleton_notes": sorted(singleton_notes, key=lambda item: item["source_note_id"] or ""),
    }
    DISCOVERY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DISCOVERY_REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def review_command(args: argparse.Namespace) -> int:
    ensure_layout()
    packets = sorted(DECISIONS_DIR.glob("*.json"))
    if args.note_id:
        packet_path = decision_packet_path(args.note_id)
        packet = load_decision_packet(args.note_id)
        if not packet or "source_note_id" not in packet:
            raise SystemExit(f"No decision packet found for {args.note_id}.")
        print(json.dumps(build_review_entry(packet, packet_path), indent=2, ensure_ascii=False))
        return 0

    output = []
    for path in packets:
        packet = json.loads(path.read_text(encoding="utf-8"))
        entry = build_review_entry(packet, path)
        if not args.all and entry.get("review_status") != "pending" and entry.get("action") not in {"compile_required", "recompile_required"}:
            continue
        output.append(entry)
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


def build_review_entry(packet: dict[str, Any], packet_path: Path) -> dict[str, Any]:
    proposal = packet.get("proposal", {})
    compiled = packet.get("compiled") or {}
    note_metadata: dict[str, Any] = {}
    note_body = ""
    canonical_path = packet.get("canonical_path")
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
    compiled_path = compiled.get("path") or (str(compiled_note_path(note_metadata)) if canonical_path else None)
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
    }


def _raw_payload_path_from_packet(packet: dict[str, Any]) -> str | None:
    canonical_path = packet.get("canonical_path")
    if not canonical_path:
        return None
    normalized_path = Path(canonical_path)
    note_id = packet.get("source_note_id")
    if not note_id:
        return None
    prefix = normalized_path.stem.rsplit("--", 1)[0]
    return str(RAW_DIR / f"{prefix}--{note_id}.json")


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


def decide_command(args: argparse.Namespace) -> int:
    ensure_layout()
    defaults, projects = load_registry()
    note_path = None
    metadata = None
    body = None
    for candidate_path in list_markdown_files(NORMALIZED_DIR):
        candidate_metadata, candidate_body = read_note(candidate_path)
        if str(candidate_metadata.get("source_note_id")) == args.note_id:
            note_path = candidate_path
            metadata = candidate_metadata
            body = candidate_body
            break
    if note_path is None or metadata is None or body is None:
        raise SystemExit(f"No normalized note found for {args.note_id}.")

    metadata = ensure_note_metadata_defaults(metadata)
    apply_note_annotations(metadata, args, args.note_id)
    decision = args.decision
    final_project = args.final_project or metadata.get("project")
    if decision == "approve":
        if not final_project:
            raise SystemExit("Approve requires a project on the note or via --final-project.")
        if final_project not in projects:
            raise SystemExit(f"Unknown project '{final_project}'.")
        metadata["status"] = "classified"
        metadata["project"] = final_project
        metadata["destination"] = final_project
        metadata["note_type"] = args.final_type or metadata.get("note_type") or projects[final_project].note_type
        metadata["review_status"] = "approved"
        metadata["requires_user_confirmation"] = False
        metadata["intent"] = classify_intent(metadata)
        remove_review_copies(note_path.name)
    elif decision == "ambiguous":
        metadata["status"] = "ambiguous"
        metadata["project"] = None
        metadata["destination"] = "ambiguous"
        metadata.pop("note_type", None)
        metadata["review_status"] = "ambiguous"
        metadata["requires_user_confirmation"] = True
        metadata["intent"] = classify_intent(metadata)
        remove_review_copies(note_path.name)
        write_note(AMBIGUOUS_DIR / note_path.name, metadata, body)
    elif decision == "pending-project":
        metadata["status"] = "pending_project"
        metadata["project"] = None
        metadata["destination"] = "pending_project"
        metadata.pop("note_type", None)
        metadata["review_status"] = "pending_project"
        metadata["requires_user_confirmation"] = True
        metadata["intent"] = classify_intent(metadata)
        remove_review_copies(note_path.name)
        write_note(PENDING_PROJECT_DIR / note_path.name, metadata, body)
    else:
        metadata["status"] = "needs_review"
        metadata["project"] = None
        metadata["destination"] = "needs_review"
        metadata.pop("note_type", None)
        metadata["review_status"] = decision.replace("-", "_")
        metadata["requires_user_confirmation"] = True
        metadata["intent"] = classify_intent(metadata)
        remove_review_copies(note_path.name)
        write_note(NEEDS_REVIEW_DIR / note_path.name, metadata, body)

    write_note(note_path, metadata, body)

    packet = load_decision_packet(args.note_id)
    packet.setdefault("reviews", [])
    packet.setdefault("source_note_id", args.note_id)
    packet.setdefault("canonical_path", str(note_path))
    packet.setdefault("title", metadata.get("title"))
    packet.setdefault("created_at", metadata.get("created_at"))
    packet["reviews"].append(
        {
            "reviewed_at": iso_now(),
            "decision": decision,
            "final_project": final_project if decision == "approve" else None,
            "final_type": metadata.get("note_type") if decision == "approve" else None,
            "thread_id": metadata.get("thread_id"),
            "continuation_of": metadata.get("continuation_of"),
            "related_note_ids": metadata.get("related_note_ids", []),
            "user_keywords": metadata.get("user_keywords", []),
            "notes": args.notes or "",
        }
    )
    packet["final_decision"] = packet["reviews"][-1]
    packet["proposal"] = build_decision_packet(note_path, metadata, body, route=str(metadata.get("project") or metadata.get("status")), details={}, reason=str(metadata.get("routing_reason") or "")).get("proposal", {})
    save_decision_packet(packet)

    print(
        json.dumps(
            {
                "source_note_id": args.note_id,
                "decision": decision,
                "status": metadata.get("status"),
                "project": metadata.get("project"),
                "review_status": metadata.get("review_status"),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def count_markdown(path: Path) -> int:
    return len(list_markdown_files(path))


def count_raw(path: Path) -> int:
    return len(list_raw_files(path))


def status_command(_: argparse.Namespace) -> int:
    ensure_layout()
    summary = {
        "raw": count_raw(RAW_DIR),
        "normalized": count_markdown(NORMALIZED_DIR),
        "compiled": count_markdown(COMPILED_DIR),
        "review_ambiguous": count_markdown(AMBIGUOUS_DIR),
        "review_pending_project": count_markdown(PENDING_PROJECT_DIR),
        "review_needs_review": count_markdown(NEEDS_REVIEW_DIR),
        "dispatched": sum(count_markdown(path) for path in DISPATCHED_DIR.glob("*") if path.is_dir()),
        "processed": count_markdown(PROCESSED_DIR),
        "decision_packets": len(list(DECISIONS_DIR.glob("*.json"))),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize = subparsers.add_parser("normalize", help="Copy raw notes into canonical normalized notes.")
    normalize.set_defaults(func=normalize_command)

    triage = subparsers.add_parser("triage", help="Classify normalized notes conservatively.")
    triage.add_argument("--all", action="store_true", help="Reserved flag for future filtering.")
    triage.set_defaults(func=triage_command)

    compile_parser = subparsers.add_parser("compile", help="Generate project-ready compiled note packages from canonical notes.")
    compile_parser.add_argument("--note-id", dest="note_ids", action="append", help="Compile only the selected source_note_id values.")
    compile_parser.set_defaults(func=compile_command)

    dispatch = subparsers.add_parser("dispatch", help="Preview or manually write classified notes to downstream project inboxes.")
    dispatch.add_argument("--dry-run", action="store_true", help="Show planned writes without touching downstream projects.")
    dispatch.add_argument("--note-id", dest="note_ids", action="append", help="Explicit source_note_id allowlist for real dispatch.")
    dispatch.add_argument(
        "--confirm-user-approval",
        action="store_true",
        help="Required for real writes after the user explicitly confirms the dispatch.",
    )
    dispatch.set_defaults(func=dispatch_command)

    review = subparsers.add_parser("review", help="List or inspect decision packets.")
    review.add_argument("--all", action="store_true", help="Include already reviewed packets.")
    review.add_argument("--note-id", help="Show the full decision packet for one source_note_id.")
    review.set_defaults(func=review_command)

    discover = subparsers.add_parser("discover", help="Analyze pending-project notes and suggest emerging buckets.")
    discover.set_defaults(func=discover_command)

    decide = subparsers.add_parser("decide", help="Record the user's review decision for one note.")
    decide.add_argument("--note-id", required=True, help="source_note_id to review.")
    decide.add_argument("--decision", required=True, choices=("approve", "reject", "needs-review", "ambiguous", "pending-project"))
    decide.add_argument("--final-project", help="Override the final project when approving.")
    decide.add_argument("--final-type", help="Override the final note type when approving.")
    decide.add_argument("--user-keyword", dest="user_keywords", action="append", help="Add a curated keyword to the note metadata.")
    decide.add_argument("--related-note-id", dest="related_note_ids", action="append", help="Link another note as related context.")
    decide.add_argument("--thread-id", help="Assign or override the note thread identifier.")
    decide.add_argument("--continuation-of", help="Mark this note as a continuation of another source_note_id.")
    decide.add_argument("--notes", help="Optional reviewer note.")
    decide.set_defaults(func=decide_command)

    status = subparsers.add_parser("status", help="Show queue counts.")
    status.set_defaults(func=status_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    load_local_env()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
