"""stdlib HTTP server for the dashboard."""
from __future__ import annotations

import json
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any


class DashboardHandler(BaseHTTPRequestHandler):
    index = None  # Set by create_server
    static_dir = None
    dev_mode = False

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = dict(urllib.parse.parse_qs(parsed.query))
        # Flatten single-value params
        params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}

        if path == "/api/status":
            self._json_response(self.index.query_status())
        elif path == "/api/notes":
            self._json_response(
                self.index.query_notes(
                    source=params.get("source"),
                    status=params.get("status"),
                    project=params.get("project"),
                    search=params.get("search"),
                    page=int(params.get("page", 1)),
                    per_page=int(params.get("per_page", 50)),
                )
            )
        elif path.startswith("/api/notes/") and path.count("/") == 3:
            note_id = path.split("/")[3]
            source = params.get("source", "voicenotes")
            note = self.index.get_note(note_id, source)
            if note:
                self._json_response({"note": note})
            else:
                self._error_response("Note not found", "NOT_FOUND", 404)
        elif path == "/api/projects":
            self._json_response({"projects": self.index.query_projects()})
        elif path == "/api/triage":
            self._json_response({"items": self.index.query_triage_items()})
        elif path == "/api/decisions":
            rows = self.index.conn.execute(
                "SELECT data FROM decisions"
            ).fetchall()
            self._json_response(
                {"decisions": [json.loads(r["data"]) for r in rows]}
            )
        elif path.startswith("/api/"):
            self._error_response("Endpoint not found", "NOT_FOUND", 404)
        elif self.static_dir:
            self._serve_static(path)
        else:
            self._error_response("No static files configured", "NO_STATIC", 404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = (
            json.loads(self.rfile.read(content_length)) if content_length else {}
        )
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/refresh":
            result = self.index.rebuild()
            self._json_response(result)
        elif path.endswith("/suggest") and "/api/notes/" in path:
            parts = path.split("/")
            note_id = parts[3]
            source = body.get("source", "voicenotes")
            note = self.index.get_note(note_id, source)
            if not note:
                self._error_response("Note not found", "NOT_FOUND", 404)
                return
            from ..services.suggestions import write_suggestion

            file_path = Path(note["file_path"])
            write_suggestion(file_path, body["user_suggested_project"])
            self.index.rebuild()  # Refresh index
            self._json_response({"ok": True, "note_id": note_id})
        elif path.endswith("/annotate") and "/api/notes/" in path:
            parts = path.split("/")
            note_id = parts[3]
            source = body.get("source", "voicenotes")
            note = self.index.get_note(note_id, source)
            if not note:
                self._error_response("Note not found", "NOT_FOUND", 404)
                return
            from ..services.notes import read_note, write_note

            file_path = Path(note["file_path"])
            metadata, note_body = read_note(file_path)
            if "reviewer_notes" in body:
                metadata["reviewer_notes"] = body["reviewer_notes"]
            if "user_keywords" in body:
                existing = metadata.get("user_keywords", [])
                new_kw = [
                    k.strip().lower()
                    for k in body["user_keywords"]
                    if k.strip()
                ]
                metadata["user_keywords"] = sorted(set(existing + new_kw))
            write_note(file_path, metadata, note_body)
            self.index.rebuild()
            self._json_response({"ok": True, "note_id": note_id})
        elif path.endswith("/decide") and "/api/notes/" in path:
            parts = path.split("/")
            note_id = parts[3]
            source = body.get("source", "voicenotes")
            decision = body.get("decision", "")
            final_project = body.get("final_project")
            valid_decisions = {"approve", "reject", "needs-review", "ambiguous", "pending-project"}
            if decision not in valid_decisions:
                self._error_response(
                    f"Invalid decision '{decision}'. Must be one of: {', '.join(sorted(valid_decisions))}",
                    "INVALID_DECISION",
                    400,
                )
                return
            note_record = self.index.get_note(note_id, source)
            if not note_record:
                self._error_response("Note not found", "NOT_FOUND", 404)
                return
            try:
                result = self._handle_decide(note_record, note_id, source, decision, final_project)
                self._json_response(result)
            except SystemExit as exc:
                self._error_response(str(exc), "DECIDE_ERROR", 400)
            except Exception as exc:
                self._error_response(str(exc), "INTERNAL_ERROR", 500)
        elif path.startswith("/api/"):
            self._error_response("Endpoint not found", "NOT_FOUND", 404)
        else:
            self._error_response(
                "Method not allowed", "METHOD_NOT_ALLOWED", 405
            )

    def _handle_decide(
        self,
        note_record: dict,
        note_id: str,
        source: str,
        decision: str,
        final_project: str | None,
    ) -> dict:
        from ..services.notes import (
            ensure_note_metadata_defaults,
            iso_now,
            read_note,
            remove_review_copies,
            review_dir_for,
            write_note,
        )
        from ..services.classification import classify_intent
        from ..services.decisions import (
            build_decision_packet,
            load_decision_packet_for_metadata,
            relative_or_absolute,
            save_decision_packet_for_metadata,
        )
        from ..services.projects import load_registry
        from ..services.paths import VOICE_SOURCE, normalize_source_name

        file_path = Path(note_record["file_path"])
        metadata, body = read_note(file_path)
        metadata = ensure_note_metadata_defaults(metadata)
        final_project = final_project or metadata.get("project")

        if decision == "approve":
            if not final_project:
                raise SystemExit("Approve requires a project on the note or via final_project.")
            _defaults, projects = load_registry()
            if final_project not in projects:
                raise SystemExit(f"Unknown project '{final_project}'.")
            metadata["status"] = "classified"
            metadata["project"] = final_project
            metadata["destination"] = final_project
            metadata["note_type"] = metadata.get("note_type") or projects[final_project].note_type
            metadata["review_status"] = "approved"
            metadata["user_suggested_project"] = None
            metadata["user_suggestion_timestamp"] = None
            metadata["requires_user_confirmation"] = False
            metadata["intent"] = classify_intent(metadata)
            remove_review_copies(file_path.name)
        elif decision == "ambiguous":
            metadata["status"] = "ambiguous"
            metadata["project"] = None
            metadata["destination"] = "ambiguous"
            metadata.pop("note_type", None)
            metadata["review_status"] = "ambiguous"
            metadata["requires_user_confirmation"] = True
            metadata["intent"] = classify_intent(metadata)
            remove_review_copies(file_path.name)
            src = normalize_source_name(str(metadata.get("source") or VOICE_SOURCE)) or VOICE_SOURCE
            target_dir = review_dir_for(src, "ambiguous")
            write_note(target_dir / file_path.name, metadata, body)
        elif decision == "pending-project":
            metadata["status"] = "pending_project"
            metadata["project"] = None
            metadata["destination"] = "pending_project"
            metadata.pop("note_type", None)
            metadata["review_status"] = "pending_project"
            metadata["requires_user_confirmation"] = True
            metadata["intent"] = classify_intent(metadata)
            remove_review_copies(file_path.name)
            src = normalize_source_name(str(metadata.get("source") or VOICE_SOURCE)) or VOICE_SOURCE
            write_note(review_dir_for(src, "pending_project") / file_path.name, metadata, body)
        else:
            # reject / needs-review
            metadata["status"] = "needs_review"
            metadata["project"] = None
            metadata["destination"] = "needs_review"
            metadata.pop("note_type", None)
            metadata["review_status"] = decision.replace("-", "_")
            metadata["requires_user_confirmation"] = True
            metadata["intent"] = classify_intent(metadata)
            remove_review_copies(file_path.name)
            src = normalize_source_name(str(metadata.get("source") or VOICE_SOURCE)) or VOICE_SOURCE
            write_note(review_dir_for(src, "needs_review") / file_path.name, metadata, body)

        # Write canonical note
        write_note(file_path, metadata, body)

        # Update decision packet
        packet = load_decision_packet_for_metadata(metadata)
        packet.setdefault("reviews", [])
        packet.setdefault("source_note_id", note_id)
        packet.setdefault("source", metadata.get("source", VOICE_SOURCE))
        packet.setdefault("source_project", metadata.get("source_project"))
        packet.setdefault("canonical_path", relative_or_absolute(file_path))
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
                "notes": "",
            }
        )
        packet["final_decision"] = packet["reviews"][-1]
        packet["proposal"] = build_decision_packet(
            file_path,
            metadata,
            body,
            route=str(metadata.get("project") or metadata.get("status")),
            details={},
            reason=str(metadata.get("routing_reason") or ""),
        ).get("proposal", {})
        save_decision_packet_for_metadata(metadata, packet)

        # Rebuild index so UI reflects changes
        self.index.rebuild()

        return {"ok": True, "decision": decision, "note_id": note_id}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _json_response(self, data: Any, status: int = 200):
        payload = json.dumps(data, ensure_ascii=False, default=str).encode(
            "utf-8"
        )
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        if self.dev_mode:
            self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _error_response(self, message: str, code: str, status: int):
        self._json_response({"error": message, "code": code}, status)

    def _serve_static(self, path: str):
        if path == "/":
            path = "/index.html"
        file_path = self.static_dir / path.lstrip("/")
        if not file_path.exists() or not file_path.is_file():
            # SPA fallback
            file_path = self.static_dir / "index.html"
        if not file_path.exists():
            self.send_error(404)
            return
        content = file_path.read_bytes()
        self.send_response(200)
        ct = self._guess_content_type(file_path.suffix)
        self.send_header("Content-Type", ct)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    @staticmethod
    def _guess_content_type(ext: str) -> str:
        types = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
            ".woff2": "font/woff2",
            ".woff": "font/woff",
            ".ttf": "font/ttf",
        }
        return types.get(ext, "application/octet-stream")

    def log_message(self, format, *args):
        pass  # Suppress default logging


def create_server(
    port: int,
    static_dir: Path | None = None,
    dev: bool = False,
) -> HTTPServer:
    """Create and configure the dashboard server."""
    from .index import DashboardIndex
    from ..services.paths import STATE_DIR

    db_path = STATE_DIR / "dashboard.db"
    index = DashboardIndex(db_path)
    index.rebuild()

    DashboardHandler.index = index
    DashboardHandler.static_dir = static_dir
    DashboardHandler.dev_mode = dev

    server = HTTPServer(("localhost", port), DashboardHandler)
    return server
