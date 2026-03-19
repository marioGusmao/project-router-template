"""Routing and classification helpers for Project Router.

Language profile loading, keyword extraction, capture-kind classification,
intent classification, and note routing.  All functions preserve original logic
from cli.py — they are moved here for reuse across modules without pulling in
the full CLI surface.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any

from .paths import (
    REGISTRY_LOCAL_PATH,
    REGISTRY_SHARED_PATH,
)
from .projects import (
    ProjectRule,
    read_registry_config,
)
from .notes import ensure_note_metadata_defaults


# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

# Resolve to the parser_language_profiles.json that lives next to cli.py
# (one directory up from services/).
PARSER_LANGUAGE_PROFILES_PATH = Path(__file__).resolve().parents[1] / "parser_language_profiles.json"
PARSER_ENABLED_LANGUAGES_DEFAULTS_KEY = "enabled_parser_languages"
GENERIC_PARSER_STOPWORDS = frozenset(
    {
        "capture",
        "meeting",
        "note",
        "notes",
        "nota",
        "notas",
        "space",
        "speaker",
        "test",
        "teste",
        "uhum",
        "voice",
        "voicenotes",
        "welcome",
    }
)
PROFILE_TERM_FIELDS = (
    "stopwords",
    "summary_terms",
    "follow_up_terms",
    "calendar_terms",
    "project_idea_terms",
    "task_terms",
    "purchase_terms",
    "journal_terms",
    "task_capture_terms",
    "project_idea_capture_terms",
    "task_triggers",
    "decision_triggers",
    "open_question_triggers",
    "follow_up_triggers",
    "timeline_terms",
    "fact_terms",
)


# ---------------------------------------------------------------------------
#  Group 1: Language profile loading
# ---------------------------------------------------------------------------


def _normalize_term_list(values: Any, *, field: str, profile: str) -> tuple[str, ...]:
    if values is None:
        return ()
    if not isinstance(values, list):
        raise SystemExit(f"Parser language profile '{profile}' field '{field}' must be a list.")
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        term = str(value).strip().lower()
        if not term or term in seen:
            continue
        seen.add(term)
        normalized.append(term)
    return tuple(normalized)


def _normalize_profile_key_list(values: Any, *, source: str) -> tuple[str, ...]:
    if values is None:
        return ()
    if not isinstance(values, list) or not values:
        raise SystemExit(f"{source} must be a non-empty list.")
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = str(value).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    if not normalized:
        raise SystemExit(f"{source} must include at least one language profile key.")
    return tuple(normalized)


def registry_enabled_parser_profiles_override() -> tuple[str, ...] | None:
    defaults: dict[str, Any] = {}
    for path in (REGISTRY_SHARED_PATH, REGISTRY_LOCAL_PATH):
        if not path.exists():
            continue
        config = read_registry_config(path)
        raw_defaults = config.get("defaults") or {}
        if not isinstance(raw_defaults, dict):
            raise SystemExit(f"Registry defaults in {path} must be an object.")
        defaults.update(raw_defaults)
    raw_override = defaults.get(PARSER_ENABLED_LANGUAGES_DEFAULTS_KEY)
    if raw_override is None:
        return None
    return _normalize_profile_key_list(
        raw_override,
        source=f"Registry defaults '{PARSER_ENABLED_LANGUAGES_DEFAULTS_KEY}'",
    )


@lru_cache(maxsize=1)
def load_parser_language_profiles() -> dict[str, Any]:
    try:
        raw = json.loads(PARSER_LANGUAGE_PROFILES_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Missing parser language profile config at {PARSER_LANGUAGE_PROFILES_PATH}.") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid parser language profile config at {PARSER_LANGUAGE_PROFILES_PATH}: {exc}") from exc

    profiles = raw.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise SystemExit("Parser language profile config must define a non-empty 'profiles' object.")

    normalized_profiles: dict[str, dict[str, tuple[str, ...]]] = {}
    for raw_key, raw_profile in profiles.items():
        profile_key = str(raw_key).strip().lower()
        if not profile_key:
            raise SystemExit("Parser language profile keys cannot be empty.")
        if not isinstance(raw_profile, dict):
            raise SystemExit(f"Parser language profile '{profile_key}' must be an object.")
        normalized_profiles[profile_key] = {
            field: _normalize_term_list(raw_profile.get(field, []), field=field, profile=profile_key)
            for field in PROFILE_TERM_FIELDS
        }

    enabled_profiles_raw = registry_enabled_parser_profiles_override() or raw.get("enabled_profiles") or sorted(normalized_profiles)
    if isinstance(enabled_profiles_raw, tuple):
        enabled_profiles_values = enabled_profiles_raw
    else:
        enabled_profiles_values = _normalize_profile_key_list(
            enabled_profiles_raw,
            source="Parser language profile config 'enabled_profiles'",
        )

    enabled_profiles: list[str] = []
    for key in enabled_profiles_values:
        if key not in normalized_profiles:
            raise SystemExit(f"Enabled parser language profile '{key}' is not defined in {PARSER_LANGUAGE_PROFILES_PATH.name}.")
        if key not in enabled_profiles:
            enabled_profiles.append(key)

    return {"enabled_profiles": tuple(enabled_profiles), "profiles": normalized_profiles}


def active_parser_profile_keys() -> tuple[str, ...]:
    return load_parser_language_profiles()["enabled_profiles"]


def active_parser_profiles() -> dict[str, dict[str, tuple[str, ...]]]:
    config = load_parser_language_profiles()
    profiles = config["profiles"]
    return {key: profiles[key] for key in config["enabled_profiles"]}


def active_parser_terms(field: str) -> tuple[str, ...]:
    if field not in PROFILE_TERM_FIELDS:
        raise SystemExit(f"Unsupported parser language profile field '{field}'.")
    ordered: list[str] = []
    seen: set[str] = set()
    for profile in active_parser_profiles().values():
        for value in profile.get(field, ()):
            if value in seen:
                continue
            seen.add(value)
            ordered.append(value)
    return tuple(ordered)


def active_parser_stopwords() -> set[str]:
    return set(GENERIC_PARSER_STOPWORDS) | set(active_parser_terms("stopwords"))


# ---------------------------------------------------------------------------
#  Group 2: Language detection
# ---------------------------------------------------------------------------


def contains_any_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def detect_note_languages(metadata: dict[str, Any], body: str) -> dict[str, Any]:
    sample_parts = [str(metadata.get("title") or "")]
    sample_parts.extend(str(tag).strip() for tag in metadata.get("tags", []) if str(tag).strip())
    sample_parts.append(body_excerpt(body, limit=1200))
    sample = " ".join(part for part in sample_parts if part).lower()
    sample_tokens = re.findall(r"[a-z0-9à-ÿ][a-z0-9à-ÿ_-]{1,}", sample)
    if not sample_tokens:
        return {
            "source_language": "unknown",
            "language_confidence": 0.0,
            "matched_languages": [],
            "mixed_languages": False,
            "active_parser_languages": list(active_parser_profile_keys()),
        }

    scores: list[tuple[str, int]] = []
    for profile_key, profile in active_parser_profiles().items():
        stopword_hits = sum(1 for token in sample_tokens if token in profile.get("stopwords", ()))
        phrase_hits = 0
        for field in PROFILE_TERM_FIELDS:
            if field == "stopwords":
                continue
            phrase_hits += sum(1 for term in profile.get(field, ()) if term and term in sample)
        score = stopword_hits + (2 * phrase_hits)
        if score > 0:
            scores.append((profile_key, score))

    if not scores:
        return {
            "source_language": "unknown",
            "language_confidence": 0.0,
            "matched_languages": [],
            "mixed_languages": False,
            "active_parser_languages": list(active_parser_profile_keys()),
        }

    scores.sort(key=lambda item: item[1], reverse=True)
    total = sum(score for _, score in scores)
    top_language, top_score = scores[0]
    second_score = scores[1][1] if len(scores) > 1 else 0
    confidence = round(min(0.95, top_score / max(1, total)), 2)
    mixed_languages = len(scores) > 1 and second_score >= max(2, int(top_score * 0.6))
    matched_languages = [language for language, _ in scores]
    return {
        "source_language": top_language,
        "language_confidence": confidence,
        "matched_languages": matched_languages,
        "mixed_languages": mixed_languages,
        "active_parser_languages": list(active_parser_profile_keys()),
    }


# ---------------------------------------------------------------------------
#  Group 3: Keyword extraction
# ---------------------------------------------------------------------------


def body_excerpt(body: str, limit: int = 240) -> str:
    compact = re.sub(r"\s+", " ", body).strip()
    return compact[:limit]


def keyword_tokens(text: str) -> list[str]:
    lowered = text.lower()
    tokens = re.findall(r"[a-z0-9à-ÿ][a-z0-9à-ÿ_-]{2,}", lowered)
    stopwords = active_parser_stopwords()
    return [token for token in tokens if token not in stopwords and not token.isdigit()]


def extract_keywords(metadata: dict[str, Any], body: str, *, limit: int = 8) -> list[str]:
    counter: Counter[str] = Counter()
    capture_kind = metadata.get("capture_kind") or classify_capture_kind(metadata, body)[0]
    title_tokens = keyword_tokens(str(metadata.get("title") or ""))
    body_source = body_excerpt(body, limit=600) if capture_kind in {"meeting_recording", "meeting_summary"} else body
    body_tokens = keyword_tokens(body_source)
    tag_tokens = [str(tag).strip().lower() for tag in metadata.get("tags", []) if str(tag).strip()]
    stopwords = active_parser_stopwords()

    for token in title_tokens:
        counter[token] += 4 if capture_kind in {"meeting_recording", "meeting_summary"} else 3
    for token in body_tokens:
        counter[token] += 1
    for token in tag_tokens:
        if token not in stopwords:
            counter[token] += 4

    return [token for token, _ in counter.most_common(limit)]


def note_keyword_set(metadata: dict[str, Any]) -> set[str]:
    values = []
    values.extend(str(tag).strip().lower() for tag in metadata.get("tags", []))
    values.extend(str(tag).strip().lower() for tag in metadata.get("user_keywords", []))
    values.extend(str(tag).strip().lower() for tag in metadata.get("inferred_keywords", []))
    stopwords = active_parser_stopwords()
    return {value for value in values if value and value not in stopwords}


# ---------------------------------------------------------------------------
#  Group 4: Classification (includes extract_signal_list as internal helper)
# ---------------------------------------------------------------------------


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
    if contains_any_term(title, active_parser_terms("summary_terms")):
        signals.append("title:summary")
    if contains_any_term(title, active_parser_terms("follow_up_terms")):
        signals.append("title:follow_up")
    if contains_any_term(title, active_parser_terms("calendar_terms")):
        signals.append("title:calendar")
    if contains_any_term(title, active_parser_terms("project_idea_terms")):
        signals.append("title:project_idea")
    if contains_any_term(title, active_parser_terms("task_terms")):
        signals.append("title:task")
    if contains_any_term(title, active_parser_terms("purchase_terms")):
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
    project_idea_terms = active_parser_terms("project_idea_terms")
    calendar_terms = active_parser_terms("calendar_terms")
    purchase_terms = active_parser_terms("purchase_terms")
    task_capture_terms = active_parser_terms("task_capture_terms")
    project_idea_capture_terms = active_parser_terms("project_idea_capture_terms")
    journal_terms = active_parser_terms("journal_terms")

    if "tag:meeting" in signal_set or "recording_type:2" in signal_set or "body:speaker_markers" in signal_set:
        if "title:summary" in signal_set:
            return "meeting_summary", signals
        return "meeting_recording", signals
    if any(token in title for token in ("automation", "integration", "codex", "obsidian")) or contains_any_term(title, project_idea_terms):
        return "project_idea", signals
    if "title:calendar" in signal_set or contains_any_term(compact_body, calendar_terms):
        return "calendar_change", signals
    if "title:purchase" in signal_set or contains_any_term(compact_body, purchase_terms):
        return "purchase_record", signals
    if "title:task" in signal_set or contains_any_term(compact_body, task_capture_terms):
        return "task_capture", signals
    if "title:project_idea" in signal_set or contains_any_term(compact_body, project_idea_capture_terms):
        return "project_idea", signals
    if contains_any_term(title, journal_terms) or contains_any_term(compact_body, journal_terms):
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
    metadata.update(detect_note_languages(metadata, body))
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


# ---------------------------------------------------------------------------
#  Group 5: Routing
# ---------------------------------------------------------------------------


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
