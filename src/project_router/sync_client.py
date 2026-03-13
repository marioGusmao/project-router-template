"""Direct VoiceNotes client using the OpenClaw-compatible integration token."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_URL = "https://api.voicenotes.com/api/integrations/open-claw"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = REPO_ROOT / "state" / "sync_state.json"
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/133.0.0.0 Safari/537.36"
    ),
}
NOTE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_local_env() -> None:
    load_env_file(REPO_ROOT / ".env")
    load_env_file(REPO_ROOT / ".env.local")


def require_api_key() -> str:
    load_local_env()
    api_key = os.environ.get("VOICENOTES_API_KEY")
    if not api_key:
        raise SystemExit("VOICENOTES_API_KEY is not set.")
    return api_key


def load_sync_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"last_synced_at": None, "last_synced_ids": []}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        "last_synced_at": raw.get("last_synced_at"),
        "last_synced_ids": list(raw.get("last_synced_ids") or []),
    }


def save_sync_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def merge_sync_state(existing: dict[str, Any], newest_created_at: str | None, newest_ids: list[str]) -> dict[str, Any]:
    last_synced_at = existing.get("last_synced_at")
    last_synced_ids = list(existing.get("last_synced_ids") or [])
    if newest_created_at and (not last_synced_at or newest_created_at > last_synced_at):
        last_synced_at = newest_created_at
        last_synced_ids = newest_ids
    elif newest_created_at and newest_created_at == last_synced_at:
        for note_id in newest_ids:
            if note_id not in last_synced_ids:
                last_synced_ids.append(note_id)

    return {
        "last_synced_at": last_synced_at,
        "last_synced_ids": last_synced_ids,
    }


def request_json(
    method: str,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
) -> Any:
    api_key = require_api_key()
    url = BASE_URL + path
    if query:
        from urllib.parse import urlencode

        clean_query = {k: v for k, v in query.items() if v is not None}
        url += "?" + urlencode(clean_query, doseq=True)

    command = [
        "curl",
        "-sS",
        "--fail-with-body",
        "-X",
        method,
        url,
        "-H",
        f"Authorization: {api_key}",
    ]
    for header_name, header_value in DEFAULT_HEADERS.items():
        command.extend(["-H", f"{header_name}: {header_value}"])
    if body is not None:
        command.extend(["-H", "Content-Type: application/json", "--data", json.dumps(body, ensure_ascii=False)])
    command.extend(["-w", "\n__CODEX_STATUS__:%{http_code}"])

    result = subprocess.run(command, capture_output=True, text=True)
    payload, marker, status_text = result.stdout.rpartition("\n__CODEX_STATUS__:")
    if not marker:
        payload = result.stdout
        status_code = None
    else:
        try:
            status_code = int(status_text.strip())
        except ValueError:
            status_code = None
    if status_code is not None and status_code >= 400:
        excerpt = payload.strip()
        raise SystemExit(f"HTTP {status_code} for {path}: {excerpt[:500]}")
    if result.returncode != 0:
        raise SystemExit(f"curl failed for {path}: {result.stderr.strip() or payload.strip()[:500]}")

    if payload.strip().startswith("<"):
        raise SystemExit(f"Non-JSON response for {path}: possible WAF or HTML error page returned.")

    if not payload.strip():
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON response for {path}: {payload[:500]}") from exc


def normalize_timestamp(value: str | None) -> str:
    if not value:
        return "unknown-time"
    return value.replace(":", "").replace("-", "").replace(".000000", "").replace("+00:00", "Z")


def require_valid_note_id(raw: Any, *, field: str = "source_note_id") -> str:
    note_id = str(raw or "").strip()
    if not note_id:
        raise SystemExit(f"{field} is required.")
    if not NOTE_ID_PATTERN.fullmatch(note_id):
        raise SystemExit(f"Invalid {field} '{note_id}'. Only letters, numbers, underscores, and hyphens are allowed.")
    return note_id


def slugify(value: str | None) -> str:
    if not value:
        return ""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:60]


def strip_html(text: str | None) -> str:
    if not text:
        return ""
    plain = html.unescape(text)
    plain = plain.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    plain = re.sub(r"</p\s*>", "\n\n", plain, flags=re.IGNORECASE)
    plain = re.sub(r"<[^>]+>", "", plain)
    return plain.strip()


def to_frontmatter_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        if not value:
            return "[]"
        rendered = ", ".join(json.dumps(str(item), ensure_ascii=False) for item in value)
        return f"[{rendered}]"
    return json.dumps(str(value), ensure_ascii=False)


def recording_markdown(recording: dict[str, Any]) -> str:
    title = recording.get("title") or f"VoiceNotes {recording.get('id') or recording.get('uuid')}"
    fields = {
        "source": "voicenotes",
        "source_note_id": recording.get("id") or recording.get("uuid"),
        "title": title,
        "created_at": recording.get("created_at"),
        "recorded_at": recording.get("recorded_at"),
        "recording_type": recording.get("recording_type"),
        "duration": recording.get("duration"),
        "tags": recording.get("tags") or [],
    }
    frontmatter = "\n".join(f"{key}: {to_frontmatter_value(value)}" for key, value in fields.items())
    transcript = strip_html(recording.get("transcript"))
    return f"---\n{frontmatter}\n---\n\n# {title}\n\n{transcript}\n"


def note_filename(recording: dict[str, Any]) -> str:
    note_id = require_valid_note_id(recording.get("id") or recording.get("uuid"))
    timestamp = normalize_timestamp(recording.get("created_at") or recording.get("recorded_at"))
    return f"{timestamp}--{note_id}.json"


def iso_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def raw_export_payload(recording: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "voicenotes",
        "source_endpoint": "recordings",
        "synced_at": iso_now(),
        "recording": recording,
    }


def same_recording_payload(path: Path, recording: dict[str, Any]) -> bool:
    if not path.exists():
        return False
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return (
        existing.get("source") == "voicenotes"
        and existing.get("source_endpoint") == "recordings"
        and existing.get("recording") == recording
    )


def unwrap_recording_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        return dict(payload["data"])
    if isinstance(payload, dict):
        return dict(payload)
    raise SystemExit("Recording payload did not contain an object.")


def print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def resolved_date_range(date_from: str | None, date_to: str | None) -> tuple[str, str] | None:
    if not date_from and not date_to:
        return None
    if not date_from:
        raise SystemExit("--from is required when --to is provided.")
    return date_from, (date_to or iso_now())


def existing_export_path(output_dir: Path, note_id: str) -> Path | None:
    safe_note_id = require_valid_note_id(note_id)
    matches = sorted(
        path
        for path in output_dir.glob(f"*--{safe_note_id}.json")
        if path.is_file()
    )
    if len(matches) > 1:
        rendered = ", ".join(str(path) for path in matches)
        raise SystemExit(f"Multiple canonical raw exports found for note '{safe_note_id}': {rendered}")
    return matches[0] if matches else None


def command_search(args: argparse.Namespace) -> int:
    payload = request_json("GET", "/search/semantic", query={"query": args.query})
    print_json(payload)
    return 0


def command_list(args: argparse.Namespace) -> int:
    body: dict[str, Any] = {}
    if args.tags:
        body["tags"] = args.tags
    date_range = resolved_date_range(args.date_from, args.date_to)
    if date_range:
        body["date_range"] = list(date_range)

    payload = request_json("POST", "/recordings", query={"page": args.page}, body=body or {})
    print_json(payload)
    return 0


def command_get(args: argparse.Namespace) -> int:
    payload = request_json("GET", f"/recordings/{args.id}")
    if args.format == "json":
        print_json(payload)
        return 0

    output = recording_markdown(unwrap_recording_payload(payload))
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


def command_create(args: argparse.Namespace) -> int:
    payload = request_json(
        "POST",
        "/recordings/new",
        body={
            "recording_type": 3,
            "transcript": args.text,
            "device_info": args.device_info,
        },
    )
    print_json(payload)
    return 0


def fetch_page(page: int, tags: list[str], date_from: str | None, date_to: str | None) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if tags:
        body["tags"] = tags
    date_range = resolved_date_range(date_from, date_to)
    if date_range:
        body["date_range"] = list(date_range)
    return request_json("POST", "/recordings", query={"page": page}, body=body or {})


def command_sync(args: argparse.Namespace) -> int:
    state = load_sync_state(args.state_file)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    date_from = args.date_from
    if not args.no_checkpoint and not date_from and not args.date_to:
        date_from = state.get("last_synced_at")

    page = 1
    written = 0
    updated = 0
    skipped = 0
    newest_created_at = state.get("last_synced_at")
    newest_ids: list[str] = list(state.get("last_synced_ids") or []) if newest_created_at else []
    while True:
        payload = fetch_page(page, args.tags or [], date_from, args.date_to)
        recordings = payload.get("data") or []
        for recording in recordings:
            note_id = require_valid_note_id(recording.get("id") or recording.get("uuid"))
            created_at = recording.get("created_at") or recording.get("recorded_at")
            if created_at and (not newest_created_at or created_at > newest_created_at):
                newest_created_at = created_at
                newest_ids = [note_id]
            elif created_at and created_at == newest_created_at and note_id not in newest_ids:
                newest_ids.append(note_id)
            filename = note_filename(recording)
            path = existing_export_path(output_dir, note_id) or (output_dir / filename)
            existed_before = path.exists()
            if path.exists() and not args.overwrite and same_recording_payload(path, recording):
                skipped += 1
                continue
            rendered = json.dumps(raw_export_payload(recording), indent=2, ensure_ascii=False) + "\n"
            path.write_text(rendered, encoding="utf-8")
            if existed_before:
                updated += 1
            else:
                written += 1

        next_link = ((payload.get("links") or {}).get("next"))
        if not next_link or page >= args.max_pages:
            break
        page += 1

    if not args.no_checkpoint:
        updated_state = merge_sync_state(state, newest_created_at, newest_ids)
        save_sync_state(args.state_file, updated_state)

    summary = {
        "output_dir": str(output_dir),
        "written": written,
        "updated": updated,
        "skipped": skipped,
        "max_pages": args.max_pages,
        "effective_from": date_from,
        "checkpoint_enabled": not args.no_checkpoint,
        "state_file": str(args.state_file),
    }
    print_json(summary)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Run semantic search across notes.")
    search_parser.add_argument("--query", required=True, help="Search query.")
    search_parser.set_defaults(func=command_search)

    list_parser = subparsers.add_parser("list", help="List recordings with optional filters.")
    list_parser.add_argument("--tag", dest="tags", action="append", help="Tag filter; repeatable.")
    list_parser.add_argument("--from", dest="date_from", help="UTC ISO start date.")
    list_parser.add_argument("--to", dest="date_to", help="UTC ISO end date.")
    list_parser.add_argument("--page", type=int, default=1, help="Results page.")
    list_parser.set_defaults(func=command_list)

    get_parser = subparsers.add_parser("get", help="Fetch one recording.")
    get_parser.add_argument("--id", required=True, help="Recording UUID.")
    get_parser.add_argument("--format", choices=("json", "markdown"), default="json")
    get_parser.add_argument("--output", help="Optional file path for markdown output.")
    get_parser.set_defaults(func=command_get)

    create_parser = subparsers.add_parser("create", help="Create a text note in VoiceNotes.")
    create_parser.add_argument("--text", required=True, help="Note content.")
    create_parser.add_argument("--device-info", default="codex", help="Device info value.")
    create_parser.set_defaults(func=command_create)

    sync_parser = subparsers.add_parser("sync", help="Export filtered recordings to canonical raw JSON files.")
    sync_parser.add_argument("--output-dir", required=True, help="Directory for raw JSON exports.")
    sync_parser.add_argument("--tag", dest="tags", action="append", help="Tag filter; repeatable.")
    sync_parser.add_argument("--from", dest="date_from", help="UTC ISO start date.")
    sync_parser.add_argument("--to", dest="date_to", help="UTC ISO end date.")
    sync_parser.add_argument("--max-pages", type=int, default=10, help="Maximum pages to fetch.")
    sync_parser.add_argument("--overwrite", action="store_true", help="Rewrite existing files.")
    sync_parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help="Local sync checkpoint file. Default: state/sync_state.json",
    )
    sync_parser.add_argument(
        "--no-checkpoint",
        action="store_true",
        help="Ignore and do not update the local sync checkpoint.",
    )
    sync_parser.set_defaults(func=command_sync)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
