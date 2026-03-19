"""SQLite read-model for the dashboard."""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class DashboardIndex:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._last_rebuild = 0.0
        self._ensure_tables()

    def _ensure_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS notes (
                source_note_id TEXT NOT NULL,
                source TEXT NOT NULL,
                source_project TEXT DEFAULT '',
                title TEXT,
                status TEXT,
                project TEXT,
                user_suggested_project TEXT,
                user_suggestion_timestamp TEXT,
                reviewer_notes TEXT,
                confidence REAL,
                capture_kind TEXT,
                intent TEXT,
                destination TEXT,
                destination_reason TEXT,
                created_at TEXT,
                tags TEXT,
                candidate_projects TEXT,
                review_status TEXT,
                thread_id TEXT,
                continuation_of TEXT,
                related_note_ids TEXT,
                extraction_status TEXT,
                file_path TEXT NOT NULL,
                queue_age_seconds REAL,
                PRIMARY KEY (source_note_id, source, source_project)
            );
            CREATE TABLE IF NOT EXISTS compiled (
                source_note_id TEXT NOT NULL,
                source TEXT NOT NULL,
                brief_summary TEXT,
                is_stale INTEGER,
                compiled_age_seconds REAL,
                compiled_at TEXT,
                file_path TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS decisions (
                source_note_id TEXT NOT NULL,
                source TEXT NOT NULL,
                packet_path TEXT NOT NULL,
                reviews TEXT,
                proposal TEXT,
                data TEXT
            );
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        self.conn.commit()

    def rebuild(self) -> dict:
        """Full rebuild from filesystem. Returns stats."""
        from ..services.notes import read_note, list_markdown_files, ensure_note_metadata_defaults
        from ..services.paths import (
            NORMALIZED_DIR, COMPILED_DIR,
            DECISIONS_DIR, KNOWN_SOURCES,
        )

        errors: list[dict[str, str]] = []
        notes_count = 0

        self.conn.execute("DELETE FROM notes")
        self.conn.execute("DELETE FROM compiled")
        self.conn.execute("DELETE FROM decisions")

        now = time.time()

        # Index normalized notes by source
        for source in sorted(KNOWN_SOURCES):
            source_dir = NORMALIZED_DIR / source
            if not source_dir.exists():
                continue
            # Handle project_router sub-dirs
            if source == "project_router":
                for project_dir in sorted(source_dir.iterdir()):
                    if project_dir.is_dir():
                        for f in list_markdown_files(project_dir):
                            try:
                                if self._index_note(f, source, now):
                                    notes_count += 1
                            except Exception as e:
                                errors.append({"file": str(f), "error": str(e)})
            else:
                for f in list_markdown_files(source_dir):
                    try:
                        if self._index_note(f, source, now):
                            notes_count += 1
                    except Exception as e:
                        errors.append({"file": str(f), "error": str(e)})

        # Index compiled notes
        for source in sorted(KNOWN_SOURCES):
            source_dir = COMPILED_DIR / source
            if not source_dir.exists():
                continue
            if source == "project_router":
                for project_dir in sorted(source_dir.iterdir()):
                    if project_dir.is_dir():
                        for f in list_markdown_files(project_dir):
                            try:
                                self._index_compiled(f)
                            except Exception:
                                pass
            else:
                for f in list_markdown_files(source_dir):
                    try:
                        self._index_compiled(f)
                    except Exception:
                        pass

        # Index decision packets
        if DECISIONS_DIR.exists():
            for f in sorted(DECISIONS_DIR.glob("*.json")):
                try:
                    self._index_decision(f)
                except Exception:
                    pass

        self.conn.commit()
        self._last_rebuild = time.time()
        self.conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            ("last_rebuild", str(self._last_rebuild)),
        )
        self.conn.commit()

        return {"rebuilt": True, "notes_count": notes_count, "errors": errors}

    def _index_note(self, file_path: Path, source: str, now: float) -> bool:
        from ..services.notes import read_note, ensure_note_metadata_defaults

        metadata, _ = read_note(file_path)
        if not metadata.get("source_note_id"):
            return False
        metadata = ensure_note_metadata_defaults(metadata)
        created = metadata.get("created_at", "")
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            age = now - dt.timestamp()
        except Exception:
            age = 0.0

        self.conn.execute(
            """INSERT OR REPLACE INTO notes VALUES
               (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                metadata.get("source_note_id"),
                metadata.get("source", source),
                metadata.get("source_project") or "",
                metadata.get("title"),
                metadata.get("status"),
                metadata.get("project"),
                metadata.get("user_suggested_project"),
                metadata.get("user_suggestion_timestamp"),
                metadata.get("reviewer_notes"),
                metadata.get("confidence", 0.0),
                metadata.get("capture_kind"),
                metadata.get("intent"),
                metadata.get("destination"),
                metadata.get("destination_reason"),
                created,
                json.dumps(metadata.get("tags", [])),
                json.dumps(metadata.get("candidate_projects", [])),
                metadata.get("review_status"),
                metadata.get("thread_id"),
                metadata.get("continuation_of"),
                json.dumps(metadata.get("related_note_ids", [])),
                metadata.get("extraction_status"),
                str(file_path),
                age,
            ),
        )
        return True

    def _index_compiled(self, file_path: Path):
        from ..services.notes import read_note

        metadata, _ = read_note(file_path)
        note_id = metadata.get("source_note_id") or metadata.get("compiled_from_path", "")
        source = metadata.get("source", "voicenotes")
        compiled_at = metadata.get("compiled_at", "")
        is_stale = (
            1
            if metadata.get("compiled_from_signature") and not metadata.get("_fresh")
            else 0
        )

        try:
            dt = datetime.fromisoformat(compiled_at.replace("Z", "+00:00"))
            age = time.time() - dt.timestamp()
        except Exception:
            age = 0.0

        self.conn.execute(
            """INSERT OR REPLACE INTO compiled
               (source_note_id, source, brief_summary, is_stale,
                compiled_age_seconds, compiled_at, file_path)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                note_id,
                source,
                metadata.get("brief_summary"),
                is_stale,
                age,
                compiled_at,
                str(file_path),
            ),
        )

    def _index_decision(self, file_path: Path):
        data = json.loads(file_path.read_text(encoding="utf-8"))
        note_id = data.get("source_note_id", "")
        source = data.get("source", "voicenotes")
        self.conn.execute(
            """INSERT OR REPLACE INTO decisions
               (source_note_id, source, packet_path, reviews, proposal, data)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                note_id,
                source,
                str(file_path),
                json.dumps(data.get("reviews", [])),
                json.dumps(data.get("proposal", {})),
                json.dumps(data),
            ),
        )

    # ------------------------------------------------------------------
    #  Query methods
    # ------------------------------------------------------------------

    def query_notes(
        self,
        source: str | None = None,
        status: str | None = None,
        project: str | None = None,
        search: str | None = None,
        review_status: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> dict[str, Any]:
        query = "SELECT * FROM notes WHERE 1=1"
        params: list[Any] = []
        if source:
            query += " AND source = ?"
            params.append(source)
        if status:
            statuses = [s.strip() for s in status.split(",")]
            query += f" AND status IN ({','.join('?' * len(statuses))})"
            params.extend(statuses)
        if project:
            query += " AND project = ?"
            params.append(project)
        if search:
            query += " AND (title LIKE ? OR tags LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if review_status:
            query += " AND review_status = ?"
            params.append(review_status)

        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        total = self.conn.execute(count_query, params).fetchone()[0]

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([per_page, (page - 1) * per_page])
        rows = self.conn.execute(query, params).fetchall()

        return {
            "notes": [self._row_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
        }

    def get_note(self, note_id: str, source: str) -> dict[str, Any] | None:
        """Get single note. Source is required."""
        row = self.conn.execute(
            "SELECT * FROM notes WHERE source_note_id = ? AND source = ?",
            (note_id, source),
        ).fetchone()
        if not row:
            return None
        result = self._row_to_dict(row)
        # Load full body from file
        from ..services.notes import read_note

        _, body = read_note(Path(row["file_path"]))
        result["body"] = body
        # Load compiled info if available
        compiled = self.conn.execute(
            "SELECT * FROM compiled WHERE source_note_id = ? AND source = ?",
            (note_id, source),
        ).fetchone()
        if compiled:
            result["compiled"] = dict(compiled)
        # Load decision packet
        decision = self.conn.execute(
            "SELECT * FROM decisions WHERE source_note_id = ? AND source = ?",
            (note_id, source),
        ).fetchone()
        if decision:
            result["decision"] = json.loads(decision["data"])
        return result

    def query_triage_items(self) -> list[dict[str, Any]]:
        """All items needing operator attention across all sources."""
        rows = self.conn.execute(
            """SELECT * FROM notes WHERE
                   status IN ('ambiguous', 'needs_review', 'pending_project',
                              'parse_errors', 'needs_extraction')
                   OR (status = 'classified'
                       AND user_suggested_project IS NOT NULL)
               ORDER BY confidence ASC, created_at ASC"""
        ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def query_projects(self) -> list[dict[str, Any]]:
        """Projects with note counts."""
        from ..services.projects import load_registry

        _, projects = load_registry()
        result = []
        for key, proj in projects.items():
            counts = self.conn.execute(
                "SELECT COUNT(*) as c FROM notes WHERE project = ?", (key,)
            ).fetchone()
            review_counts = self.conn.execute(
                "SELECT COUNT(*) as c FROM notes WHERE project = ? "
                "AND status IN ('needs_review', 'ambiguous')",
                (key,),
            ).fetchone()
            result.append(
                {
                    "key": key,
                    "display_name": proj.display_name,
                    "language": proj.language,
                    "keywords": proj.keywords,
                    "note_type": proj.note_type,
                    "note_count": counts["c"] if counts else 0,
                    "review_count": review_counts["c"] if review_counts else 0,
                }
            )
        return result

    def query_status(self) -> dict[str, Any]:
        """Pipeline status from index."""
        from ..services.status import compute_pipeline_status
        from ..services.paths import KNOWN_SOURCES

        result = compute_pipeline_status(KNOWN_SOURCES)
        result["index_age_seconds"] = self.last_rebuild_age()
        return result

    def last_rebuild_age(self) -> float:
        """Seconds since last rebuild."""
        row = self.conn.execute(
            "SELECT value FROM meta WHERE key = 'last_rebuild'"
        ).fetchone()
        if row:
            return time.time() - float(row["value"])
        return float("inf")

    def _row_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        for field in ("tags", "candidate_projects", "related_note_ids"):
            if field in d and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d

    def close(self):
        self.conn.close()
