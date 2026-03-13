from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from src.voice_notes import cli


def load_sync_module():
    script_path = Path(__file__).resolve().parents[1] / "src" / "voice_notes" / "sync_client.py"
    spec = importlib.util.spec_from_file_location("voicenotes_client_test", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_bootstrap_private_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap_private_repo.py"
    spec = importlib.util.spec_from_file_location("bootstrap_private_repo_test", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare_repo(root: Path) -> None:
    for path in (
        root / "data" / "raw",
        root / "data" / "normalized",
        root / "data" / "compiled",
        root / "data" / "review" / "ambiguous",
        root / "data" / "review" / "needs_review",
        root / "data" / "review" / "pending_project",
        root / "data" / "dispatched",
        root / "data" / "processed",
        root / "projects",
        root / "state",
        root / "state" / "decisions",
        root / "state" / "discoveries",
    ):
        path.mkdir(parents=True, exist_ok=True)


def patch_cli_paths(root: Path) -> ExitStack:
    data = root / "data"
    stack = ExitStack()
    for key, value in {
        "ROOT": root,
        "DATA_DIR": data,
        "RAW_DIR": data / "raw",
        "NORMALIZED_DIR": data / "normalized",
        "COMPILED_DIR": data / "compiled",
        "AMBIGUOUS_DIR": data / "review" / "ambiguous",
        "NEEDS_REVIEW_DIR": data / "review" / "needs_review",
        "PENDING_PROJECT_DIR": data / "review" / "pending_project",
        "DISPATCHED_DIR": data / "dispatched",
        "PROCESSED_DIR": data / "processed",
        "STATE_DIR": root / "state",
        "DECISIONS_DIR": root / "state" / "decisions",
        "DISCOVERIES_DIR": root / "state" / "discoveries",
        "DISCOVERY_REPORT_PATH": root / "state" / "discoveries" / "pending_project_latest.json",
        "REGISTRY_LOCAL_PATH": root / "projects" / "registry.local.json",
        "REGISTRY_SHARED_PATH": root / "projects" / "registry.shared.json",
        "REGISTRY_EXAMPLE_PATH": root / "projects" / "registry.example.json",
        "ENV_LOCAL_PATH": root / ".env.local",
        "ENV_PATH": root / ".env",
    }.items():
        stack.enter_context(mock.patch.object(cli, key, value))
    return stack


TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp-tests"
TEST_TMP_ROOT.mkdir(exist_ok=True)


def temporary_repo_dir():
    return tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT)


class VoiceNotesFlowTests(unittest.TestCase):
    def test_normalize_json_raw_creates_markdown_with_raw_link(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            raw_path = root / "data" / "raw" / "20260311T160000Z--vn_123.json"
            raw_path.write_text(
                json.dumps(
                    {
                        "source": "voicenotes",
                        "source_endpoint": "recordings",
                        "recording": {
                            "id": "vn_123",
                            "title": "Renovation idea",
                            "created_at": "2026-03-11T16:00:00Z",
                            "recorded_at": "2026-03-11T16:00:00Z",
                            "recording_type": 3,
                            "duration": 0,
                            "tags": ["renovation"],
                            "transcript": "Hello<br>world",
                        },
                    }
                ),
                encoding="utf-8",
            )

            with patch_cli_paths(root):
                cli.normalize_command(type("Args", (), {})())

            normalized = root / "data" / "normalized" / "20260311T160000Z--vn_123.md"
            metadata, body = cli.read_note(normalized)
            self.assertEqual(metadata["raw_payload_path"], str(raw_path))
            self.assertEqual(metadata["source_item_type"], "note")
            self.assertEqual(metadata["transcript_format"], "html")
            self.assertIn("Hello\nworld", body)

    def test_dispatch_requires_explicit_note_ids(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            (root / "projects" / "registry.local.json").write_text(
                json.dumps(
                    {
                        "defaults": {"auto_dispatch_threshold": 0.9},
                        "projects": {
                            "home_renovation": {
                                "display_name": "Home Renovation",
                                "language": "en",
                                "inbox_path": str(root / "home-renovation-inbox"),
                                "note_type": "project-idea",
                                "auto_dispatch_threshold": 0.9,
                                "keywords": ["renovation"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_123.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_123",
                    "title": "Renovation idea",
                    "created_at": "2026-03-11T16:00:00Z",
                    "tags": ["renovation"],
                    "status": "classified",
                    "project": "home_renovation",
                    "candidate_projects": ["home_renovation"],
                    "confidence": 1.0,
                    "routing_reason": "Matched keywords.",
                    "requires_user_confirmation": True,
                    "canonical_path": str(note_path),
                    "dispatched_to": [],
                    "note_type": "project-idea",
                },
                "# Renovation idea\n\nBody\n",
            )

            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.dispatch_command(type("Args", (), {"dry_run": False, "confirm_user_approval": True, "note_ids": []})())
            self.assertIn("--note-id", str(ctx.exception))

    def test_triage_cleans_old_review_copy(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            (root / "projects" / "registry.local.json").write_text(
                json.dumps(
                    {
                        "defaults": {"min_keyword_hits": 2},
                        "projects": {
                            "home_renovation": {
                                "display_name": "Home Renovation",
                                "language": "en",
                                "inbox_path": str(root / "home-renovation-inbox"),
                                "note_type": "project-idea",
                                "auto_dispatch_threshold": 0.9,
                                "keywords": ["renovation"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_123.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_123",
                    "title": "Loose note",
                    "created_at": "2026-03-11T16:00:00Z",
                    "tags": [],
                    "status": "normalized",
                    "project": None,
                    "candidate_projects": [],
                    "confidence": 0.0,
                    "routing_reason": "",
                    "requires_user_confirmation": True,
                    "canonical_path": str(note_path),
                    "dispatched_to": [],
                },
                "# Loose note\n\nNo matching keywords.\n",
            )
            ambiguous_path = root / "data" / "review" / "ambiguous" / note_path.name
            cli.write_note(ambiguous_path, {"status": "ambiguous"}, "stale\n")

            with patch_cli_paths(root):
                cli.triage_command(type("Args", (), {"all": False})())

            self.assertFalse(ambiguous_path.exists())
            self.assertTrue((root / "data" / "review" / "pending_project" / note_path.name).exists())

    def test_triage_routes_unmatched_note_to_pending_project(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            (root / "projects" / "registry.local.json").write_text(
                json.dumps(
                    {
                        "defaults": {"min_keyword_hits": 2},
                        "projects": {
                            "home_renovation": {
                                "display_name": "Home Renovation",
                                "language": "en",
                                "inbox_path": str(root / "home-renovation-inbox"),
                                "note_type": "project-idea",
                                "auto_dispatch_threshold": 0.9,
                                "keywords": ["renovation"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_999.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_999",
                    "title": "Future bucket",
                    "created_at": "2026-03-11T16:00:00Z",
                    "tags": [],
                    "status": "normalized",
                    "project": None,
                    "candidate_projects": [],
                    "confidence": 0.0,
                    "routing_reason": "",
                    "requires_user_confirmation": True,
                    "canonical_path": str(note_path),
                    "dispatched_to": [],
                },
                "# Future bucket\n\nThis note does not match any current project.\n",
            )

            with patch_cli_paths(root):
                cli.triage_command(type("Args", (), {"all": False})())

            metadata, _ = cli.read_note(note_path)
            self.assertEqual(metadata["status"], "pending_project")
            self.assertTrue((root / "data" / "review" / "pending_project" / note_path.name).exists())

    def test_triage_routes_weekly_meal_prep_note_when_multiple_keywords_match(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            meal_prep_inbox = root / "weekly-meal-prep-inbox"
            (root / "projects" / "registry.local.json").write_text(
                json.dumps(
                    {
                        "defaults": {"min_keyword_hits": 2},
                        "projects": {
                            "weekly_meal_prep": {
                                "display_name": "Weekly Meal Prep",
                                "language": "en",
                                "inbox_path": str(meal_prep_inbox),
                                "note_type": "daily-ops",
                                "auto_dispatch_threshold": 0.9,
                                "keywords": ["meal prep", "groceries", "recipe", "ingredients"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_weekly_meal.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_weekly_meal",
                    "title": "Meal prep groceries",
                    "created_at": "2026-03-11T16:00:00Z",
                    "tags": ["groceries"],
                    "status": "normalized",
                    "project": None,
                    "candidate_projects": [],
                    "confidence": 0.0,
                    "routing_reason": "",
                    "requires_user_confirmation": True,
                    "canonical_path": str(note_path),
                    "dispatched_to": [],
                },
                "# Meal prep groceries\n\nNeed to review the recipe ingredients and grocery list for next week.\n",
            )

            with patch_cli_paths(root):
                cli.triage_command(type("Args", (), {"all": False})())

            metadata, _ = cli.read_note(note_path)
            self.assertEqual(metadata["status"], "classified")
            self.assertEqual(metadata["project"], "weekly_meal_prep")
            self.assertEqual(metadata["note_type"], "daily-ops")
            self.assertEqual(metadata["destination"], "weekly_meal_prep")

    def test_triage_routes_brand_only_weekly_meal_prep_note_to_needs_review(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            meal_prep_inbox = root / "weekly-meal-prep-inbox"
            (root / "projects" / "registry.local.json").write_text(
                json.dumps(
                    {
                        "defaults": {"min_keyword_hits": 2},
                        "projects": {
                            "weekly_meal_prep": {
                                "display_name": "Weekly Meal Prep",
                                "language": "en",
                                "inbox_path": str(meal_prep_inbox),
                                "note_type": "daily-ops",
                                "auto_dispatch_threshold": 0.9,
                                "keywords": ["meal prep", "groceries", "recipe", "ingredients"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_weekly_meal_brand.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_weekly_meal_brand",
                    "title": "Meal Prep",
                    "created_at": "2026-03-11T16:00:00Z",
                    "tags": [],
                    "status": "normalized",
                    "project": None,
                    "candidate_projects": [],
                    "confidence": 0.0,
                    "routing_reason": "",
                    "requires_user_confirmation": True,
                    "canonical_path": str(note_path),
                    "dispatched_to": [],
                },
                "# Meal Prep\n\nNeed to confirm the plan after reviewing the grocery list.\n",
            )

            with patch_cli_paths(root):
                cli.triage_command(type("Args", (), {"all": False})())

            metadata, _ = cli.read_note(note_path)
            self.assertEqual(metadata["status"], "needs_review")
            self.assertIsNone(metadata["project"])
            self.assertEqual(metadata["destination"], "needs_review")
            self.assertTrue((root / "data" / "review" / "needs_review" / note_path.name).exists())

    def test_dispatch_requires_local_registry(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            (root / "projects" / "registry.shared.json").write_text(
                json.dumps(
                    {
                        "defaults": {},
                        "projects": {
                            "home_renovation": {
                                "display_name": "Home Renovation",
                                "language": "en",
                                "inbox_path": "/ABSOLUTE/PATH/TO/HOME_RENOVATION/Inbox/VoiceNotes",
                                "note_type": "project-idea",
                                "auto_dispatch_threshold": 0.9,
                                "keywords": ["renovation"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.load_registry(require_local=True)
            self.assertIn("registry.local.json", str(ctx.exception))

    def test_load_registry_merges_shared_and_local_overlay(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            (root / "projects" / "registry.shared.json").write_text(
                json.dumps(
                    {
                        "defaults": {"min_keyword_hits": 2, "auto_dispatch_threshold": 0.9},
                        "projects": {
                            "home_renovation": {
                                "display_name": "Home Renovation",
                                "language": "en",
                                "note_type": "project-idea",
                                "keywords": ["renovation", "contractor"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            (root / "projects" / "registry.local.json").write_text(
                json.dumps(
                    {
                        "defaults": {"min_keyword_hits": 1},
                        "projects": {
                            "home_renovation": {
                                "inbox_path": str(root / "home-renovation-inbox"),
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            with patch_cli_paths(root):
                defaults, projects = cli.load_registry(require_local=True)

            self.assertEqual(defaults["min_keyword_hits"], 1)
            self.assertIn("home_renovation", projects)
            self.assertEqual(projects["home_renovation"].display_name, "Home Renovation")
            self.assertEqual(projects["home_renovation"].note_type, "project-idea")
            self.assertEqual(projects["home_renovation"].keywords, ["renovation", "contractor"])
            self.assertEqual(projects["home_renovation"].inbox_path, root / "home-renovation-inbox")

    def test_shared_registry_supports_triage_without_local_paths(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            (root / "projects" / "registry.shared.json").write_text(
                json.dumps(
                    {
                        "defaults": {"min_keyword_hits": 1},
                        "projects": {
                            "home_renovation": {
                                "display_name": "Home Renovation",
                                "language": "en",
                                "note_type": "project-idea",
                                "auto_dispatch_threshold": 0.9,
                                "keywords": ["renovation"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_shared.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_shared",
                    "title": "Renovation shared registry note",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "normalized",
                    "project": None,
                    "dispatched_to": [],
                },
                "# Renovation shared registry note\n\nRenovation contractor follow-up.\n",
            )

            with patch_cli_paths(root):
                cli.triage_command(type("Args", (), {"all": False})())

            metadata, _ = cli.read_note(note_path)
            self.assertEqual(metadata["status"], "classified")
            self.assertEqual(metadata["project"], "home_renovation")
            self.assertEqual(metadata["note_type"], "project-idea")

    def test_shared_registry_requires_local_inbox_override_for_dispatch(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            (root / "projects" / "registry.shared.json").write_text(
                json.dumps(
                    {
                        "defaults": {},
                        "projects": {
                            "home_renovation": {
                                "display_name": "Home Renovation",
                                "language": "en",
                                "note_type": "project-idea",
                                "keywords": ["renovation"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            (root / "projects" / "registry.local.json").write_text(
                json.dumps({"projects": {"home_renovation": {}}}),
                encoding="utf-8",
            )
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_missing_inbox.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_missing_inbox",
                    "title": "Shared registry dispatch",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "classified",
                    "project": "home_renovation",
                    "note_type": "project-idea",
                    "confidence": 1.0,
                    "review_status": "approved",
                    "requires_user_confirmation": False,
                    "dispatched_to": [],
                },
                "# Shared registry dispatch\n\nBody\n",
            )
            normalized_metadata, normalized_body = cli.read_note(note_path)
            compiled_path = root / "data" / "compiled" / "20260311T160000Z--vn_missing_inbox.md"
            cli.write_note(
                compiled_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_missing_inbox",
                    "title": "Shared registry dispatch",
                    "created_at": "2026-03-11T16:00:00Z",
                    "compiled_at": "2026-03-11T16:05:00Z",
                    "compiled_from_signature": cli.canonical_compile_signature(normalized_metadata, normalized_body),
                    "brief_summary": "Compiled summary",
                    "entities": ["project:home_renovation"],
                    "facts": [],
                    "tasks": [],
                    "decisions": [],
                    "open_questions": [],
                    "follow_ups": [],
                    "timeline": [],
                    "ambiguities": [],
                    "confidence_by_field": {"routing": 1.0},
                    "evidence_spans": [],
                },
                "# Shared registry dispatch\n\n## Project-ready brief\n\nCompiled summary\n",
            )

            with patch_cli_paths(root), mock.patch("builtins.print") as print_mock:
                cli.dispatch_command(type("Args", (), {"dry_run": True, "confirm_user_approval": False, "note_ids": []})())

            payload = json.loads(print_mock.call_args.args[0])
            self.assertEqual(payload["dispatched"], 0)
            self.assertEqual(payload["candidates"][0]["skip_reason"], "no local inbox_path for project 'home_renovation'")

    def test_dispatch_requires_absolute_local_registry_path(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            (root / "projects" / "registry.local.json").write_text(
                json.dumps(
                    {
                        "defaults": {},
                        "projects": {
                            "home_renovation": {
                                "display_name": "Home Renovation",
                                "language": "en",
                                "inbox_path": "relative/inbox",
                                "note_type": "project-idea",
                                "auto_dispatch_threshold": 0.9,
                                "keywords": ["renovation"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_relative_inbox.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_relative_inbox",
                    "title": "Relative inbox path",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "classified",
                    "project": "home_renovation",
                    "note_type": "project-idea",
                    "confidence": 1.0,
                    "review_status": "approved",
                    "requires_user_confirmation": False,
                    "dispatched_to": [],
                },
                "# Relative inbox path\n\nBody\n",
            )
            normalized_metadata, normalized_body = cli.read_note(note_path)
            compiled_path = root / "data" / "compiled" / "20260311T160000Z--vn_relative_inbox.md"
            cli.write_note(
                compiled_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_relative_inbox",
                    "title": "Relative inbox path",
                    "created_at": "2026-03-11T16:00:00Z",
                    "compiled_at": "2026-03-11T16:05:00Z",
                    "compiled_from_signature": cli.canonical_compile_signature(normalized_metadata, normalized_body),
                    "brief_summary": "Compiled summary",
                    "entities": ["project:home_renovation"],
                    "facts": [],
                    "tasks": [],
                    "decisions": [],
                    "open_questions": [],
                    "follow_ups": [],
                    "timeline": [],
                    "ambiguities": [],
                    "confidence_by_field": {"routing": 1.0},
                    "evidence_spans": [],
                },
                "# Relative inbox path\n\n## Project-ready brief\n\nCompiled summary\n",
            )

            with patch_cli_paths(root), mock.patch("builtins.print") as print_mock:
                cli.dispatch_command(type("Args", (), {"dry_run": True, "confirm_user_approval": False, "note_ids": []})())

            payload = json.loads(print_mock.call_args.args[0])
            self.assertEqual(payload["dispatched"], 0)
            self.assertIn("absolute inbox path", payload["candidates"][0]["skip_reason"])

    def test_dispatch_mixed_batch_skips_unconfigured_project_and_keeps_valid_candidate(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            (root / "projects" / "registry.shared.json").write_text(
                json.dumps(
                    {
                        "defaults": {"auto_dispatch_threshold": 0.9},
                        "projects": {
                            "home_renovation": {
                                "display_name": "Home Renovation",
                                "language": "en",
                                "note_type": "project-idea",
                                "keywords": ["renovation"],
                            },
                            "weekly_meal_prep": {
                                "display_name": "Weekly Meal Prep",
                                "language": "en",
                                "note_type": "daily-ops",
                                "keywords": ["meal prep"],
                            },
                        },
                    }
                ),
                encoding="utf-8",
            )
            (root / "projects" / "registry.local.json").write_text(
                json.dumps(
                    {
                        "projects": {
                            "home_renovation": {
                                "inbox_path": str(root / "home-renovation-inbox"),
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            def seed_candidate(note_id: str, project_key: str, title: str) -> None:
                note_path = root / "data" / "normalized" / f"20260311T160000Z--{note_id}.md"
                cli.write_note(
                    note_path,
                    {
                        "source": "voicenotes",
                        "source_note_id": note_id,
                        "title": title,
                        "created_at": "2026-03-11T16:00:00Z",
                        "status": "classified",
                        "project": project_key,
                        "note_type": "project-idea" if project_key == "home_renovation" else "daily-ops",
                        "confidence": 1.0,
                        "review_status": "approved",
                        "requires_user_confirmation": False,
                        "dispatched_to": [],
                    },
                    f"# {title}\n\nBody\n",
                )
                normalized_metadata, normalized_body = cli.read_note(note_path)
                compiled_path = root / "data" / "compiled" / note_path.name
                cli.write_note(
                    compiled_path,
                    {
                        "source": "voicenotes",
                        "source_note_id": note_id,
                        "title": title,
                        "created_at": "2026-03-11T16:00:00Z",
                        "compiled_at": "2026-03-11T16:05:00Z",
                        "compiled_from_signature": cli.canonical_compile_signature(normalized_metadata, normalized_body),
                        "brief_summary": "Compiled summary",
                        "entities": [f"project:{project_key}"],
                        "facts": [],
                        "tasks": [],
                        "decisions": [],
                        "open_questions": [],
                        "follow_ups": [],
                        "timeline": [],
                        "ambiguities": [],
                        "confidence_by_field": {"routing": 1.0},
                        "evidence_spans": [],
                    },
                    f"# {title}\n\n## Project-ready brief\n\nCompiled summary\n",
                )

            seed_candidate("vn_home", "home_renovation", "Home renovation follow-up")
            seed_candidate("vn_meal", "weekly_meal_prep", "Weekly meal prep follow-up")

            with patch_cli_paths(root), mock.patch("builtins.print") as print_mock:
                cli.dispatch_command(type("Args", (), {"dry_run": True, "confirm_user_approval": False, "note_ids": []})())

            payload = json.loads(print_mock.call_args.args[0])
            self.assertEqual(payload["dispatched"], 1)
            self.assertEqual(payload["skipped"], 1)
            candidate_map = {item["source_note_id"]: item for item in payload["candidates"]}
            self.assertIsNone(candidate_map["vn_home"]["skip_reason"])
            self.assertEqual(candidate_map["vn_meal"]["skip_reason"], "no local inbox_path for project 'weekly_meal_prep'")

    def test_normalize_updates_existing_note_and_preserves_manual_metadata(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            raw_path = root / "data" / "raw" / "20260311T160000Z--vn_123.json"
            raw_path.write_text(
                json.dumps(
                    {
                        "source": "voicenotes",
                        "source_endpoint": "recordings",
                        "recording": {
                            "id": "vn_123",
                            "title": "Updated meeting",
                            "created_at": "2026-03-11T16:00:00Z",
                            "recorded_at": "2026-03-11T16:00:00Z",
                            "recording_type": 2,
                            "duration": 120,
                            "tags": ["Meeting"],
                            "transcript": "Speaker 1<br>Updated transcript",
                        },
                    }
                ),
                encoding="utf-8",
            )
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_123.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_123",
                    "title": "Old title",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "classified",
                    "project": "home_renovation",
                    "review_status": "approved",
                    "requires_user_confirmation": False,
                    "user_keywords": ["important"],
                    "thread_id": "thread-1",
                    "dispatched_to": [],
                },
                "# Old title\n\nOld transcript\n",
            )

            with patch_cli_paths(root):
                cli.normalize_command(type("Args", (), {})())

            metadata, body = cli.read_note(note_path)
            self.assertEqual(metadata["title"], "Updated meeting")
            self.assertEqual(metadata["project"], "home_renovation")
            self.assertEqual(metadata["review_status"], "approved")
            self.assertEqual(metadata["user_keywords"], ["important"])
            self.assertEqual(metadata["thread_id"], "thread-1")
            self.assertEqual(metadata["capture_kind"], "meeting_recording")
            self.assertIn("Updated transcript", body)

    def test_normalize_rejects_invalid_note_id(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            raw_path = root / "data" / "raw" / "20260311T160000Z--evil.json"
            raw_path.write_text(
                json.dumps(
                    {
                        "source": "voicenotes",
                        "source_endpoint": "recordings",
                        "recording": {
                            "id": "../escape",
                            "title": "Invalid id",
                            "created_at": "2026-03-11T16:00:00Z",
                            "recorded_at": "2026-03-11T16:00:00Z",
                            "recording_type": 3,
                            "duration": 0,
                            "tags": [],
                            "transcript": "Body",
                        },
                    }
                ),
                encoding="utf-8",
            )

            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.normalize_command(type("Args", (), {})())

            self.assertIn("Invalid source_note_id", str(ctx.exception))

    def test_normalize_reuses_existing_canonical_path_when_created_at_changes(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            first_raw = root / "data" / "raw" / "20260311T160000Z--vn_same.json"
            second_raw = root / "data" / "raw" / "20260312T160000Z--vn_same.json"
            first_raw.write_text(
                json.dumps(
                    {
                        "source": "voicenotes",
                        "source_endpoint": "recordings",
                        "recording": {
                            "id": "vn_same",
                            "title": "First title",
                            "created_at": "2026-03-11T16:00:00Z",
                            "recorded_at": "2026-03-11T16:00:00Z",
                            "recording_type": 3,
                            "duration": 0,
                            "tags": [],
                            "transcript": "First body",
                        },
                    }
                ),
                encoding="utf-8",
            )
            second_raw.write_text(
                json.dumps(
                    {
                        "source": "voicenotes",
                        "source_endpoint": "recordings",
                        "recording": {
                            "id": "vn_same",
                            "title": "Second title",
                            "created_at": "2026-03-12T16:00:00Z",
                            "recorded_at": "2026-03-12T16:00:00Z",
                            "recording_type": 3,
                            "duration": 0,
                            "tags": [],
                            "transcript": "Second body",
                        },
                    }
                ),
                encoding="utf-8",
            )

            with patch_cli_paths(root):
                cli.normalize_command(type("Args", (), {})())

            normalized_files = sorted((root / "data" / "normalized").glob("*.md"))
            self.assertEqual([path.name for path in normalized_files], ["20260311T160000Z--vn_same.md"])
            metadata, body = cli.read_note(normalized_files[0])
            self.assertEqual(metadata["source_note_id"], "vn_same")
            self.assertEqual(metadata["title"], "Second title")
            self.assertIn("Second body", body)

    def test_triage_preserves_approved_note_when_route_is_unchanged(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            (root / "projects" / "registry.local.json").write_text(
                json.dumps(
                    {
                        "defaults": {"min_keyword_hits": 1},
                        "projects": {
                            "home_renovation": {
                                "display_name": "Home Renovation",
                                "language": "en",
                                "inbox_path": str(root / "home-renovation-inbox"),
                                "note_type": "project-idea",
                                "auto_dispatch_threshold": 0.9,
                                "keywords": ["renovation"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_124.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_124",
                    "title": "Renovation idea",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "classified",
                    "project": "home_renovation",
                    "review_status": "approved",
                    "requires_user_confirmation": False,
                    "dispatched_to": [],
                },
                "# Renovation idea\n\nRenovation planning project.\n",
            )

            with patch_cli_paths(root):
                cli.triage_command(type("Args", (), {"all": False})())

            metadata, _ = cli.read_note(note_path)
            self.assertEqual(metadata["review_status"], "approved")
            self.assertFalse(metadata["requires_user_confirmation"])

    def test_manual_approve_can_dispatch_below_threshold(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            inbox = root / "home-renovation-inbox"
            (root / "projects" / "registry.local.json").write_text(
                json.dumps(
                    {
                        "defaults": {"auto_dispatch_threshold": 0.9},
                        "projects": {
                            "home_renovation": {
                                "display_name": "Home Renovation",
                                "language": "en",
                                "inbox_path": str(inbox),
                                "note_type": "project-idea",
                                "auto_dispatch_threshold": 0.9,
                                "keywords": ["renovation"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_low.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_low",
                    "title": "Manual low confidence review",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "needs_review",
                    "destination": "needs_review",
                    "project": None,
                    "candidate_projects": ["home_renovation"],
                    "confidence": 0.2,
                    "routing_reason": "Weak match.",
                    "review_status": "pending",
                    "requires_user_confirmation": True,
                    "canonical_path": str(note_path),
                    "raw_payload_path": str(root / "data" / "raw" / "20260311T160000Z--vn_low.json"),
                    "dispatched_to": [],
                },
                "# Manual low confidence review\n\nMaybe this belongs to the renovation project.\n",
            )

            with patch_cli_paths(root):
                cli.decide_command(
                    type(
                        "Args",
                        (),
                        {
                            "note_id": "vn_low",
                            "decision": "approve",
                            "final_project": "home_renovation",
                            "final_type": None,
                            "user_keywords": None,
                            "related_note_ids": None,
                            "thread_id": None,
                            "continuation_of": None,
                            "notes": None,
                        },
                    )()
                )
                cli.compile_command(type("Args", (), {"note_ids": None})())
                cli.dispatch_command(
                    type(
                        "Args",
                        (),
                        {"dry_run": False, "confirm_user_approval": True, "note_ids": ["vn_low"]},
                    )()
                )

            metadata, _ = cli.read_note(note_path)
            self.assertEqual(metadata["status"], "dispatched")
            self.assertTrue((inbox / "20260311T160000Z--vn_low.md").exists())

    def test_dispatch_success_writes_downstream_and_mirror(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            inbox = root / "home-renovation-inbox"
            (root / "projects" / "registry.local.json").write_text(
                json.dumps(
                    {
                        "defaults": {"auto_dispatch_threshold": 0.9},
                        "projects": {
                            "home_renovation": {
                                "display_name": "Home Renovation",
                                "language": "en",
                                "inbox_path": str(inbox),
                                "note_type": "project-idea",
                                "auto_dispatch_threshold": 0.9,
                                "keywords": ["renovation"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_125.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_125",
                    "title": "Renovation dispatch",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "classified",
                    "project": "home_renovation",
                    "note_type": "project-idea",
                    "confidence": 1.0,
                    "review_status": "approved",
                    "requires_user_confirmation": False,
                    "dispatched_to": [],
                },
                "# Renovation dispatch\n\nBody\n",
            )
            normalized_metadata, normalized_body = cli.read_note(note_path)
            compiled_path = root / "data" / "compiled" / "20260311T160000Z--vn_125.md"
            cli.write_note(
                compiled_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_125",
                    "title": "Renovation dispatch",
                    "created_at": "2026-03-11T16:00:00Z",
                    "compiled_at": "2026-03-11T16:05:00Z",
                    "compiled_from_signature": cli.canonical_compile_signature(normalized_metadata, normalized_body),
                    "brief_summary": "Compiled summary",
                    "entities": ["project:home_renovation"],
                    "facts": ["captured_at: 2026-03-11T16:00:00Z"],
                    "tasks": ["Follow up with the team."],
                    "decisions": [],
                    "open_questions": [],
                    "follow_ups": [],
                    "timeline": [],
                    "ambiguities": [],
                    "confidence_by_field": {"routing": 1.0},
                    "evidence_spans": [{"field": "tasks", "excerpt": "Follow up with the team."}],
                },
                "# Renovation dispatch\n\n## Project-ready brief\n\nCompiled summary\n",
            )

            with patch_cli_paths(root):
                cli.dispatch_command(
                    type(
                        "Args",
                        (),
                        {"dry_run": False, "confirm_user_approval": True, "note_ids": ["vn_125"]},
                    )()
                )

            destination = inbox / "20260311T160000Z--vn_125.md"
            mirror = root / "data" / "dispatched" / "home_renovation" / "20260311T160000Z--vn_125.md"
            metadata, _ = cli.read_note(note_path)
            dispatched_metadata, dispatched_body = cli.read_note(destination)
            packet = json.loads((root / "state" / "decisions" / "vn_125.json").read_text(encoding="utf-8"))
            self.assertTrue(destination.exists())
            self.assertTrue(mirror.exists())
            self.assertEqual(metadata["status"], "dispatched")
            self.assertEqual(metadata["dispatched_to"], [str(destination)])
            self.assertEqual(packet["dispatch"]["destination"], str(destination))
            self.assertEqual(packet["dispatch"]["compiled_path"], str(compiled_path))
            self.assertEqual(dispatched_metadata["compiled_path"], str(compiled_path))
            self.assertIn("Project-ready brief", dispatched_body)

    def test_compile_generates_project_ready_package(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_126.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_126",
                    "title": "Renovation weekly meeting follow-up",
                    "created_at": "2026-03-11T16:00:00Z",
                    "recording_type": 2,
                    "tags": ["Meeting", "renovation"],
                    "capture_kind": "meeting_recording",
                    "intent": "decision_log",
                    "destination": "home_renovation",
                    "status": "classified",
                    "project": "home_renovation",
                    "note_type": "project-idea",
                    "confidence": 0.92,
                    "review_status": "approved",
                    "user_keywords": ["strategy"],
                    "inferred_keywords": ["renovation", "meeting", "follow-up"],
                    "related_note_ids": ["vn_120"],
                    "canonical_path": str(note_path),
                    "raw_payload_path": str(root / "data" / "raw" / "20260311T160000Z--vn_126.json"),
                    "dispatched_to": [],
                },
                "# Renovation weekly meeting follow-up\n\nWe decided to test the contractor pilot this week. I need to send the proposal tomorrow. Can we confirm the pricing?\n",
            )

            with patch_cli_paths(root):
                cli.compile_command(type("Args", (), {"note_ids": None})())

            compiled_path = root / "data" / "compiled" / "20260311T160000Z--vn_126.md"
            metadata, body = cli.read_note(compiled_path)
            self.assertTrue(compiled_path.exists())
            self.assertEqual(metadata["compiled_from_path"], str(note_path))
            self.assertEqual(metadata["project"], "home_renovation")
            self.assertIn("Project-ready brief", body)
            self.assertTrue(metadata["tasks"])
            self.assertTrue(metadata["decisions"])
            self.assertTrue(metadata["open_questions"])
            self.assertTrue(metadata["evidence_spans"])

    def test_dispatch_skips_candidates_without_compiled_package(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            inbox = root / "home-renovation-inbox"
            (root / "projects" / "registry.local.json").write_text(
                json.dumps(
                    {
                        "defaults": {"auto_dispatch_threshold": 0.9},
                        "projects": {
                            "home_renovation": {
                                "display_name": "Home Renovation",
                                "language": "en",
                                "inbox_path": str(inbox),
                                "note_type": "project-idea",
                                "auto_dispatch_threshold": 0.9,
                                "keywords": ["renovation"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_127.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_127",
                    "title": "Renovation dispatch pending compile",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "classified",
                    "project": "home_renovation",
                    "note_type": "project-idea",
                    "confidence": 1.0,
                    "review_status": "approved",
                    "requires_user_confirmation": False,
                    "dispatched_to": [],
                },
                "# Renovation dispatch pending compile\n\nBody\n",
            )

            with patch_cli_paths(root), mock.patch("builtins.print") as print_mock:
                cli.dispatch_command(type("Args", (), {"dry_run": False, "confirm_user_approval": True, "note_ids": ["vn_127"]})())

            payload = json.loads(print_mock.call_args.args[0])
            self.assertEqual(payload["dispatched"], 0)
            self.assertEqual(payload["candidates"][0]["compiled_ready"], False)
            self.assertFalse((inbox / "20260311T160000Z--vn_127.md").exists())

    def test_dispatch_skips_stale_compiled_package(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            inbox = root / "home-renovation-inbox"
            (root / "projects" / "registry.local.json").write_text(
                json.dumps(
                    {
                        "defaults": {"auto_dispatch_threshold": 0.9},
                        "projects": {
                            "home_renovation": {
                                "display_name": "Home Renovation",
                                "language": "en",
                                "inbox_path": str(inbox),
                                "note_type": "project-idea",
                                "auto_dispatch_threshold": 0.9,
                                "keywords": ["renovation"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_128.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_128",
                    "title": "Renovation stale compile",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "classified",
                    "project": "home_renovation",
                    "note_type": "project-idea",
                    "confidence": 1.0,
                    "review_status": "approved",
                    "requires_user_confirmation": False,
                    "dispatched_to": [],
                },
                "# Renovation stale compile\n\nNeed to send the old proposal.\n",
            )

            with patch_cli_paths(root):
                cli.compile_command(type("Args", (), {"note_ids": None})())
                metadata, body = cli.read_note(note_path)
                cli.write_note(note_path, metadata, "# Renovation stale compile\n\nNeed to send the NEW proposal.\n")
                with mock.patch("builtins.print") as print_mock:
                    cli.dispatch_command(type("Args", (), {"dry_run": False, "confirm_user_approval": True, "note_ids": ["vn_128"]})())

            payload = json.loads(print_mock.call_args.args[0])
            self.assertEqual(payload["dispatched"], 0)
            self.assertEqual(payload["candidates"][0]["compiled_ready"], True)
            self.assertEqual(payload["candidates"][0]["compiled_fresh"], False)
            self.assertFalse((inbox / "20260311T160000Z--vn_128.md").exists())

    def test_dispatch_dry_run_targets_weekly_meal_prep_inbox(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            inbox = root / "weekly-meal-prep-inbox"
            (root / "projects" / "registry.local.json").write_text(
                json.dumps(
                    {
                        "defaults": {"auto_dispatch_threshold": 0.9},
                        "projects": {
                            "weekly_meal_prep": {
                                "display_name": "Weekly Meal Prep",
                                "language": "en",
                                "inbox_path": str(inbox),
                                "note_type": "daily-ops",
                                "auto_dispatch_threshold": 0.9,
                                "keywords": ["meal prep", "groceries"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_weekly_meal_dispatch.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_weekly_meal_dispatch",
                    "title": "Weekly meal prep dispatch",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "classified",
                    "project": "weekly_meal_prep",
                    "note_type": "daily-ops",
                    "confidence": 1.0,
                    "review_status": "approved",
                    "requires_user_confirmation": False,
                    "dispatched_to": [],
                },
                "# Weekly meal prep dispatch\n\nBody\n",
            )

            normalized_metadata, normalized_body = cli.read_note(note_path)
            compiled_path = root / "data" / "compiled" / "20260311T160000Z--vn_weekly_meal_dispatch.md"
            cli.write_note(
                compiled_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_weekly_meal_dispatch",
                    "title": "Weekly meal prep dispatch",
                    "created_at": "2026-03-11T16:00:00Z",
                    "compiled_at": "2026-03-11T16:05:00Z",
                    "compiled_from_signature": cli.canonical_compile_signature(normalized_metadata, normalized_body),
                    "brief_summary": "Compiled summary",
                    "entities": ["project:weekly_meal_prep"],
                    "facts": ["captured_at: 2026-03-11T16:00:00Z"],
                    "tasks": ["Confirm stock counts."],
                    "decisions": [],
                    "open_questions": [],
                    "follow_ups": [],
                    "timeline": [],
                    "ambiguities": [],
                    "confidence_by_field": {"routing": 1.0},
                    "evidence_spans": [{"field": "tasks", "excerpt": "Confirm stock counts."}],
                },
                "# Weekly meal prep dispatch\n\n## Project-ready brief\n\nCompiled summary\n",
            )

            with patch_cli_paths(root), mock.patch("builtins.print") as print_mock:
                cli.dispatch_command(
                    type(
                        "Args",
                        (),
                        {"dry_run": True, "confirm_user_approval": False, "note_ids": []},
                    )()
                )

            payload = json.loads(print_mock.call_args.args[0])
            self.assertEqual(payload["dispatched"], 1)
            self.assertEqual(
                payload["candidates"][0]["destination"],
                str(inbox / "20260311T160000Z--vn_weekly_meal_dispatch.md"),
            )
            self.assertFalse((inbox / "20260311T160000Z--vn_weekly_meal_dispatch.md").exists())

    def test_compile_is_idempotent_and_preserves_compiled_at_when_unchanged(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_129.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_129",
                    "title": "Idempotent compile",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "pending_project",
                    "review_status": "pending",
                    "capture_kind": "reference",
                    "intent": "reference",
                    "destination": "pending_project",
                    "related_note_ids": [],
                    "dispatched_to": [],
                },
                "# Idempotent compile\n\nReference body.\n",
            )

            with patch_cli_paths(root), mock.patch("builtins.print"):
                cli.compile_command(type("Args", (), {"note_ids": None})())
                compiled_path = root / "data" / "compiled" / "20260311T160000Z--vn_129.md"
                first_metadata, _ = cli.read_note(compiled_path)
                cli.compile_command(type("Args", (), {"note_ids": None})())
                second_metadata, _ = cli.read_note(compiled_path)

            self.assertEqual(first_metadata["compiled_at"], second_metadata["compiled_at"])

    def test_discover_groups_pending_project_notes(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            note_one = root / "data" / "normalized" / "20260311T160000Z--vn_201.md"
            note_two = root / "data" / "normalized" / "20260311T161000Z--vn_202.md"
            cli.write_note(
                note_one,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_201",
                    "title": "Insurance renewal for vacuum",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "pending_project",
                    "review_status": "pending",
                    "capture_kind": "purchase_record",
                    "intent": "pending_project",
                    "user_keywords": ["insurance"],
                    "inferred_keywords": ["vacuum", "renewal", "insurance"],
                    "related_note_ids": [],
                    "dispatched_to": [],
                },
                "# Insurance renewal for vacuum\n\nNeed to review warranty and insurance renewal.\n",
            )
            cli.write_note(
                note_two,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_202",
                    "title": "Warranty follow-up for vacuum",
                    "created_at": "2026-03-11T16:10:00Z",
                    "status": "pending_project",
                    "review_status": "pending",
                    "capture_kind": "purchase_record",
                    "intent": "pending_project",
                    "user_keywords": [],
                    "inferred_keywords": ["vacuum", "warranty", "insurance"],
                    "related_note_ids": [],
                    "dispatched_to": [],
                },
                "# Warranty follow-up for vacuum\n\nNeed to review warranty insurance details.\n",
            )
            review_copy_one = root / "data" / "review" / "pending_project" / note_one.name
            cli.write_note(review_copy_one, {"status": "pending_project"}, "stale copy\n")

            with patch_cli_paths(root):
                cli.discover_command(type("Args", (), {})())

            report = json.loads((root / "state" / "discoveries" / "pending_project_latest.json").read_text(encoding="utf-8"))
            refreshed_metadata, refreshed_body = cli.read_note(review_copy_one)
            self.assertEqual(report["pending_project_notes"], 2)
            self.assertEqual(report["clusters"][0]["note_count"], 2)
            self.assertIn("insurance", report["clusters"][0]["suggested_keywords"])
            self.assertEqual(report["clusters"][0]["notes"][0]["normalized_path"], str(note_one))
            self.assertEqual(report["clusters"][0]["notes"][0]["review_path"], str(review_copy_one))
            self.assertEqual(refreshed_metadata["source_note_id"], "vn_201")
            self.assertIn("insurance renewal", refreshed_body.lower())

    def test_decide_records_thread_annotations(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            (root / "projects" / "registry.local.json").write_text(
                json.dumps(
                    {
                        "defaults": {"min_keyword_hits": 2},
                        "projects": {
                            "home_renovation": {
                                "display_name": "Home Renovation",
                                "language": "en",
                                "inbox_path": str(root / "home-renovation-inbox"),
                                "note_type": "project-idea",
                                "auto_dispatch_threshold": 0.9,
                                "keywords": ["renovation"],
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_300.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_300",
                    "title": "Renovation thread note",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "classified",
                    "project": "home_renovation",
                    "candidate_projects": ["home_renovation"],
                    "confidence": 1.0,
                    "routing_reason": "Matched keywords.",
                    "review_status": "pending",
                    "requires_user_confirmation": True,
                    "canonical_path": str(note_path),
                    "user_keywords": [],
                    "inferred_keywords": ["renovation", "planning"],
                    "related_note_ids": [],
                    "dispatched_to": [],
                    "note_type": "project-idea",
                },
                "# Renovation thread note\n\nBody\n",
            )

            with patch_cli_paths(root):
                cli.decide_command(
                    type(
                        "Args",
                        (),
                        {
                            "note_id": "vn_300",
                            "decision": "approve",
                            "final_project": "home_renovation",
                            "final_type": None,
                            "user_keywords": ["strategy"],
                            "related_note_ids": ["vn_299"],
                            "thread_id": "renovation-planning",
                            "continuation_of": "vn_299",
                            "notes": "linked thread",
                        },
                    )()
                )

            metadata, _ = cli.read_note(note_path)
            self.assertEqual(metadata["thread_id"], "renovation-planning")
            self.assertEqual(metadata["continuation_of"], "vn_299")
            self.assertEqual(metadata["user_keywords"], ["strategy"])
            self.assertEqual(metadata["related_note_ids"], ["vn_299"])
            packet = json.loads((root / "state" / "decisions" / "vn_300.json").read_text(encoding="utf-8"))
            self.assertFalse(packet["proposal"]["requires_user_confirmation"])

    def test_review_uses_canonical_metadata_when_packet_is_stale(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_400.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_400",
                    "title": "Meeting follow-up",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "pending_project",
                    "review_status": "pending",
                    "capture_kind": "meeting_recording",
                    "intent": "decision_log",
                    "destination": "pending_project",
                    "user_keywords": ["audit"],
                    "inferred_keywords": ["meeting", "follow-up"],
                    "classification_basis": ["recording_type:2"],
                    "related_note_ids": [],
                    "dispatched_to": [],
                },
                "# Meeting follow-up\n\nBody\n",
            )
            (root / "state" / "decisions" / "vn_400.json").write_text(
                json.dumps(
                    {
                        "source_note_id": "vn_400",
                        "canonical_path": str(note_path),
                        "title": "Meeting follow-up",
                        "proposal": {"status": "pending_project", "review_status": "pending", "action": "pending_project"},
                        "intent": "pending_project",
                        "capture_kind": None,
                        "user_keywords": [],
                        "inferred_keywords": [],
                        "thread": {},
                    }
                ),
                encoding="utf-8",
            )

            with patch_cli_paths(root), mock.patch("builtins.print") as print_mock:
                cli.review_command(type("Args", (), {"all": True, "note_id": None})())

            payload = json.loads(print_mock.call_args.args[0])
            self.assertEqual(payload[0]["intent"], "decision_log")
            self.assertEqual(payload[0]["capture_kind"], "meeting_recording")
            self.assertEqual(payload[0]["user_keywords"], ["audit"])

    def test_review_note_id_uses_reconciled_view(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_401.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_401",
                    "title": "Canonical title",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "pending_project",
                    "review_status": "pending",
                    "capture_kind": "meeting_recording",
                    "intent": "decision_log",
                    "destination": "pending_project",
                    "user_keywords": ["audit"],
                    "inferred_keywords": ["meeting"],
                    "related_note_ids": [],
                    "dispatched_to": [],
                },
                "# Canonical title\n\nBody\n",
            )
            (root / "state" / "decisions" / "vn_401.json").write_text(
                json.dumps(
                    {
                        "source_note_id": "vn_401",
                        "canonical_path": str(note_path),
                        "title": "Stale title",
                        "proposal": {"status": "classified", "review_status": "approved", "action": "propose_dispatch"},
                        "intent": "reference",
                        "capture_kind": "reference",
                    }
                ),
                encoding="utf-8",
            )

            with patch_cli_paths(root), mock.patch("builtins.print") as print_mock:
                cli.review_command(type("Args", (), {"all": True, "note_id": "vn_401"})())

            payload = json.loads(print_mock.call_args.args[0])
            self.assertEqual(payload["title"], "Canonical title")
            self.assertEqual(payload["intent"], "decision_log")
            self.assertEqual(payload["review_status"], "pending")

    def test_review_filters_using_canonical_review_status(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_402.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_402",
                    "title": "Needs canonical review",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "needs_review",
                    "review_status": "pending",
                    "capture_kind": "reference",
                    "intent": "reference",
                    "destination": "needs_review",
                    "related_note_ids": [],
                    "dispatched_to": [],
                },
                "# Needs canonical review\n\nBody\n",
            )
            (root / "state" / "decisions" / "vn_402.json").write_text(
                json.dumps(
                    {
                        "source_note_id": "vn_402",
                        "canonical_path": str(note_path),
                        "proposal": {"status": "classified", "review_status": "approved", "action": "propose_dispatch"},
                    }
                ),
                encoding="utf-8",
            )

            with patch_cli_paths(root), mock.patch("builtins.print") as print_mock:
                cli.review_command(type("Args", (), {"all": False, "note_id": None})())

            payload = json.loads(print_mock.call_args.args[0])
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["source_note_id"], "vn_402")
            self.assertEqual(payload[0]["review_status"], "pending")

    def test_review_surfaces_compile_required_notes(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            note_path = root / "data" / "normalized" / "20260311T160000Z--vn_403.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_403",
                    "title": "Approved without compile",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "classified",
                    "project": "home_renovation",
                    "note_type": "project-idea",
                    "confidence": 0.98,
                    "review_status": "approved",
                    "requires_user_confirmation": False,
                    "capture_kind": "project_idea",
                    "intent": "actionable",
                    "destination": "home_renovation",
                    "related_note_ids": [],
                    "dispatched_to": [],
                },
                "# Approved without compile\n\nBody\n",
            )
            (root / "state" / "decisions" / "vn_403.json").write_text(
                json.dumps(
                    {
                        "source_note_id": "vn_403",
                        "canonical_path": str(note_path),
                        "proposal": {"status": "classified", "review_status": "approved", "proposed_project": "home_renovation"},
                    }
                ),
                encoding="utf-8",
            )

            with patch_cli_paths(root), mock.patch("builtins.print") as print_mock:
                cli.review_command(type("Args", (), {"all": False, "note_id": None})())

            payload = json.loads(print_mock.call_args.args[0])
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["source_note_id"], "vn_403")
            self.assertEqual(payload[0]["action"], "compile_required")
            self.assertFalse(payload[0]["compiled_ready"])

    def test_extract_facts_treats_large_duration_values_as_milliseconds(self) -> None:
        facts = cli.extract_facts(
            {"created_at": "2026-03-11T16:00:00Z", "duration": 4693101},
            [],
        )
        self.assertIn("duration_ms: 4693101", facts)
        self.assertIn("duration_seconds_approx: 4693.1", facts)
        self.assertNotIn("duration_seconds: 4693101", facts)

    def test_parser_accepts_discover_and_decide_annotation_flags(self) -> None:
        parser = cli.build_parser()
        discover_args = parser.parse_args(["discover"])
        compile_args = parser.parse_args(["compile", "--note-id", "vn_2"])
        decide_args = parser.parse_args(
            [
                "decide",
                "--note-id",
                "vn_1",
                "--decision",
                "pending-project",
                "--user-keyword",
                "insurance",
                "--related-note-id",
                "vn_0",
                "--thread-id",
                "thread-1",
                "--continuation-of",
                "vn_0",
            ]
        )
        self.assertEqual(discover_args.command, "discover")
        self.assertEqual(compile_args.note_ids, ["vn_2"])
        self.assertEqual(decide_args.user_keywords, ["insurance"])
        self.assertEqual(decide_args.related_note_ids, ["vn_0"])
        self.assertEqual(decide_args.thread_id, "thread-1")


class SyncClientTests(unittest.TestCase):
    def test_note_filename_does_not_change_when_title_changes(self) -> None:
        module = load_sync_module()
        base = {"id": "vn_123", "created_at": "2026-03-11T16:00:00.000000Z"}
        self.assertEqual(
            module.note_filename({**base, "title": "First title"}),
            module.note_filename({**base, "title": "Changed title"}),
        )

    def test_note_filename_rejects_invalid_note_id(self) -> None:
        module = load_sync_module()
        with self.assertRaises(SystemExit) as ctx:
            module.note_filename({"id": "../escape", "created_at": "2026-03-11T16:00:00.000000Z"})
        self.assertIn("Invalid source_note_id", str(ctx.exception))

    def test_merge_sync_state_keeps_boundary_ids(self) -> None:
        module = load_sync_module()
        state = module.merge_sync_state(
            {"last_synced_at": "2026-03-11T10:00:00Z", "last_synced_ids": ["a"]},
            "2026-03-11T10:00:00Z",
            ["b"],
        )
        self.assertEqual(state["last_synced_ids"], ["a", "b"])

    def test_unwrap_recording_payload_reads_live_detail_envelope(self) -> None:
        module = load_sync_module()
        payload = {"data": {"id": "vn_500", "title": "Meeting"}}
        self.assertEqual(module.unwrap_recording_payload(payload)["id"], "vn_500")

    def test_request_json_raises_on_http_status_error(self) -> None:
        module = load_sync_module()
        result = mock.Mock(returncode=22, stdout='{"error":"denied"}\n__CODEX_STATUS__:403', stderr="")
        with mock.patch.object(module, "require_api_key", return_value="token"), mock.patch.object(module.subprocess, "run", return_value=result):
            with self.assertRaises(SystemExit) as ctx:
                module.request_json("GET", "/recordings/test")
        self.assertIn("HTTP 403", str(ctx.exception))

    def test_command_sync_updates_existing_payload_when_recording_changes(self) -> None:
        module = load_sync_module()
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            output_dir = root / "raw"
            output_dir.mkdir(parents=True, exist_ok=True)
            state_file = root / "sync_state.json"
            previous_recording = {
                "id": "vn_600",
                "title": "Old title",
                "created_at": "2026-03-11T16:00:00.000000Z",
                "recorded_at": "2026-03-11T16:00:00.000000Z",
                "recording_type": 3,
                "duration": 60,
                "tags": ["renovation"],
                "transcript": "Old transcript",
            }
            raw_path = output_dir / module.note_filename(previous_recording)
            raw_path.write_text(json.dumps(module.raw_export_payload(previous_recording), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            updated_recording = {**previous_recording, "title": "Updated title", "transcript": "Updated transcript"}
            args = type(
                "Args",
                (),
                {
                    "state_file": state_file,
                    "output_dir": str(output_dir),
                    "date_from": None,
                    "date_to": None,
                    "no_checkpoint": True,
                    "tags": None,
                    "max_pages": 1,
                    "overwrite": False,
                },
            )()

            with mock.patch.object(module, "fetch_page", return_value={"data": [updated_recording], "links": {}}), mock.patch("builtins.print") as print_mock:
                module.command_sync(args)

            payload = json.loads(raw_path.read_text(encoding="utf-8"))
            summary = json.loads(print_mock.call_args.args[0])
            self.assertEqual(payload["recording"]["title"], "Updated title")
            self.assertEqual(payload["recording"]["transcript"], "Updated transcript")
            self.assertEqual(summary["written"], 0)
            self.assertEqual(summary["updated"], 1)
            self.assertEqual(summary["skipped"], 0)

    def test_command_sync_uses_checkpoint_range_without_explicit_to(self) -> None:
        module = load_sync_module()
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            output_dir = root / "raw"
            output_dir.mkdir(parents=True, exist_ok=True)
            state_file = root / "sync_state.json"
            state_file.write_text(
                json.dumps({"last_synced_at": "2026-03-11T10:00:00Z", "last_synced_ids": ["vn_100"]}),
                encoding="utf-8",
            )
            args = type(
                "Args",
                (),
                {
                    "state_file": state_file,
                    "output_dir": str(output_dir),
                    "date_from": None,
                    "date_to": None,
                    "no_checkpoint": False,
                    "tags": None,
                    "max_pages": 1,
                    "overwrite": False,
                },
            )()

            with (
                mock.patch.object(module, "iso_now", return_value="2026-03-12T00:00:00Z"),
                mock.patch.object(module, "request_json", return_value={"data": [], "links": {}}) as request_mock,
                mock.patch("builtins.print"),
            ):
                module.command_sync(args)

            self.assertEqual(
                request_mock.call_args.kwargs["body"]["date_range"],
                ["2026-03-11T10:00:00Z", "2026-03-12T00:00:00Z"],
            )

    def test_command_sync_reuses_existing_export_when_created_at_changes(self) -> None:
        module = load_sync_module()
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            output_dir = root / "raw"
            output_dir.mkdir(parents=True, exist_ok=True)
            state_file = root / "sync_state.json"
            previous_recording = {
                "id": "vn_601",
                "title": "Old title",
                "created_at": "2026-03-11T16:00:00.000000Z",
                "recorded_at": "2026-03-11T16:00:00.000000Z",
                "recording_type": 3,
                "duration": 60,
                "tags": ["renovation"],
                "transcript": "Old transcript",
            }
            raw_path = output_dir / module.note_filename(previous_recording)
            raw_path.write_text(json.dumps(module.raw_export_payload(previous_recording), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            updated_recording = {
                **previous_recording,
                "created_at": "2026-03-12T16:00:00.000000Z",
                "recorded_at": "2026-03-12T16:00:00.000000Z",
                "title": "Updated title",
            }
            args = type(
                "Args",
                (),
                {
                    "state_file": state_file,
                    "output_dir": str(output_dir),
                    "date_from": None,
                    "date_to": None,
                    "no_checkpoint": True,
                    "tags": None,
                    "max_pages": 1,
                    "overwrite": False,
                },
            )()

            with mock.patch.object(module, "fetch_page", return_value={"data": [updated_recording], "links": {}}), mock.patch("builtins.print") as print_mock:
                module.command_sync(args)

            payload = json.loads(raw_path.read_text(encoding="utf-8"))
            summary = json.loads(print_mock.call_args.args[0])
            self.assertEqual(sorted(path.name for path in output_dir.glob("*.json")), [raw_path.name])
            self.assertEqual(payload["recording"]["created_at"], "2026-03-12T16:00:00.000000Z")
            self.assertEqual(summary["written"], 0)
            self.assertEqual(summary["updated"], 1)


class BootstrapPrivateRepoTests(unittest.TestCase):
    def test_bootstrap_private_repo_writes_metadata_and_updates_managed_blocks(self) -> None:
        module = load_bootstrap_private_module()
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir(parents=True, exist_ok=True)
            (root / "README.md").write_text(
                "# Demo\n\n<!-- repository-mode:begin -->\nTemplate mode.\n<!-- repository-mode:end -->\n",
                encoding="utf-8",
            )
            (root / "README.pt-PT.md").write_text(
                "# Demo PT\n\n<!-- repository-mode:begin -->\nModo template.\n<!-- repository-mode:end -->\n",
                encoding="utf-8",
            )
            (root / "AGENTS.md").write_text(
                "# AGENTS\n\n<!-- repository-mode:begin -->\n## Repository Mode\n- Current mode: shared starter upstream.\n<!-- repository-mode:end -->\n",
                encoding="utf-8",
            )
            (root / "CLAUDE.md").write_text(
                "# CLAUDE\n\n<!-- repository-mode:begin -->\n## Repository Mode\n\n- Current role: shared starter upstream.\n<!-- repository-mode:end -->\n",
                encoding="utf-8",
            )
            (root / "template.meta.json").write_text(
                json.dumps(
                    {
                        "template_name": "project-router-template",
                        "template_repo": "marioGusmao/project-router-template",
                        "version": "0.1.0",
                    }
                ),
                encoding="utf-8",
            )

            with (
                mock.patch.object(module, "ROOT", root),
                mock.patch.object(module, "README_PATH", root / "README.md"),
                mock.patch.object(module, "README_PT_PATH", root / "README.pt-PT.md"),
                mock.patch.object(module, "AGENTS_PATH", root / "AGENTS.md"),
                mock.patch.object(module, "CLAUDE_PATH", root / "CLAUDE.md"),
                mock.patch.object(module, "TEMPLATE_META_PATH", root / "template.meta.json"),
                mock.patch.object(module, "TEMPLATE_BASE_PATH", root / "template-base.json"),
                mock.patch.object(module, "PRIVATE_META_PATH", root / "private.meta.json"),
                mock.patch.object(module, "iso_now", return_value="2026-03-13T18:30:00Z"),
                mock.patch.object(module, "git_output", return_value="abc123def"),
            ):
                exit_code = module.main(["--private-repo-name", "project-router-private"])

            self.assertEqual(exit_code, 0)
            private_meta = json.loads((root / "private.meta.json").read_text(encoding="utf-8"))
            template_base = json.loads((root / "template-base.json").read_text(encoding="utf-8"))
            self.assertEqual(private_meta["repo_role"], "private-derived")
            self.assertEqual(private_meta["private_repo_name"], "project-router-private")
            self.assertEqual(private_meta["template_repo"], "marioGusmao/project-router-template")
            self.assertEqual(template_base["template_base_tag"], "v0.1.0")
            self.assertEqual(template_base["template_base_commit"], "abc123def")
            self.assertIn("private operational VoiceNotes triage repo", (root / "README.md").read_text(encoding="utf-8"))
            self.assertIn("repositório operacional privado", (root / "README.pt-PT.md").read_text(encoding="utf-8"))
            self.assertIn("Current mode: private derived repository.", (root / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertIn("Current role: private derived repository.", (root / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_bootstrap_private_repo_refuses_template_upstream_without_force(self) -> None:
        module = load_bootstrap_private_module()
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "# Demo\n\n<!-- repository-mode:begin -->\nTemplate mode.\n<!-- repository-mode:end -->\n",
                encoding="utf-8",
            )
            (root / "README.pt-PT.md").write_text(
                "# Demo PT\n\n<!-- repository-mode:begin -->\nModo template.\n<!-- repository-mode:end -->\n",
                encoding="utf-8",
            )
            (root / "AGENTS.md").write_text(
                "# AGENTS\n\n<!-- repository-mode:begin -->\n## Repository Mode\n- Current mode: shared starter upstream.\n<!-- repository-mode:end -->\n",
                encoding="utf-8",
            )
            (root / "CLAUDE.md").write_text(
                "# CLAUDE\n\n<!-- repository-mode:begin -->\n## Repository Mode\n\n- Current role: shared starter upstream.\n<!-- repository-mode:end -->\n",
                encoding="utf-8",
            )
            (root / "template.meta.json").write_text(
                json.dumps(
                    {
                        "template_name": "project-router-template",
                        "template_repo": "marioGusmao/project-router-template",
                        "version": "0.1.0",
                    }
                ),
                encoding="utf-8",
            )

            with (
                mock.patch.object(module, "ROOT", root),
                mock.patch.object(module, "README_PATH", root / "README.md"),
                mock.patch.object(module, "README_PT_PATH", root / "README.pt-PT.md"),
                mock.patch.object(module, "AGENTS_PATH", root / "AGENTS.md"),
                mock.patch.object(module, "CLAUDE_PATH", root / "CLAUDE.md"),
                mock.patch.object(module, "TEMPLATE_META_PATH", root / "template.meta.json"),
                mock.patch.object(module, "TEMPLATE_BASE_PATH", root / "template-base.json"),
                mock.patch.object(module, "PRIVATE_META_PATH", root / "private.meta.json"),
                mock.patch.object(module, "current_origin_repo_slug", return_value="marioGusmao/project-router-template"),
            ):
                with self.assertRaises(SystemExit) as ctx:
                    module.main([])

            self.assertIn("Current origin remote still points to the template upstream", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
