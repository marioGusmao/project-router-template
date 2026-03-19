"""Readwise Reader sync client — fetches documents via the Reader API v3."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


BASE_URL = "https://readwise.io/api/v3"
AUTH_URL = "https://readwise.io/api/v2/auth/"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = REPO_ROOT / "state" / "readwise_sync_state.json"
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


def require_access_token() -> str:
    load_local_env()
    token = os.environ.get("READWISE_ACCESS_TOKEN") or os.environ.get("READWISE_TOKEN")
    if not token or token == "replace-with-your-readwise-token":
        raise SystemExit(
            "READWISE_ACCESS_TOKEN is not set. "
            "Get your token at https://readwise.io/access_token and add it to .env.local"
        )
    return token


def require_valid_note_id(raw: Any, *, field: str = "source_note_id") -> str:
    note_id = str(raw or "").strip()
    if not note_id:
        raise SystemExit(f"{field} is required.")
    if not NOTE_ID_PATTERN.fullmatch(note_id):
        raise SystemExit(f"Invalid {field} '{note_id}'.")
    return note_id


def normalize_timestamp(value: str | None) -> str:
    if not value:
        return "unknown-time"
    return value.replace(":", "").replace("-", "").replace(".000000", "").replace("+00:00", "Z")


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def should_skip_document(doc: dict[str, Any]) -> bool:
    """Skip child highlights (non-null parent_id) in v1."""
    return doc.get("parent_id") is not None


def readwise_note_filename(doc: dict[str, Any]) -> str:
    raw_id = str(doc.get("id") or "").strip()
    note_id = require_valid_note_id(f"rw_{raw_id}")
    timestamp = normalize_timestamp(doc.get("created_at"))
    return f"{timestamp}--{note_id}.json"


def raw_export_payload(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "readwise",
        "source_endpoint": "reader/list",
        "source_item_type": "reader_document",
        "synced_at": iso_now(),
        "document": doc,
    }


def existing_export_path(output_dir: Path, note_id: str) -> Path | None:
    safe_id = require_valid_note_id(note_id)
    matches = sorted(p for p in output_dir.glob(f"*--{safe_id}.json") if p.is_file())
    if len(matches) > 1:
        rendered = ", ".join(str(p) for p in matches)
        raise SystemExit(f"Multiple raw exports for '{safe_id}': {rendered}")
    return matches[0] if matches else None


def same_document_payload(path: Path, doc: dict[str, Any]) -> bool:
    if not path.exists():
        return False
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return existing.get("source") == "readwise" and existing.get("document") == doc


def request_json(url: str, token: str) -> Any:
    req = urllib.request.Request(url, headers={
        "Authorization": f"Token {token}",
        "Accept": "application/json",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            retry_after = int(exc.headers.get("Retry-After", "60"))
            print(f"Rate limited. Waiting {retry_after}s...", file=sys.stderr)
            time.sleep(retry_after)
            return request_json(url, token)
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"HTTP {exc.code} from Readwise: {body}") from exc


def validate_token(token: str) -> None:
    req = urllib.request.Request(AUTH_URL, headers={"Authorization": f"Token {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            if resp.status != 204:
                raise SystemExit(f"Token validation returned HTTP {resp.status}.")
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Invalid Readwise token (HTTP {exc.code}).") from exc


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


def merge_sync_state(
    existing: dict[str, Any],
    newest_updated_at: str | None,
    newest_ids: list[str],
) -> dict[str, Any]:
    last = existing.get("last_synced_at")
    last_ids = list(existing.get("last_synced_ids") or [])
    if newest_updated_at and (not last or newest_updated_at > last):
        last = newest_updated_at
        last_ids = newest_ids
    elif newest_updated_at and newest_updated_at == last:
        for nid in newest_ids:
            if nid not in last_ids:
                last_ids.append(nid)
    return {"last_synced_at": last, "last_synced_ids": last_ids}


def iso_days_ago(days: int) -> str:
    if days <= 0:
        raise SystemExit("--window-days must be greater than 0.")
    now = datetime.fromisoformat(iso_now().replace("Z", "+00:00"))
    return (now - timedelta(days=days)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def command_sync(args: argparse.Namespace) -> int:
    token = require_access_token()
    validate_token(token)

    state = load_sync_state(args.state_file)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.full_history and (args.updated_after or args.window_days is not None):
        raise SystemExit("--full-history cannot be combined with --updated-after or --window-days.")
    if args.window_days is not None and args.updated_after:
        raise SystemExit("--window-days cannot be combined with --updated-after.")

    updated_after = args.updated_after
    if args.window_days is not None:
        updated_after = iso_days_ago(args.window_days)
    elif args.full_history:
        updated_after = None
    elif not args.no_checkpoint and not updated_after:
        updated_after = state.get("last_synced_at")
    if not updated_after and not args.full_history and (args.no_checkpoint or not state.get("last_synced_at")):
        raise SystemExit(
            "First sync requires an explicit scope. "
            "Use --window-days <N>, --updated-after <ISO>, or --full-history."
        )

    page_cursor = None
    pages_fetched = 0
    written = 0
    updated = 0
    skipped = 0
    skipped_highlights = 0
    newest_updated_at = state.get("last_synced_at")
    newest_ids: list[str] = list(state.get("last_synced_ids") or []) if newest_updated_at else []

    while pages_fetched < args.max_pages:
        params = []
        if updated_after:
            params.append(f"updatedAfter={updated_after}")
        if args.category:
            params.append(f"category={args.category}")
        if args.location:
            params.append(f"location={args.location}")
        for tag in (args.tags or []):
            params.append(f"tag={tag}")
        if page_cursor:
            params.append(f"pageCursor={page_cursor}")
        url = f"{BASE_URL}/list/" + ("?" + "&".join(params) if params else "")
        payload = request_json(url, token)
        results = payload.get("results") or []
        pages_fetched += 1

        for doc in results:
            if should_skip_document(doc):
                skipped_highlights += 1
                continue

            raw_id = str(doc.get("id") or "").strip()
            note_id = f"rw_{raw_id}"
            doc_updated_at = doc.get("updated_at")
            if doc_updated_at and (not newest_updated_at or doc_updated_at > newest_updated_at):
                newest_updated_at = doc_updated_at
                newest_ids = [note_id]
            elif doc_updated_at and doc_updated_at == newest_updated_at and note_id not in newest_ids:
                newest_ids.append(note_id)

            filename = readwise_note_filename(doc)
            path = existing_export_path(output_dir, note_id) or (output_dir / filename)
            existed_before = path.exists()
            if path.exists() and not args.overwrite and same_document_payload(path, doc):
                skipped += 1
                continue
            rendered = json.dumps(raw_export_payload(doc), indent=2, ensure_ascii=False) + "\n"
            path.write_text(rendered, encoding="utf-8")
            if existed_before:
                updated += 1
            else:
                written += 1

        page_cursor = payload.get("nextPageCursor")
        if not page_cursor:
            break

    if not args.no_checkpoint:
        updated_state = merge_sync_state(state, newest_updated_at, newest_ids)
        save_sync_state(args.state_file, updated_state)

    summary = {
        "output_dir": str(output_dir),
        "written": written,
        "updated": updated,
        "skipped": skipped,
        "skipped_highlights": skipped_highlights,
        "pages_fetched": pages_fetched,
        "max_pages": args.max_pages,
        "effective_updated_after": updated_after,
        "checkpoint_enabled": not args.no_checkpoint,
        "state_file": str(args.state_file),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_p = subparsers.add_parser("sync", help="Sync Readwise Reader documents to canonical raw JSON.")
    sync_p.add_argument("--output-dir", required=True, help="Directory for raw JSON exports.")
    sync_p.add_argument("--updated-after", help="ISO 8601 date: only docs updated after this.")
    sync_p.add_argument("--window-days", type=int, help="Fetch docs updated in the last N days.")
    sync_p.add_argument("--full-history", action="store_true", help="Fetch all documents.")
    sync_p.add_argument("--category", help="Filter: article, email, pdf, epub, tweet, video.")
    sync_p.add_argument("--location", help="Filter: new, later, archive, feed.")
    sync_p.add_argument("--tag", dest="tags", action="append", help="Tag filter; repeatable (up to 5).")
    sync_p.add_argument("--max-pages", type=int, default=10, help="Max API pages to fetch.")
    sync_p.add_argument("--overwrite", action="store_true", help="Rewrite existing files.")
    sync_p.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH, help="Sync checkpoint file.")
    sync_p.add_argument("--no-checkpoint", action="store_true", help="Ignore/skip sync checkpoint.")
    sync_p.set_defaults(func=command_sync)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
