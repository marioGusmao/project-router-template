"""Smoke tests for extracted service modules."""
from __future__ import annotations

import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
