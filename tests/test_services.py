"""Smoke tests for extracted service modules."""
from __future__ import annotations

import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
