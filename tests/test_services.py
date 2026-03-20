"""Smoke tests for extracted service modules."""
from __future__ import annotations

import unittest
from pathlib import Path

from src.project_router import cli

from tests.test_project_router import (
    temporary_repo_dir,
    prepare_repo,
    write_registry,
    patch_cli_paths,
)


class TestNotesService(unittest.TestCase):
    def test_parse_scalar_types(self):
        from src.project_router.services.notes import parse_scalar
        self.assertIsNone(parse_scalar("null"))
        self.assertTrue(parse_scalar("true"))
        self.assertFalse(parse_scalar("false"))
        self.assertEqual(parse_scalar("42"), 42)
        self.assertEqual(parse_scalar("3.14"), 3.14)
        self.assertEqual(parse_scalar('"hello"'), "hello")
        self.assertEqual(parse_scalar("[1, 2]"), [1, 2])
        self.assertEqual(parse_scalar("plain text"), "plain text")

    def test_dump_value_round_trip(self):
        from src.project_router.services.notes import dump_value, parse_scalar
        for val in [None, True, False, 42, 3.14, "hello", [1, 2], {"a": 1}]:
            self.assertEqual(parse_scalar(dump_value(val)), val)


class TestProjectsService(unittest.TestCase):
    def test_load_registry_returns_projects(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                from src.project_router.services.projects import load_registry
                defaults, projects = load_registry()
                self.assertIn("home_renovation", projects)

    def test_has_placeholder_path(self):
        from src.project_router.services.projects import has_placeholder_path
        self.assertTrue(has_placeholder_path(Path("/ABSOLUTE/PATH/to/inbox")))
        self.assertFalse(has_placeholder_path(Path("/home/user/inbox")))

    def test_read_json_if_exists_missing(self):
        from src.project_router.services.projects import read_json_if_exists
        self.assertIsNone(read_json_if_exists(Path("/nonexistent/file.json")))

    def test_merge_registry_configs(self):
        from src.project_router.services.projects import merge_registry_configs
        shared = {
            "defaults": {"min_keyword_hits": 2},
            "projects": {"p1": {"display_name": "P1", "language": "en"}},
        }
        local = {
            "defaults": {"min_keyword_hits": 3},
            "projects": {"p1": {"inbox_path": "/tmp/inbox"}},
        }
        merged = merge_registry_configs(shared, local)
        self.assertEqual(merged["defaults"]["min_keyword_hits"], 3)
        self.assertEqual(merged["projects"]["p1"]["display_name"], "P1")
        self.assertEqual(merged["projects"]["p1"]["inbox_path"], "/tmp/inbox")


class TestClassificationService(unittest.TestCase):
    def test_route_note_pending_project(self):
        from src.project_router.services.classification import route_note
        metadata = {"title": "Random note", "tags": [], "user_keywords": [], "inferred_keywords": []}
        defaults = {"min_keyword_hits": 2}
        projects = {}
        route, details, reason = route_note("Some body", metadata, defaults, projects)
        self.assertEqual(route, "pending_project")


class TestSuggestionsService(unittest.TestCase):
    def test_write_suggestion(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            with patch_cli_paths(root):
                note_path = cli.NORMALIZED_DIR / "voicenotes" / "20260318T100000Z--vn_sug.md"
                metadata = cli.ensure_note_metadata_defaults({
                    "source": "voicenotes", "source_note_id": "vn_sug", "title": "Test",
                    "status": "classified", "project": "home_renovation",
                })
                cli.write_note(note_path, metadata, "Body")
                from src.project_router.services.suggestions import write_suggestion
                result = write_suggestion(note_path, "garden")
                self.assertEqual(result["user_suggested_project"], "garden")
                self.assertIsNotNone(result["user_suggestion_timestamp"])
                # Verify persisted
                loaded, _ = cli.read_note(note_path)
                self.assertEqual(loaded["user_suggested_project"], "garden")

    def test_clear_suggestion(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            with patch_cli_paths(root):
                note_path = cli.NORMALIZED_DIR / "voicenotes" / "20260318T100000Z--vn_clr.md"
                metadata = cli.ensure_note_metadata_defaults({
                    "source": "voicenotes", "source_note_id": "vn_clr", "title": "Test",
                    "user_suggested_project": "garden",
                    "user_suggestion_timestamp": "2026-03-18T14:30:00Z",
                })
                cli.write_note(note_path, metadata, "Body")
                from src.project_router.services.suggestions import clear_suggestion
                result = clear_suggestion(note_path)
                self.assertIsNone(result["user_suggested_project"])
                self.assertIsNone(result["user_suggestion_timestamp"])

    def test_write_suggestion_logs_to_decision_packet(self):
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                note_path = cli.NORMALIZED_DIR / "voicenotes" / "20260318T100000Z--vn_pkt.md"
                metadata = cli.ensure_note_metadata_defaults({
                    "source": "voicenotes", "source_note_id": "vn_pkt", "title": "Test",
                    "status": "classified", "project": "home_renovation",
                })
                cli.write_note(note_path, metadata, "Body")
                from src.project_router.services.suggestions import write_suggestion
                write_suggestion(note_path, "garden")
                # Check decision packet has a suggestion review entry
                packet = cli.load_decision_packet_for_metadata(metadata)
                reviews = packet.get("reviews", [])
                self.assertTrue(len(reviews) >= 1)
                last = reviews[-1]
                self.assertEqual(last["decision"], "suggestion")
                self.assertEqual(last["suggested_project"], "garden")
                self.assertEqual(last["provenance"], "dashboard")


if __name__ == "__main__":
    unittest.main()
