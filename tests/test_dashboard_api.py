"""Tests for the dashboard API server and SQLite index."""
from __future__ import annotations

import json
import threading
import unittest
import urllib.request
from pathlib import Path

from src.project_router import cli
from src.project_router.services import paths as svc_paths
from tests.test_project_router import (
    temporary_repo_dir,
    prepare_repo,
    write_registry,
    patch_cli_paths,
)


class TestDashboardAPI(unittest.TestCase):
    def test_status_endpoint(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                from src.project_router.web.server import create_server

                server = create_server(port=0, static_dir=None)
                port = server.server_address[1]
                thread = threading.Thread(target=server.serve_forever)
                thread.daemon = True
                thread.start()
                try:
                    url = f"http://localhost:{port}/api/status"
                    with urllib.request.urlopen(url, timeout=5) as resp:
                        data = json.loads(resp.read())
                        self.assertIn("sources", data)
                finally:
                    server.shutdown()
                    server.server_close()

    def test_notes_endpoint(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                note_dir = svc_paths.NORMALIZED_DIR / "voicenotes"
                note_path = note_dir / "20260318T100000Z--vn_api.md"
                metadata = cli.ensure_note_metadata_defaults(
                    {
                        "source": "voicenotes",
                        "source_note_id": "vn_api",
                        "title": "API test note",
                        "status": "classified",
                        "project": "home_renovation",
                    }
                )
                cli.write_note(note_path, metadata, "Test body")

                from src.project_router.web.server import create_server

                server = create_server(port=0, static_dir=None)
                port = server.server_address[1]
                thread = threading.Thread(target=server.serve_forever)
                thread.daemon = True
                thread.start()
                try:
                    url = f"http://localhost:{port}/api/notes"
                    with urllib.request.urlopen(url, timeout=5) as resp:
                        data = json.loads(resp.read())
                        self.assertGreaterEqual(data["total"], 1)
                        self.assertEqual(
                            data["notes"][0]["source_note_id"], "vn_api"
                        )
                finally:
                    server.shutdown()
                    server.server_close()

    def test_notes_filter_by_source(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                note_dir = svc_paths.NORMALIZED_DIR / "voicenotes"
                note_path = note_dir / "20260318T100000Z--vn_filter.md"
                metadata = cli.ensure_note_metadata_defaults(
                    {
                        "source": "voicenotes",
                        "source_note_id": "vn_filter",
                        "title": "Filter test",
                        "status": "classified",
                        "project": "home_renovation",
                    }
                )
                cli.write_note(note_path, metadata, "Body")

                from src.project_router.web.server import create_server

                server = create_server(port=0, static_dir=None)
                port = server.server_address[1]
                thread = threading.Thread(target=server.serve_forever)
                thread.daemon = True
                thread.start()
                try:
                    url = f"http://localhost:{port}/api/notes?source=voicenotes"
                    with urllib.request.urlopen(url, timeout=5) as resp:
                        data = json.loads(resp.read())
                        self.assertGreaterEqual(data["total"], 1)

                    url = f"http://localhost:{port}/api/notes?source=filesystem"
                    with urllib.request.urlopen(url, timeout=5) as resp:
                        data = json.loads(resp.read())
                        self.assertEqual(data["total"], 0)
                finally:
                    server.shutdown()
                    server.server_close()

    def test_single_note_endpoint(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                note_dir = svc_paths.NORMALIZED_DIR / "voicenotes"
                note_path = note_dir / "20260318T100000Z--vn_single.md"
                metadata = cli.ensure_note_metadata_defaults(
                    {
                        "source": "voicenotes",
                        "source_note_id": "vn_single",
                        "title": "Single note test",
                        "status": "classified",
                        "project": "home_renovation",
                    }
                )
                cli.write_note(note_path, metadata, "Detailed body content")

                from src.project_router.web.server import create_server

                server = create_server(port=0, static_dir=None)
                port = server.server_address[1]
                thread = threading.Thread(target=server.serve_forever)
                thread.daemon = True
                thread.start()
                try:
                    url = f"http://localhost:{port}/api/notes/vn_single?source=voicenotes"
                    with urllib.request.urlopen(url, timeout=5) as resp:
                        data = json.loads(resp.read())
                        self.assertEqual(
                            data["note"]["source_note_id"], "vn_single"
                        )
                        self.assertIn("body", data["note"])
                finally:
                    server.shutdown()
                    server.server_close()

    def test_projects_endpoint(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                from src.project_router.web.server import create_server

                server = create_server(port=0, static_dir=None)
                port = server.server_address[1]
                thread = threading.Thread(target=server.serve_forever)
                thread.daemon = True
                thread.start()
                try:
                    url = f"http://localhost:{port}/api/projects"
                    with urllib.request.urlopen(url, timeout=5) as resp:
                        data = json.loads(resp.read())
                        self.assertIn("projects", data)
                        keys = [p["key"] for p in data["projects"]]
                        self.assertIn("home_renovation", keys)
                finally:
                    server.shutdown()
                    server.server_close()

    def test_triage_endpoint(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                note_dir = svc_paths.NORMALIZED_DIR / "voicenotes"
                note_path = note_dir / "20260318T100000Z--vn_triage.md"
                metadata = cli.ensure_note_metadata_defaults(
                    {
                        "source": "voicenotes",
                        "source_note_id": "vn_triage",
                        "title": "Ambiguous note",
                        "status": "ambiguous",
                        "project": "home_renovation",
                    }
                )
                cli.write_note(note_path, metadata, "Needs triage")

                from src.project_router.web.server import create_server

                server = create_server(port=0, static_dir=None)
                port = server.server_address[1]
                thread = threading.Thread(target=server.serve_forever)
                thread.daemon = True
                thread.start()
                try:
                    url = f"http://localhost:{port}/api/triage"
                    with urllib.request.urlopen(url, timeout=5) as resp:
                        data = json.loads(resp.read())
                        self.assertIn("items", data)
                        ids = [i["source_note_id"] for i in data["items"]]
                        self.assertIn("vn_triage", ids)
                finally:
                    server.shutdown()
                    server.server_close()

    def test_refresh_endpoint(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                from src.project_router.web.server import create_server

                server = create_server(port=0, static_dir=None)
                port = server.server_address[1]
                thread = threading.Thread(target=server.serve_forever)
                thread.daemon = True
                thread.start()
                try:
                    url = f"http://localhost:{port}/api/refresh"
                    req = urllib.request.Request(
                        url, data=b"{}", method="POST"
                    )
                    req.add_header("Content-Type", "application/json")
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        data = json.loads(resp.read())
                        self.assertTrue(data["rebuilt"])
                finally:
                    server.shutdown()
                    server.server_close()

    def test_404_for_unknown_api_endpoint(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                from src.project_router.web.server import create_server

                server = create_server(port=0, static_dir=None)
                port = server.server_address[1]
                thread = threading.Thread(target=server.serve_forever)
                thread.daemon = True
                thread.start()
                try:
                    url = f"http://localhost:{port}/api/nonexistent"
                    req = urllib.request.Request(url)
                    try:
                        urllib.request.urlopen(req, timeout=5)
                        self.fail("Expected HTTP error")
                    except urllib.error.HTTPError as e:
                        self.assertEqual(e.code, 404)
                finally:
                    server.shutdown()
                    server.server_close()

    def test_options_cors(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                from src.project_router.web.server import create_server

                server = create_server(port=0, static_dir=None, dev=True)
                port = server.server_address[1]
                thread = threading.Thread(target=server.serve_forever)
                thread.daemon = True
                thread.start()
                try:
                    url = f"http://localhost:{port}/api/status"
                    req = urllib.request.Request(url, method="OPTIONS")
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        self.assertEqual(resp.status, 204)
                        self.assertEqual(
                            resp.headers.get("Access-Control-Allow-Origin"),
                            "*",
                        )
                finally:
                    server.shutdown()
                    server.server_close()

    def test_status_includes_index_age(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                from src.project_router.web.server import create_server

                server = create_server(port=0, static_dir=None)
                port = server.server_address[1]
                thread = threading.Thread(target=server.serve_forever)
                thread.daemon = True
                thread.start()
                try:
                    url = f"http://localhost:{port}/api/status"
                    with urllib.request.urlopen(url, timeout=5) as resp:
                        data = json.loads(resp.read())
                        self.assertIn("index_age_seconds", data)
                        self.assertIsInstance(
                            data["index_age_seconds"], (int, float)
                        )
                        self.assertGreaterEqual(data["index_age_seconds"], 0)
                finally:
                    server.shutdown()
                    server.server_close()

    def test_notes_filter_by_review_status(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                note_dir = svc_paths.NORMALIZED_DIR / "voicenotes"

                meta_reject = cli.ensure_note_metadata_defaults(
                    {
                        "source": "voicenotes",
                        "source_note_id": "vn_rej",
                        "title": "Rejected note",
                        "status": "needs_review",
                        "project": "home_renovation",
                    }
                )
                meta_reject["review_status"] = "reject"
                cli.write_note(
                    note_dir / "20260318T100000Z--vn_rej.md",
                    meta_reject,
                    "Rejected body",
                )

                meta_defer = cli.ensure_note_metadata_defaults(
                    {
                        "source": "voicenotes",
                        "source_note_id": "vn_def",
                        "title": "Deferred note",
                        "status": "needs_review",
                        "project": "home_renovation",
                    }
                )
                meta_defer["review_status"] = "defer"
                cli.write_note(
                    note_dir / "20260318T100100Z--vn_def.md",
                    meta_defer,
                    "Deferred body",
                )

                from src.project_router.web.server import create_server

                server = create_server(port=0, static_dir=None)
                port = server.server_address[1]
                thread = threading.Thread(target=server.serve_forever)
                thread.daemon = True
                thread.start()
                try:
                    # Filter for rejected only
                    url = f"http://localhost:{port}/api/notes?review_status=reject"
                    with urllib.request.urlopen(url, timeout=5) as resp:
                        data = json.loads(resp.read())
                        ids = [n["source_note_id"] for n in data["notes"]]
                        self.assertIn("vn_rej", ids)
                        self.assertNotIn("vn_def", ids)

                    # Filter for deferred only
                    url = f"http://localhost:{port}/api/notes?review_status=defer"
                    with urllib.request.urlopen(url, timeout=5) as resp:
                        data = json.loads(resp.read())
                        ids = [n["source_note_id"] for n in data["notes"]]
                        self.assertIn("vn_def", ids)
                        self.assertNotIn("vn_rej", ids)
                finally:
                    server.shutdown()
                    server.server_close()

    def test_notes_comma_separated_status(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                note_dir = svc_paths.NORMALIZED_DIR / "voicenotes"

                meta_dispatched = cli.ensure_note_metadata_defaults(
                    {
                        "source": "voicenotes",
                        "source_note_id": "vn_disp",
                        "title": "Dispatched note",
                        "status": "dispatched",
                        "project": "home_renovation",
                    }
                )
                cli.write_note(
                    note_dir / "20260318T100000Z--vn_disp.md",
                    meta_dispatched,
                    "Dispatched body",
                )

                meta_processed = cli.ensure_note_metadata_defaults(
                    {
                        "source": "voicenotes",
                        "source_note_id": "vn_proc",
                        "title": "Processed note",
                        "status": "processed",
                        "project": "home_renovation",
                    }
                )
                cli.write_note(
                    note_dir / "20260318T100100Z--vn_proc.md",
                    meta_processed,
                    "Processed body",
                )

                from src.project_router.web.server import create_server

                server = create_server(port=0, static_dir=None)
                port = server.server_address[1]
                thread = threading.Thread(target=server.serve_forever)
                thread.daemon = True
                thread.start()
                try:
                    url = f"http://localhost:{port}/api/notes?status=dispatched,processed"
                    with urllib.request.urlopen(url, timeout=5) as resp:
                        data = json.loads(resp.read())
                        ids = {n["source_note_id"] for n in data["notes"]}
                        self.assertIn("vn_disp", ids)
                        self.assertIn("vn_proc", ids)
                        self.assertEqual(data["total"], 2)
                finally:
                    server.shutdown()
                    server.server_close()

    def test_project_router_note_identity_uses_source_project_for_detail_and_actions(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                alpha_path = svc_paths.NORMALIZED_DIR / "project_router" / "alpha" / "20260318T100000Z--pkt_same.md"
                beta_path = svc_paths.NORMALIZED_DIR / "project_router" / "beta" / "20260318T100500Z--pkt_same.md"

                alpha_meta = cli.ensure_note_metadata_defaults(
                    {
                        "source": "project_router",
                        "source_project": "alpha",
                        "source_note_id": "pkt_same",
                        "title": "Alpha packet",
                        "status": "classified",
                        "project": "home_renovation",
                    }
                )
                beta_meta = cli.ensure_note_metadata_defaults(
                    {
                        "source": "project_router",
                        "source_project": "beta",
                        "source_note_id": "pkt_same",
                        "title": "Beta packet",
                        "status": "classified",
                        "project": "home_renovation",
                    }
                )
                cli.write_note(alpha_path, alpha_meta, "Alpha body")
                cli.write_note(beta_path, beta_meta, "Beta body")

                from src.project_router.web.server import create_server

                server = create_server(port=0, static_dir=None)
                port = server.server_address[1]
                thread = threading.Thread(target=server.serve_forever)
                thread.daemon = True
                thread.start()
                try:
                    with urllib.request.urlopen(
                        f"http://localhost:{port}/api/notes?source=project_router",
                        timeout=5,
                    ) as resp:
                        data = json.loads(resp.read())
                    self.assertEqual(data["total"], 2)
                    self.assertEqual(
                        sorted(note["source_project"] for note in data["notes"]),
                        ["alpha", "beta"],
                    )

                    with urllib.request.urlopen(
                        f"http://localhost:{port}/api/notes/pkt_same?source=project_router&source_project=beta",
                        timeout=5,
                    ) as resp:
                        detail = json.loads(resp.read())["note"]
                    self.assertEqual(detail["title"], "Beta packet")
                    self.assertEqual(detail["source_project"], "beta")

                    request = urllib.request.Request(
                        f"http://localhost:{port}/api/notes/pkt_same/suggest",
                        data=json.dumps(
                            {
                                "source": "project_router",
                                "source_project": "beta",
                                "user_suggested_project": "operations",
                            }
                        ).encode("utf-8"),
                        method="POST",
                    )
                    request.add_header("Content-Type", "application/json")
                    with urllib.request.urlopen(request, timeout=5) as resp:
                        payload = json.loads(resp.read())
                    self.assertTrue(payload["ok"])

                    alpha_updated, _ = cli.read_note(alpha_path)
                    beta_updated, _ = cli.read_note(beta_path)
                    self.assertIsNone(alpha_updated.get("user_suggested_project"))
                    self.assertEqual(
                        beta_updated.get("user_suggested_project"),
                        "operations",
                    )
                finally:
                    server.shutdown()
                    server.server_close()


if __name__ == "__main__":
    unittest.main()
