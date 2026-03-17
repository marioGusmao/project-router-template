"""Minimal CLI for Project Router for VoiceNotes."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
import shutil
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
NORMALIZED_DIR = DATA_DIR / "normalized"
COMPILED_DIR = DATA_DIR / "compiled"
REVIEW_DIR = DATA_DIR / "review"
DISPATCHED_DIR = DATA_DIR / "dispatched"
PROCESSED_DIR = DATA_DIR / "processed"
STATE_DIR = ROOT / "state"
DECISIONS_DIR = STATE_DIR / "decisions"
DISCOVERIES_DIR = STATE_DIR / "discoveries"
PROJECT_ROUTER_STATE_DIR = STATE_DIR / "project_router"
OUTBOX_SCAN_STATE_PATH = PROJECT_ROUTER_STATE_DIR / "outbox_scan_state.json"
OUTBOX_SCAN_LOCK_PATH = PROJECT_ROUTER_STATE_DIR / "scan.lock"
REGISTRY_LOCAL_PATH = ROOT / "projects" / "registry.local.json"
REGISTRY_SHARED_PATH = ROOT / "projects" / "registry.shared.json"
REGISTRY_EXAMPLE_PATH = ROOT / "projects" / "registry.example.json"
ENV_LOCAL_PATH = ROOT / ".env.local"
ENV_PATH = ROOT / ".env"
DISCOVERY_REPORT_PATH = DISCOVERIES_DIR / "pending_project_latest.json"
LOCAL_ROUTER_DIR = ROOT / "router"
LOCAL_ROUTER_ARCHIVE_DIR = LOCAL_ROUTER_DIR / "archive"
INBOX_STATUS_DIR = PROJECT_ROUTER_STATE_DIR / "inbox_status"
NOTE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
VOICE_SOURCE = "voicenotes"
PROJECT_ROUTER_SOURCE = "project_router"
FILESYSTEM_SOURCE = "filesystem"
KNOWN_SOURCES = frozenset({VOICE_SOURCE, PROJECT_ROUTER_SOURCE, FILESYSTEM_SOURCE})
REVIEW_QUEUE_STATUSES = ("ambiguous", "needs_review", "pending_project")
FILESYSTEM_REVIEW_STATUSES = ("parse_errors", "needs_extraction", "needs_review", "ambiguous", "pending_project")
AMBIGUOUS_DIR = REVIEW_DIR / VOICE_SOURCE / "ambiguous"
NEEDS_REVIEW_DIR = REVIEW_DIR / VOICE_SOURCE / "needs_review"
PENDING_PROJECT_DIR = REVIEW_DIR / VOICE_SOURCE / "pending_project"

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
    router_root_path: Path | None
    note_type: str
    keywords: list[str]


def ensure_layout() -> None:
    for path in (
        RAW_DIR / VOICE_SOURCE,
        RAW_DIR / PROJECT_ROUTER_SOURCE,
        RAW_DIR / FILESYSTEM_SOURCE / "default" / "manifests",
        RAW_DIR / FILESYSTEM_SOURCE / "default" / "artifacts",
        NORMALIZED_DIR / VOICE_SOURCE,
        NORMALIZED_DIR / PROJECT_ROUTER_SOURCE,
        NORMALIZED_DIR / FILESYSTEM_SOURCE,
        COMPILED_DIR / VOICE_SOURCE,
        COMPILED_DIR / PROJECT_ROUTER_SOURCE,
        COMPILED_DIR / FILESYSTEM_SOURCE,
        REVIEW_DIR / VOICE_SOURCE / "ambiguous",
        REVIEW_DIR / VOICE_SOURCE / "needs_review",
        REVIEW_DIR / VOICE_SOURCE / "pending_project",
        REVIEW_DIR / PROJECT_ROUTER_SOURCE / "parse_errors",
        REVIEW_DIR / PROJECT_ROUTER_SOURCE / "needs_review",
        REVIEW_DIR / PROJECT_ROUTER_SOURCE / "pending_project",
        REVIEW_DIR / FILESYSTEM_SOURCE / "parse_errors",
        REVIEW_DIR / FILESYSTEM_SOURCE / "needs_extraction",
        REVIEW_DIR / FILESYSTEM_SOURCE / "needs_review",
        REVIEW_DIR / FILESYSTEM_SOURCE / "ambiguous",
        REVIEW_DIR / FILESYSTEM_SOURCE / "pending_project",
        DISPATCHED_DIR,
        PROCESSED_DIR,
        DECISIONS_DIR,
        DISCOVERIES_DIR,
        PROJECT_ROUTER_STATE_DIR,
        INBOX_STATUS_DIR,
        LOCAL_ROUTER_ARCHIVE_DIR,
        STATE_DIR / "filesystem_ingest",
    ):
        path.mkdir(parents=True, exist_ok=True)


def normalize_source_name(raw: str | None) -> str | None:
    if raw is None:
        return None
    cleaned = str(raw).strip().lower()
    aliases = {
        "voice_notes": VOICE_SOURCE,
        "voice-notes": VOICE_SOURCE,
        "project-router": PROJECT_ROUTER_SOURCE,
        "filesystem": FILESYSTEM_SOURCE,
        "fs": FILESYSTEM_SOURCE,
        "local-inbox": FILESYSTEM_SOURCE,
        "inbox": FILESYSTEM_SOURCE,
    }
    return aliases.get(cleaned, cleaned)


def parse_source_filter(raw: str | None) -> set[str]:
    source = normalize_source_name(raw)
    if source is None or source in {"all", "*"}:
        return set(KNOWN_SOURCES)
    if source not in KNOWN_SOURCES:
        raise SystemExit(f"Unsupported --source '{raw}'. Use one of: {', '.join(sorted(KNOWN_SOURCES))}, all.")
    return {source}


def source_project_key(metadata: dict[str, Any]) -> str | None:
    value = metadata.get("source_project")
    if value in (None, "", "null"):
        return None
    return str(value)


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


def raw_dir_for(source: str, source_project: str | None = None) -> Path:
    source = normalize_source_name(source) or source
    if source == VOICE_SOURCE:
        return RAW_DIR / VOICE_SOURCE
    if source == PROJECT_ROUTER_SOURCE:
        if not source_project:
            raise SystemExit("project_router artifacts require source_project.")
        return RAW_DIR / PROJECT_ROUTER_SOURCE / source_project
    if source == FILESYSTEM_SOURCE:
        return RAW_DIR / FILESYSTEM_SOURCE
    raise SystemExit(f"Unsupported source '{source}'.")


def normalized_dir_for(source: str, source_project: str | None = None) -> Path:
    source = normalize_source_name(source) or source
    if source == VOICE_SOURCE:
        return NORMALIZED_DIR / VOICE_SOURCE
    if source == PROJECT_ROUTER_SOURCE:
        if not source_project:
            raise SystemExit("project_router artifacts require source_project.")
        return NORMALIZED_DIR / PROJECT_ROUTER_SOURCE / source_project
    if source == FILESYSTEM_SOURCE:
        return NORMALIZED_DIR / FILESYSTEM_SOURCE
    raise SystemExit(f"Unsupported source '{source}'.")


def compiled_dir_for(source: str, source_project: str | None = None) -> Path:
    source = normalize_source_name(source) or source
    if source == VOICE_SOURCE:
        return COMPILED_DIR / VOICE_SOURCE
    if source == PROJECT_ROUTER_SOURCE:
        if not source_project:
            raise SystemExit("project_router artifacts require source_project.")
        return COMPILED_DIR / PROJECT_ROUTER_SOURCE / source_project
    if source == FILESYSTEM_SOURCE:
        return COMPILED_DIR / FILESYSTEM_SOURCE
    raise SystemExit(f"Unsupported source '{source}'.")


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


def outbox_path_for_project(project: ProjectRule) -> Path | None:
    if project.router_root_path is None:
        return None
    return project.router_root_path / "outbox"


def inbox_path_for_project(project: ProjectRule) -> Path | None:
    if project.router_root_path is not None:
        return project.router_root_path / "inbox"
    return project.inbox_path


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
    return output


def iter_raw_files_by_source(sources: set[str]) -> list[Path]:
    output: list[Path] = []
    non_fs_sources = sources - {FILESYSTEM_SOURCE}
    if non_fs_sources:
        for directory in iter_source_dirs("raw", non_fs_sources):
            output.extend(list_raw_files(directory))
    if FILESYSTEM_SOURCE in sources:
        output.extend(list_filesystem_manifests())
    return sorted(output)


def iter_normalized_files_by_source(sources: set[str]) -> list[Path]:
    output: list[Path] = []
    for directory in iter_source_dirs("normalized", sources):
        output.extend(list_markdown_files(directory))
    return sorted(output)


def iter_compiled_files_by_source(sources: set[str]) -> list[Path]:
    output: list[Path] = []
    for directory in iter_source_dirs("compiled", sources):
        output.extend(list_markdown_files(directory))
    return sorted(output)


def review_queue_directories(sources: set[str]) -> list[Path]:
    output: list[Path] = []
    if VOICE_SOURCE in sources:
        output.extend(review_dir_for(VOICE_SOURCE, status) for status in REVIEW_QUEUE_STATUSES)
    if PROJECT_ROUTER_SOURCE in sources:
        output.extend(review_dir_for(PROJECT_ROUTER_SOURCE, status) for status in ("parse_errors", "needs_review", "pending_project"))
    if FILESYSTEM_SOURCE in sources:
        output.extend(review_dir_for(FILESYSTEM_SOURCE, status) for status in FILESYSTEM_REVIEW_STATUSES)
    return output


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


def load_filesystem_inboxes(config: dict[str, Any]) -> dict[str, Path]:
    """Load filesystem inbox paths from the merged config sources section."""
    raw_inboxes = (config.get("sources") or {}).get("filesystem_inboxes") or {}
    result: dict[str, Path] = {}
    for key, entry in raw_inboxes.items():
        if not NOTE_ID_PATTERN.fullmatch(key):
            raise SystemExit(f"Filesystem inbox key '{key}' is invalid. Only letters, numbers, underscores, and hyphens are allowed.")
        if not isinstance(entry, dict):
            continue
        raw_path = entry.get("inbox_path")
        if not raw_path:
            continue
        path = Path(str(raw_path))
        if has_placeholder_path(path):
            continue
        if not path.is_absolute():
            raise SystemExit(f"Filesystem inbox '{key}' must use an absolute path.")
        if ".." in path.parts:
            raise SystemExit(f"Filesystem inbox '{key}' contains an unsafe path component.")
        result[key] = path
    return result


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
        sys.stderr.write(f"Warning: {path} has unclosed frontmatter. Treating as plain text.\n")
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
    for review_dir in review_queue_directories(KNOWN_SOURCES):
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


def generate_filesystem_note_id() -> str:
    """Generate an event-based note ID for filesystem ingestion."""
    import secrets

    ts = iso_now().replace("-", "").replace(":", "")
    suffix = secrets.token_hex(3)
    return f"fs_{ts}_{suffix}"


def compute_content_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file's contents."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def create_manifest(
    source_note_id: str,
    inbox_key: str,
    evidence: dict[str, Any],
    interpretation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "manifest_version": 1,
        "source": FILESYSTEM_SOURCE,
        "source_note_id": source_note_id,
        "inbox_key": inbox_key,
        "evidence": evidence,
        "interpretation": interpretation,
    }


def read_manifest(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise SystemExit(f"Failed to read manifest {path}: {exc}")


def update_manifest_interpretation(
    path: Path,
    interpretation: dict[str, Any],
    attempt_record: dict[str, Any],
) -> None:
    manifest = read_manifest(path)
    manifest["interpretation"] = interpretation
    manifest["evidence"].setdefault("extractor_attempts", []).append(attempt_record)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def find_manifest_by_content_hash(manifests_dir: Path, content_hash: str) -> Path | None:
    if not manifests_dir.exists():
        return None
    for f in manifests_dir.iterdir():
        if f.is_file() and f.name.endswith(".manifest.json"):
            try:
                m = json.loads(f.read_text(encoding="utf-8"))
                if m.get("evidence", {}).get("content_hash") == content_hash:
                    return f
            except (json.JSONDecodeError, OSError) as exc:
                print(f"warning: skipping unreadable manifest {f}: {exc}", file=sys.stderr)
                continue
    return None


def _ingest_state_dir(inbox_key: str) -> Path:
    return STATE_DIR / "filesystem_ingest" / inbox_key


def _read_ingest_state(inbox_key: str, note_id: str) -> dict[str, Any] | None:
    """Read ingest state for crash recovery. Returns None if missing or corrupt."""
    path = _ingest_state_dir(inbox_key) / f"{note_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_ingest_state(inbox_key: str, note_id: str, state: dict[str, Any]) -> None:
    state_dir = _ingest_state_dir(inbox_key)
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / f"{note_id}.json"
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def ingest_file(file_path: Path, inbox_key: str, inbox_path: Path) -> dict[str, Any]:
    """Ingest a single file into the filesystem pipeline. Returns summary dict."""
    from .extractors import extract as run_extractor

    content_hash = compute_content_hash(file_path)
    manifests_dir = RAW_DIR / FILESYSTEM_SOURCE / inbox_key / "manifests"
    artifacts_dir = RAW_DIR / FILESYSTEM_SOURCE / inbox_key / "artifacts"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    same_content_as: list[str] = []
    existing = find_manifest_by_content_hash(manifests_dir, content_hash)
    if existing is not None:
        try:
            existing_manifest = read_manifest(existing)
            same_content_as.append(existing_manifest.get("source_note_id", ""))
        except SystemExit:
            pass

    note_id = generate_filesystem_note_id()
    timestamp = iso_now()
    ts_prefix = normalize_timestamp(timestamp)
    ext = file_path.suffix

    def _state(status: str, *, error_code: str | None = None, error_detail: str | None = None,
               manifest_path_val: str | None = None, artifact_path_val: str | None = None,
               archive_status: str = "pending") -> dict[str, Any]:
        return {
            "first_seen_at": timestamp, "last_seen_at": iso_now(), "status": status,
            "manifest_path": manifest_path_val, "artifact_path": artifact_path_val,
            "archive_status": archive_status, "error_code": error_code,
            "error_detail": error_detail, "content_hash": content_hash,
        }

    _write_ingest_state(inbox_key, note_id, _state("ingesting"))

    blob_name = f"{ts_prefix}--{note_id}{ext}"
    blob_path = artifacts_dir / blob_name
    try:
        shutil.copy2(str(file_path), str(blob_path))
    except OSError as exc:
        _write_ingest_state(inbox_key, note_id, _state("error", error_code="blob_copy_failed", error_detail=str(exc)))
        raise

    try:
        result = run_extractor(blob_path)
    except (MemoryError, RecursionError):
        _write_ingest_state(inbox_key, note_id, _state("error", error_code="extraction_fatal", error_detail="MemoryError or RecursionError",
                                                         artifact_path_val=str(blob_path.relative_to(ROOT))))
        raise
    except Exception as exc:
        _write_ingest_state(inbox_key, note_id, _state("error", error_code="extraction_failed", error_detail=str(exc),
                                                         artifact_path_val=str(blob_path.relative_to(ROOT))))
        raise

    from datetime import datetime, timezone
    file_stat = file_path.stat()
    file_stat_dict = {
        "size_bytes": file_stat.st_size,
        "mtime": datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": oct(file_stat.st_mode & 0o777),
    }

    import secrets
    event_id = f"evt_{timestamp.replace('-', '').replace(':', '')}_{secrets.token_hex(3)}"

    attempt_record = {
        "method": result.extraction_method,
        "timestamp": timestamp,
        "success": result.error is None,
        "needs_ai": result.needs_ai_extraction,
    }

    evidence = {
        "ingest_event_id": event_id,
        "content_hash": content_hash,
        "original_path_snapshot": str(file_path),
        "file_stat": file_stat_dict,
        "canonical_blob_ref": f"artifacts/{blob_name}",
        "ingested_at": timestamp,
        "duplicate_of": None,
        "same_content_as": same_content_as,
        "archive_status": "pending",
        "archive_path_snapshot": None,
        "extractor_attempts": [attempt_record],
        "errors": ([result.error] if result.error else []),
    }

    interpretation = {
        "extracted_text": result.text,
        "extraction_method": result.extraction_method if result.text else None,
        "text_quality": ("good" if result.text and not result.needs_ai_extraction else "needs_extraction" if result.needs_ai_extraction else None),
        "observations": result.metadata,
        "routing_hints": {},
        "confidence": (0.8 if result.text and not result.needs_ai_extraction else 0.0),
        "review_annotations": {},
        "updated_at": timestamp,
    }

    manifest = create_manifest(note_id, inbox_key, evidence, interpretation)
    manifest_name = f"{ts_prefix}--{note_id}.manifest.json"
    manifest_path = manifests_dir / manifest_name
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    rel_manifest = str(manifest_path.relative_to(ROOT))
    rel_artifact = str(blob_path.relative_to(ROOT))
    _write_ingest_state(inbox_key, note_id, _state("ingested", manifest_path_val=rel_manifest, artifact_path_val=rel_artifact))

    # Archive: move original to inbox_path/processed/YYYY-MM-DD/
    archive_dir = inbox_path / "processed" / timestamp[:10]
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_dest = archive_dir / file_path.name
    # Handle collision: append note_id suffix if destination exists
    if archive_dest.exists():
        archive_dest = archive_dir / f"{file_path.stem}--{note_id}{file_path.suffix}"
    try:
        shutil.move(str(file_path), str(archive_dest))
    except OSError as exc:
        _write_ingest_state(inbox_key, note_id, _state("ingested", error_code="archive_failed", error_detail=str(exc),
                                                         manifest_path_val=rel_manifest, artifact_path_val=rel_artifact))
        raise

    evidence["archive_status"] = "archived"
    evidence["archive_path_snapshot"] = str(archive_dest)
    manifest["evidence"] = evidence
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    _write_ingest_state(inbox_key, note_id, _state("ingested", manifest_path_val=rel_manifest,
                                                     artifact_path_val=rel_artifact, archive_status="archived"))

    return {
        "note_id": note_id,
        "content_hash": content_hash,
        "needs_extraction": result.needs_ai_extraction,
        "extraction_method": result.extraction_method,
        "same_content_as": same_content_as,
    }


def ingest_command(args: argparse.Namespace) -> int:
    ensure_layout()
    integration = getattr(args, "integration", None)
    if integration != FILESYSTEM_SOURCE:
        raise SystemExit(f"Unsupported integration '{integration}'. Currently only 'filesystem' is supported.")

    config = {}
    if REGISTRY_SHARED_PATH.exists():
        shared_config = read_registry_config(REGISTRY_SHARED_PATH)
        local_config = read_registry_config(REGISTRY_LOCAL_PATH) if REGISTRY_LOCAL_PATH.exists() else {}
        config = merge_registry_configs(shared_config, local_config)
    elif REGISTRY_LOCAL_PATH.exists():
        config = read_registry_config(REGISTRY_LOCAL_PATH)

    inboxes = load_filesystem_inboxes(config)
    target_inbox = getattr(args, "inbox", None)
    if target_inbox:
        if target_inbox not in inboxes:
            raise SystemExit(f"Unknown inbox key '{target_inbox}'. Configured: {sorted(inboxes)}")
        inboxes = {target_inbox: inboxes[target_inbox]}

    if not inboxes:
        raise SystemExit("No filesystem inboxes configured. Run: python3 scripts/bootstrap_local.py")

    dry_run = getattr(args, "dry_run", False)
    error_details: list[dict[str, str]] = []
    results: dict[str, Any] = {"ingested": 0, "skipped": 0, "errors": 0, "needs_extraction": 0, "inboxes_processed": []}

    for inbox_key, inbox_path in sorted(inboxes.items()):
        if not inbox_path.exists():
            results["errors"] += 1
            detail = {"inbox": inbox_key, "path": str(inbox_path), "error": "inbox path does not exist"}
            error_details.append(detail)
            print(f"error: inbox '{inbox_key}' path does not exist: {inbox_path}", file=sys.stderr)
            continue
        results["inboxes_processed"].append(inbox_key)
        for item in sorted(inbox_path.iterdir()):
            if not item.is_file():
                continue
            if item.name.startswith("."):
                continue
            if dry_run:
                results["ingested"] += 1
                continue
            try:
                summary = ingest_file(item, inbox_key, inbox_path)
                results["ingested"] += 1
                if summary.get("needs_extraction"):
                    results["needs_extraction"] += 1
            except (MemoryError, RecursionError):
                raise
            except OSError as exc:
                results["errors"] += 1
                detail = {"file": str(item), "inbox": inbox_key, "error": str(exc)}
                error_details.append(detail)
                print(f"error: failed to ingest {item}: {exc}", file=sys.stderr)
            except Exception as exc:
                results["errors"] += 1
                detail = {"file": str(item), "inbox": inbox_key, "error": f"{type(exc).__name__}: {exc}"}
                error_details.append(detail)
                print(f"error: failed to ingest {item}: {exc}", file=sys.stderr)

    if error_details:
        results["error_details"] = error_details
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


def extract_command(args: argparse.Namespace) -> int:
    """List or update extraction results for filesystem notes."""
    ensure_layout()
    note_id = getattr(args, "note_id", None)

    if note_id is None:
        # List mode: show notes needing extraction
        pending: list[dict[str, Any]] = []
        for note_path in iter_normalized_files_by_source({FILESYSTEM_SOURCE}):
            metadata, body = read_note(note_path)
            if metadata.get("extraction_status") != "needs_extraction":
                continue
            pending.append({
                "source_note_id": metadata.get("source_note_id"),
                "canonical_blob_ref": metadata.get("canonical_blob_ref"),
                "original_filename": metadata.get("original_filename"),
                "ai_extraction_hint": metadata.get("ai_extraction_hint", ""),
                "normalized_path": str(note_path),
            })
        print(json.dumps({"pending_extraction": pending, "count": len(pending)}, indent=2, ensure_ascii=False))
        return 0

    # Write mode: update extraction for a specific note
    note_path = resolve_unique_normalized_note_path(note_id, sources={FILESYSTEM_SOURCE})
    metadata, body = read_note(note_path)

    extracted_text = getattr(args, "text", None) or ""
    observations_raw = getattr(args, "observations", None) or "{}"
    try:
        observations = json.loads(observations_raw)
    except json.JSONDecodeError:
        raise SystemExit(f"Invalid --observations JSON: {observations_raw}")

    # Find and update the manifest
    manifest_path = None
    raw_path_str = metadata.get("raw_payload_path")
    if raw_path_str:
        candidate = ROOT / raw_path_str if not Path(raw_path_str).is_absolute() else Path(raw_path_str)
        if candidate.exists():
            manifest_path = candidate

    if manifest_path is None:
        print(f"warning: manifest not found for note {note_id} (raw_payload_path={raw_path_str}). Extraction history will not be recorded.", file=sys.stderr)

    if manifest_path:
        timestamp = iso_now()
        interpretation = {
            "extracted_text": extracted_text,
            "extraction_method": "ai_assisted",
            "text_quality": "good" if extracted_text else "needs_extraction",
            "observations": observations,
            "routing_hints": {},
            "confidence": 0.8 if extracted_text else 0.0,
            "review_annotations": {},
            "updated_at": timestamp,
        }
        attempt_record = {
            "method": "ai_assisted",
            "timestamp": timestamp,
            "success": bool(extracted_text),
            "needs_ai": False,
        }
        update_manifest_interpretation(manifest_path, interpretation, attempt_record)

    # Update normalized note
    title = metadata.get("title", note_id)
    new_body = f"# {title}\n\n{extracted_text.strip()}\n" if extracted_text else body
    metadata["extraction_status"] = "complete" if extracted_text else "needs_extraction"
    metadata["extraction_method"] = "ai_assisted"
    write_note(note_path, metadata, new_body)

    # Remove from needs_extraction review queue
    remove_review_copies(note_path.name)

    print(json.dumps({"updated": note_id, "extraction_status": metadata["extraction_status"]}, indent=2, ensure_ascii=False))
    return 0


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
    metadata.setdefault("source", VOICE_SOURCE)
    metadata.setdefault("source_project", None)
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
    metadata.setdefault("content_hash", None)
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
    if path.name.endswith(".manifest.json"):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        return manifest, "filesystem-manifest"
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("source") == PROJECT_ROUTER_SOURCE:
            return payload, "project-router-json"
        if "recording" in payload:
            return payload, "json"
        # tolerate direct recording payloads too
        return {"source": VOICE_SOURCE, "source_endpoint": "recordings", "recording": payload}, "json"

    metadata, body = read_note(path)
    if metadata.get("packet_id") or metadata.get("source") == PROJECT_ROUTER_SOURCE:
        return (
            {
                "source": PROJECT_ROUTER_SOURCE,
                "source_project": metadata.get("source_project"),
                "source_endpoint": "outbox",
                "packet": metadata,
                "body": body,
            },
            "project-router-markdown",
        )
    return (
        {
            "source": metadata.get("source", VOICE_SOURCE),
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
    source = normalize_source_name(str(raw_payload.get("source") or VOICE_SOURCE)) or VOICE_SOURCE
    if source == PROJECT_ROUTER_SOURCE:
        packet = dict(raw_payload.get("packet") or {})
        note_id = require_valid_note_id(packet.get("packet_id") or packet.get("source_note_id"), field="packet_id")
        source_project = str(raw_payload.get("source_project") or packet.get("source_project") or "").strip()
        if not source_project:
            raise SystemExit(f"Raw project_router packet '{raw_path}' is missing source_project.")
        title = packet.get("title") or f"Project Router {note_id}"
        created_at = packet.get("created_at")
        note_dir = normalized_dir_for(PROJECT_ROUTER_SOURCE, source_project)
        normalized_path = existing_artifact_path(note_dir, note_id, ".md") or (note_dir / f"{normalize_timestamp(created_at)}--{note_id}.md")
        body = str(raw_payload.get("body") or "")
        metadata = {
            "source": PROJECT_ROUTER_SOURCE,
            "source_project": source_project,
            "source_note_id": note_id,
            "source_item_type": "outbox_packet",
            "source_endpoint": "outbox",
            "title": title,
            "created_at": created_at,
            "recorded_at": packet.get("recorded_at"),
            "recording_type": None,
            "duration": None,
            "tags": packet.get("tags") or [],
            "capture_kind": None,
            "intent": None,
            "destination": packet.get("target_project"),
            "destination_reason": "",
            "user_keywords": [],
            "inferred_keywords": [],
            "transcript_format": "markdown",
            "summary_available": False,
            "summary_source": None,
            "audio_available": False,
            "audio_local_path": None,
            "classification_basis": [],
            "derived_outputs": [],
            "thread_id": None,
            "continuation_of": packet.get("continuation_of"),
            "related_note_ids": packet.get("related_note_ids") or [],
            "status": "normalized",
            "project": None,
            "candidate_projects": [],
            "confidence": 0.0,
            "routing_reason": "",
            "review_status": "pending",
            "requires_user_confirmation": True,
            "content_hash": raw_payload.get("content_hash"),
            "canonical_path": relative_or_absolute(normalized_path),
            "raw_payload_path": relative_or_absolute(raw_path),
            "dispatched_to": [],
            "packet_type": packet.get("packet_type"),
            "supported_packet_types": packet.get("supported_packet_types"),
            "native_packet_id": packet.get("packet_id"),
        }
        rendered_body = body if body.startswith("# ") else f"# {title}\n\n{body.strip()}\n"
        return normalized_path, enrich_note_metadata(metadata, rendered_body), rendered_body

    if source == FILESYSTEM_SOURCE:
        note_id = require_valid_note_id(raw_payload.get("source_note_id"))
        evidence = raw_payload.get("evidence") or {}
        interpretation = raw_payload.get("interpretation") or {}
        inbox_key = raw_payload.get("inbox_key", "default")
        created_at = evidence.get("ingested_at")
        original_snapshot = evidence.get("original_path_snapshot", "")
        original_filename = Path(original_snapshot).name if original_snapshot else note_id
        title = original_filename
        note_dir = normalized_dir_for(FILESYSTEM_SOURCE)
        normalized_path = existing_artifact_path(note_dir, note_id, ".md") or (note_dir / f"{normalize_timestamp(created_at)}--{note_id}.md")
        extracted_text = interpretation.get("extracted_text") or ""
        needs_ai = interpretation.get("text_quality") == "needs_extraction" or not extracted_text
        extraction_status = "complete" if extracted_text and not needs_ai else "needs_extraction"
        body_text = extracted_text if extracted_text else f"[Binary file — extraction pending: {original_filename}]"
        body = f"# {title}\n\n{body_text.strip()}\n"
        metadata = {
            "source": FILESYSTEM_SOURCE,
            "source_project": None,
            "source_note_id": note_id,
            "source_item_type": "filesystem_ingest",
            "source_endpoint": f"filesystem/{inbox_key}",
            "title": title,
            "created_at": created_at,
            "recorded_at": None,
            "recording_type": None,
            "duration": None,
            "tags": [],
            "capture_kind": None,
            "intent": None,
            "destination": None,
            "destination_reason": "",
            "user_keywords": [],
            "inferred_keywords": [],
            "transcript_format": "markdown",
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
            "content_hash": evidence.get("content_hash"),
            "canonical_path": relative_or_absolute(normalized_path),
            "raw_payload_path": relative_or_absolute(raw_path),
            "dispatched_to": [],
            "original_filename": original_filename,
            "extraction_status": extraction_status,
            "extraction_method": interpretation.get("extraction_method"),
            "ai_extraction_hint": (interpretation.get("observations") or {}).get("ai_extraction_hint", ""),
            "canonical_blob_ref": evidence.get("canonical_blob_ref"),
        }
        return normalized_path, enrich_note_metadata(metadata, body), body

    recording = dict(raw_payload.get("recording") or {})
    note_id = require_valid_note_id(recording.get("id") or recording.get("uuid"))
    title = recording.get("title") or f"VoiceNotes {recording.get('id') or recording.get('uuid')}"
    note_dir = normalized_dir_for(VOICE_SOURCE)
    normalized_path = existing_artifact_path(note_dir, note_id, ".md") or (note_dir / normalized_filename_from_recording(recording))
    transcript = recording.get("transcript")
    metadata = {
        "source": raw_payload.get("source", VOICE_SOURCE),
        "source_project": None,
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
        "content_hash": None,
        "canonical_path": relative_or_absolute(normalized_path),
        "raw_payload_path": relative_or_absolute(raw_path),
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
    source, source_project, note_id = note_identity(metadata)
    directory = compiled_dir_for(source, source_project)
    return existing_artifact_path(directory, note_id, ".md") or (directory / compiled_filename_from_metadata(metadata))


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


def compile_command(args: argparse.Namespace) -> int:
    ensure_layout()
    note_filter = set(args.note_ids or [])
    sources = parse_source_filter(getattr(args, "source", None))
    written = 0
    updated = 0
    skipped = 0
    for note_path in iter_normalized_files_by_source(sources):
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
        packet = load_decision_packet_for_metadata(metadata)
        packet.setdefault("source_note_id", source_note_id)
        packet.setdefault("source", metadata.get("source", VOICE_SOURCE))
        packet.setdefault("source_project", metadata.get("source_project"))
        packet.setdefault("canonical_path", relative_or_absolute(note_path))
        packet.setdefault("title", metadata.get("title"))
        if artifact_path.exists():
            existing_metadata, existing_body = read_note(artifact_path)
            preserved_compiled_at = existing_metadata.get("compiled_at")
            artifact_metadata["compiled_at"] = preserved_compiled_at or artifact_metadata["compiled_at"]
            if existing_metadata == artifact_metadata and existing_body == artifact_body:
                packet["compiled"] = {
                    "path": relative_or_absolute(artifact_path),
                    "compiled_at": artifact_metadata.get("compiled_at"),
                    "brief_summary": artifact_metadata.get("brief_summary"),
                    "entities": artifact_metadata.get("entities", []),
                    "tasks": artifact_metadata.get("tasks", []),
                    "decisions": artifact_metadata.get("decisions", []),
                    "open_questions": artifact_metadata.get("open_questions", []),
                    "ambiguities": artifact_metadata.get("ambiguities", []),
                }
                save_decision_packet_for_metadata(metadata, packet)
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
            save_decision_packet_for_metadata(metadata, packet)
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
        save_decision_packet_for_metadata(metadata, packet)
        written += 1
    print(
        json.dumps(
            {
                "compiled_written": written,
                "compiled_updated": updated,
                "skipped": skipped,
                "note_ids": sorted(note_filter),
                "sources": sorted(sources),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


def compiled_artifact_state(metadata: dict[str, Any], body: str) -> tuple[Path, bool, dict[str, Any] | None, str | None]:
    path = compiled_note_path(metadata)
    if not path.exists():
        return path, False, None, None
    compiled_metadata, _ = read_note(path)
    current_signature = canonical_compile_signature(metadata, body)
    is_fresh = compiled_metadata.get("compiled_from_signature") == current_signature
    return path, is_fresh, compiled_metadata, current_signature


def normalize_command(args: argparse.Namespace) -> int:
    ensure_layout()
    sources = parse_source_filter(getattr(args, "source", None))
    written = 0
    updated = 0
    skipped = 0
    for raw_file in iter_raw_files_by_source(sources):
        raw_payload, raw_format = load_raw_recording(raw_file)
        detected_source = normalize_source_name(str(raw_payload.get("source") or VOICE_SOURCE))
        if detected_source == PROJECT_ROUTER_SOURCE:
            packet = raw_payload.get("packet") or {}
            note_id = packet.get("packet_id") or packet.get("source_note_id")
        elif detected_source == FILESYSTEM_SOURCE:
            note_id = raw_payload.get("source_note_id")
        else:
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
        if metadata.get("extraction_status") == "needs_extraction" and detected_source == FILESYSTEM_SOURCE:
            needs_ext_dir = review_dir_for(FILESYSTEM_SOURCE, "needs_extraction")
            write_note(needs_ext_dir / normalized_path.name, metadata, body)
        written += 1

    print(
        json.dumps(
            {"normalized_written": written, "normalized_updated": updated, "skipped": skipped, "sources": sorted(sources)},
            indent=2,
            ensure_ascii=False,
        )
    )
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
    sources = parse_source_filter(getattr(args, "source", None))
    triaged = 0
    for note_path in iter_normalized_files_by_source(sources):
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
        if previous_review_status == "reject":
            preserve_manual_review = True
        elif previous_review_status == "approved":
            preserve_manual_review = (
                route not in ("ambiguous", "needs_review", "pending_project")
                and previous_status == "classified"
                and previous_project == route
            )
        else:
            if route in ("ambiguous", "needs_review", "pending_project"):
                preserve_manual_review = (
                    previous_status == route
                    and previous_review_status not in (None, "pending")
                )
            else:
                preserve_manual_review = (
                    previous_status == "classified"
                    and previous_project == route
                    and previous_review_status not in (None, "pending")
                )

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
            source = normalize_source_name(str(metadata.get("source") or VOICE_SOURCE)) or VOICE_SOURCE
            if source == PROJECT_ROUTER_SOURCE and route == "ambiguous":
                target_dir = review_dir_for(PROJECT_ROUTER_SOURCE, "needs_review")
            elif route == "ambiguous":
                target_dir = review_dir_for(source, "ambiguous")
            elif route == "pending_project":
                target_dir = review_dir_for(source, "pending_project")
            else:
                target_dir = review_dir_for(source, "needs_review")
            write_note(target_dir / note_path.name, metadata, body)
        else:
            metadata["status"] = "classified"
            metadata["project"] = route
            metadata["note_type"] = projects[route].note_type
            metadata["intent"] = classify_intent(metadata)
            write_note(note_path, metadata, body)
            remove_review_copies(note_path.name)
        save_decision_packet_for_metadata(metadata, build_decision_packet(note_path, metadata, body, route=route, details=details, reason=reason))
        triaged += 1

    print(json.dumps({"triaged": triaged, "mode": "all" if args.all else "default", "sources": sorted(sources)}, indent=2, ensure_ascii=False))
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
        "source": metadata.get("source", VOICE_SOURCE),
        "source_project": metadata.get("source_project"),
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
        "canonical_path": relative_or_absolute(canonical_path),
        "compiled_path": relative_or_absolute(compiled_path),
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
    inbox_path = inbox_path_for_project(project)
    if inbox_path is None:
        return None, (
            f"no local router_root_path or inbox_path for project '{project.key}'. "
            f"Run: python3 scripts/project_router.py adopt-router-root --project {project.key}"
        )

    try:
        ensure_safe_inbox_path(inbox_path, project_key=project.key, registry_path=REGISTRY_LOCAL_PATH)
    except SystemExit as exc:
        return None, str(exc)

    title = metadata.get("title") or f"VoiceNotes {metadata.get('source_note_id')}"
    return inbox_path / dispatch_filename(metadata, title), None


def dispatch_command(args: argparse.Namespace) -> int:
    ensure_layout()
    _, projects = load_registry(require_local=True)
    sources = parse_source_filter(getattr(args, "source", None))
    dispatched = 0
    skipped = 0
    candidates: list[dict[str, Any]] = []
    approved_note_ids = set(args.note_ids or [])

    if args.confirm_user_approval and not approved_note_ids:
        raise SystemExit("Real dispatch requires at least one --note-id after the user confirms those exact notes.")

    for note_path in iter_normalized_files_by_source(sources):
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
                "note": relative_or_absolute(note_path),
                "source_note_id": source_note_id,
                "compiled_path": relative_or_absolute(compiled_path),
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

        if compiled_metadata is None:
            raise SystemExit(f"Internal error: compiled metadata missing for {source_note_id}.")
        if destination is None:
            raise SystemExit(f"Internal error: dispatch destination unresolved for {source_note_id}.")
        if mirror_path is None:
            raise SystemExit(f"Internal error: mirror path unresolved for {source_note_id}.")
        _, compiled_body = read_note(compiled_path)
        title, content = build_dispatch_note(metadata, compiled_metadata, compiled_body, project, note_path, compiled_path)
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8")
            mirror_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, mirror_path)
            # For filesystem-source notes, also dispatch the original blob
            blob_ref = metadata.get("canonical_blob_ref")
            source = normalize_source_name(str(metadata.get("source") or VOICE_SOURCE)) or VOICE_SOURCE
            if source == FILESYSTEM_SOURCE and blob_ref:
                inbox_key = (metadata.get("source_endpoint") or "").replace("filesystem/", "") or "default"
                blob_source = RAW_DIR / FILESYSTEM_SOURCE / inbox_key / blob_ref
                if blob_source.exists():
                    blob_ext = blob_source.suffix
                    blob_dest = destination.parent / f"{destination.stem}{blob_ext}"
                    shutil.copy2(str(blob_source), str(blob_dest))
                    blob_mirror = mirror_path.parent / blob_dest.name
                    shutil.copy2(str(blob_source), str(blob_mirror))
                    candidates[-1]["blob_dispatched"] = str(blob_dest)
        except OSError as exc:
            candidates[-1]["skip_reason"] = f"downstream write failed: {exc}"
            skipped += 1
            continue

        metadata["status"] = "dispatched"
        metadata["dispatched_at"] = "manual-run"
        dispatched_paths = [str(destination)]
        if candidates[-1].get("blob_dispatched"):
            dispatched_paths.append(candidates[-1]["blob_dispatched"])
        metadata["dispatched_to"] = dispatched_paths
        metadata["requires_user_confirmation"] = False
        write_note(note_path, metadata, body)
        packet = load_decision_packet_for_metadata(metadata)
        packet.setdefault("source_note_id", source_note_id)
        packet.setdefault("source", metadata.get("source", VOICE_SOURCE))
        packet.setdefault("source_project", metadata.get("source_project"))
        packet.setdefault("canonical_path", relative_or_absolute(note_path))
        packet.setdefault("title", metadata.get("title"))
        packet.setdefault("created_at", metadata.get("created_at"))
        packet["dispatch"] = {
            "destination": str(destination),
            "dispatched_at": metadata["dispatched_at"],
            "compiled_path": relative_or_absolute(compiled_path),
        }
        save_decision_packet_for_metadata(metadata, packet)
        dispatched += 1

    summary = {
        "candidates": candidates,
        "dispatched": dispatched if args.confirm_user_approval else 0 if not args.dry_run else dispatched,
        "skipped": skipped,
        "dry_run": args.dry_run,
        "confirmation_required": not args.dry_run and not args.confirm_user_approval,
        "approved_note_ids": sorted(approved_note_ids),
        "sources": sorted(sources),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def pending_project_notes(*, sources: set[str] | None = None) -> list[dict[str, Any]]:
    active_sources = sources or set(KNOWN_SOURCES)
    items: list[dict[str, Any]] = []
    for note_path in iter_normalized_files_by_source(active_sources):
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
        source = normalize_source_name(str(metadata.get("source") or VOICE_SOURCE)) or VOICE_SOURCE
        review_path = review_dir_for(source, "pending_project") / note_path.name
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
    sources = parse_source_filter(getattr(_, "source", None))
    items = pending_project_notes(sources=sources)
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
                    "decision_packet_path": str(decision_packet_path_for_metadata(item["metadata"])),
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
                        "decision_packet_path": str(decision_packet_path_for_metadata(item["metadata"])),
                    }
                    for item in sorted(cluster, key=note_sort_key)
                ],
            }
        )

    report = {
        "generated_at": iso_now(),
        "sources": sorted(sources),
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
    sources = parse_source_filter(getattr(args, "source", None))
    packets = sorted(DECISIONS_DIR.glob("*.json"))
    if args.note_id:
        packet_path = resolve_unique_decision_packet_path(args.note_id, sources=sources)
        packet = load_decision_packet_by_path(packet_path)
        if not packet or "source_note_id" not in packet:
            raise SystemExit(f"No decision packet found for {args.note_id}.")
        if normalize_source_name(str(packet.get("source") or VOICE_SOURCE)) not in sources:
            raise SystemExit(f"Decision packet {args.note_id} exists outside the current --source filter.")
        print(json.dumps(build_review_entry(packet, packet_path), indent=2, ensure_ascii=False))
        return 0

    output = []
    for path in packets:
        packet = load_decision_packet_by_path(path)
        if normalize_source_name(str(packet.get("source") or VOICE_SOURCE)) not in sources:
            continue
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
    }


def _raw_payload_path_from_packet(packet: dict[str, Any]) -> str | None:
    return packet.get("raw_payload_path")


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


def find_normalized_note_paths(note_id: str, *, sources: set[str] | None = None) -> list[Path]:
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
    sources = parse_source_filter(getattr(args, "source", None))
    note_path = resolve_unique_normalized_note_path(args.note_id, sources=sources)
    metadata, body = read_note(note_path)

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
        source = normalize_source_name(str(metadata.get("source") or VOICE_SOURCE)) or VOICE_SOURCE
        if source == VOICE_SOURCE:
            target_dir = review_dir_for(VOICE_SOURCE, "ambiguous")
        elif source == PROJECT_ROUTER_SOURCE:
            target_dir = review_dir_for(PROJECT_ROUTER_SOURCE, "needs_review")
        else:
            target_dir = review_dir_for(source, "ambiguous")
        write_note(target_dir / note_path.name, metadata, body)
    elif decision == "pending-project":
        metadata["status"] = "pending_project"
        metadata["project"] = None
        metadata["destination"] = "pending_project"
        metadata.pop("note_type", None)
        metadata["review_status"] = "pending_project"
        metadata["requires_user_confirmation"] = True
        metadata["intent"] = classify_intent(metadata)
        remove_review_copies(note_path.name)
        write_note(review_dir_for(normalize_source_name(str(metadata.get("source") or VOICE_SOURCE)) or VOICE_SOURCE, "pending_project") / note_path.name, metadata, body)
    else:
        metadata["status"] = "needs_review"
        metadata["project"] = None
        metadata["destination"] = "needs_review"
        metadata.pop("note_type", None)
        metadata["review_status"] = decision.replace("-", "_")
        metadata["requires_user_confirmation"] = True
        metadata["intent"] = classify_intent(metadata)
        remove_review_copies(note_path.name)
        write_note(review_dir_for(normalize_source_name(str(metadata.get("source") or VOICE_SOURCE)) or VOICE_SOURCE, "needs_review") / note_path.name, metadata, body)

    write_note(note_path, metadata, body)

    packet = load_decision_packet_for_metadata(metadata)
    packet.setdefault("reviews", [])
    packet.setdefault("source_note_id", args.note_id)
    packet.setdefault("source", metadata.get("source", VOICE_SOURCE))
    packet.setdefault("source_project", metadata.get("source_project"))
    packet.setdefault("canonical_path", relative_or_absolute(note_path))
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
    save_decision_packet_for_metadata(metadata, packet)

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


def load_outbox_scan_state() -> dict[str, Any]:
    if not OUTBOX_SCAN_STATE_PATH.exists():
        return {"schema_version": "1", "scanned_packets": {}}
    return json.loads(OUTBOX_SCAN_STATE_PATH.read_text(encoding="utf-8"))


def save_outbox_scan_state(state: dict[str, Any]) -> None:
    OUTBOX_SCAN_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTBOX_SCAN_STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def scan_state_entry(state: dict[str, Any], project_key: str, note_id: str) -> dict[str, Any] | None:
    return ((state.get("scanned_packets") or {}).get(project_key) or {}).get(note_id)


def update_scan_state(state: dict[str, Any], project_key: str, note_id: str, payload: dict[str, Any]) -> None:
    packets = state.setdefault("scanned_packets", {})
    project_packets = packets.setdefault(project_key, {})
    project_packets[note_id] = payload


def count_active_scan_state_errors(state: dict[str, Any] | None = None) -> int:
    if state is None:
        state = load_outbox_scan_state()
    active_errors = 0
    for project_packets in (state.get("scanned_packets") or {}).values():
        if not isinstance(project_packets, dict):
            continue
        for entry in project_packets.values():
            if isinstance(entry, dict) and entry.get("status") == "invalid":
                active_errors += 1
    return active_errors


def legacy_source_layout_operations() -> list[tuple[Path, Path]]:
    operations: list[tuple[Path, Path]] = []
    legacy_map = {
        RAW_DIR: raw_dir_for(VOICE_SOURCE),
        NORMALIZED_DIR: normalized_dir_for(VOICE_SOURCE),
        COMPILED_DIR: compiled_dir_for(VOICE_SOURCE),
        REVIEW_DIR / "ambiguous": review_dir_for(VOICE_SOURCE, "ambiguous"),
        REVIEW_DIR / "needs_review": review_dir_for(VOICE_SOURCE, "needs_review"),
        REVIEW_DIR / "pending_project": review_dir_for(VOICE_SOURCE, "pending_project"),
    }
    for src_dir, dest_dir in legacy_map.items():
        if not src_dir.exists():
            continue
        for item in src_dir.iterdir():
            if item.is_file() and item.name != ".gitkeep":
                operations.append((item, dest_dir / item.name))
    return operations


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # process exists but belongs to another user


def acquire_scan_lock() -> None:
    OUTBOX_SCAN_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(OUTBOX_SCAN_LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except FileExistsError:
        # Check if the holding process is still alive
        try:
            lock_pid = int(OUTBOX_SCAN_LOCK_PATH.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            lock_pid = None
        if lock_pid is not None and _is_pid_alive(lock_pid):
            raise SystemExit(f"Another scan-outboxes command is already running (PID {lock_pid}, lock: {OUTBOX_SCAN_LOCK_PATH}).")
        # Stale lock — reclaim by overwriting with our PID
        try:
            fd = os.open(OUTBOX_SCAN_LOCK_PATH, os.O_WRONLY | os.O_TRUNC)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
        except OSError as exc:
            raise SystemExit(f"Could not reclaim stale scan lock ({OUTBOX_SCAN_LOCK_PATH}): {exc}") from exc


def release_scan_lock() -> None:
    OUTBOX_SCAN_LOCK_PATH.unlink(missing_ok=True)


def relative_or_absolute(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def packet_content_hash(metadata: dict[str, Any], body: str) -> str:
    payload = json.dumps({"frontmatter": metadata, "body": body}, sort_keys=True, ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_router_contract(contract: dict[str, Any], *, expected_project_key: str | None = None, strict: bool = False) -> list[str]:
    errors: list[str] = []
    required = ("schema_version", "project_key", "default_language", "supported_packet_types")
    for field in required:
        if field not in contract:
            errors.append(f"router-contract.json missing required field '{field}'")
    allowed = set(required)
    extras = sorted(key for key in contract if key not in allowed)
    if strict and extras:
        errors.append(f"router-contract.json contains unsupported fields: {', '.join(extras)}")
    if "supported_packet_types" in contract and not isinstance(contract.get("supported_packet_types"), list):
        errors.append("router-contract.json field 'supported_packet_types' must be a JSON array.")
    if expected_project_key and contract.get("project_key") != expected_project_key:
        errors.append(
            f"router-contract.json project_key '{contract.get('project_key')}' does not match expected registry key '{expected_project_key}'."
        )
    return errors


def validate_outbox_packet(
    path: Path,
    metadata: dict[str, Any],
    body: str,
    *,
    expected_project_key: str,
    strict: bool = False,
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    required = (
        "schema_version",
        "packet_id",
        "created_at",
        "source_project",
        "packet_type",
        "title",
        "language",
        "status",
    )
    for field in required:
        if field not in metadata or metadata.get(field) in (None, "", []):
            errors.append(f"{path.name}: missing required frontmatter field '{field}'")
    packet_id = None
    if metadata.get("packet_id") not in (None, ""):
        try:
            packet_id = require_valid_note_id(metadata.get("packet_id"), field="packet_id")
        except SystemExit as exc:
            errors.append(f"{path.name}: {exc}")
    created_at = metadata.get("created_at")
    if created_at and not parse_note_datetime(str(created_at)):
        errors.append(f"{path.name}: created_at must be an ISO-8601 datetime.")
    if metadata.get("source_project") and str(metadata.get("source_project")) != expected_project_key:
        errors.append(
            f"{path.name}: source_project '{metadata.get('source_project')}' does not match expected project '{expected_project_key}'."
        )
    if packet_id and path.name != f"{normalize_timestamp(str(created_at))}--{packet_id}.md":
        errors.append(f"{path.name}: filename must match '{normalize_timestamp(str(created_at))}--{packet_id}.md'.")
    if strict and metadata.get("source_note_id"):
        errors.append(f"{path.name}: authored outbox packets must not define source_note_id directly.")
    content_hash = packet_content_hash(metadata, body)
    normalized = {
        "source": PROJECT_ROUTER_SOURCE,
        "source_project": expected_project_key,
        "source_note_id": packet_id,
        "content_hash": content_hash,
    }
    return errors, normalized


def parse_outbox_packet(path: Path, *, expected_project_key: str, strict: bool = False) -> tuple[dict[str, Any], str, list[str], dict[str, Any]]:
    metadata, body = read_note(path)
    errors, normalized = validate_outbox_packet(path, metadata, body, expected_project_key=expected_project_key, strict=strict)
    return metadata, body, errors, normalized


# --- Inbox consumption helpers ---

CLASSIFICATION_TO_PACKET_TYPE = {
    "maintainer-follow-up": "improvement_proposal",
}


def extract_packet_id(path: Path) -> str:
    """Extract packet_id from filename like '20260316T185247Z--some_id.md'."""
    stem = path.stem
    parts = stem.split("--", 1)
    if len(parts) < 2 or not parts[1]:
        raise SystemExit(f"Cannot extract packet_id from filename '{path.name}'. Expected format: '{{TIMESTAMP}}--{{PACKET_ID}}.md'.")
    return parts[1]


def load_inbox_packet_state(packet_id: str) -> dict[str, Any] | None:
    state_path = INBOX_STATUS_DIR / f"{packet_id}.json"
    if not state_path.exists():
        return None
    return json.loads(state_path.read_text(encoding="utf-8"))


def save_inbox_packet_state(packet_id: str, state: dict[str, Any]) -> None:
    INBOX_STATUS_DIR.mkdir(parents=True, exist_ok=True)
    state_path = INBOX_STATUS_DIR / f"{packet_id}.json"
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(state_path)


def list_inbox_packets() -> list[tuple[Path, dict[str, Any], str]]:
    """List .md files in router/inbox/. Returns list of (path, metadata, body)."""
    inbox = LOCAL_ROUTER_DIR / "inbox"
    if not inbox.exists():
        return []
    results = []
    for p in sorted(inbox.iterdir()):
        if not p.is_file() or p.suffix != ".md" or p.name == ".gitkeep":
            continue
        metadata, body = read_note(p)
        results.append((p, metadata, body))
    return results


def convert_brief_to_packet(metadata: dict[str, Any], body: str) -> tuple[dict[str, Any], str]:
    """Convert compiled-brief metadata to protocol packet format."""
    converted: dict[str, Any] = {}
    converted["schema_version"] = "1"
    packet_id = str(metadata.get("source_note_id") or "")
    if packet_id:
        converted["packet_id"] = packet_id
    converted["created_at"] = str(metadata.get("created_at") or metadata.get("compiled_at") or iso_now())
    converted["source_project"] = str(metadata.get("source_project") or metadata.get("project") or "unknown")
    classification = str(metadata.get("classification") or "")
    packet_type = CLASSIFICATION_TO_PACKET_TYPE.get(classification)
    if packet_type is None:
        if classification:
            sys.stderr.write(f"Warning: unknown classification '{classification}', defaulting to 'insight'.\n")
        packet_type = "insight"
    converted["packet_type"] = packet_type
    title = ""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            break
    if not title:
        title = str(metadata.get("brief_summary") or metadata.get("title") or "Untitled")
        if len(title) > 120:
            title = title[:117] + "..."
    converted["title"] = title
    contract_path = LOCAL_ROUTER_DIR / "router-contract.json"
    language = "en"
    if contract_path.exists():
        try:
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            language = contract.get("default_language", "en")
        except (json.JSONDecodeError, OSError):
            pass
    converted["language"] = language
    converted["status"] = "open"
    return converted, body


def build_project_router_raw_payload(
    *,
    project_key: str,
    source_path: Path,
    metadata: dict[str, Any],
    body: str,
    normalized: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source": PROJECT_ROUTER_SOURCE,
        "source_project": project_key,
        "source_endpoint": "outbox",
        "source_item_type": "outbox_packet",
        "source_path": str(source_path),
        "content_hash": normalized["content_hash"],
        "packet": dict(metadata),
        "body": body,
        "scanned_at": iso_now(),
    }


def parse_error_note_path(project_key: str, note_id: str) -> Path:
    return review_dir_for(PROJECT_ROUTER_SOURCE, "parse_errors") / f"{slugify(project_key)}--{note_id}.md"


def write_parse_error_note(
    *,
    project_key: str,
    source_path: Path,
    note_id: str,
    errors: list[str],
    metadata: dict[str, Any] | None = None,
) -> Path:
    path = parse_error_note_path(project_key, note_id)
    note_metadata = {
        "source": PROJECT_ROUTER_SOURCE,
        "source_project": project_key,
        "source_note_id": note_id,
        "source_item_type": "outbox_packet",
        "source_endpoint": "outbox",
        "title": f"Parse error for {project_key}/{note_id}",
        "created_at": iso_now(),
        "status": "parse_error",
        "review_status": "pending",
        "routing_reason": "; ".join(errors),
        "canonical_path": relative_or_absolute(path),
        "raw_payload_path": relative_or_absolute(source_path),
        "content_hash": packet_content_hash(metadata or {}, "\n".join(errors)),
    }
    body = "## Errors\n\n" + "\n".join(f"- {error}" for error in errors) + f"\n\n## Source path\n\n- {source_path}\n"
    write_note(path, note_metadata, body)
    return path


def project_contract_path(router_root: Path) -> Path:
    return router_root / "router-contract.json"


def outbox_packet_paths(router_root: Path) -> list[Path]:
    outbox_dir = router_root / "outbox"
    if not outbox_dir.exists():
        return []
    return sorted(path for path in outbox_dir.iterdir() if path.is_file() and path.suffix == ".md")


# ---------------------------------------------------------------------------
#  Shared scaffold utilities (used by init-router-root and adopt-router-root)
# ---------------------------------------------------------------------------

DEFAULT_PACKET_TYPES = ["improvement_proposal", "question", "insight"]


def write_scaffold_dirs(router_root: Path) -> list[Path]:
    """Create inbox/, outbox/, conformance/, archive/. Return created dirs."""
    created: list[Path] = []
    for name in ("inbox", "outbox", "conformance", "archive"):
        d = router_root / name
        d.mkdir(parents=True, exist_ok=True)
        created.append(d)
    return created


def write_contract_json(router_root: Path, project_key: str, language: str, packet_types: list[str]) -> Path:
    """Write router-contract.json. Return path."""
    contract = {
        "schema_version": "1",
        "project_key": project_key,
        "default_language": language,
        "supported_packet_types": packet_types,
    }
    path = router_root / "router-contract.json"
    path.write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_conformance_fixtures(
    router_root: Path,
    project_key: str,
    language: str,
    packet_type: str,
    *,
    skip_existing: bool = False,
) -> list[Path]:
    """Write valid/invalid conformance fixtures. Return created paths."""
    created: list[Path] = []
    conformance = router_root / "conformance"
    conformance.mkdir(parents=True, exist_ok=True)

    valid_path = conformance / "valid-packet.example.md"
    if not skip_existing or not valid_path.exists():
        valid_path.write_text(
            "---\n"
            'schema_version: "1"\n'
            f'packet_id: "template_{packet_type}_sample"\n'
            f'created_at: "{iso_now()}"\n'
            f'source_project: "{project_key}"\n'
            f'packet_type: "{packet_type}"\n'
            f'title: "Sample {packet_type.replace("_", " ")} packet"\n'
            f'language: "{language}"\n'
            'status: "open"\n'
            "---\n\n"
            f"# Sample {packet_type.replace('_', ' ')} packet\n\n"
            "This is a valid conformance fixture.\n",
            encoding="utf-8",
        )
        created.append(valid_path)

    invalid_path = conformance / "invalid-packet.example.md"
    if not skip_existing or not invalid_path.exists():
        invalid_path.write_text(
            "---\n"
            'schema_version: "1"\n'
            'packet_id: "invalid_example"\n'
            "---\n\n"
            "This fixture is intentionally invalid because it omits required packet fields.\n",
            encoding="utf-8",
        )
        created.append(invalid_path)

    return created


def validate_router_root_path(router_root: Path) -> None:
    """Validate that a router root path is absolute, has no placeholder, and no '..'."""
    if not router_root.is_absolute():
        raise SystemExit(f"--router-root must be an absolute path, got: {router_root}")
    if has_placeholder_path(router_root):
        raise SystemExit(f"--router-root contains a placeholder path: {router_root}")
    if ".." in router_root.parts:
        raise SystemExit(f"--router-root contains an unsafe '..' component: {router_root}")


def structural_preflight(target: Path) -> None:
    """Three-tier structural preflight for a target directory."""
    if (target / ".git").exists():
        raise SystemExit(
            f"Target is a repository root, not a project-router directory. "
            f"Did you mean '{target / 'router'}'?"
        )
    if target.exists() and not target.is_dir():
        raise SystemExit(f"--router-root must be a directory, not a file: {target}")
    if target.exists() and target.is_dir() and any(target.iterdir()):
        protocol_markers = {"inbox", "outbox", "conformance", "router-contract.json"}
        contents = {p.name for p in target.iterdir()}
        if not contents & protocol_markers:
            raise SystemExit(
                "Target directory exists with non-protocol content. "
                "Verify the path or use an empty directory."
            )


def parse_packet_types_arg(raw: str | None) -> list[str]:
    """Parse and validate packet types for scaffold commands."""
    if raw is None:
        return list(DEFAULT_PACKET_TYPES)

    packet_types = [token.strip() for token in raw.split(",") if token.strip()]
    if not packet_types:
        raise SystemExit("--packet-types must include at least one non-empty packet type.")

    duplicates = sorted({packet_type for packet_type in packet_types if packet_types.count(packet_type) > 1})
    if duplicates:
        raise SystemExit(
            f"--packet-types contains duplicate values: {', '.join(duplicates)}."
        )

    return packet_types


def init_router_root_command(args: argparse.Namespace) -> int:
    project_key = args.project
    if not NOTE_ID_PATTERN.fullmatch(project_key):
        raise SystemExit(f"Invalid project key '{project_key}'. Only letters, numbers, underscores, and hyphens are allowed.")

    raw_root = Path(args.router_root)
    if not raw_root.is_absolute():
        raise SystemExit(f"--router-root must be an absolute path, got: {raw_root}")
    router_root = raw_root.resolve()
    validate_router_root_path(router_root)
    structural_preflight(router_root)

    # Project must exist in shared registry
    if not REGISTRY_SHARED_PATH.exists():
        raise SystemExit(f"Missing shared registry at {REGISTRY_SHARED_PATH}.")
    shared_config = read_registry_config(REGISTRY_SHARED_PATH)
    shared_projects = shared_config.get("projects") or {}
    if project_key not in shared_projects:
        raise SystemExit(
            f"Project '{project_key}' not found in registry.shared.json. "
            f"Available projects: {', '.join(sorted(shared_projects.keys()))}."
        )

    project_config = shared_projects[project_key]
    language = project_config.get("language", "en")

    # Parse packet types
    packet_types = parse_packet_types_arg(args.packet_types)

    # Fail if contract already exists (bootstrap-only)
    contract_path = router_root / "router-contract.json"
    if contract_path.exists():
        raise SystemExit(
            f"router-contract.json already exists at {contract_path}. "
            "Use adopt-router-root for repair."
        )

    # Create scaffold
    router_root.mkdir(parents=True, exist_ok=True)
    created_dirs = write_scaffold_dirs(router_root)
    contract = write_contract_json(router_root, project_key, language, packet_types)
    fixtures = write_conformance_fixtures(router_root, project_key, language, packet_types[0])

    # Validate what we just wrote
    contract_data = json.loads(contract.read_text(encoding="utf-8"))
    errors = validate_router_contract(contract_data, expected_project_key=project_key)
    if errors:
        raise SystemExit(f"Scaffold validation failed: {'; '.join(errors)}")

    report = {
        "status": "created",
        "project_key": project_key,
        "router_root": str(router_root),
        "language": language,
        "packet_types": packet_types,
        "created_dirs": [str(d) for d in created_dirs],
        "contract": str(contract),
        "fixtures": [str(f) for f in fixtures],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


# ---------------------------------------------------------------------------
#  adopt-router-root — transaction-style migration
# ---------------------------------------------------------------------------

ADOPTIONS_DIR = PROJECT_ROUTER_STATE_DIR / "adoptions"


@dataclass
class AdoptionState:
    project_key: str
    project_rule: ProjectRule
    current_inbox_path: Path | None
    current_router_root: Path | None
    target_router_root: Path
    inbox_content_count: int
    inbox_naturally_preserved: bool
    inbox_collisions: list[Path]
    scaffold_exists: bool
    scaffold_complete: bool
    needs_registry_rewrite: bool
    downstream_agent_config: Path | None
    status: str  # "legacy" | "partial" | "already_current" | "no_path"


@dataclass
class AdoptionOperation:
    kind: str  # "mkdir" | "write_file" | "write_json" | "backup_file" | "rewrite_registry" | "copy_file"
    target: Path
    description: str
    source: Path | None = None
    content: str | None = None


def find_downstream_agent_config(target: Path) -> Path | None:
    """Walk up from target to find .git, then check for AGENTS.md/CLAUDE.md."""
    current = target
    while current != current.parent:
        if (current / ".git").exists():
            for name in ("AGENTS.md", "CLAUDE.md"):
                agent_path = current / name
                if agent_path.exists():
                    return agent_path
            return None
        current = current.parent
    return None


def resolve_adoption_state(
    project_key: str,
    project_rule: ProjectRule,
    explicit_router_root: str | None,
) -> AdoptionState:
    """Resolve adoption state for a single project."""
    # Determine target
    if explicit_router_root:
        raw_root = Path(explicit_router_root)
        if not raw_root.is_absolute():
            raise SystemExit(f"--router-root must be an absolute path, got: {raw_root}")
        target = raw_root.resolve()
        validate_router_root_path(target)
        structural_preflight(target)
    elif project_rule.router_root_path and not has_placeholder_path(project_rule.router_root_path):
        target = project_rule.router_root_path
        # Normalize corrupted router_root_path ending in /inbox
        if target.name == "inbox":
            target = target.parent
    elif project_rule.inbox_path and not has_placeholder_path(project_rule.inbox_path):
        candidate_parent = project_rule.inbox_path.parent
        if (candidate_parent / "router-contract.json").exists():
            target = candidate_parent
        else:
            raise SystemExit(
                f"Cannot infer router root: no router-contract.json found in '{candidate_parent}'. "
                f"Use --router-root."
            )
    else:
        raise SystemExit(
            f"No path available for project '{project_key}'. Use --router-root."
        )

    validate_router_root_path(target)

    # Determine current state
    current_inbox = project_rule.inbox_path
    current_rr = project_rule.router_root_path
    contract_exists = (target / "router-contract.json").exists()
    inbox_dir = target / "inbox"
    outbox_dir = target / "outbox"
    conformance_dir = target / "conformance"

    scaffold_exists = contract_exists or inbox_dir.exists() or outbox_dir.exists() or conformance_dir.exists()
    scaffold_complete = (
        contract_exists
        and inbox_dir.exists()
        and outbox_dir.exists()
        and conformance_dir.exists()
        and (conformance_dir / "valid-packet.example.md").exists()
        and (conformance_dir / "invalid-packet.example.md").exists()
    )

    # Inbox content analysis
    inbox_content_count = 0
    inbox_naturally_preserved = True
    inbox_collisions: list[Path] = []

    old_inbox = current_inbox
    new_inbox = target / "inbox"

    if old_inbox and old_inbox.exists() and old_inbox.resolve() != new_inbox.resolve():
        inbox_naturally_preserved = False
        old_files = sorted(old_inbox.iterdir()) if old_inbox.is_dir() else []
        inbox_content_count = len([f for f in old_files if f.is_file()])
        if new_inbox.exists():
            for old_file in old_files:
                if not old_file.is_file():
                    continue
                new_file = new_inbox / old_file.name
                if new_file.exists() and old_file.read_bytes() != new_file.read_bytes():
                    inbox_collisions.append(old_file)
    elif old_inbox and old_inbox.exists():
        inbox_content_count = len([f for f in old_inbox.iterdir() if f.is_file()])

    # Registry rewrite check
    needs_rewrite = (current_rr is None) or (current_rr != target)

    # Status: registry state takes priority over scaffold state
    if current_rr and current_rr == target and scaffold_complete:
        status = "already_current"
    elif current_inbox and not current_rr:
        status = "legacy"
    elif not current_inbox and not current_rr:
        status = "no_path"
    elif scaffold_exists and not scaffold_complete:
        status = "partial"
    else:
        status = "legacy"

    downstream_config = find_downstream_agent_config(target)

    return AdoptionState(
        project_key=project_key,
        project_rule=project_rule,
        current_inbox_path=current_inbox,
        current_router_root=current_rr,
        target_router_root=target,
        inbox_content_count=inbox_content_count,
        inbox_naturally_preserved=inbox_naturally_preserved,
        inbox_collisions=inbox_collisions,
        scaffold_exists=scaffold_exists,
        scaffold_complete=scaffold_complete,
        needs_registry_rewrite=needs_rewrite,
        downstream_agent_config=downstream_config,
        status=status,
    )


def plan_adoption_operations(state: AdoptionState, shared_config: dict[str, Any]) -> list[AdoptionOperation]:
    """Plan operations for adopting a project."""
    ops: list[AdoptionOperation] = []
    target = state.target_router_root
    project_config = (shared_config.get("projects") or {}).get(state.project_key, {})
    language = project_config.get("language", "en")
    packet_types = list(DEFAULT_PACKET_TYPES)

    # 1. Backup registry
    if REGISTRY_LOCAL_PATH.exists():
        timestamp = iso_now().replace(":", "").replace("-", "")
        backup_path = REGISTRY_LOCAL_PATH.parent / f"registry.local.json.pre-adopt-{timestamp}"
        ops.append(AdoptionOperation(
            kind="backup_file",
            target=backup_path,
            description=f"Backup registry to {backup_path.name}",
            source=REGISTRY_LOCAL_PATH,
        ))

    # 2. Scaffold dirs
    for name in ("inbox", "outbox", "conformance"):
        d = target / name
        if not d.exists():
            ops.append(AdoptionOperation(kind="mkdir", target=d, description=f"Create {name}/"))

    # 3. Contract
    if not (target / "router-contract.json").exists():
        ops.append(AdoptionOperation(
            kind="write_json",
            target=target / "router-contract.json",
            description="Write router-contract.json",
            content=json.dumps({
                "schema_version": "1",
                "project_key": state.project_key,
                "default_language": language,
                "supported_packet_types": packet_types,
            }, indent=2, ensure_ascii=False) + "\n",
        ))

    # 4. Conformance fixtures
    conformance = target / "conformance"
    if not (conformance / "valid-packet.example.md").exists():
        packet_type = packet_types[0] if packet_types else "improvement_proposal"
        ops.append(AdoptionOperation(
            kind="write_file",
            target=conformance / "valid-packet.example.md",
            description="Write valid conformance fixture",
            content=(
                "---\n"
                'schema_version: "1"\n'
                f'packet_id: "template_{packet_type}_sample"\n'
                f'created_at: "{iso_now()}"\n'
                f'source_project: "{state.project_key}"\n'
                f'packet_type: "{packet_type}"\n'
                f'title: "Sample {packet_type.replace("_", " ")} packet"\n'
                f'language: "{language}"\n'
                'status: "open"\n'
                "---\n\n"
                f"# Sample {packet_type.replace('_', ' ')} packet\n\n"
                "This is a valid conformance fixture.\n"
            ),
        ))
    if not (conformance / "invalid-packet.example.md").exists():
        ops.append(AdoptionOperation(
            kind="write_file",
            target=conformance / "invalid-packet.example.md",
            description="Write invalid conformance fixture",
            content=(
                "---\n"
                'schema_version: "1"\n'
                'packet_id: "invalid_example"\n'
                "---\n\n"
                "This fixture is intentionally invalid because it omits required packet fields.\n"
            ),
        ))

    # 5. Copy inbox content
    if not state.inbox_naturally_preserved and state.current_inbox_path and state.current_inbox_path.exists():
        new_inbox = target / "inbox"
        for f in sorted(state.current_inbox_path.iterdir()):
            if not f.is_file():
                continue
            dest = new_inbox / f.name
            if dest.exists() and f.read_bytes() == dest.read_bytes():
                continue
            ops.append(AdoptionOperation(
                kind="copy_file",
                target=dest,
                description=f"Copy inbox file {f.name}",
                source=f,
            ))

    # 6. Rewrite registry
    if state.needs_registry_rewrite:
        ops.append(AdoptionOperation(
            kind="rewrite_registry",
            target=REGISTRY_LOCAL_PATH,
            description=f"Set router_root_path, remove inbox_path for {state.project_key}",
        ))

    return ops


def execute_adoption(state: AdoptionState, operations: list[AdoptionOperation]) -> None:
    """Execute planned adoption operations."""
    for op in operations:
        if op.kind == "mkdir":
            op.target.mkdir(parents=True, exist_ok=True)
        elif op.kind == "write_file":
            op.target.parent.mkdir(parents=True, exist_ok=True)
            op.target.write_text(op.content, encoding="utf-8")
        elif op.kind == "write_json":
            op.target.parent.mkdir(parents=True, exist_ok=True)
            op.target.write_text(op.content, encoding="utf-8")
        elif op.kind == "backup_file":
            if op.source and op.source.exists():
                shutil.copy2(op.source, op.target)
        elif op.kind == "copy_file":
            op.target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(op.source, op.target)
        elif op.kind == "rewrite_registry":
            _rewrite_registry_for_adopt(state)


def _rewrite_registry_for_adopt(state: AdoptionState) -> None:
    """Update registry.local.json: set router_root_path, remove inbox_path."""
    if REGISTRY_LOCAL_PATH.exists():
        local = json.loads(REGISTRY_LOCAL_PATH.read_text(encoding="utf-8"))
    else:
        local = {"projects": {}}
    projects = local.setdefault("projects", {})
    entry = projects.setdefault(state.project_key, {})
    entry["router_root_path"] = str(state.target_router_root)
    entry.pop("inbox_path", None)
    REGISTRY_LOCAL_PATH.write_text(json.dumps(local, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_full_doctor_validation(router_root: Path, project_key: str) -> dict[str, Any]:
    """Run the same validation as doctor_command."""
    contract_path = router_root / "router-contract.json"
    if not contract_path.exists():
        return {"status": "error", "errors": [f"Missing router contract: {contract_path}"], "warnings": [], "packets": []}
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    errors = validate_router_contract(contract, expected_project_key=project_key)
    warnings: list[str] = []
    for name in ("inbox", "outbox", "conformance"):
        if not (router_root / name).exists():
            errors.append(f"Missing required router directory: {router_root / name}")
    for fixture_name in ("valid-packet.example.md", "invalid-packet.example.md"):
        if not (router_root / "conformance" / fixture_name).exists():
            errors.append(f"Missing conformance fixture: {router_root / 'conformance' / fixture_name}")
    packet_ids: set[str] = set()
    packets_report: list[dict[str, Any]] = []
    for path in outbox_packet_paths(router_root):
        metadata, body, packet_errors, normalized = parse_outbox_packet(path, expected_project_key=str(contract.get("project_key") or project_key))
        packet_id = normalized.get("source_note_id")
        if packet_id in packet_ids:
            packet_errors.append(f"{path.name}: duplicate packet_id '{packet_id}' in outbox.")
        if packet_id:
            packet_ids.add(packet_id)
        packets_report.append({"path": str(path), "packet_id": packet_id, "status": "ok" if not packet_errors else "invalid", "errors": packet_errors})
        errors.extend(packet_errors)
    return {"status": "ok" if not errors else "error", "errors": errors, "warnings": warnings, "packets": packets_report}


def adoption_follow_ups(state: AdoptionState) -> list[str]:
    """Generate follow-up suggestions."""
    follow_ups: list[str] = []
    if state.downstream_agent_config:
        follow_ups.append(f"Review downstream agent config: {state.downstream_agent_config}")
    if not state.inbox_naturally_preserved and state.inbox_content_count > 0:
        follow_ups.append(f"Verify {state.inbox_content_count} inbox files were preserved at {state.target_router_root / 'inbox'}")
    return follow_ups


def write_adoption_journal(
    state: AdoptionState,
    operations: list[AdoptionOperation],
    doctor_result: dict[str, Any],
    follow_ups: list[str],
) -> Path:
    """Persist adoption journal to state/project_router/adoptions/."""
    ADOPTIONS_DIR.mkdir(parents=True, exist_ok=True)
    journal = {
        "schema_version": "1",
        "project_key": state.project_key,
        "adopted_at": iso_now(),
        "detected_inputs": {
            "inbox_path": str(state.current_inbox_path) if state.current_inbox_path else None,
            "router_root_path": str(state.current_router_root) if state.current_router_root else None,
            "inbox_content_count": state.inbox_content_count,
        },
        "chosen_target": str(state.target_router_root),
        "operations_executed": [
            {"kind": op.kind, "target": str(op.target), "description": op.description}
            for op in operations
        ],
        "config_diff": {
            "before": {
                "inbox_path": str(state.current_inbox_path) if state.current_inbox_path else None,
                "router_root_path": str(state.current_router_root) if state.current_router_root else None,
            },
            "after": {"router_root_path": str(state.target_router_root)},
        },
        "doctor_result": doctor_result,
        "downstream_agent_config": str(state.downstream_agent_config) if state.downstream_agent_config else None,
        "manual_follow_ups": follow_ups,
        "registry_backup": next(
            (str(op.target) for op in operations if op.kind == "backup_file"),
            None,
        ),
    }
    path = ADOPTIONS_DIR / f"{state.project_key}.json"
    path.write_text(json.dumps(journal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def adopt_router_root_command(args: argparse.Namespace) -> int:
    ensure_layout()
    ADOPTIONS_DIR.mkdir(parents=True, exist_ok=True)

    use_all = getattr(args, "all", False)
    project_key = getattr(args, "project", None)
    confirm = getattr(args, "confirm", False)
    dry_run = getattr(args, "dry_run", False)
    explicit_router_root = getattr(args, "router_root", None)

    defaults, projects = load_registry(require_local=True)

    # Load shared config for language/packet_types
    shared_config = read_registry_config(REGISTRY_SHARED_PATH) if REGISTRY_SHARED_PATH.exists() else {}

    if use_all:
        if confirm:
            raise SystemExit("--all --confirm is not supported in v1. Adopt projects individually.")
        # Fleet preview
        summary: list[dict[str, Any]] = []
        for key, rule in sorted(projects.items()):
            try:
                state = resolve_adoption_state(key, rule, None)
                summary.append({
                    "project_key": key,
                    "status": state.status,
                    "current_inbox_path": str(state.current_inbox_path) if state.current_inbox_path else None,
                    "current_router_root": str(state.current_router_root) if state.current_router_root else None,
                    "target_router_root": str(state.target_router_root),
                    "inbox_content_count": state.inbox_content_count,
                    "scaffold_exists": state.scaffold_exists,
                    "scaffold_complete": state.scaffold_complete,
                })
            except SystemExit as exc:
                summary.append({
                    "project_key": key,
                    "status": "error",
                    "error": str(exc),
                })
        counts = Counter(item["status"] for item in summary)
        report = {"mode": "fleet_preview", "projects": summary, "counts": dict(counts)}
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    # Per-project mode
    if not project_key:
        raise SystemExit("Either --project or --all is required.")
    rule = projects.get(project_key)
    if not rule:
        raise SystemExit(f"Project '{project_key}' not found in registry.")

    state = resolve_adoption_state(project_key, rule, explicit_router_root)

    if state.status == "already_current":
        print(json.dumps({"status": "already_current", "project_key": project_key, "router_root": str(state.target_router_root)}, indent=2))
        return 0

    if state.inbox_collisions:
        collision_names = [str(p.name) for p in state.inbox_collisions]
        raise SystemExit(
            f"Inbox collision detected for {len(state.inbox_collisions)} file(s): "
            f"{', '.join(collision_names)}. Resolve manually before adopting."
        )

    operations = plan_adoption_operations(state, shared_config)

    if not confirm or dry_run:
        preview = {
            "mode": "preview",
            "project_key": project_key,
            "status": state.status,
            "target_router_root": str(state.target_router_root),
            "inbox_content_count": state.inbox_content_count,
            "inbox_naturally_preserved": state.inbox_naturally_preserved,
            "operations": [{"kind": op.kind, "target": str(op.target), "description": op.description} for op in operations],
            "downstream_agent_config": str(state.downstream_agent_config) if state.downstream_agent_config else None,
        }
        print(json.dumps(preview, indent=2, ensure_ascii=False))
        return 0

    # Execute
    execute_adoption(state, operations)
    doctor_result = run_full_doctor_validation(state.target_router_root, project_key)
    follow_ups = adoption_follow_ups(state)
    journal_path = write_adoption_journal(state, operations, doctor_result, follow_ups)

    report = {
        "mode": "executed",
        "project_key": project_key,
        "target_router_root": str(state.target_router_root),
        "operations_count": len(operations),
        "doctor_status": doctor_result["status"],
        "doctor_errors": doctor_result.get("errors", []),
        "follow_ups": follow_ups,
        "journal": str(journal_path),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if doctor_result["status"] == "ok" else 1


def resolve_doctor_target(args: argparse.Namespace) -> tuple[Path, str, dict[str, Any] | None]:
    if getattr(args, "router_root", None):
        router_root = Path(args.router_root).resolve()
        contract = json.loads(project_contract_path(router_root).read_text(encoding="utf-8"))
        return router_root, str(contract.get("project_key") or ""), None
    defaults, projects = load_registry(require_local=True)
    if getattr(args, "project", None):
        key = args.project
        project = projects.get(key)
        if not project:
            raise SystemExit(f"Project '{key}' not found. Check spelling or registry.shared.json.")
        if project.router_root_path is None:
            if project.inbox_path is not None:
                raise SystemExit(
                    f"Project '{key}' has inbox_path but no router_root_path. "
                    f"Run: python3 scripts/project_router.py adopt-router-root --project {key}"
                )
            raise SystemExit(
                f"Project '{key}' has no router_root_path configured. "
                f"Run: python3 scripts/project_router.py adopt-router-root --project {key} --router-root <path>"
            )
        return project.router_root_path, project.key, defaults
    raise SystemExit("doctor requires either --router-root or --project.")


def doctor_command(args: argparse.Namespace) -> int:
    ensure_layout()
    router_root, expected_project_key, _ = resolve_doctor_target(args)
    contract_path = project_contract_path(router_root)
    if not contract_path.exists():
        raise SystemExit(f"Missing router contract: {contract_path}")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    errors = validate_router_contract(contract, expected_project_key=expected_project_key or None, strict=args.strict)
    warnings: list[str] = []
    required_dirs = [
        router_root / "inbox",
        router_root / "outbox",
        router_root / "conformance",
    ]
    for path in required_dirs:
        if not path.exists():
            errors.append(f"Missing required router directory: {path}")
    for fixture_name in ("valid-packet.example.md", "invalid-packet.example.md"):
        fixture = router_root / "conformance" / fixture_name
        if not fixture.exists():
            errors.append(f"Missing conformance fixture: {fixture}")
    packet_ids: set[str] = set()
    packets_report: list[dict[str, Any]] = []
    packet_candidates = [Path(args.packet).resolve()] if getattr(args, "packet", None) else outbox_packet_paths(router_root)
    for candidate in packet_candidates:
        if not candidate.exists():
            errors.append(f"Packet path does not exist: {candidate}")
    for path in packet_candidates:
        if not path.exists():
            continue
        metadata, body, packet_errors, normalized = parse_outbox_packet(
            path,
            expected_project_key=str(contract.get("project_key") or expected_project_key),
            strict=args.strict,
        )
        packet_id = normalized.get("source_note_id")
        if packet_id in packet_ids:
            packet_errors.append(f"{path.name}: duplicate packet_id '{packet_id}' in outbox.")
        if packet_id:
            packet_ids.add(packet_id)
        packets_report.append(
            {
                "path": str(path),
                "packet_id": packet_id,
                "status": "ok" if not packet_errors else "invalid",
                "errors": packet_errors,
            }
        )
        errors.extend(packet_errors)
    report = {
        "status": "ok" if not errors else "error",
        "project_key": contract.get("project_key"),
        "router_root": str(router_root),
        "strict": args.strict,
        "errors": errors,
        "warnings": warnings,
        "packets": packets_report,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


def configured_scan_projects(projects: dict[str, ProjectRule], *, include_self: bool) -> list[tuple[str, Path]]:
    targets = [(project.key, project.router_root_path) for project in projects.values() if project.router_root_path is not None]
    if include_self and project_contract_path(LOCAL_ROUTER_DIR).exists():
        contract = json.loads(project_contract_path(LOCAL_ROUTER_DIR).read_text(encoding="utf-8"))
        self_key = str(contract.get("project_key") or "self")
        if all(key != self_key for key, _ in targets):
            targets.append((self_key, LOCAL_ROUTER_DIR))
    return [(key, path) for key, path in targets if path is not None]


def scan_outboxes_command(args: argparse.Namespace) -> int:
    ensure_layout()
    _, projects = load_registry(require_local=True)
    acquire_scan_lock()
    try:
        state = load_outbox_scan_state()
        ingested = 0
        unchanged = 0
        invalid = 0
        content_changed = 0
        scanned_packets: list[dict[str, Any]] = []
        for project_key, router_root in configured_scan_projects(projects, include_self=args.include_self):
            contract_path = project_contract_path(router_root)
            if not contract_path.exists():
                errors = [f"Missing project-router contract at {contract_path}"]
                invalid += 1
                write_parse_error_note(project_key=project_key, source_path=contract_path, note_id="router-contract", errors=errors)
                update_scan_state(state, project_key, "router-contract", {
                    "source_path": str(contract_path),
                    "status": "invalid",
                    "error_code": "MISSING_CONTRACT",
                    "error_detail": "; ".join(errors),
                    "last_seen_at": iso_now(),
                })
                scanned_packets.append(
                    {
                        "project_key": project_key,
                        "packet": str(contract_path),
                        "status": "invalid",
                        "errors": errors,
                    }
                )
                continue
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract_errors = validate_router_contract(contract, expected_project_key=project_key, strict=args.strict)
            if contract_errors:
                invalid += 1
                write_parse_error_note(project_key=project_key, source_path=contract_path, note_id="router-contract", errors=contract_errors)
                update_scan_state(state, project_key, "router-contract", {
                    "source_path": str(contract_path),
                    "status": "invalid",
                    "error_code": "INVALID_CONTRACT",
                    "error_detail": "; ".join(contract_errors),
                    "last_seen_at": iso_now(),
                })
                scanned_packets.append(
                    {
                        "project_key": project_key,
                        "packet": str(contract_path),
                        "status": "invalid",
                        "errors": contract_errors,
                    }
                )
                continue
            # Contract is valid — update scan state and reconcile error notes
            update_scan_state(state, project_key, "router-contract", {
                "source_path": str(contract_path),
                "status": "valid",
                "error_code": None,
                "error_detail": None,
                "last_seen_at": iso_now(),
            })
            error_dir = review_dir_for(PROJECT_ROUTER_SOURCE, "parse_errors")
            contract_note_id = "router-contract"
            stable_contract_error = error_dir / f"{slugify(project_key)}--{contract_note_id}.md"
            stable_contract_error.unlink(missing_ok=True)
            for legacy_contract_error in error_dir.glob(f"*--{slugify(project_key)}--{contract_note_id}.md"):
                legacy_contract_error.unlink(missing_ok=True)
            for packet_path in outbox_packet_paths(router_root):
                metadata, body, errors, normalized = parse_outbox_packet(packet_path, expected_project_key=project_key, strict=args.strict)
                note_id = normalized.get("source_note_id") or slugify(packet_path.stem) or "invalid-packet"
                entry = scan_state_entry(state, project_key, note_id)
                if errors:
                    invalid += 1
                    parse_error_path = write_parse_error_note(project_key=project_key, source_path=packet_path, note_id=note_id, errors=errors, metadata=metadata)
                    update_scan_state(
                        state,
                        project_key,
                        note_id,
                        {
                            "source_path": str(packet_path),
                            "content_hash": normalized.get("content_hash"),
                            "first_seen_at": (entry or {}).get("first_seen_at") or iso_now(),
                            "last_seen_at": iso_now(),
                            "status": "invalid",
                            "raw_path": None,
                            "error_code": "INVALID_PACKET",
                            "error_detail": "; ".join(errors),
                            "parse_error_path": str(parse_error_path),
                        },
                    )
                    scanned_packets.append({"project_key": project_key, "packet": str(packet_path), "status": "invalid", "errors": errors})
                    continue
                # Reconcile: clean up parse error notes for this now-valid packet
                error_dir = review_dir_for(PROJECT_ROUTER_SOURCE, "parse_errors")
                stable_error = error_dir / f"{slugify(project_key)}--{note_id}.md"
                stable_error.unlink(missing_ok=True)
                for legacy_error in error_dir.glob(f"*--{slugify(project_key)}--{note_id}.md"):
                    legacy_error.unlink(missing_ok=True)
                status = "ingested"
                if entry and entry.get("content_hash") == normalized.get("content_hash"):
                    unchanged += 1
                    update_scan_state(
                        state,
                        project_key,
                        note_id,
                        {
                            **entry,
                            "source_path": str(packet_path),
                            "last_seen_at": iso_now(),
                            "status": "unchanged",
                        },
                    )
                    scanned_packets.append({"project_key": project_key, "packet": str(packet_path), "status": "unchanged"})
                    continue
                if entry and entry.get("content_hash") != normalized.get("content_hash"):
                    status = "content_changed"
                    content_changed += 1
                else:
                    ingested += 1
                payload = build_project_router_raw_payload(project_key=project_key, source_path=packet_path, metadata=metadata, body=body, normalized=normalized)
                raw_dir = raw_dir_for(PROJECT_ROUTER_SOURCE, project_key)
                raw_path = existing_artifact_path(raw_dir, note_id, ".json") or (raw_dir / f"{normalize_timestamp(str(metadata.get('created_at')))}--{note_id}.json")
                raw_dir.mkdir(parents=True, exist_ok=True)
                raw_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                update_scan_state(
                    state,
                    project_key,
                    note_id,
                    {
                        "source_path": str(packet_path),
                        "content_hash": normalized.get("content_hash"),
                        "first_seen_at": (entry or {}).get("first_seen_at") or iso_now(),
                        "last_seen_at": iso_now(),
                        "status": status,
                        "raw_path": str(raw_path),
                        "error_code": None,
                        "error_detail": None,
                    },
                )
                scanned_packets.append({"project_key": project_key, "packet": str(packet_path), "status": status, "raw_path": str(raw_path)})
        save_outbox_scan_state(state)
        print(
            json.dumps(
                {
                    "ingested": ingested,
                    "content_changed": content_changed,
                    "unchanged": unchanged,
                    "invalid": invalid,
                    "include_self": args.include_self,
                    "packets": scanned_packets,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    finally:
        release_scan_lock()


def migrate_note_references(path: Path, replacements: dict[str, str]) -> None:
    metadata, body = read_note(path)
    changed = False
    for key in ("canonical_path", "raw_payload_path", "compiled_from_path", "compiled_path"):
        value = metadata.get(key)
        if value in replacements:
            metadata[key] = replacements[value]
            changed = True
    if changed:
        write_note(path, metadata, body)


def migrate_decision_packet(path: Path, replacements: dict[str, str]) -> None:
    packet = json.loads(path.read_text(encoding="utf-8"))
    changed = False
    for key in ("canonical_path", "raw_payload_path"):
        value = packet.get(key)
        if value in replacements:
            packet[key] = replacements[value]
            changed = True
    compiled = packet.get("compiled")
    if isinstance(compiled, dict) and compiled.get("path") in replacements:
        compiled["path"] = replacements[compiled["path"]]
        changed = True
    dispatch = packet.get("dispatch")
    if isinstance(dispatch, dict) and dispatch.get("compiled_path") in replacements:
        dispatch["compiled_path"] = replacements[dispatch["compiled_path"]]
        changed = True
    if changed:
        path.write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def migrate_source_layout_command(args: argparse.Namespace) -> int:
    ensure_layout()
    operations = legacy_source_layout_operations()
    replacements: dict[str, str] = {str(src): str(dest) for src, dest in operations}
    if args.dry_run or not args.confirm:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "operations": [{"from": str(src), "to": str(dest)} for src, dest in operations],
                    "confirm_required": not args.confirm,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    for src, dest in operations:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
    for note_path in iter_normalized_files_by_source(set(KNOWN_SOURCES)) + iter_compiled_files_by_source(set(KNOWN_SOURCES)):
        migrate_note_references(note_path, replacements)
    for packet_path in sorted(DECISIONS_DIR.glob("*.json")):
        migrate_decision_packet(packet_path, replacements)
    if DISCOVERY_REPORT_PATH.exists():
        report = json.loads(DISCOVERY_REPORT_PATH.read_text(encoding="utf-8"))
        payload = json.dumps(report)
        for old, new in replacements.items():
            payload = payload.replace(old, new)
        DISCOVERY_REPORT_PATH.write_text(json.dumps(json.loads(payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "dry_run": False,
                "migrated": len(operations),
                "operations": [{"from": str(src), "to": str(dest)} for src, dest in operations],
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


def count_manifests(directory: Path | None = None) -> int:
    return len(list_filesystem_manifests(directory))


def status_command(args: argparse.Namespace) -> int:
    ensure_layout()
    sources = parse_source_filter(getattr(args, "source", None))
    voicenotes_raw = count_raw(raw_dir_for(VOICE_SOURCE)) if VOICE_SOURCE in sources else 0
    voicenotes_normalized = count_markdown(normalized_dir_for(VOICE_SOURCE)) if VOICE_SOURCE in sources else 0
    voicenotes_compiled = count_markdown(compiled_dir_for(VOICE_SOURCE)) if VOICE_SOURCE in sources else 0
    project_router_raw = sum(count_raw(path) for path in iter_source_dirs("raw", {PROJECT_ROUTER_SOURCE})) if PROJECT_ROUTER_SOURCE in sources else 0
    project_router_normalized = sum(count_markdown(path) for path in iter_source_dirs("normalized", {PROJECT_ROUTER_SOURCE})) if PROJECT_ROUTER_SOURCE in sources else 0
    project_router_compiled = sum(count_markdown(path) for path in iter_source_dirs("compiled", {PROJECT_ROUTER_SOURCE})) if PROJECT_ROUTER_SOURCE in sources else 0
    filesystem_raw = count_manifests() if FILESYSTEM_SOURCE in sources else 0
    filesystem_normalized = count_markdown(normalized_dir_for(FILESYSTEM_SOURCE)) if FILESYSTEM_SOURCE in sources else 0
    filesystem_compiled = count_markdown(compiled_dir_for(FILESYSTEM_SOURCE)) if FILESYSTEM_SOURCE in sources else 0
    scan_state = load_outbox_scan_state() if PROJECT_ROUTER_SOURCE in sources else None
    legacy_backlog = len(legacy_source_layout_operations())

    summary: dict[str, Any] = {
        "sources": sorted(sources),
        "raw": {
            "voicenotes": voicenotes_raw,
            "project_router": project_router_raw,
            "filesystem": filesystem_raw,
        },
        "normalized": {
            "voicenotes": voicenotes_normalized,
            "project_router": project_router_normalized,
            "filesystem": filesystem_normalized,
        },
        "compiled": {
            "voicenotes": voicenotes_compiled,
            "project_router": project_router_compiled,
            "filesystem": filesystem_compiled,
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
        },
        "dispatched": sum(count_markdown(path) for path in DISPATCHED_DIR.glob("*") if path.is_dir()),
        "processed": count_markdown(PROCESSED_DIR),
        "decision_packets": len(list(DECISIONS_DIR.glob("*.json"))),
        "inbox": _count_inbox_states(),
        "legacy_backlog": legacy_backlog,
        "scan_state_path": str(OUTBOX_SCAN_STATE_PATH),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def _count_inbox_states() -> dict[str, int]:
    """Count inbox packets by status for the status command."""
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


def inbox_intake_command(args: argparse.Namespace) -> int:
    ensure_layout()
    dry_run = getattr(args, "dry_run", False)
    packets = list_inbox_packets()
    ingested = 0
    skipped = 0
    errors = 0

    for path, metadata, body in packets:
        try:
            packet_id = extract_packet_id(path)
        except SystemExit as exc:
            sys.stderr.write(f"Error: {exc}\n")
            errors += 1
            continue

        existing_state = load_inbox_packet_state(packet_id)
        if existing_state is not None:
            skipped += 1
            continue

        is_brief = (metadata.get("capture_kind") or metadata.get("inferred_keywords")) and not metadata.get("packet_id")
        if is_brief:
            converted_meta, body = convert_brief_to_packet(metadata, body)
            if not dry_run:
                sys.stderr.write(f"Converting compiled brief '{packet_id}' to protocol packet.\n")
            metadata = converted_meta

        if "packet_id" not in metadata:
            metadata["packet_id"] = packet_id

        required = ("schema_version", "packet_id", "created_at", "source_project", "packet_type", "title", "language", "status")
        missing = [f for f in required if f not in metadata or metadata.get(f) in (None, "", [])]
        if missing:
            sys.stderr.write(f"Error: {path.name} missing required fields: {', '.join(missing)}\n")
            if not dry_run:
                save_inbox_packet_state(packet_id, {
                    "packet_id": packet_id,
                    "status": "error",
                    "error_detail": f"Missing required fields: {', '.join(missing)}",
                    "transitions": [{"status": "error", "timestamp": iso_now(), "notes": f"Missing: {', '.join(missing)}"}],
                })
            errors += 1
            continue

        if dry_run:
            print(f"[dry-run] Would intake: {packet_id} ({metadata.get('packet_type', '?')})")
            ingested += 1
            continue

        archive_dir = LOCAL_ROUTER_ARCHIVE_DIR / packet_id
        archive_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(path), str(archive_dir / "original.md"))

        now = iso_now()
        save_inbox_packet_state(packet_id, {
            "packet_id": packet_id,
            "status": "open",
            "title": metadata.get("title", ""),
            "packet_type": metadata.get("packet_type", ""),
            "source_project": metadata.get("source_project", ""),
            "created_at": metadata.get("created_at", ""),
            "ingested_at": now,
            "transitions": [{"status": "open", "timestamp": now, "notes": "Ingested via inbox-intake"}],
        })

        path.unlink()
        ingested += 1

    summary = {"ingested": ingested, "skipped": skipped, "errors": errors}
    print(json.dumps(summary, indent=2))
    return 0


def inbox_status_command(args: argparse.Namespace) -> int:
    ensure_layout()
    show_all = getattr(args, "all", False)
    packet_id_filter = getattr(args, "packet_id", None)
    terminal_states = {"applied", "blocked", "rejected", "error"}

    results: list[dict[str, Any]] = []
    if INBOX_STATUS_DIR.exists():
        for state_path in sorted(INBOX_STATUS_DIR.glob("*.json")):
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            if packet_id_filter and state.get("packet_id") != packet_id_filter:
                continue

            if not show_all and state.get("status") in terminal_states:
                continue

            results.append(state)

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

    output: dict[str, Any] = {"packets": results, "unprocessed_in_inbox": unprocessed}
    if packet_id_filter and len(results) == 1:
        output = results[0]
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


def inbox_ack_command(args: argparse.Namespace) -> int:
    ensure_layout()
    packet_id = require_valid_note_id(args.packet_id, field="packet-id")
    new_status = args.status
    notes = getattr(args, "notes", None) or ""
    ref = getattr(args, "ref", None) or ""

    state = load_inbox_packet_state(packet_id)
    if state is None:
        raise SystemExit(f"No inbox state found for packet '{packet_id}'. Run inbox-intake first.")

    current_status = state.get("status", "")
    terminal_states = {"applied", "blocked", "rejected", "error"}

    if current_status in terminal_states:
        raise SystemExit(f"Packet '{packet_id}' is already in terminal state '{current_status}'. Cannot re-ack.")

    now = iso_now()
    state["status"] = new_status
    transitions = state.get("transitions", [])
    transition: dict[str, Any] = {"status": new_status, "timestamp": now, "notes": notes}
    if ref:
        transition["ref"] = ref
    transitions.append(transition)
    state["transitions"] = transitions

    save_inbox_packet_state(packet_id, state)

    if new_status in {"applied", "blocked", "rejected"}:
        contract_path = LOCAL_ROUTER_DIR / "router-contract.json"
        source_project = "project_router_template"
        language = "en"
        if contract_path.exists():
            try:
                contract = json.loads(contract_path.read_text(encoding="utf-8"))
                source_project = contract.get("project_key", source_project)
                language = contract.get("default_language", language)
            except (json.JSONDecodeError, OSError):
                pass

        ack_packet_id = f"ack_{packet_id}"
        ack_meta: dict[str, Any] = {
            "schema_version": "1",
            "packet_id": ack_packet_id,
            "created_at": now,
            "source_project": source_project,
            "packet_type": "ack",
            "title": f"Acknowledgement: {state.get('title', packet_id)}",
            "language": language,
            "status": new_status,
            "related_packet_id": packet_id,
            "resolution": new_status,
        }
        if ref:
            ack_meta["implementation_ref"] = ref
        if notes:
            ack_meta["notes"] = notes

        ack_body = f"# Acknowledgement: {state.get('title', packet_id)}\n\nPacket `{packet_id}` has been marked as **{new_status}**."
        if notes:
            ack_body += f"\n\n## Notes\n\n{notes}"
        if ref:
            ack_body += f"\n\n## Reference\n\n{ref}"

        ts_prefix = normalize_timestamp(now)
        outbox_path = LOCAL_ROUTER_DIR / "outbox" / f"{ts_prefix}--{ack_packet_id}.md"
        write_note(outbox_path, ack_meta, ack_body)
        sys.stderr.write(f"Ack packet written to {outbox_path.relative_to(ROOT)}\n")

    print(json.dumps({"packet_id": packet_id, "new_status": new_status, "timestamp": now}, indent=2))
    return 0


def context_command(args: argparse.Namespace) -> int:
    """Generate a compact Markdown briefing from repo state."""
    sections: list[str] = ["# Project Router Context", ""]

    # --- Project purpose ---
    tldr_path = ROOT / "Knowledge" / "TLDR.md"
    if tldr_path.exists():
        for line in tldr_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                sections.append(f"**Purpose:** {stripped}")
                sections.append("")
                break

    # --- Registered projects ---
    if REGISTRY_SHARED_PATH.exists():
        try:
            registry = json.loads(REGISTRY_SHARED_PATH.read_text(encoding="utf-8"))
            projects_map = registry.get("projects", {}) if isinstance(registry, dict) else {}
            keys = sorted(projects_map.keys()) if isinstance(projects_map, dict) else []
            sections.append(f"## Registered Projects ({len(keys)})")
            sections.append("")
            for k in keys:
                sections.append(f"- {k}")
            sections.append("")
        except json.JSONDecodeError:
            sections.append("## Registered Projects")
            sections.append("")
            sections.append("- **WARNING:** registry.shared.json contains invalid JSON")
            sections.append("")
        except OSError:
            pass

    # --- Pipeline state ---
    source_filter = getattr(args, "source", None)
    sources = parse_source_filter(source_filter)
    stages = {"raw": RAW_DIR, "normalized": NORMALIZED_DIR, "compiled": COMPILED_DIR,
              "review": REVIEW_DIR, "dispatched": DISPATCHED_DIR}
    sections.append("## Pipeline State")
    sections.append("")
    for stage_name, stage_dir in stages.items():
        if stage_name == "review":
            review_counts = count_pending_review_entries(sources=sources)
            if PROJECT_ROUTER_SOURCE in sources:
                review_counts[PROJECT_ROUTER_SOURCE] = review_counts.get(PROJECT_ROUTER_SOURCE, 0) + count_active_scan_state_errors()
            total = 0
            details: list[str] = []
            for source in sorted(sources):
                n = review_counts.get(source, 0)
                if n:
                    details.append(f"{source}={n}")
                    total += n
            if total:
                sections.append(f"- **{stage_name}** ({total}): {', '.join(details)}")
            continue
        if not stage_dir.exists():
            continue
        total = 0
        details: list[str] = []
        for sub in sorted(stage_dir.iterdir()):
            if not sub.is_dir():
                continue
            if sources and sub.name not in sources:
                continue
            n = len([f for f in sub.rglob("*") if f.is_file()])
            if n:
                details.append(f"{sub.name}={n}")
                total += n
        if total:
            sections.append(f"- **{stage_name}** ({total}): {', '.join(details)}")
    sections.append("")

    # --- Environment notes ---
    env_notes: list[str] = []
    if REGISTRY_LOCAL_PATH.exists():
        try:
            local_reg = json.loads(REGISTRY_LOCAL_PATH.read_text(encoding="utf-8"))
            local_projects = local_reg.get("projects", {}) if isinstance(local_reg, dict) else {}
            demo_paths = [k for k, v in local_projects.items() if isinstance(v, dict) and "demo-inboxes" in str(v.get("router_root_path", ""))]
            if demo_paths:
                env_notes.append(f"Demo mode active (demo-inboxes configured for: {', '.join(demo_paths)})")
        except json.JSONDecodeError:
            env_notes.append("WARNING: registry.local.json contains invalid JSON")
        except OSError:
            pass
    legacy_total = len(legacy_source_layout_operations())
    if legacy_total > 0:
        env_notes.append(f"Legacy layout backlog: {legacy_total} files (run migrate-source-layout)")
    parse_error_count = count_active_scan_state_errors()
    if parse_error_count > 0:
        env_notes.append(f"Active parse errors: {parse_error_count}")
    if env_notes:
        sections.append("## Environment Notes")
        sections.append("")
        for note in env_notes:
            sections.append(f"- {note}")
        sections.append("")

    # --- Available scripts ---
    scripts_dir = ROOT / "scripts"
    if scripts_dir.exists():
        sections.append("## Available Scripts")
        sections.append("")
        docstring_re = re.compile(r'^"""(.*?)"""', re.DOTALL | re.MULTILINE)
        scripts_unreadable = 0
        for script in sorted(scripts_dir.glob("*.py")):
            try:
                text = script.read_text(encoding="utf-8")
            except OSError:
                scripts_unreadable += 1
                continue
            m = docstring_re.search(text)
            if m:
                first_line = m.group(1).strip().splitlines()[0]
                sections.append(f"- `{script.name}`: {first_line}")
            else:
                sections.append(f"- `{script.name}`")
        if scripts_unreadable:
            sections.append(f"- ({scripts_unreadable} script(s) could not be read)")
        sections.append("")

    # --- Available skills ---
    seen_skills: dict[str, str] = {}
    skills_unreadable = 0
    for pattern in [".agents/skills/*/SKILL.md", ".claude/skills/*/SKILL.md", ".codex/skills/*/SKILL.md"]:
        for skill_path in sorted(ROOT.glob(pattern)):
            skill_name = skill_path.parent.name
            if skill_name in seen_skills:
                continue
            try:
                for line in skill_path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("# "):
                        seen_skills[skill_name] = line[2:].strip()
                        break
                else:
                    seen_skills[skill_name] = skill_name
            except OSError:
                seen_skills[skill_name] = f"{skill_name} (unreadable)"
                skills_unreadable += 1
    if seen_skills:
        sections.append("## Available Skills")
        sections.append("")
        for name, heading in sorted(seen_skills.items()):
            sections.append(f"- **{name}**: {heading}")
        sections.append("")

    # --- ADR index ---
    adr_dir = ROOT / "Knowledge" / "ADR"
    if adr_dir.exists():
        adr_files = sorted(adr_dir.glob("[0-9]*.md"))
        if adr_files:
            sections.append("## ADR Index")
            sections.append("")
            adr_unreadable = 0
            for adr in adr_files:
                status = "unknown"
                try:
                    for line in adr.read_text(encoding="utf-8").splitlines():
                        stripped = line.strip().strip("*").strip()
                        if stripped.lower().startswith("status:"):
                            status = stripped.split(":", 1)[1].strip().strip("*").strip()
                            break
                except OSError:
                    status = "unreadable"
                    adr_unreadable += 1
                stem = adr.stem
                sections.append(f"- {stem}: {status}")
            sections.append("")

    # --- Safety invariants ---
    adr005 = ROOT / "Knowledge" / "ADR" / "005-safety-invariants.md"
    if adr005.exists():
        try:
            text = adr005.read_text(encoding="utf-8")
            in_decision = False
            invariants: list[str] = []
            for line in text.splitlines():
                if line.strip().startswith("## Decision"):
                    in_decision = True
                    continue
                if in_decision and line.strip().startswith("## "):
                    break
                stripped_line = line.strip().lstrip("#").strip()
                if in_decision and re.match(r"^\d+\.\s", stripped_line):
                    invariants.append(stripped_line)
            if invariants:
                sections.append("## Safety Invariants")
                sections.append("")
                for inv in invariants:
                    sections.append(f"- {inv}")
                sections.append("")
        except OSError:
            pass

    # --- Where to find what ---
    context_pack = ROOT / "Knowledge" / "ContextPack.md"
    if context_pack.exists():
        try:
            table_lines = [line for line in context_pack.read_text(encoding="utf-8").splitlines() if line.startswith("|")]
            if table_lines:
                sections.append("## Where to Find What")
                sections.append("")
                sections.extend(table_lines)
                sections.append("")
        except OSError:
            pass

    output = "\n".join(sections).rstrip() + "\n"
    print(output, end="")
    return 0


def add_source_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", choices=("all", *sorted(KNOWN_SOURCES)), default="all", help="Filter work to one source or use all sources.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    normalize = subparsers.add_parser("normalize", help="Copy raw notes into canonical normalized notes.")
    add_source_argument(normalize)
    normalize.set_defaults(func=normalize_command)

    triage = subparsers.add_parser("triage", help="Classify normalized notes conservatively.")
    add_source_argument(triage)
    triage.add_argument("--all", action="store_true", help="Label the output JSON mode as 'all' instead of 'default'. Does not change triage behaviour.")
    triage.set_defaults(func=triage_command)

    compile_parser = subparsers.add_parser("compile", help="Generate project-ready compiled note packages from canonical notes.")
    add_source_argument(compile_parser)
    compile_parser.add_argument("--note-id", dest="note_ids", action="append", help="Compile only the selected source_note_id values.")
    compile_parser.set_defaults(func=compile_command)

    dispatch = subparsers.add_parser("dispatch", help="Preview or manually write classified notes to downstream project inboxes.")
    add_source_argument(dispatch)
    dispatch.add_argument("--dry-run", action="store_true", help="Show planned writes without touching downstream projects.")
    dispatch.add_argument("--note-id", dest="note_ids", action="append", help="Explicit source_note_id allowlist for real dispatch.")
    dispatch.add_argument(
        "--confirm-user-approval",
        action="store_true",
        help="Required for real writes after the user explicitly confirms the dispatch.",
    )
    dispatch.set_defaults(func=dispatch_command)

    review = subparsers.add_parser("review", help="List or inspect decision packets.")
    add_source_argument(review)
    review.add_argument("--all", action="store_true", help="Include already reviewed packets.")
    review.add_argument("--note-id", help="Show the full decision packet for one source_note_id.")
    review.set_defaults(func=review_command)

    discover = subparsers.add_parser("discover", help="Analyze pending-project notes and suggest emerging buckets.")
    add_source_argument(discover)
    discover.set_defaults(func=discover_command)

    decide = subparsers.add_parser("decide", help="Record the user's review decision for one note.")
    add_source_argument(decide)
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

    scan_outboxes = subparsers.add_parser("scan-outboxes", help="Read downstream project outboxes without mutating them.")
    scan_outboxes.add_argument("--include-self", action="store_true", help="Also scan this repository's local router/outbox if configured.")
    scan_outboxes.add_argument("--strict", action="store_true", help="Treat protocol warnings as hard failures while scanning.")
    scan_outboxes.set_defaults(func=scan_outboxes_command)

    doctor = subparsers.add_parser("doctor", help="Validate a router contract and outbox surface.")
    doctor.add_argument("--router-root", help="Direct path to a router root for local validation.")
    doctor.add_argument("--project", help="Project key from the central registry for validation.")
    doctor.add_argument("--packet", help="Reserved flag for validating a single packet path.")
    doctor.add_argument("--strict", action="store_true", help="Treat warnings as errors.")
    doctor.set_defaults(func=doctor_command)

    migrate = subparsers.add_parser("migrate-source-layout", help="Move legacy flat data folders into source-aware storage.")
    migrate.add_argument("--dry-run", action="store_true", help="Show the planned moves without mutating files.")
    migrate.add_argument("--confirm", action="store_true", help="Apply the migration.")
    migrate.set_defaults(func=migrate_source_layout_command)

    status = subparsers.add_parser("status", help="Show queue counts.")
    add_source_argument(status)
    status.set_defaults(func=status_command)

    context = subparsers.add_parser("context", help="Generate a live project briefing from repo state.")
    add_source_argument(context)
    context.set_defaults(func=context_command)

    ingest = subparsers.add_parser("ingest", help="Ingest files from a configured filesystem inbox.")
    ingest.add_argument("--integration", required=True, help="Integration type (currently: filesystem).")
    ingest.add_argument("--inbox", help="Specific inbox key (default: all configured inboxes).")
    ingest.add_argument("--dry-run", action="store_true", help="List files without ingesting.")
    ingest.set_defaults(func=ingest_command)

    extract_parser = subparsers.add_parser("extract", help="List or update extraction results for filesystem notes.")
    add_source_argument(extract_parser)
    extract_parser.add_argument("--note-id", help="Note ID to update extraction for.")
    extract_parser.add_argument("--text", help="Extracted text content.")
    extract_parser.add_argument("--observations", help="JSON observations dict.")
    extract_parser.set_defaults(func=extract_command)

    init_rr = subparsers.add_parser("init-router-root", help="Create a downstream router scaffold.")
    init_rr.add_argument("--project", required=True, help="Project key (must exist in registry.shared.json).")
    init_rr.add_argument("--router-root", required=True, help="Absolute path to the router directory.")
    init_rr.add_argument("--packet-types", help="Comma-separated packet types (default: improvement_proposal,question,insight).")
    init_rr.set_defaults(func=init_router_root_command)

    adopt = subparsers.add_parser(
        "adopt-router-root",
        help="Migrate a project from legacy inbox_path to router_root_path with downstream scaffold.",
    )
    adopt_target = adopt.add_mutually_exclusive_group(required=True)
    adopt_target.add_argument("--project", help="Project key to adopt.")
    adopt_target.add_argument("--all", action="store_true", help="Preview adoption status for all projects (no mutation).")
    adopt.add_argument("--router-root", help="Explicit router root (inferred from inbox_path if safe).")
    adopt.add_argument("--dry-run", action="store_true", help="Alias for preview mode.")
    adopt.add_argument("--confirm", action="store_true", help="Required to apply changes.")
    adopt.set_defaults(func=adopt_router_root_command)

    inbox_intake = subparsers.add_parser("inbox-intake", help="Validate and archive incoming inbox packets.")
    inbox_intake.add_argument("--dry-run", action="store_true", help="Preview without mutation.")
    inbox_intake.set_defaults(func=inbox_intake_command)

    inbox_status_parser = subparsers.add_parser("inbox-status", help="List inbox packet states.")
    inbox_status_parser.add_argument("--all", action="store_true", help="Include terminal states.")
    inbox_status_parser.add_argument("--packet-id", help="Show single packet detail.")
    inbox_status_parser.set_defaults(func=inbox_status_command)

    inbox_ack = subparsers.add_parser("inbox-ack", help="Acknowledge an inbox packet.")
    inbox_ack.add_argument("--packet-id", required=True, dest="packet_id", help="Packet ID to acknowledge.")
    inbox_ack.add_argument("--status", required=True, choices=("in_progress", "applied", "blocked", "rejected"), help="New status.")
    inbox_ack.add_argument("--notes", help="Optional notes for the acknowledgement.")
    inbox_ack.add_argument("--ref", help="External reference (e.g., PR URL).")
    inbox_ack.set_defaults(func=inbox_ack_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    load_local_env()
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
