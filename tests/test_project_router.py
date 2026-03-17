from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from src.project_router import cli


TEST_TMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp-tests"
TEST_TMP_ROOT.mkdir(exist_ok=True)


def temporary_repo_dir():
    return tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT)


def prepare_repo(root: Path) -> None:
    for path in (
        root / "data" / "raw" / "voicenotes",
        root / "data" / "raw" / "project_router",
        root / "data" / "raw" / "filesystem" / "default" / "manifests",
        root / "data" / "raw" / "filesystem" / "default" / "artifacts",
        root / "data" / "normalized" / "voicenotes",
        root / "data" / "normalized" / "project_router",
        root / "data" / "normalized" / "filesystem",
        root / "data" / "compiled" / "voicenotes",
        root / "data" / "compiled" / "project_router",
        root / "data" / "compiled" / "filesystem",
        root / "data" / "review" / "voicenotes" / "ambiguous",
        root / "data" / "review" / "voicenotes" / "needs_review",
        root / "data" / "review" / "voicenotes" / "pending_project",
        root / "data" / "review" / "project_router" / "parse_errors",
        root / "data" / "review" / "project_router" / "needs_review",
        root / "data" / "review" / "project_router" / "pending_project",
        root / "data" / "review" / "filesystem" / "parse_errors",
        root / "data" / "review" / "filesystem" / "needs_extraction",
        root / "data" / "review" / "filesystem" / "needs_review",
        root / "data" / "review" / "filesystem" / "ambiguous",
        root / "data" / "review" / "filesystem" / "pending_project",
        root / "data" / "dispatched",
        root / "data" / "processed",
        root / "projects",
        root / "state" / "decisions",
        root / "state" / "discoveries",
        root / "state" / "project_router",
        root / "state" / "project_router" / "adoptions",
        root / "state" / "project_router" / "inbox_status",
        root / "state" / "filesystem_ingest",
        root / "router" / "inbox",
        root / "router" / "outbox",
        root / "router" / "archive",
    ):
        path.mkdir(parents=True, exist_ok=True)


def patch_cli_paths(root: Path) -> ExitStack:
    data = root / "data"
    state = root / "state"
    stack = ExitStack()
    patches = {
        "ROOT": root,
        "DATA_DIR": data,
        "RAW_DIR": data / "raw",
        "NORMALIZED_DIR": data / "normalized",
        "COMPILED_DIR": data / "compiled",
        "REVIEW_DIR": data / "review",
        "AMBIGUOUS_DIR": data / "review" / "voicenotes" / "ambiguous",
        "NEEDS_REVIEW_DIR": data / "review" / "voicenotes" / "needs_review",
        "PENDING_PROJECT_DIR": data / "review" / "voicenotes" / "pending_project",
        "DISPATCHED_DIR": data / "dispatched",
        "PROCESSED_DIR": data / "processed",
        "STATE_DIR": state,
        "DECISIONS_DIR": state / "decisions",
        "DISCOVERIES_DIR": state / "discoveries",
        "PROJECT_ROUTER_STATE_DIR": state / "project_router",
        "OUTBOX_SCAN_STATE_PATH": state / "project_router" / "outbox_scan_state.json",
        "OUTBOX_SCAN_LOCK_PATH": state / "project_router" / "scan.lock",
        "ADOPTIONS_DIR": state / "project_router" / "adoptions",
        "DISCOVERY_REPORT_PATH": state / "discoveries" / "pending_project_latest.json",
        "REGISTRY_LOCAL_PATH": root / "projects" / "registry.local.json",
        "REGISTRY_SHARED_PATH": root / "projects" / "registry.shared.json",
        "REGISTRY_EXAMPLE_PATH": root / "projects" / "registry.example.json",
        "ENV_LOCAL_PATH": root / ".env.local",
        "ENV_PATH": root / ".env",
        "LOCAL_ROUTER_DIR": root / "router",
        "LOCAL_ROUTER_ARCHIVE_DIR": root / "router" / "archive",
        "INBOX_STATUS_DIR": state / "project_router" / "inbox_status",
    }
    for key, value in patches.items():
        stack.enter_context(mock.patch.object(cli, key, value))
    return stack


def write_registry(root: Path, *, include_router_root: bool = True) -> Path:
    shared = {
        "defaults": {"min_keyword_hits": 2},
        "projects": {
            "home_renovation": {
                "display_name": "Home Renovation",
                "language": "en",
                "note_type": "project-idea",
                "keywords": ["renovation", "contractor", "budget"],
            }
        },
    }
    local_project: dict[str, object] = {
        "inbox_path": str(root / "repos" / "home-renovation" / "project-router" / "inbox"),
    }
    if include_router_root:
        local_project["router_root_path"] = str(root / "repos" / "home-renovation" / "project-router")
    (root / "projects" / "registry.shared.json").write_text(json.dumps(shared), encoding="utf-8")
    (root / "projects" / "registry.local.json").write_text(
        json.dumps({"projects": {"home_renovation": local_project}}, indent=2),
        encoding="utf-8",
    )
    return Path(local_project["inbox_path"])


def write_router_contract(router_root: Path, project_key: str = "home_renovation") -> None:
    (router_root / "inbox").mkdir(parents=True, exist_ok=True)
    (router_root / "outbox").mkdir(parents=True, exist_ok=True)
    (router_root / "conformance").mkdir(parents=True, exist_ok=True)
    (router_root / "router-contract.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "project_key": project_key,
                "default_language": "en",
                "supported_packet_types": ["insight", "question", "proposal"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (router_root / "conformance" / "valid-packet.example.md").write_text(
        "---\n"
        'schema_version: "1"\n'
        'packet_id: "sample_valid"\n'
        'created_at: "2026-03-13T10:00:00Z"\n'
        'source_project: "home_renovation"\n'
        'packet_type: "proposal"\n'
        'title: "Valid sample"\n'
        'language: "en"\n'
        'status: "open"\n'
        "---\n\n# Valid sample\n\nBody\n",
        encoding="utf-8",
    )
    (router_root / "conformance" / "invalid-packet.example.md").write_text(
        "---\n"
        'schema_version: "1"\n'
        'packet_id: "sample_invalid"\n'
        "---\n\nBroken\n",
        encoding="utf-8",
    )


def write_outbox_packet(router_root: Path, packet_id: str, body: str, *, title: str = "Packet", project_key: str = "home_renovation") -> Path:
    packet_path = router_root / "outbox" / f"20260313T100000Z--{packet_id}.md"
    packet_path.write_text(
        "---\n"
        'schema_version: "1"\n'
        f'packet_id: "{packet_id}"\n'
        'created_at: "2026-03-13T10:00:00Z"\n'
        f'source_project: "{project_key}"\n'
        'packet_type: "proposal"\n'
        f'title: "{title}"\n'
        'language: "en"\n'
        'status: "open"\n'
        "---\n\n"
        + body
        + "\n",
        encoding="utf-8",
    )
    return packet_path


def parse_print_json(print_mock: mock.Mock):
    args = print_mock.call_args[0]
    if len(args) != 1:
        raise AssertionError(f"Expected one print arg, got: {args}")
    return json.loads(args[0])


class ProjectRouterFlowTests(unittest.TestCase):
    def test_normalize_voicenotes_raw_uses_source_aware_dir(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            raw_path = root / "data" / "raw" / "voicenotes" / "20260311T160000Z--vn_123.json"
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
                cli.normalize_command(type("Args", (), {"source": "voicenotes"})())
            normalized = root / "data" / "normalized" / "voicenotes" / "20260311T160000Z--vn_123.md"
            metadata, body = cli.read_note(normalized)
            self.assertEqual(metadata["source"], "voicenotes")
            # raw_payload_path is now project-relative
            self.assertIn("data/raw/voicenotes/20260311T160000Z--vn_123.json", metadata["raw_payload_path"])
            self.assertIn("Hello\nworld", body)

    def test_triage_routes_unmatched_voicenote_to_pending_project_queue(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            note_path = root / "data" / "normalized" / "voicenotes" / "20260311T160000Z--vn_999.md"
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
                "# Future bucket\n\nNo matching keywords.\n",
            )
            with patch_cli_paths(root):
                cli.triage_command(type("Args", (), {"all": False, "source": "voicenotes"})())
            metadata, _ = cli.read_note(note_path)
            self.assertEqual(metadata["status"], "pending_project")
            self.assertTrue((root / "data" / "review" / "voicenotes" / "pending_project" / note_path.name).exists())

    def test_dispatch_derives_inbox_from_router_root_path(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            inbox_path = write_registry(root)
            note_path = root / "data" / "normalized" / "voicenotes" / "20260311T160000Z--vn_126.md"
            compiled_path = root / "data" / "compiled" / "voicenotes" / "20260311T160000Z--vn_126.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_126",
                    "title": "Renovation idea",
                    "created_at": "2026-03-11T16:00:00Z",
                    "tags": ["renovation", "contractor"],
                    "status": "classified",
                    "project": "home_renovation",
                    "candidate_projects": ["home_renovation"],
                    "confidence": 1.0,
                    "routing_reason": "Matched keywords.",
                    "requires_user_confirmation": False,
                    "review_status": "approved",
                    "canonical_path": str(note_path),
                    "raw_payload_path": str(root / "data" / "raw" / "voicenotes" / "20260311T160000Z--vn_126.json"),
                    "note_type": "project-idea",
                },
                "# Renovation idea\n\nNeed contractor quotes.\n",
            )
            compiled_path.parent.mkdir(parents=True, exist_ok=True)
            compiled_metadata = {
                "source": "voicenotes",
                "source_note_id": "vn_126",
                "title": "Renovation idea",
                "created_at": "2026-03-11T16:00:00Z",
                "compiled_at": "2026-03-11T16:05:00Z",
                "compiled_from_signature": cli.canonical_compile_signature(
                    cli.read_note(note_path)[0],
                    cli.read_note(note_path)[1],
                ),
                "brief_summary": "Summary",
            }
            cli.write_note(compiled_path, compiled_metadata, "# Renovation idea\n\nCompiled\n")
            with patch_cli_paths(root):
                cli.dispatch_command(
                    type(
                        "Args",
                        (),
                        {"dry_run": False, "confirm_user_approval": True, "note_ids": ["vn_126"], "source": "voicenotes"},
                    )()
                )
            self.assertTrue((inbox_path / "20260311T160000Z--vn_126.md").exists())

    def test_scan_outboxes_ingests_valid_packet_read_only(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            router_root = root / "repos" / "home-renovation" / "project-router"
            write_router_contract(router_root)
            packet_path = write_outbox_packet(router_root, "pkt_001", "# Improvement\n\nNeed better tags.\n", title="Improvement")
            original = packet_path.read_text(encoding="utf-8")
            with patch_cli_paths(root):
                cli.scan_outboxes_command(type("Args", (), {"include_self": False, "strict": False})())
            self.assertEqual(packet_path.read_text(encoding="utf-8"), original)
            raw_path = root / "data" / "raw" / "project_router" / "home_renovation" / "20260313T100000Z--pkt_001.json"
            self.assertTrue(raw_path.exists())
            state = json.loads((root / "state" / "project_router" / "outbox_scan_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["scanned_packets"]["home_renovation"]["pkt_001"]["status"], "ingested")

    def test_scan_outboxes_tracks_unchanged_then_content_changed(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            router_root = root / "repos" / "home-renovation" / "project-router"
            write_router_contract(router_root)
            packet_path = write_outbox_packet(router_root, "pkt_002", "# Improvement\n\nOriginal body.\n")
            with patch_cli_paths(root):
                cli.scan_outboxes_command(type("Args", (), {"include_self": False, "strict": False})())
                cli.scan_outboxes_command(type("Args", (), {"include_self": False, "strict": False})())
            state = json.loads((root / "state" / "project_router" / "outbox_scan_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["scanned_packets"]["home_renovation"]["pkt_002"]["status"], "unchanged")
            packet_path.write_text(packet_path.read_text(encoding="utf-8").replace("Original body.", "Updated body."), encoding="utf-8")
            with patch_cli_paths(root):
                cli.scan_outboxes_command(type("Args", (), {"include_self": False, "strict": False})())
            state = json.loads((root / "state" / "project_router" / "outbox_scan_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["scanned_packets"]["home_renovation"]["pkt_002"]["status"], "content_changed")

    def test_scan_outboxes_invalid_packet_creates_parse_error(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            router_root = root / "repos" / "home-renovation" / "project-router"
            write_router_contract(router_root)
            invalid_packet = router_root / "outbox" / "20260313T100000Z--pkt_bad.md"
            invalid_packet.write_text(
                "---\n"
                'schema_version: "1"\n'
                'packet_id: "pkt_bad"\n'
                'created_at: "2026-03-13T10:00:00Z"\n'
                'source_project: "home_renovation"\n'
                'packet_type: "proposal"\n'
                'language: "en"\n'
                'status: "open"\n'
                "---\n\nBroken body\n",
                encoding="utf-8",
            )
            with patch_cli_paths(root):
                cli.scan_outboxes_command(type("Args", (), {"include_self": False, "strict": False})())
            error_dir = root / "data" / "review" / "project_router" / "parse_errors"
            self.assertEqual(len(list(error_dir.glob("*.md"))), 1)
            state = json.loads((root / "state" / "project_router" / "outbox_scan_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["scanned_packets"]["home_renovation"]["pkt_bad"]["status"], "invalid")

    def test_normalize_project_router_raw_maps_packet_id_to_source_note_id(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            raw_path = root / "data" / "raw" / "project_router" / "home_renovation" / "20260313T100000Z--pkt_003.json"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(
                json.dumps(
                    {
                        "source": "project_router",
                        "source_project": "home_renovation",
                        "source_endpoint": "outbox",
                        "content_hash": "sha256:test",
                        "packet": {
                            "packet_id": "pkt_003",
                            "created_at": "2026-03-13T10:00:00Z",
                            "source_project": "home_renovation",
                            "packet_type": "proposal",
                            "title": "Router packet",
                            "language": "en",
                            "status": "open",
                        },
                        "body": "# Router packet\n\nBody\n",
                    }
                ),
                encoding="utf-8",
            )
            with patch_cli_paths(root):
                cli.normalize_command(type("Args", (), {"source": "project_router"})())
            note_path = root / "data" / "normalized" / "project_router" / "home_renovation" / "20260313T100000Z--pkt_003.md"
            metadata, _ = cli.read_note(note_path)
            self.assertEqual(metadata["source"], "project_router")
            self.assertEqual(metadata["source_project"], "home_renovation")
            self.assertEqual(metadata["source_note_id"], "pkt_003")

    def test_doctor_validates_local_router_root(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            router_root = root / "project-router"
            write_router_contract(router_root)
            write_outbox_packet(router_root, "pkt_doctor", "# Doctor\n\nBody\n")
            with patch_cli_paths(root), mock.patch("builtins.print") as print_mock:
                exit_code = cli.doctor_command(type("Args", (), {"router_root": str(router_root), "project": None, "packet": None, "strict": False})())
            payload = parse_print_json(print_mock)
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "ok")

    def test_doctor_rejects_invalid_packet(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            router_root = root / "project-router"
            write_router_contract(router_root)
            invalid_packet = router_root / "outbox" / "bad.md"
            invalid_packet.write_text("---\npacket_id: \"bad\"\n---\n\nBroken\n", encoding="utf-8")
            with patch_cli_paths(root), mock.patch("builtins.print") as print_mock:
                exit_code = cli.doctor_command(type("Args", (), {"router_root": str(router_root), "project": None, "packet": None, "strict": False})())
            payload = parse_print_json(print_mock)
            self.assertEqual(exit_code, 1)
            self.assertEqual(payload["status"], "error")

    def test_review_filters_by_source(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                voice_path = root / "data" / "normalized" / "voicenotes" / "20260311T160000Z--vn_a.md"
                voice_metadata = {
                    "source": "voicenotes",
                    "source_note_id": "vn_a",
                    "title": "Voice",
                    "created_at": "2026-03-11T16:00:00Z",
                    "status": "pending_project",
                    "review_status": "pending",
                    "canonical_path": str(voice_path),
                }
                cli.write_note(voice_path, voice_metadata, "# Voice\n\nBody\n")
                cli.save_decision_packet_for_metadata(
                    voice_metadata,
                    {"source": "voicenotes", "source_note_id": "vn_a", "canonical_path": str(voice_path), "proposal": {"status": "pending_project", "review_status": "pending"}},
                )

                project_path = root / "data" / "normalized" / "project_router" / "home_renovation" / "20260313T100000Z--pkt_a.md"
                project_path.parent.mkdir(parents=True, exist_ok=True)
                project_metadata = {
                    "source": "project_router",
                    "source_project": "home_renovation",
                    "source_note_id": "pkt_a",
                    "title": "Packet",
                    "created_at": "2026-03-13T10:00:00Z",
                    "status": "pending_project",
                    "review_status": "pending",
                    "canonical_path": str(project_path),
                }
                cli.write_note(project_path, project_metadata, "# Packet\n\nBody\n")
                cli.save_decision_packet_for_metadata(
                    project_metadata,
                    {
                        "source": "project_router",
                        "source_project": "home_renovation",
                        "source_note_id": "pkt_a",
                        "canonical_path": str(project_path),
                        "proposal": {"status": "pending_project", "review_status": "pending"},
                    },
                )

            with patch_cli_paths(root), mock.patch("builtins.print") as print_mock:
                cli.review_command(type("Args", (), {"all": True, "note_id": None, "source": "project_router"})())
            payload = parse_print_json(print_mock)
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["source_note_id"], "pkt_a")

    def test_status_splits_counts_by_source(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            (root / "data" / "raw" / "voicenotes" / "a.json").write_text("{}", encoding="utf-8")
            (root / "data" / "raw" / "project_router" / "home_renovation").mkdir(parents=True, exist_ok=True)
            (root / "data" / "raw" / "project_router" / "home_renovation" / "b.json").write_text("{}", encoding="utf-8")
            with patch_cli_paths(root), mock.patch("builtins.print") as print_mock:
                cli.status_command(type("Args", (), {"source": "all"})())
            payload = parse_print_json(print_mock)
            self.assertEqual(payload["raw"]["voicenotes"], 1)
            self.assertEqual(payload["raw"]["project_router"], 1)

    def test_migrate_source_layout_moves_legacy_voicenotes_files(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            legacy_raw = root / "data" / "raw" / "20260311T160000Z--vn_legacy.json"
            legacy_raw.write_text("{}", encoding="utf-8")
            legacy_normalized = root / "data" / "normalized" / "20260311T160000Z--vn_legacy.md"
            cli.write_note(
                legacy_normalized,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_legacy",
                    "title": "Legacy",
                    "created_at": "2026-03-11T16:00:00Z",
                    "canonical_path": str(legacy_normalized),
                    "raw_payload_path": str(legacy_raw),
                },
                "# Legacy\n\nBody\n",
            )
            with patch_cli_paths(root):
                cli.migrate_source_layout_command(type("Args", (), {"dry_run": False, "confirm": True})())
            self.assertTrue((root / "data" / "raw" / "voicenotes" / legacy_raw.name).exists())
            migrated_note = root / "data" / "normalized" / "voicenotes" / legacy_normalized.name
            self.assertTrue(migrated_note.exists())
            metadata, _ = cli.read_note(migrated_note)
            self.assertEqual(metadata["raw_payload_path"], str(root / "data" / "raw" / "voicenotes" / legacy_raw.name))

    def test_scan_outboxes_include_self_ingests_local_router_packets(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            (root / "projects" / "registry.shared.json").write_text(json.dumps({"defaults": {}, "projects": {}}), encoding="utf-8")
            (root / "projects" / "registry.local.json").write_text(json.dumps({"projects": {}}), encoding="utf-8")
            router_root = root / "router"
            write_router_contract(router_root, project_key="project_router_template")
            write_outbox_packet(router_root, "self_pkt", "# Self\n\nBody\n", project_key="project_router_template")
            with patch_cli_paths(root):
                cli.scan_outboxes_command(type("Args", (), {"include_self": True, "strict": False})())
            raw_path = root / "data" / "raw" / "project_router" / "project_router_template" / "20260313T100000Z--self_pkt.json"
            self.assertTrue(raw_path.exists())

    def test_scan_outboxes_skips_projects_without_router_contract(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            shared = {
                "defaults": {"min_keyword_hits": 2},
                "projects": {
                    "home_renovation": {
                        "display_name": "Home Renovation",
                        "language": "en",
                        "note_type": "project-idea",
                        "keywords": ["renovation"],
                    }
                },
            }
            (root / "projects" / "registry.shared.json").write_text(json.dumps(shared), encoding="utf-8")
            router_root = root / "repos" / "home-renovation" / "project-router"
            router_root.mkdir(parents=True, exist_ok=True)
            (root / "projects" / "registry.local.json").write_text(
                json.dumps({"projects": {"home_renovation": {"router_root_path": str(router_root)}}}, indent=2),
                encoding="utf-8",
            )

            with patch_cli_paths(root), mock.patch("builtins.print") as print_mock:
                cli.scan_outboxes_command(type("Args", (), {"include_self": False, "strict": False})())

            payload = parse_print_json(print_mock)
            self.assertEqual(payload["invalid"], 1)
            self.assertEqual(payload["packets"][0]["status"], "invalid")
            self.assertIn("Missing project-router contract", payload["packets"][0]["errors"][0])
            parse_errors = list((root / "data" / "review" / "project_router" / "parse_errors").glob("*home-renovation--router-contract.md"))
            self.assertEqual(len(parse_errors), 1)


REPO_ROOT = Path(__file__).resolve().parents[1]


class KnowledgeGovernanceTests(unittest.TestCase):
    def test_knowledge_ownership_classification(self) -> None:
        script = str(REPO_ROOT / "scripts" / "check_repo_ownership.py")
        cases = [
            ("Knowledge/local", 1),
            ("Knowledge/local/README.md", 1),
            ("Knowledge/local/ADR/100-custom.md", 1),
            ("Knowledge/TLDR.md", 0),
            ("Knowledge/ADR/001-stdlib-only.md", 0),
            ("Knowledge/Templates/local/README.md", 0),
        ]
        for path, expected_exit in cases:
            result = subprocess.run(
                ["python3", script, "--mode", "template-sync", "--path", path],
                capture_output=True, text=True,
            )
            self.assertEqual(
                result.returncode, expected_exit,
                f"Expected exit {expected_exit} for {path}, got {result.returncode}: {result.stderr}",
            )

    def test_knowledge_local_not_in_sync_paths(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "template-upstream-sync.yml").read_text(encoding="utf-8")
        in_paths = False
        for line in workflow.splitlines():
            stripped = line.strip()
            if stripped.startswith("paths=("):
                in_paths = True
                continue
            if in_paths and stripped == ")":
                break
            if in_paths and not stripped.startswith("#"):
                self.assertNotIn("Knowledge/local", stripped, "Knowledge/local must not appear in sync paths")

    def test_bootstrap_seeds_knowledge_local(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            # Copy the bootstrap script so ROOT resolves to the temp dir
            scripts_dir = root / "scripts"
            scripts_dir.mkdir()
            shutil.copy2(REPO_ROOT / "scripts" / "bootstrap_private_repo.py", scripts_dir / "bootstrap_private_repo.py")
            shutil.copy2(REPO_ROOT / "scripts" / "knowledge_local_scaffold.py", scripts_dir / "knowledge_local_scaffold.py")
            shutil.copytree(REPO_ROOT / "Knowledge" / "Templates", root / "Knowledge" / "Templates")
            # Create minimal required files for bootstrap
            (root / "template.meta.json").write_text(
                json.dumps({"version": "0.2.0", "template_name": "project-router-template", "template_repo": "test/repo"}),
                encoding="utf-8",
            )
            (root / "README.md").write_text(
                "<!-- repository-mode:begin -->\nTemplate mode.\n<!-- repository-mode:end -->\n\n"
                "<!-- template-onboarding:begin -->\nTemplate onboarding.\n<!-- template-onboarding:end -->\n",
                encoding="utf-8",
            )
            (root / "README.pt-PT.md").write_text(
                "<!-- repository-mode:begin -->\nModo template.\n<!-- repository-mode:end -->\n\n"
                "<!-- template-onboarding:begin -->\nOnboarding template.\n<!-- template-onboarding:end -->\n",
                encoding="utf-8",
            )
            for doc_name in ("AGENTS.md", "CLAUDE.md"):
                (root / doc_name).write_text(
                    "<!-- repository-mode:begin -->\nTemplate mode.\n<!-- repository-mode:end -->\n\n"
                    "<!-- customization-contract:begin -->\nContract placeholder.\n<!-- customization-contract:end -->\n",
                    encoding="utf-8",
                )
            result = subprocess.run(
                ["python3", str(scripts_dir / "bootstrap_private_repo.py"), "--force"],
                capture_output=True, text=True, cwd=str(root),
            )
            self.assertEqual(result.returncode, 0, f"Bootstrap failed: {result.stderr}")
            for rel in (
                "Knowledge/local/README.md",
                "Knowledge/local/Roadmap.md",
                "Knowledge/local/ADR/README.md",
                "Knowledge/local/notes/README.md",
                "Knowledge/local/TLDR/README.md",
                "Knowledge/local/AI/README.md",
                "Knowledge/local/AI/claude.md",
                "Knowledge/local/AI/codex.md",
            ):
                self.assertTrue((root / rel).exists(), f"Missing seeded scaffold file: {rel}")
            for rel in (
                "README.md",
                "README.pt-PT.md",
            ):
                text = (root / rel).read_text(encoding="utf-8")
                self.assertIn("bootstrap_local.py", text)
                self.assertIn("Knowledge/local/Roadmap.md", text)
                self.assertNotIn("Template onboarding.", text)
            for rel in (
                "README.md",
                "Roadmap.md",
                "ADR/README.md",
                "notes/README.md",
                "TLDR/README.md",
                "AI/README.md",
                "AI/claude.md",
                "AI/codex.md",
            ):
                source = (REPO_ROOT / "Knowledge" / "Templates" / "local" / rel).read_bytes()
                target = (root / "Knowledge" / "local" / rel).read_bytes()
                self.assertEqual(target, source, f"Seeded scaffold drifted from template source for {rel}")
            # Verify idempotent: re-run should not overwrite
            mtime_readme = (root / "Knowledge" / "local" / "README.md").stat().st_mtime
            mtime_roadmap = (root / "Knowledge" / "local" / "Roadmap.md").stat().st_mtime
            result2 = subprocess.run(
                ["python3", str(scripts_dir / "bootstrap_private_repo.py"), "--force"],
                capture_output=True, text=True, cwd=str(root),
            )
            self.assertEqual(result2.returncode, 0)
            self.assertEqual((root / "Knowledge" / "local" / "README.md").stat().st_mtime, mtime_readme)
            self.assertEqual((root / "Knowledge" / "local" / "Roadmap.md").stat().st_mtime, mtime_roadmap)

    def test_refresh_knowledge_local_preview_and_apply_missing(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            scripts_dir = root / "scripts"
            scripts_dir.mkdir()
            shutil.copy2(REPO_ROOT / "scripts" / "knowledge_local_scaffold.py", scripts_dir / "knowledge_local_scaffold.py")
            shutil.copy2(REPO_ROOT / "scripts" / "refresh_knowledge_local.py", scripts_dir / "refresh_knowledge_local.py")
            shutil.copytree(REPO_ROOT / "Knowledge" / "Templates", root / "Knowledge" / "Templates")

            local_root = root / "Knowledge" / "local"
            (local_root / "README.md").parent.mkdir(parents=True, exist_ok=True)
            (local_root / "README.md").write_text("# Customized local README\n", encoding="utf-8")

            preview = subprocess.run(
                ["python3", str(scripts_dir / "refresh_knowledge_local.py")],
                capture_output=True, text=True, cwd=str(root),
            )
            self.assertEqual(preview.returncode, 0, f"Refresh preview failed: {preview.stderr}")
            preview_payload = json.loads(preview.stdout)
            self.assertTrue(preview_payload["dry_run"])
            self.assertIn("README.md", preview_payload["different"])
            self.assertIn("Roadmap.md", preview_payload["missing"])
            self.assertIn("ADR/README.md", preview_payload["missing"])
            self.assertIn("notes/README.md", preview_payload["missing"])
            self.assertIn("TLDR/README.md", preview_payload["missing"])

            apply_missing = subprocess.run(
                ["python3", str(scripts_dir / "refresh_knowledge_local.py"), "--apply-missing"],
                capture_output=True, text=True, cwd=str(root),
            )
            self.assertEqual(apply_missing.returncode, 0, f"Refresh apply-missing failed: {apply_missing.stderr}")
            apply_payload = json.loads(apply_missing.stdout)
            self.assertFalse(apply_payload["dry_run"])
            self.assertEqual((local_root / "README.md").read_text(encoding="utf-8"), "# Customized local README\n")
            self.assertTrue((local_root / "Roadmap.md").exists())
            self.assertTrue((local_root / "ADR" / "README.md").exists())
            self.assertTrue((local_root / "notes" / "README.md").exists())
            self.assertTrue((local_root / "TLDR" / "README.md").exists())

    def test_knowledge_structure_validator(self) -> None:
        result = subprocess.run(
            ["python3", str(REPO_ROOT / "scripts" / "check_knowledge_structure.py"), "--strict"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, f"Validator failed: {result.stderr}")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")

    def test_rsync_directory_fix_in_sync_workflow(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "template-upstream-sync.yml").read_text(encoding="utf-8")
        self.assertIn('[ -d "$upstream/$path" ]', workflow, "rsync block must detect directories")
        self.assertIn('"$upstream/$path/"', workflow, "rsync must use trailing slash for directory source")
        self.assertIn('"$path/"', workflow, "rsync must use trailing slash for directory destination")

    def test_context_subcommand(self) -> None:
        result = subprocess.run(
            ["python3", str(REPO_ROOT / "scripts" / "project_router.py"), "context"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, f"Context command failed: {result.stderr}")
        output = result.stdout
        self.assertTrue(output.startswith("# "), "Context output must start with a Markdown heading")
        self.assertIn("Registered Projects", output)
        self.assertIn("Available Scripts", output)

    def test_context_help_no_longer_exposes_write_flag(self) -> None:
        top_help = subprocess.run(
            ["python3", str(REPO_ROOT / "scripts" / "project_router.py"), "--help"],
            capture_output=True, text=True,
        )
        self.assertEqual(top_help.returncode, 0)
        self.assertNotIn("--write", top_help.stdout)

        context_help = subprocess.run(
            ["python3", str(REPO_ROOT / "scripts" / "project_router.py"), "context", "--help"],
            capture_output=True, text=True,
        )
        self.assertEqual(context_help.returncode, 0)
        self.assertNotIn("--write", context_help.stdout)

    def test_context_does_not_modify_context_pack(self) -> None:
        context_pack = REPO_ROOT / "Knowledge" / "ContextPack.md"
        before = context_pack.read_bytes()
        result = subprocess.run(
            ["python3", str(REPO_ROOT / "scripts" / "project_router.py"), "context"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, f"Context command failed: {result.stderr}")
        self.assertEqual(context_pack.read_bytes(), before)

    def test_strict_validator_fails_when_curated_file_missing(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "repo-governance").mkdir()
            shutil.copy2(REPO_ROOT / "scripts" / "check_knowledge_structure.py", root / "scripts" / "check_knowledge_structure.py")
            shutil.copy2(REPO_ROOT / "repo-governance" / "ownership.manifest.json", root / "repo-governance" / "ownership.manifest.json")
            shutil.copytree(REPO_ROOT / "Knowledge", root / "Knowledge")
            (root / "Knowledge" / "ADR" / "005-safety-invariants.md").unlink()

            result = subprocess.run(
                ["python3", str(root / "scripts" / "check_knowledge_structure.py"), "--strict"],
                capture_output=True, text=True, cwd=str(root),
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("005-safety-invariants.md", result.stderr)

    def test_strict_validator_requires_repo_native_plan_file(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "repo-governance").mkdir()
            shutil.copy2(REPO_ROOT / "scripts" / "check_knowledge_structure.py", root / "scripts" / "check_knowledge_structure.py")
            shutil.copy2(REPO_ROOT / "repo-governance" / "ownership.manifest.json", root / "repo-governance" / "ownership.manifest.json")
            shutil.copytree(REPO_ROOT / "Knowledge", root / "Knowledge")
            (root / "Knowledge" / "runbooks" / "plans" / "router-root-migration-and-scaffold.plan.md").unlink()

            result = subprocess.run(
                ["python3", str(root / "scripts" / "check_knowledge_structure.py"), "--strict"],
                capture_output=True, text=True, cwd=str(root),
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("Knowledge/runbooks/plans/router-root-migration-and-scaffold.plan.md", result.stderr)

    def test_strict_validator_fails_when_template_scaffold_source_missing(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "repo-governance").mkdir()
            shutil.copy2(REPO_ROOT / "scripts" / "check_knowledge_structure.py", root / "scripts" / "check_knowledge_structure.py")
            shutil.copy2(REPO_ROOT / "repo-governance" / "ownership.manifest.json", root / "repo-governance" / "ownership.manifest.json")
            shutil.copytree(REPO_ROOT / "Knowledge", root / "Knowledge")
            (root / "Knowledge" / "Templates" / "local" / "README.md").unlink()

            result = subprocess.run(
                ["python3", str(root / "scripts" / "check_knowledge_structure.py"), "--strict"],
                capture_output=True, text=True, cwd=str(root),
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("Knowledge/Templates/local/README.md", result.stderr)

    def test_strict_validator_requires_materialized_local_scaffold_for_private_repo(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "repo-governance").mkdir()
            shutil.copy2(REPO_ROOT / "scripts" / "check_knowledge_structure.py", root / "scripts" / "check_knowledge_structure.py")
            shutil.copy2(REPO_ROOT / "repo-governance" / "ownership.manifest.json", root / "repo-governance" / "ownership.manifest.json")
            shutil.copytree(REPO_ROOT / "Knowledge", root / "Knowledge")
            shutil.rmtree(root / "Knowledge" / "local")
            (root / "private.meta.json").write_text(json.dumps({"repo_role": "private-derived"}), encoding="utf-8")
            (root / "template-base.json").write_text(json.dumps({"template_repo": "test/repo"}), encoding="utf-8")

            result = subprocess.run(
                ["python3", str(root / "scripts" / "check_knowledge_structure.py"), "--strict"],
                capture_output=True, text=True, cwd=str(root),
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("Knowledge/local/README.md", result.stderr)
            self.assertIn("Knowledge/local/TLDR/README.md", result.stderr)

    def test_strict_validator_requires_private_metadata_when_repo_declares_private_mode(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "repo-governance").mkdir()
            shutil.copy2(REPO_ROOT / "scripts" / "check_knowledge_structure.py", root / "scripts" / "check_knowledge_structure.py")
            shutil.copy2(REPO_ROOT / "repo-governance" / "ownership.manifest.json", root / "repo-governance" / "ownership.manifest.json")
            shutil.copytree(REPO_ROOT / "Knowledge", root / "Knowledge")
            (root / "README.md").write_text(
                "This repository is a private operational Project Router repo for VoiceNotes.\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["python3", str(root / "scripts" / "check_knowledge_structure.py"), "--strict"],
                capture_output=True, text=True, cwd=str(root),
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("Private-derived metadata missing: private.meta.json", result.stderr)
            self.assertIn("Private-derived metadata missing: template-base.json", result.stderr)

    def test_sync_manifest_alignment_validator(self) -> None:
        result = subprocess.run(
            ["python3", str(REPO_ROOT / "scripts" / "check_sync_manifest_alignment.py")],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, f"Sync alignment validator failed: {result.stderr}")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertIn("Knowledge/Templates", payload["sync_paths"])

    def test_sync_manifest_alignment_rejects_blocked_path(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            (root / "scripts").mkdir()
            (root / "repo-governance").mkdir(parents=True)
            (root / ".github" / "workflows").mkdir(parents=True)
            shutil.copy2(REPO_ROOT / "scripts" / "check_repo_ownership.py", root / "scripts" / "check_repo_ownership.py")
            shutil.copy2(REPO_ROOT / "scripts" / "check_sync_manifest_alignment.py", root / "scripts" / "check_sync_manifest_alignment.py")
            shutil.copy2(REPO_ROOT / "repo-governance" / "ownership.manifest.json", root / "repo-governance" / "ownership.manifest.json")
            shutil.copy2(REPO_ROOT / "repo-governance" / "customization-contracts.json", root / "repo-governance" / "customization-contracts.json")
            (root / ".github" / "workflows" / "template-upstream-sync.yml").write_text(
                "paths=(\n"
                "  Knowledge/README.md\n"
                "  Knowledge/local\n"
                ")\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["python3", str(root / "scripts" / "check_sync_manifest_alignment.py")],
                capture_output=True, text=True, cwd=str(root),
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("Knowledge/local", result.stderr)


class TestCheckAdrRelatedLinks(unittest.TestCase):
    """Tests for scripts/check_adr_related_links.py."""

    SCRIPT = str(REPO_ROOT / "scripts" / "check_adr_related_links.py")

    def _make_adr_tree(self, root: Path, adrs: dict[str, str]) -> None:
        """Create ADR files in root/Knowledge/ADR/ from a {filename: content} dict."""
        adr_dir = root / "Knowledge" / "ADR"
        adr_dir.mkdir(parents=True, exist_ok=True)
        for name, content in adrs.items():
            (adr_dir / name).write_text(content, encoding="utf-8")

    def _make_local_adr_tree(self, root: Path, adrs: dict[str, str]) -> None:
        """Create ADR files in root/Knowledge/local/ADR/."""
        adr_dir = root / "Knowledge" / "local" / "ADR"
        adr_dir.mkdir(parents=True, exist_ok=True)
        for name, content in adrs.items():
            (adr_dir / name).write_text(content, encoding="utf-8")

    def _setup_script(self, root: Path) -> None:
        """Copy the validator script into the temp repo."""
        scripts_dir = root / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        shutil.copy2(REPO_ROOT / "scripts" / "check_adr_related_links.py", scripts_dir / "check_adr_related_links.py")

    def _run(self, root: Path, mode: str = "warn") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(root / "scripts" / "check_adr_related_links.py"), "--mode", mode],
            capture_output=True, text=True, cwd=str(root),
        )

    def test_valid_template_to_template_ref(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            self._setup_script(root)
            self._make_adr_tree(root, {
                "001-first.md": "# ADR-001\n\n## Related\n\n- ADR-002: Second\n",
                "002-second.md": "# ADR-002\n\n## Related\n\n- ADR-001: First\n",
            })
            result = self._run(root, "block")
            self.assertEqual(result.returncode, 0, f"Unexpected failure: {result.stderr}")

    def test_valid_template_to_local_ref(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            self._setup_script(root)
            self._make_adr_tree(root, {
                "001-first.md": "# ADR-001\n\n## Related\n\n- ADR-100: Local decision\n",
            })
            self._make_local_adr_tree(root, {
                "100-local.md": "# ADR-100\n\n## Related\n\n- ADR-001: First\n",
            })
            result = self._run(root, "block")
            self.assertEqual(result.returncode, 0, f"Unexpected failure: {result.stderr}")

    def test_valid_local_to_template_ref(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            self._setup_script(root)
            self._make_adr_tree(root, {
                "001-first.md": "# ADR-001\n",
            })
            self._make_local_adr_tree(root, {
                "100-local.md": "# ADR-100\n\n## Related\n\n- ADR-001: First\n",
            })
            result = self._run(root, "block")
            self.assertEqual(result.returncode, 0, f"Unexpected failure: {result.stderr}")

    def test_missing_target_errors(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            self._setup_script(root)
            self._make_adr_tree(root, {
                "001-first.md": "# ADR-001\n\n## Related\n\n- ADR-999: Does not exist\n",
            })
            result = self._run(root, "block")
            self.assertEqual(result.returncode, 1)
            self.assertIn("nonexistent target ADR-999", result.stderr)

    def test_missing_target_warn_mode_exits_zero(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            self._setup_script(root)
            self._make_adr_tree(root, {
                "001-first.md": "# ADR-001\n\n## Related\n\n- ADR-999: Does not exist\n",
            })
            result = self._run(root, "warn")
            self.assertEqual(result.returncode, 0)
            self.assertIn("nonexistent target ADR-999", result.stderr)

    def test_self_reference_errors(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            self._setup_script(root)
            self._make_adr_tree(root, {
                "001-first.md": "# ADR-001\n\n## Related\n\n- ADR-001: Self\n",
            })
            result = self._run(root, "block")
            self.assertEqual(result.returncode, 1)
            self.assertIn("self-reference ADR-001", result.stderr)

    def test_no_related_section_is_fine(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            self._setup_script(root)
            self._make_adr_tree(root, {
                "001-first.md": "# ADR-001\n\n## Context\n\nSome context.\n",
            })
            result = self._run(root, "block")
            self.assertEqual(result.returncode, 0, f"Unexpected failure: {result.stderr}")

    def test_malformed_reference_warns(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            self._setup_script(root)
            self._make_adr_tree(root, {
                "001-first.md": "# ADR-001\n\n## Related\n\n- Adr 2: Bad format\n",
            })
            result = self._run(root, "block")
            self.assertEqual(result.returncode, 0)
            self.assertIn("WARNING", result.stderr)
            self.assertIn("malformed", result.stderr)

    def test_mixed_valid_and_malformed_reference_still_warns(self) -> None:
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            self._setup_script(root)
            self._make_adr_tree(root, {
                "001-first.md": "# ADR-001\n\n## Related\n\n- ADR-002: Good and Adr 3: Bad\n",
                "002-second.md": "# ADR-002\n",
            })
            result = self._run(root, "block")
            self.assertEqual(result.returncode, 0, f"Unexpected failure: {result.stderr}")
            self.assertIn("WARNING", result.stderr)
            self.assertIn("malformed ADR reference 'Adr 3'", result.stderr)

    def test_real_repo_passes(self) -> None:
        """The actual repo's ADRs should pass in block mode."""
        result = subprocess.run(
            ["python3", self.SCRIPT, "--mode", "block"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, f"Real repo failed: {result.stderr}")


class PR1FixTests(unittest.TestCase):
    """Tests covering PR 1 confirmed-defect fixes."""

    def test_review_all_with_missing_canonical(self) -> None:
        """review --all must not crash when decision packets have empty metadata."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            # Create a note and triage it so we have a valid decision packet
            note_path = root / "data" / "normalized" / "voicenotes" / "20260311T160000Z--vn_good.md"
            cli.write_note(
                note_path,
                {
                    "source": "voicenotes",
                    "source_note_id": "vn_good",
                    "title": "Good note",
                    "created_at": "2026-03-11T16:00:00Z",
                    "tags": ["renovation"],
                    "status": "normalized",
                    "project": None,
                    "candidate_projects": [],
                    "confidence": 0.0,
                    "routing_reason": "",
                    "requires_user_confirmation": True,
                    "canonical_path": str(note_path),
                    "dispatched_to": [],
                },
                "# Good note\n\nRenovation ideas.\n",
            )
            with patch_cli_paths(root):
                cli.triage_command(type("Args", (), {"all": False, "source": "voicenotes"})())
                # Plant a stale decision packet with a non-existent canonical_path
                stale_packet = {
                    "source_note_id": "vn_stale",
                    "source": "voicenotes",
                    "canonical_path": "/does/not/exist/stale.md",
                    "proposal": {"status": "pending_project", "review_status": "pending"},
                    "reviews": [],
                }
                (root / "state" / "decisions" / "voicenotes--vn_stale.json").write_text(
                    json.dumps(stale_packet), encoding="utf-8"
                )
                # review --all must return without crashing
                with unittest.mock.patch("builtins.print") as mock_print:
                    result = cli.review_command(type("Args", (), {"all": True, "source": "all", "note_id": None})())
                self.assertEqual(result, 0)
                output = parse_print_json(mock_print)
                self.assertIsInstance(output, list)
                # The stale entry should be present with degraded data (no crash)
                stale_entries = [e for e in output if e.get("source_note_id") == "vn_stale"]
                self.assertEqual(len(stale_entries), 1)

    def test_parse_error_deduplication(self) -> None:
        """Re-scanning with errors must not duplicate parse error notes."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            router_root = root / "repos" / "home-renovation" / "project-router"
            write_router_contract(router_root)
            # Create an invalid packet (missing title)
            invalid_packet = router_root / "outbox" / "20260313T100000Z--pkt_dup.md"
            invalid_packet.write_text(
                "---\n"
                'schema_version: "1"\n'
                'packet_id: "pkt_dup"\n'
                'created_at: "2026-03-13T10:00:00Z"\n'
                'source_project: "home_renovation"\n'
                'packet_type: "proposal"\n'
                'language: "en"\n'
                'status: "open"\n'
                "---\n\nBody\n",
                encoding="utf-8",
            )
            with patch_cli_paths(root):
                cli.scan_outboxes_command(type("Args", (), {"include_self": False, "strict": False})())
                cli.scan_outboxes_command(type("Args", (), {"include_self": False, "strict": False})())
            error_dir = root / "data" / "review" / "project_router" / "parse_errors"
            error_files = list(error_dir.glob("*pkt_dup*.md"))
            self.assertEqual(len(error_files), 1, f"Expected 1 parse error note, got {len(error_files)}: {error_files}")

    def test_parse_error_reconciliation_packet(self) -> None:
        """Fixing a packet must remove its parse error note (stable + legacy)."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            router_root = root / "repos" / "home-renovation" / "project-router"
            write_router_contract(router_root)
            error_dir = root / "data" / "review" / "project_router" / "parse_errors"
            # Seed a legacy timestamped error file
            legacy_error = error_dir / "20260101T000000Z--home-renovation--pkt_fix.md"
            legacy_error.write_text("---\ntitle: legacy\n---\n\nOld error.\n", encoding="utf-8")
            # Create an invalid packet first (missing title)
            packet_path = router_root / "outbox" / "20260313T100000Z--pkt_fix.md"
            packet_path.write_text(
                "---\n"
                'schema_version: "1"\n'
                'packet_id: "pkt_fix"\n'
                'created_at: "2026-03-13T10:00:00Z"\n'
                'source_project: "home_renovation"\n'
                'packet_type: "proposal"\n'
                'language: "en"\n'
                'status: "open"\n'
                "---\n\nBody\n",
                encoding="utf-8",
            )
            with patch_cli_paths(root):
                cli.scan_outboxes_command(type("Args", (), {"include_self": False, "strict": False})())
            self.assertTrue(any(error_dir.glob("*pkt_fix*")))
            # Now fix the packet (add title)
            packet_path.write_text(
                "---\n"
                'schema_version: "1"\n'
                'packet_id: "pkt_fix"\n'
                'created_at: "2026-03-13T10:00:00Z"\n'
                'source_project: "home_renovation"\n'
                'packet_type: "proposal"\n'
                'title: "Fixed packet"\n'
                'language: "en"\n'
                'status: "open"\n'
                "---\n\n# Fixed packet\n\nFixed.\n",
                encoding="utf-8",
            )
            with patch_cli_paths(root):
                cli.scan_outboxes_command(type("Args", (), {"include_self": False, "strict": False})())
            remaining = list(error_dir.glob("*pkt_fix*"))
            self.assertEqual(len(remaining), 0, f"Expected 0 error notes after fix, got {len(remaining)}: {remaining}")

    def test_parse_error_reconciliation_contract(self) -> None:
        """Fixing a contract must remove its router-contract error note."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            router_root = root / "repos" / "home-renovation" / "project-router"
            (router_root / "inbox").mkdir(parents=True, exist_ok=True)
            (router_root / "outbox").mkdir(parents=True, exist_ok=True)
            (router_root / "conformance").mkdir(parents=True, exist_ok=True)
            error_dir = root / "data" / "review" / "project_router" / "parse_errors"
            # Write a bad contract (missing fields)
            (router_root / "router-contract.json").write_text(
                json.dumps({"schema_version": "1"}), encoding="utf-8"
            )
            with patch_cli_paths(root):
                cli.scan_outboxes_command(type("Args", (), {"include_self": False, "strict": False})())
            contract_errors = list(error_dir.glob("*router-contract*"))
            self.assertGreaterEqual(len(contract_errors), 1)
            # Fix the contract
            write_router_contract(router_root)
            with patch_cli_paths(root):
                cli.scan_outboxes_command(type("Args", (), {"include_self": False, "strict": False})())
            remaining = list(error_dir.glob("*router-contract*"))
            self.assertEqual(len(remaining), 0, f"Expected 0 contract error notes after fix, got: {remaining}")

    def test_contract_error_tracked_in_scan_state(self) -> None:
        """Contract errors must be recorded in outbox_scan_state.json."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            router_root = root / "repos" / "home-renovation" / "project-router"
            (router_root / "inbox").mkdir(parents=True, exist_ok=True)
            (router_root / "outbox").mkdir(parents=True, exist_ok=True)
            # Write a bad contract
            (router_root / "router-contract.json").write_text(
                json.dumps({"schema_version": "1"}), encoding="utf-8"
            )
            with patch_cli_paths(root):
                cli.scan_outboxes_command(type("Args", (), {"include_self": False, "strict": False})())
            state = json.loads((root / "state" / "project_router" / "outbox_scan_state.json").read_text(encoding="utf-8"))
            contract_entry = state["scanned_packets"]["home_renovation"]["router-contract"]
            self.assertEqual(contract_entry["status"], "invalid")
            self.assertEqual(contract_entry["error_code"], "INVALID_CONTRACT")
            # Fix the contract and verify state updates to valid
            write_router_contract(router_root)
            with patch_cli_paths(root):
                cli.scan_outboxes_command(type("Args", (), {"include_self": False, "strict": False})())
            state = json.loads((root / "state" / "project_router" / "outbox_scan_state.json").read_text(encoding="utf-8"))
            contract_entry = state["scanned_packets"]["home_renovation"]["router-contract"]
            self.assertEqual(contract_entry["status"], "valid")
            self.assertIsNone(contract_entry["error_code"])

    def test_status_uses_scan_state_for_active_parse_errors(self) -> None:
        """status must count active parse errors from scan state, not stale queue files."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            error_dir = root / "data" / "review" / "project_router" / "parse_errors"
            (error_dir / "20260313T225438Z--home-renovation--router-contract.md").write_text(
                "---\ntitle: stale\n---\n\nOld error.\n",
                encoding="utf-8",
            )
            (error_dir / "20260313T225506Z--weekly-meal-prep--router-contract.md").write_text(
                "---\ntitle: stale\n---\n\nOld error.\n",
                encoding="utf-8",
            )
            scan_state = {
                "schema_version": "1",
                "scanned_packets": {
                    "home_renovation": {
                        "router-contract": {
                            "status": "invalid",
                            "error_code": "INVALID_CONTRACT",
                        },
                        "pkt-ok": {
                            "status": "valid",
                            "error_code": None,
                        },
                    }
                },
            }
            (root / "state" / "project_router" / "outbox_scan_state.json").write_text(
                json.dumps(scan_state, indent=2),
                encoding="utf-8",
            )
            with patch_cli_paths(root):
                with unittest.mock.patch("builtins.print") as mock_print:
                    cli.status_command(type("Args", (), {"source": "all"})())
            output = parse_print_json(mock_print)
            self.assertEqual(output["review"]["project_router"]["parse_errors"], 1)

    def test_context_ignores_stale_parse_error_files_without_active_scan_state(self) -> None:
        """context must not report active parse errors when only stale queue files exist."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            error_dir = root / "data" / "review" / "project_router" / "parse_errors"
            (error_dir / "20260313T225438Z--home-renovation--router-contract.md").write_text(
                "---\ntitle: stale\n---\n\nOld error.\n",
                encoding="utf-8",
            )
            with patch_cli_paths(root):
                with unittest.mock.patch("builtins.print") as mock_print:
                    cli.context_command(type("Args", (), {"source": "all"})())
            output = mock_print.call_args[0][0]
            self.assertNotIn("Active parse errors", output)

    def test_context_pipeline_state_uses_pending_review_entries(self) -> None:
        """context pipeline state must use pending review entries, not stale review files."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            (root / "state" / "decisions" / "voicenotes--vn_ctx1.json").write_text(
                json.dumps(
                    {
                        "source_note_id": "vn_ctx1",
                        "source": "voicenotes",
                        "proposal": {"status": "pending_project", "review_status": "pending"},
                        "reviews": [],
                    }
                ),
                encoding="utf-8",
            )
            error_dir = root / "data" / "review" / "project_router" / "parse_errors"
            (error_dir / "20260313T225438Z--home-renovation--router-contract.md").write_text(
                "---\ntitle: stale\n---\n\nOld error.\n",
                encoding="utf-8",
            )
            with patch_cli_paths(root):
                with unittest.mock.patch("builtins.print") as mock_print:
                    cli.context_command(type("Args", (), {"source": "all"})())
            output = mock_print.call_args[0][0]
            self.assertIn("- **review** (1): voicenotes=1", output)
            self.assertNotIn("project_router=1", output)

    def test_context_pipeline_state_uses_active_parse_errors(self) -> None:
        """context pipeline state must use active parse errors from scan state."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            error_dir = root / "data" / "review" / "project_router" / "parse_errors"
            (error_dir / "20260313T225438Z--home-renovation--router-contract.md").write_text(
                "---\ntitle: stale\n---\n\nOld error.\n",
                encoding="utf-8",
            )
            (error_dir / "20260313T225506Z--weekly-meal-prep--router-contract.md").write_text(
                "---\ntitle: stale\n---\n\nOld error.\n",
                encoding="utf-8",
            )
            scan_state = {
                "schema_version": "1",
                "scanned_packets": {
                    "home_renovation": {
                        "router-contract": {
                            "status": "invalid",
                            "error_code": "INVALID_CONTRACT",
                        }
                    }
                },
            }
            (root / "state" / "project_router" / "outbox_scan_state.json").write_text(
                json.dumps(scan_state, indent=2),
                encoding="utf-8",
            )
            with patch_cli_paths(root):
                with unittest.mock.patch("builtins.print") as mock_print:
                    cli.context_command(type("Args", (), {"source": "all"})())
            output = mock_print.call_args[0][0]
            self.assertIn("- **review** (1): project_router=1", output)
            self.assertNotIn("project_router=2", output)

    def test_metadata_paths_are_relative(self) -> None:
        """Decision packets must use project-relative paths for internal metadata."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            raw_path = root / "data" / "raw" / "voicenotes" / "20260311T160000Z--vn_rel.json"
            raw_path.write_text(
                json.dumps(
                    {
                        "source": "voicenotes",
                        "source_endpoint": "recordings",
                        "recording": {
                            "id": "vn_rel",
                            "title": "Renovation scope",
                            "created_at": "2026-03-11T16:00:00Z",
                            "recorded_at": "2026-03-11T16:00:00Z",
                            "recording_type": 3,
                            "duration": 0,
                            "tags": ["renovation"],
                            "transcript": "Check the contractor schedule.",
                        },
                    }
                ),
                encoding="utf-8",
            )
            with patch_cli_paths(root):
                cli.normalize_command(type("Args", (), {"source": "voicenotes"})())
                cli.triage_command(type("Args", (), {"all": False, "source": "voicenotes"})())
            # Check normalized note metadata
            note_path = root / "data" / "normalized" / "voicenotes" / "20260311T160000Z--vn_rel.md"
            metadata, _ = cli.read_note(note_path)
            self.assertFalse(
                metadata.get("canonical_path", "").startswith("/"),
                f"canonical_path should be relative, got: {metadata.get('canonical_path')}",
            )
            self.assertFalse(
                str(metadata.get("raw_payload_path", "")).startswith("/"),
                f"raw_payload_path should be relative, got: {metadata.get('raw_payload_path')}",
            )
            # Check decision packet (slugify converts _ to -)
            packet_files = list((root / "state" / "decisions").glob("*vn-rel*"))
            self.assertGreaterEqual(len(packet_files), 1)
            packet = json.loads(packet_files[0].read_text(encoding="utf-8"))
            self.assertFalse(
                str(packet.get("canonical_path", "")).startswith("/"),
                f"Decision packet canonical_path should be relative, got: {packet.get('canonical_path')}",
            )

    def test_status_counts_legacy_backlog(self) -> None:
        """status must report legacy_backlog when files exist in non-source-aware dirs."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            # Place a file directly in the top-level normalized dir (legacy layout)
            legacy_file = root / "data" / "normalized" / "legacy_note.md"
            legacy_file.write_text("---\ntitle: Legacy\n---\n\nOld.\n", encoding="utf-8")
            with patch_cli_paths(root):
                with unittest.mock.patch("builtins.print") as mock_print:
                    cli.status_command(type("Args", (), {"source": "all"})())
            output = parse_print_json(mock_print)
            self.assertIn("legacy_backlog", output)
            self.assertGreaterEqual(output["legacy_backlog"], 1)

    def test_status_legacy_backlog_includes_review_queue_files(self) -> None:
        """legacy_backlog must include legacy review queue files, not only core data stages."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            (root / "data" / "normalized" / "legacy_note.md").write_text(
                "---\ntitle: Legacy\n---\n\nOld.\n",
                encoding="utf-8",
            )
            (root / "data" / "review" / "pending_project" / "legacy_review.md").parent.mkdir(parents=True, exist_ok=True)
            (root / "data" / "review" / "pending_project" / "legacy_review.md").write_text(
                "---\ntitle: Legacy review\n---\n\nOld review.\n",
                encoding="utf-8",
            )
            with patch_cli_paths(root):
                with unittest.mock.patch("builtins.print") as mock_print:
                    cli.status_command(type("Args", (), {"source": "all"})())
            output = parse_print_json(mock_print)
            self.assertEqual(output["legacy_backlog"], 2)

    def test_status_legacy_backlog_matches_migrate_dry_run(self) -> None:
        """legacy_backlog must match the number of migrate-source-layout dry-run operations."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            (root / "data" / "raw" / "20260311T160000Z--legacy.json").write_text("{}", encoding="utf-8")
            (root / "data" / "review" / "ambiguous" / "legacy_review.md").parent.mkdir(parents=True, exist_ok=True)
            (root / "data" / "review" / "ambiguous" / "legacy_review.md").write_text(
                "---\ntitle: Legacy review\n---\n\nOld review.\n",
                encoding="utf-8",
            )
            with patch_cli_paths(root):
                with unittest.mock.patch("builtins.print") as status_print:
                    cli.status_command(type("Args", (), {"source": "all"})())
                with unittest.mock.patch("builtins.print") as migrate_print:
                    cli.migrate_source_layout_command(type("Args", (), {"dry_run": True, "confirm": False})())
            status_output = parse_print_json(status_print)
            migrate_output = parse_print_json(migrate_print)
            self.assertEqual(status_output["legacy_backlog"], len(migrate_output["operations"]))


def _write_triaged_note(root: Path, note_id: str, *, status: str = "classified", project: str = "home_renovation",
                        title: str = "Test note", body_text: str = "Renovation ideas.\n",
                        review_status: str = "pending", tags: list | None = None) -> Path:
    """Helper: write a normalized note that looks like it has been through triage."""
    note_path = root / "data" / "normalized" / "voicenotes" / f"20260311T160000Z--{note_id}.md"
    cli.write_note(
        note_path,
        {
            "source": "voicenotes",
            "source_note_id": note_id,
            "title": title,
            "created_at": "2026-03-11T16:00:00Z",
            "tags": tags or ["renovation"],
            "status": status,
            "project": project,
            "candidate_projects": [project] if project else [],
            "confidence": 0.8,
            "routing_reason": "Keyword match.",
            "requires_user_confirmation": True,
            "review_status": review_status,
            "canonical_path": str(note_path.relative_to(root)),
            "raw_payload_path": str((root / "data" / "raw" / "voicenotes" / f"20260311T160000Z--{note_id}.json").relative_to(root)),
            "note_type": "project-idea",
            "dispatched_to": [],
        },
        f"# {title}\n\n{body_text}",
    )
    return note_path


class DecideCommandTests(unittest.TestCase):
    """Tests for decide_command (PR 2, section 2.1)."""

    def test_decide_approve_sets_classified_status(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            note_path = _write_triaged_note(root, "vn_d1", status="pending_project", project=None)
            # Place a review copy so we can verify removal
            review_copy_dir = root / "data" / "review" / "voicenotes" / "pending_project"
            cli.write_note(review_copy_dir / note_path.name, {"source": "voicenotes", "source_note_id": "vn_d1", "status": "pending_project"}, "# Review\n")
            self.assertTrue((review_copy_dir / note_path.name).exists())
            with patch_cli_paths(root):
                cli.decide_command(type("Args", (), {
                    "note_id": "vn_d1", "decision": "approve", "final_project": "home_renovation",
                    "final_type": None, "user_keywords": None, "related_note_ids": None,
                    "thread_id": None, "continuation_of": None, "notes": "", "source": "all",
                })())
            metadata, _ = cli.read_note(root / "data" / "normalized" / "voicenotes" / "20260311T160000Z--vn_d1.md")
            self.assertEqual(metadata["status"], "classified")
            self.assertEqual(metadata["project"], "home_renovation")
            self.assertEqual(metadata["review_status"], "approved")
            # Review copies should be removed
            for queue in ("ambiguous", "needs_review", "pending_project"):
                self.assertFalse((root / "data" / "review" / "voicenotes" / queue / "20260311T160000Z--vn_d1.md").exists())

    def test_decide_approve_without_project_fails(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            _write_triaged_note(root, "vn_d2", status="pending_project", project=None)
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.decide_command(type("Args", (), {
                        "note_id": "vn_d2", "decision": "approve", "final_project": None,
                        "final_type": None, "user_keywords": None, "related_note_ids": None,
                        "thread_id": None, "continuation_of": None, "notes": "", "source": "all",
                    })())
                self.assertIn("Approve requires", str(ctx.exception))

    def test_decide_approve_invalid_project_fails(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            _write_triaged_note(root, "vn_d3", status="pending_project", project=None)
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.decide_command(type("Args", (), {
                        "note_id": "vn_d3", "decision": "approve", "final_project": "nonexistent_project",
                        "final_type": None, "user_keywords": None, "related_note_ids": None,
                        "thread_id": None, "continuation_of": None, "notes": "", "source": "all",
                    })())
                self.assertIn("Unknown project", str(ctx.exception))

    def test_decide_ambiguous_creates_review_copy(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            _write_triaged_note(root, "vn_d4", status="classified", project="home_renovation")
            with patch_cli_paths(root):
                cli.decide_command(type("Args", (), {
                    "note_id": "vn_d4", "decision": "ambiguous", "final_project": None,
                    "final_type": None, "user_keywords": None, "related_note_ids": None,
                    "thread_id": None, "continuation_of": None, "notes": "", "source": "all",
                })())
            metadata, _ = cli.read_note(root / "data" / "normalized" / "voicenotes" / "20260311T160000Z--vn_d4.md")
            self.assertEqual(metadata["status"], "ambiguous")
            self.assertTrue((root / "data" / "review" / "voicenotes" / "ambiguous" / "20260311T160000Z--vn_d4.md").exists())

    def test_decide_pending_project_creates_review_copy(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            _write_triaged_note(root, "vn_d5", status="classified", project="home_renovation")
            with patch_cli_paths(root):
                cli.decide_command(type("Args", (), {
                    "note_id": "vn_d5", "decision": "pending-project", "final_project": None,
                    "final_type": None, "user_keywords": None, "related_note_ids": None,
                    "thread_id": None, "continuation_of": None, "notes": "", "source": "all",
                })())
            metadata, _ = cli.read_note(root / "data" / "normalized" / "voicenotes" / "20260311T160000Z--vn_d5.md")
            self.assertEqual(metadata["status"], "pending_project")
            self.assertTrue((root / "data" / "review" / "voicenotes" / "pending_project" / "20260311T160000Z--vn_d5.md").exists())

    def test_decide_reject_creates_needs_review(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            _write_triaged_note(root, "vn_d6", status="classified", project="home_renovation")
            with patch_cli_paths(root):
                cli.decide_command(type("Args", (), {
                    "note_id": "vn_d6", "decision": "reject", "final_project": None,
                    "final_type": None, "user_keywords": None, "related_note_ids": None,
                    "thread_id": None, "continuation_of": None, "notes": "", "source": "all",
                })())
            metadata, _ = cli.read_note(root / "data" / "normalized" / "voicenotes" / "20260311T160000Z--vn_d6.md")
            self.assertEqual(metadata["status"], "needs_review")
            self.assertEqual(metadata["review_status"], "reject")
            self.assertTrue((root / "data" / "review" / "voicenotes" / "needs_review" / "20260311T160000Z--vn_d6.md").exists())

    def test_decide_creates_decision_packet(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            _write_triaged_note(root, "vn_d7", status="pending_project", project=None)
            with patch_cli_paths(root):
                cli.decide_command(type("Args", (), {
                    "note_id": "vn_d7", "decision": "approve", "final_project": "home_renovation",
                    "final_type": "meeting-notes", "user_keywords": None, "related_note_ids": None,
                    "thread_id": None, "continuation_of": None, "notes": "Looks good", "source": "all",
                })())
            packets = list((root / "state" / "decisions").glob("*vn-d7*"))
            self.assertEqual(len(packets), 1)
            packet = json.loads(packets[0].read_text(encoding="utf-8"))
            self.assertEqual(packet["source_note_id"], "vn_d7")
            self.assertIn("reviews", packet)
            self.assertEqual(len(packet["reviews"]), 1)
            self.assertEqual(packet["reviews"][0]["decision"], "approve")
            self.assertEqual(packet["reviews"][0]["final_project"], "home_renovation")
            self.assertEqual(packet["final_decision"]["decision"], "approve")

    def test_decide_applies_note_annotations(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            _write_triaged_note(root, "vn_d8", status="pending_project", project=None)
            with patch_cli_paths(root):
                cli.decide_command(type("Args", (), {
                    "note_id": "vn_d8", "decision": "approve", "final_project": "home_renovation",
                    "final_type": None, "user_keywords": ["bathroom", "tile"],
                    "related_note_ids": ["vn_d7"], "thread_id": "thread-001",
                    "continuation_of": "vn_d7", "notes": "", "source": "all",
                })())
            metadata, _ = cli.read_note(root / "data" / "normalized" / "voicenotes" / "20260311T160000Z--vn_d8.md")
            self.assertIn("bathroom", metadata.get("user_keywords", []))
            self.assertIn("tile", metadata.get("user_keywords", []))
            self.assertEqual(metadata.get("thread_id"), "thread-001")
            self.assertEqual(metadata.get("continuation_of"), "vn_d7")
            self.assertIn("vn_d7", metadata.get("related_note_ids", []))


def _write_dispatch_ready_note(root: Path, note_id: str = "vn_126") -> tuple[Path, Path]:
    """Helper: write a classified+approved note with a fresh compiled artifact."""
    note_path = root / "data" / "normalized" / "voicenotes" / f"20260311T160000Z--{note_id}.md"
    compiled_path = root / "data" / "compiled" / "voicenotes" / f"20260311T160000Z--{note_id}.md"
    note_metadata = {
        "source": "voicenotes",
        "source_note_id": note_id,
        "title": "Renovation idea",
        "created_at": "2026-03-11T16:00:00Z",
        "tags": ["renovation", "contractor"],
        "status": "classified",
        "project": "home_renovation",
        "candidate_projects": ["home_renovation"],
        "confidence": 1.0,
        "routing_reason": "Matched keywords.",
        "requires_user_confirmation": False,
        "review_status": "approved",
        "canonical_path": str(note_path.relative_to(root)),
        "raw_payload_path": str((root / "data" / "raw" / "voicenotes" / f"20260311T160000Z--{note_id}.json").relative_to(root)),
        "note_type": "project-idea",
    }
    body = "# Renovation idea\n\nNeed contractor quotes.\n"
    cli.write_note(note_path, note_metadata, body)
    compiled_path.parent.mkdir(parents=True, exist_ok=True)
    compiled_metadata = {
        "source": "voicenotes",
        "source_note_id": note_id,
        "title": "Renovation idea",
        "created_at": "2026-03-11T16:00:00Z",
        "compiled_at": "2026-03-11T16:05:00Z",
        "compiled_from_signature": cli.canonical_compile_signature(
            cli.read_note(note_path)[0],
            cli.read_note(note_path)[1],
        ),
        "brief_summary": "Summary",
    }
    cli.write_note(compiled_path, compiled_metadata, "# Renovation idea\n\nCompiled\n")
    return note_path, compiled_path


class DispatchCommandTests(unittest.TestCase):
    """Tests for dispatch_command safety and correctness."""

    def test_dispatch_updates_metadata_and_decision_packet(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            note_path, compiled_path = _write_dispatch_ready_note(root)
            with patch_cli_paths(root):
                cli.dispatch_command(
                    type("Args", (), {"dry_run": False, "confirm_user_approval": True, "note_ids": ["vn_126"], "source": "voicenotes"})()
                )
                metadata, _ = cli.read_note(note_path)
                self.assertEqual(metadata["status"], "dispatched")
                self.assertIn("dispatched_at", metadata)
                self.assertIsInstance(metadata["dispatched_to"], list)
                self.assertGreater(len(metadata["dispatched_to"]), 0)
                # Decision packet has dispatch block
                packet = cli.load_decision_packet_for_metadata(metadata)
                self.assertIn("dispatch", packet)
                self.assertIn("destination", packet["dispatch"])
                self.assertIn("compiled_path", packet["dispatch"])
            # Mirror file exists
            mirror = root / "data" / "dispatched" / "home_renovation" / "20260311T160000Z--vn_126.md"
            self.assertTrue(mirror.exists())

    def test_dispatch_idempotent_skips_dispatched(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            note_path, _ = _write_dispatch_ready_note(root)
            with patch_cli_paths(root):
                cli.dispatch_command(
                    type("Args", (), {"dry_run": False, "confirm_user_approval": True, "note_ids": ["vn_126"], "source": "voicenotes"})()
                )
                with unittest.mock.patch("builtins.print") as mock_print:
                    cli.dispatch_command(
                        type("Args", (), {"dry_run": False, "confirm_user_approval": True, "note_ids": ["vn_126"], "source": "voicenotes"})()
                    )
            output = parse_print_json(mock_print)
            self.assertEqual(output["dispatched"], 0)

    def test_dispatch_dry_run_no_side_effects(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            inbox_path = write_registry(root)
            note_path, _ = _write_dispatch_ready_note(root)
            original_content = note_path.read_text(encoding="utf-8")
            with patch_cli_paths(root):
                with unittest.mock.patch("builtins.print") as mock_print:
                    cli.dispatch_command(
                        type("Args", (), {"dry_run": True, "confirm_user_approval": False, "note_ids": None, "source": "voicenotes"})()
                    )
            output = parse_print_json(mock_print)
            self.assertEqual(output["dispatched"], 1)
            self.assertFalse((inbox_path / "20260311T160000Z--vn_126.md").exists())
            mirror = root / "data" / "dispatched" / "home_renovation" / "20260311T160000Z--vn_126.md"
            self.assertFalse(mirror.exists())
            self.assertEqual(note_path.read_text(encoding="utf-8"), original_content)

    def test_dispatch_skips_stale_compiled(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            note_path, _ = _write_dispatch_ready_note(root)
            metadata, _ = cli.read_note(note_path)
            cli.write_note(note_path, metadata, "# Renovation idea\n\nBody has been changed.\n")
            with patch_cli_paths(root):
                with unittest.mock.patch("builtins.print") as mock_print:
                    cli.dispatch_command(
                        type("Args", (), {"dry_run": True, "confirm_user_approval": False, "note_ids": None, "source": "voicenotes"})()
                    )
            output = parse_print_json(mock_print)
            self.assertEqual(output["dispatched"], 0)
            self.assertEqual(output["candidates"][0]["skip_reason"], "compiled package is stale")

    def test_dispatch_skips_missing_compiled(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            note_path, compiled_path = _write_dispatch_ready_note(root)
            compiled_path.unlink()
            with patch_cli_paths(root):
                with unittest.mock.patch("builtins.print") as mock_print:
                    cli.dispatch_command(
                        type("Args", (), {"dry_run": True, "confirm_user_approval": False, "note_ids": None, "source": "voicenotes"})()
                    )
            output = parse_print_json(mock_print)
            self.assertEqual(output["dispatched"], 0)
            self.assertEqual(output["candidates"][0]["skip_reason"], "compiled package missing")

    def test_dispatch_downstream_write_failure_leaves_metadata_unchanged(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            note_path, _ = _write_dispatch_ready_note(root)
            original_content = note_path.read_text(encoding="utf-8")
            inbox_dir = root / "repos" / "home-renovation" / "project-router" / "inbox"
            inbox_dir.mkdir(parents=True, exist_ok=True)
            with patch_cli_paths(root):
                # Mock Path.write_text to raise OSError for downstream writes
                original_write_text = Path.write_text
                def failing_write_text(self_path, *a, **kw):
                    if str(inbox_dir) in str(self_path):
                        raise OSError("Simulated downstream write failure")
                    return original_write_text(self_path, *a, **kw)
                with unittest.mock.patch.object(Path, "write_text", failing_write_text):
                    with unittest.mock.patch("builtins.print"):
                        cli.dispatch_command(
                            type("Args", (), {"dry_run": False, "confirm_user_approval": True, "note_ids": ["vn_126"], "source": "voicenotes"})()
                        )
                metadata, _ = cli.read_note(note_path)
                self.assertEqual(metadata["status"], "classified")
                mirror = root / "data" / "dispatched" / "home_renovation" / "20260311T160000Z--vn_126.md"
                self.assertFalse(mirror.exists())
                # Decision packet should NOT have dispatch block
                packet = cli.load_decision_packet_for_metadata(metadata)
                self.assertNotIn("dispatch", packet)


class ReadNoteTests(unittest.TestCase):
    """Tests for read_note frontmatter parsing edge cases."""

    def test_read_note_unclosed_frontmatter(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            note_path = root / "unclosed.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            note_path.write_text("---\ntitle: Test\nstatus: draft\nThis line never closes.\n", encoding="utf-8")
            import io
            captured = io.StringIO()
            with mock.patch("sys.stderr", captured):
                metadata, body = cli.read_note(note_path)
            self.assertEqual(metadata, {})
            self.assertIn("---", body)
            self.assertIn("unclosed frontmatter", captured.getvalue())

    def test_read_note_no_frontmatter(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            note_path = root / "plain.md"
            note_path.parent.mkdir(parents=True, exist_ok=True)
            content = "# Just a heading\n\nSome body text.\n"
            note_path.write_text(content, encoding="utf-8")
            import io
            captured = io.StringIO()
            with mock.patch("sys.stderr", captured):
                metadata, body = cli.read_note(note_path)
            self.assertEqual(metadata, {})
            self.assertEqual(body, content)
            self.assertEqual(captured.getvalue(), "")


class CompileCommandTests(unittest.TestCase):
    """Tests for compile_command (PR 2, section 2.2)."""

    def test_compile_creates_artifact(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            _write_triaged_note(root, "vn_c1", body_text="Need to get budget estimates for kitchen renovation.\n")
            with patch_cli_paths(root):
                with unittest.mock.patch("builtins.print") as mock_print:
                    cli.compile_command(type("Args", (), {"note_ids": None, "source": "all"})())
            output = parse_print_json(mock_print)
            self.assertEqual(output["compiled_written"], 1)
            compiled_path = root / "data" / "compiled" / "voicenotes" / "20260311T160000Z--vn_c1.md"
            self.assertTrue(compiled_path.exists())
            compiled_meta, _ = cli.read_note(compiled_path)
            self.assertIn("compiled_from_signature", compiled_meta)
            self.assertIn("brief_summary", compiled_meta)

    def test_compile_idempotent_when_unchanged(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            _write_triaged_note(root, "vn_c2", body_text="Check contractor availability.\n")
            with patch_cli_paths(root):
                cli.compile_command(type("Args", (), {"note_ids": None, "source": "all"})())
                compiled_path = root / "data" / "compiled" / "voicenotes" / "20260311T160000Z--vn_c2.md"
                first_content = compiled_path.read_text(encoding="utf-8")
                cli.compile_command(type("Args", (), {"note_ids": None, "source": "all"})())
            second_content = compiled_path.read_text(encoding="utf-8")
            self.assertEqual(first_content, second_content, "Compiled artifact changed on re-run with same source")

    def test_compile_updates_when_source_changed(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            note_path = _write_triaged_note(root, "vn_c3", body_text="Original body.\n")
            with patch_cli_paths(root):
                cli.compile_command(type("Args", (), {"note_ids": None, "source": "all"})())
                compiled_path = root / "data" / "compiled" / "voicenotes" / "20260311T160000Z--vn_c3.md"
                first_content = compiled_path.read_text(encoding="utf-8")
                # Change the source note body
                metadata, _ = cli.read_note(note_path)
                cli.write_note(note_path, metadata, "# Test note\n\nUpdated body with entirely new content.\n")
                cli.compile_command(type("Args", (), {"note_ids": None, "source": "all"})())
            second_content = compiled_path.read_text(encoding="utf-8")
            self.assertNotEqual(first_content, second_content, "Compiled artifact should change when source changes")

    def test_compile_skips_dispatched_notes(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            _write_triaged_note(root, "vn_c4", status="dispatched")
            with patch_cli_paths(root):
                with unittest.mock.patch("builtins.print") as mock_print:
                    cli.compile_command(type("Args", (), {"note_ids": None, "source": "all"})())
            output = parse_print_json(mock_print)
            self.assertEqual(output["compiled_written"], 0)
            self.assertEqual(output["compiled_updated"], 0)
            self.assertEqual(output["skipped"], 1)


class DiscoverCommandTests(unittest.TestCase):
    """Tests for discover_command (PR 2, section 2.3)."""

    def test_discover_empty_queue(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                with unittest.mock.patch("builtins.print") as mock_print:
                    cli.discover_command(type("Args", (), {"source": "all"})())
            output = parse_print_json(mock_print)
            self.assertEqual(output["pending_project_notes"], 0)
            self.assertEqual(output["clusters"], [])

    def test_discover_clusters_related_notes(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            # Two notes with overlapping keywords should cluster
            _write_triaged_note(root, "vn_disc1", status="pending_project", project=None,
                                title="Garden landscaping plan",
                                body_text="Need to plan the garden landscaping and patio design.\n",
                                tags=["garden", "landscaping"])
            _write_triaged_note(root, "vn_disc2", status="pending_project", project=None,
                                title="Patio furniture selection",
                                body_text="Research patio furniture options for the garden area.\n",
                                tags=["garden", "patio"])
            with patch_cli_paths(root):
                with unittest.mock.patch("builtins.print") as mock_print:
                    cli.discover_command(type("Args", (), {"source": "all"})())
            output = parse_print_json(mock_print)
            self.assertEqual(output["pending_project_notes"], 2)
            # With shared keywords (garden), these should cluster together
            self.assertGreater(len(output["clusters"]), 0, "Expected at least one cluster to form")
            self.assertEqual(output["clusters"][0]["note_count"], 2)

    def test_discover_filters_system_notes(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            _write_triaged_note(root, "welcome_810492", status="pending_project", project=None,
                                title="Welcome to VoiceNotes",
                                body_text="Capture your thoughts with meeting and recording features.\n",
                                tags=[])
            _write_triaged_note(root, "vn_disc3", status="pending_project", project=None,
                                title="Actual pending note",
                                body_text="Something real to discuss.\n",
                                tags=["discussion"])
            with patch_cli_paths(root):
                with unittest.mock.patch("builtins.print") as mock_print:
                    cli.discover_command(type("Args", (), {"source": "all"})())
            output = parse_print_json(mock_print)
            # System note should be in ignored_system_notes
            ignored_ids = [n["source_note_id"] for n in output.get("ignored_system_notes", [])]
            self.assertIn("welcome_810492", ignored_ids)
            # Real note should not be ignored
            self.assertNotIn("vn_disc3", ignored_ids)


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


class TemplateSyncTests(unittest.TestCase):
    """Tests for template-sync related scripts:
    sync_ai_files.py, apply_managed_block_sync.py, migrate_add_contract_block.py,
    check_managed_blocks.py, check_customization_contracts.py
    """

    # ---- Helpers to load script modules via importlib ----

    @staticmethod
    def _load_module(name: str, script_path: Path):
        import importlib.util

        # Add the script's parent directory to sys.path so sibling imports
        # (e.g. check_customization_contracts → check_repo_ownership) resolve.
        parent = str(script_path.parent)
        added = parent not in sys.path
        if added:
            sys.path.insert(0, parent)
        try:
            spec = importlib.util.spec_from_file_location(name, str(script_path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        finally:
            if added and parent in sys.path:
                sys.path.remove(parent)
        return mod

    # =====================================================================
    #  sync_ai_files.py tests
    # =====================================================================

    def test_restore_contract_block_from_backup(self) -> None:
        """Private contract block from backup replaces upstream placeholder in local file."""
        mod = self._load_module("sync_ai_files", SCRIPTS_DIR / "sync_ai_files.py")
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            backup_dir = root / "backup"
            local_dir = root / "local"
            backup_dir.mkdir()
            local_dir.mkdir()

            private_block = (
                "<!-- customization-contract:begin -->\n"
                "## Private AI Rules\n"
                "@Knowledge/local/AI/claude.md\n"
                "<!-- customization-contract:end -->"
            )
            upstream_block = (
                "<!-- customization-contract:begin -->\n"
                "## Upstream placeholder\n"
                "<!-- customization-contract:end -->"
            )

            # Backup has private block
            (backup_dir / "CLAUDE.md").write_text(
                f"# CLAUDE.md\n\nSome text.\n\n{private_block}\n",
                encoding="utf-8",
            )
            # Local (post-overwrite) has upstream placeholder block
            (local_dir / "CLAUDE.md").write_text(
                f"# CLAUDE.md\n\nUpstream content.\n\n{upstream_block}\n",
                encoding="utf-8",
            )

            result = mod.restore_contract_block(
                backup_dir / "CLAUDE.md", local_dir / "CLAUDE.md"
            )
            self.assertTrue(result)

            updated = (local_dir / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("@Knowledge/local/AI/claude.md", updated)
            self.assertIn("Upstream content.", updated)
            self.assertNotIn("Upstream placeholder", updated)

    def test_restore_contract_block_appends_when_upstream_lacks_it(self) -> None:
        """When upstream file has no contract block, the private block is appended."""
        mod = self._load_module("sync_ai_files", SCRIPTS_DIR / "sync_ai_files.py")
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            backup_dir = root / "backup"
            local_dir = root / "local"
            backup_dir.mkdir()
            local_dir.mkdir()

            private_block = (
                "<!-- customization-contract:begin -->\n"
                "## Private AI Rules\n"
                "<!-- customization-contract:end -->"
            )

            (backup_dir / "CLAUDE.md").write_text(
                f"# Backup CLAUDE\n\n{private_block}\n",
                encoding="utf-8",
            )
            # Local file has no contract block at all
            (local_dir / "CLAUDE.md").write_text(
                "# CLAUDE.md\n\nUpstream only content.\n",
                encoding="utf-8",
            )

            result = mod.restore_contract_block(
                backup_dir / "CLAUDE.md", local_dir / "CLAUDE.md"
            )
            self.assertTrue(result)

            updated = (local_dir / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertIn("customization-contract:begin", updated)
            self.assertIn("Upstream only content.", updated)

    def test_restore_no_op_when_backup_has_no_block(self) -> None:
        """No changes when backup has no contract block."""
        mod = self._load_module("sync_ai_files", SCRIPTS_DIR / "sync_ai_files.py")
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            backup_dir = root / "backup"
            local_dir = root / "local"
            backup_dir.mkdir()
            local_dir.mkdir()

            (backup_dir / "CLAUDE.md").write_text(
                "# Backup without contract block\n",
                encoding="utf-8",
            )
            (local_dir / "CLAUDE.md").write_text(
                "# Local CLAUDE\n",
                encoding="utf-8",
            )

            result = mod.restore_contract_block(
                backup_dir / "CLAUDE.md", local_dir / "CLAUDE.md"
            )
            self.assertFalse(result)

            # File should not be modified
            self.assertEqual(
                (local_dir / "CLAUDE.md").read_text(encoding="utf-8"),
                "# Local CLAUDE\n",
            )

    def test_restore_skips_missing_files(self) -> None:
        """Returns False without error when backup or local file is missing."""
        mod = self._load_module("sync_ai_files", SCRIPTS_DIR / "sync_ai_files.py")
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            backup_dir = root / "backup"
            local_dir = root / "local"
            backup_dir.mkdir()
            local_dir.mkdir()

            # Missing backup file
            (local_dir / "CLAUDE.md").write_text("# CLAUDE\n", encoding="utf-8")
            result = mod.restore_contract_block(
                backup_dir / "CLAUDE.md", local_dir / "CLAUDE.md"
            )
            self.assertFalse(result)

            # Missing local file
            (backup_dir / "CLAUDE.md").write_text("# CLAUDE\n", encoding="utf-8")
            (local_dir / "CLAUDE.md").unlink()
            result = mod.restore_contract_block(
                backup_dir / "CLAUDE.md", local_dir / "CLAUDE.md"
            )
            self.assertFalse(result)

    # =====================================================================
    #  apply_managed_block_sync.py tests
    # =====================================================================

    def test_replace_managed_block_from_upstream(self) -> None:
        """Local managed block content is replaced with upstream content, preserving outside content."""
        mod = self._load_module(
            "apply_managed_block_sync", SCRIPTS_DIR / "apply_managed_block_sync.py"
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            upstream_dir = root / "upstream"
            local_dir = root / "local"
            upstream_dir.mkdir()
            local_dir.mkdir()

            marker = "repository-mode"
            local_content = (
                "# README\n\n"
                "Custom header.\n\n"
                f"<!-- {marker}:begin -->\n"
                "Old local block content.\n"
                f"<!-- {marker}:end -->\n\n"
                "Custom footer.\n"
            )
            upstream_content = (
                "# README\n\n"
                f"<!-- {marker}:begin -->\n"
                "New upstream block content.\n"
                f"<!-- {marker}:end -->\n"
            )

            (local_dir / "README.md").write_text(local_content, encoding="utf-8")
            (upstream_dir / "README.md").write_text(upstream_content, encoding="utf-8")

            changed = mod.sync_managed_blocks(
                upstream_dir / "README.md",
                local_dir / "README.md",
                [marker],
            )
            self.assertTrue(changed)

            updated = (local_dir / "README.md").read_text(encoding="utf-8")
            self.assertIn("New upstream block content.", updated)
            self.assertNotIn("Old local block content.", updated)
            self.assertIn("Custom header.", updated)
            self.assertIn("Custom footer.", updated)

    def test_no_op_when_blocks_identical(self) -> None:
        """No changes when upstream and local blocks are identical."""
        mod = self._load_module(
            "apply_managed_block_sync", SCRIPTS_DIR / "apply_managed_block_sync.py"
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            upstream_dir = root / "upstream"
            local_dir = root / "local"
            upstream_dir.mkdir()
            local_dir.mkdir()

            marker = "repository-mode"
            same_content = (
                "# README\n\n"
                f"<!-- {marker}:begin -->\n"
                "Same block content.\n"
                f"<!-- {marker}:end -->\n"
            )

            (local_dir / "README.md").write_text(same_content, encoding="utf-8")
            (upstream_dir / "README.md").write_text(same_content, encoding="utf-8")

            changed = mod.sync_managed_blocks(
                upstream_dir / "README.md",
                local_dir / "README.md",
                [marker],
            )
            self.assertFalse(changed)

    def test_missing_marker_in_upstream(self) -> None:
        """Missing marker in upstream warns but does not crash."""
        mod = self._load_module(
            "apply_managed_block_sync", SCRIPTS_DIR / "apply_managed_block_sync.py"
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            upstream_dir = root / "upstream"
            local_dir = root / "local"
            upstream_dir.mkdir()
            local_dir.mkdir()

            marker = "repository-mode"
            local_content = (
                "# README\n\n"
                f"<!-- {marker}:begin -->\n"
                "Local block content.\n"
                f"<!-- {marker}:end -->\n"
            )
            upstream_content = "# README\n\nNo markers here.\n"

            (local_dir / "README.md").write_text(local_content, encoding="utf-8")
            (upstream_dir / "README.md").write_text(upstream_content, encoding="utf-8")

            # Should not raise
            changed = mod.sync_managed_blocks(
                upstream_dir / "README.md",
                local_dir / "README.md",
                [marker],
            )
            # No changes since upstream lacks the marker
            self.assertFalse(changed)

    # =====================================================================
    #  migrate_add_contract_block.py tests
    # =====================================================================

    def test_inserts_block_when_missing(self) -> None:
        """Contract block is appended when missing from file."""
        mod = self._load_module(
            "migrate_add_contract_block", SCRIPTS_DIR / "migrate_add_contract_block.py"
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            target = root / "CLAUDE.md"
            target.write_text("# CLAUDE.md\n\nSome content.\n", encoding="utf-8")

            result = mod.insert_block(target, mod.CLAUDE_BLOCK)
            self.assertTrue(result)

            updated = target.read_text(encoding="utf-8")
            self.assertIn("customization-contract:begin", updated)
            self.assertIn("customization-contract:end", updated)
            self.assertIn("Some content.", updated)

    def test_idempotent_no_double_insertion(self) -> None:
        """Running insert_block twice does not duplicate the block."""
        mod = self._load_module(
            "migrate_add_contract_block", SCRIPTS_DIR / "migrate_add_contract_block.py"
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            target = root / "AGENTS.md"
            target.write_text("# AGENTS.md\n\nContent.\n", encoding="utf-8")

            first = mod.insert_block(target, mod.AGENTS_BLOCK)
            self.assertTrue(first)

            second = mod.insert_block(target, mod.AGENTS_BLOCK)
            self.assertFalse(second)

            updated = target.read_text(encoding="utf-8")
            # Only one occurrence of begin marker
            self.assertEqual(
                updated.count("customization-contract:begin"), 1
            )

    def test_skips_nonexistent_file(self) -> None:
        """insert_block returns False for nonexistent file without error."""
        mod = self._load_module(
            "migrate_add_contract_block", SCRIPTS_DIR / "migrate_add_contract_block.py"
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            result = mod.insert_block(root / "nonexistent.md", mod.CLAUDE_BLOCK)
            self.assertFalse(result)

    # =====================================================================
    #  check_managed_blocks.py tests
    # =====================================================================

    def test_passes_with_valid_markers(self) -> None:
        """validate_file passes when all required begin/end markers are present."""
        mod = self._load_module(
            "check_managed_blocks", SCRIPTS_DIR / "check_managed_blocks.py"
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            content = (
                "# README\n\n"
                "<!-- repository-mode:begin -->\nMode block\n<!-- repository-mode:end -->\n\n"
                "<!-- template-onboarding:begin -->\nOnboarding block\n<!-- template-onboarding:end -->\n"
            )
            (root / "README.md").write_text(content, encoding="utf-8")

            # Monkeypatch ROOT so validate_file resolves against our temp dir
            original_root = mod.ROOT
            try:
                mod.ROOT = root
                errors = mod.validate_file("README.md", ["repository-mode", "template-onboarding"])
            finally:
                mod.ROOT = original_root

            self.assertEqual(errors, [])

    def test_fails_with_missing_begin_marker(self) -> None:
        """validate_file reports error when a required begin marker is missing."""
        mod = self._load_module(
            "check_managed_blocks", SCRIPTS_DIR / "check_managed_blocks.py"
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            # Has repository-mode but is missing template-onboarding begin marker
            content = (
                "# README\n\n"
                "<!-- repository-mode:begin -->\nMode block\n<!-- repository-mode:end -->\n\n"
                "<!-- template-onboarding:end -->\n"
            )
            (root / "README.md").write_text(content, encoding="utf-8")

            original_root = mod.ROOT
            try:
                mod.ROOT = root
                errors = mod.validate_file("README.md", ["repository-mode", "template-onboarding"])
            finally:
                mod.ROOT = original_root

            error_text = "\n".join(errors)
            self.assertIn("missing <!-- template-onboarding:begin -->", error_text)

    def test_detects_duplicate_markers(self) -> None:
        """validate_file detects duplicate begin markers."""
        mod = self._load_module(
            "check_managed_blocks", SCRIPTS_DIR / "check_managed_blocks.py"
        )
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmpdir:
            root = Path(tmpdir)
            content = (
                "# README\n\n"
                "<!-- repository-mode:begin -->\nFirst\n<!-- repository-mode:end -->\n\n"
                "<!-- repository-mode:begin -->\nDuplicate\n<!-- repository-mode:end -->\n\n"
                "<!-- template-onboarding:begin -->\nOnboarding\n<!-- template-onboarding:end -->\n"
            )
            (root / "README.md").write_text(content, encoding="utf-8")

            original_root = mod.ROOT
            try:
                mod.ROOT = root
                errors = mod.validate_file("README.md", ["repository-mode", "template-onboarding"])
            finally:
                mod.ROOT = original_root

            error_text = "\n".join(errors)
            self.assertIn("duplicate", error_text.lower())
            self.assertIn("repository-mode", error_text)

    # =====================================================================
    #  check_customization_contracts.py tests
    # =====================================================================

    def test_validates_schema_fields(self) -> None:
        """check_schema reports error for entries with missing required fields."""
        mod = self._load_module(
            "check_customization_contracts",
            SCRIPTS_DIR / "check_customization_contracts.py",
        )
        incomplete_surface = {
            "pattern": "CLAUDE.md",
            "ownership": "shared_review",
            # Missing: sync_policy, customization_model, private_overlay,
            # bootstrap_source, agent_load_rule, migration_policy, validator_hooks
        }
        errors = mod.check_schema([incomplete_surface])
        self.assertTrue(len(errors) > 0)
        error_text = "\n".join(errors)
        self.assertIn("missing fields", error_text)

    def test_detects_invalid_ownership(self) -> None:
        """check_schema reports error for invalid ownership value."""
        mod = self._load_module(
            "check_customization_contracts",
            SCRIPTS_DIR / "check_customization_contracts.py",
        )
        bad_surface = {
            "pattern": "CLAUDE.md",
            "ownership": "invalid_ownership_value",
            "sync_policy": "template_sync",
            "customization_model": "overwrite",
            "private_overlay": None,
            "bootstrap_source": None,
            "agent_load_rule": None,
            "migration_policy": "silent_ok",
            "validator_hooks": [],
        }
        errors = mod.check_schema([bad_surface])
        self.assertTrue(len(errors) > 0)
        error_text = "\n".join(errors)
        self.assertIn("invalid ownership", error_text)


# =====================================================================
#  init-router-root tests (Phase 1)
# =====================================================================


class InitRouterRootTests(unittest.TestCase):

    def test_init_creates_scaffold(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            target = root / "downstream" / "project-router"
            with patch_cli_paths(root):
                rc = cli.main(["init-router-root", "--project", "home_renovation", "--router-root", str(target)])
            self.assertEqual(rc, 0)
            self.assertTrue((target / "router-contract.json").exists())
            self.assertTrue((target / "inbox").is_dir())
            self.assertTrue((target / "outbox").is_dir())
            self.assertTrue((target / "conformance").is_dir())
            self.assertTrue((target / "conformance" / "valid-packet.example.md").exists())
            self.assertTrue((target / "conformance" / "invalid-packet.example.md").exists())
            contract = json.loads((target / "router-contract.json").read_text(encoding="utf-8"))
            self.assertEqual(contract["project_key"], "home_renovation")
            errors = cli.validate_router_contract(contract, expected_project_key="home_renovation")
            self.assertEqual(errors, [])

    def test_init_refuses_overwrite(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            target = root / "downstream" / "project-router"
            target.mkdir(parents=True)
            (target / "router-contract.json").write_text("{}", encoding="utf-8")
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main(["init-router-root", "--project", "home_renovation", "--router-root", str(target)])
            self.assertIn("already exists", str(ctx.exception))

    def test_init_uses_registry_language(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            shared = {
                "defaults": {"min_keyword_hits": 2},
                "projects": {
                    "home_renovation": {
                        "display_name": "Renovação Casa",
                        "language": "pt",
                        "note_type": "project-idea",
                        "keywords": ["renovação"],
                    }
                },
            }
            (root / "projects" / "registry.shared.json").write_text(json.dumps(shared), encoding="utf-8")
            (root / "projects" / "registry.local.json").write_text(
                json.dumps({"projects": {"home_renovation": {"router_root_path": str(root / "repos" / "hr" / "project-router")}}}),
                encoding="utf-8",
            )
            target = root / "downstream" / "project-router"
            with patch_cli_paths(root):
                rc = cli.main(["init-router-root", "--project", "home_renovation", "--router-root", str(target)])
            self.assertEqual(rc, 0)
            contract = json.loads((target / "router-contract.json").read_text(encoding="utf-8"))
            self.assertEqual(contract["default_language"], "pt")

    def test_init_rejects_unknown_project(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            target = root / "downstream" / "project-router"
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main(["init-router-root", "--project", "nonexistent", "--router-root", str(target)])
            self.assertIn("not found", str(ctx.exception))

    def test_init_rejects_relative_path(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit):
                    cli.main(["init-router-root", "--project", "home_renovation", "--router-root", "relative/path"])

    def test_init_rejects_repo_root(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            target = root / "downstream"
            target.mkdir(parents=True, exist_ok=True)
            (target / ".git").mkdir()
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main(["init-router-root", "--project", "home_renovation", "--router-root", str(target)])
            self.assertIn("repository root", str(ctx.exception))

    def test_init_rejects_non_protocol_dir(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            target = root / "downstream"
            target.mkdir(parents=True, exist_ok=True)
            (target / "random_file.txt").write_text("hello", encoding="utf-8")
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main(["init-router-root", "--project", "home_renovation", "--router-root", str(target)])
            self.assertIn("non-protocol content", str(ctx.exception))

    def test_init_custom_packet_types(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            target = root / "downstream" / "project-router"
            with patch_cli_paths(root):
                rc = cli.main(["init-router-root", "--project", "home_renovation", "--router-root", str(target), "--packet-types", "insight,task"])
            self.assertEqual(rc, 0)
            contract = json.loads((target / "router-contract.json").read_text(encoding="utf-8"))
            self.assertEqual(contract["supported_packet_types"], ["insight", "task"])

    def test_init_rejects_empty_packet_types(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            target = root / "downstream" / "project-router"
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main(["init-router-root", "--project", "home_renovation", "--router-root", str(target), "--packet-types", ",,,"])
            self.assertIn("at least one non-empty packet type", str(ctx.exception))
            self.assertFalse((target / "router-contract.json").exists())

    def test_init_rejects_duplicate_packet_types(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            target = root / "downstream" / "project-router"
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main(
                        [
                            "init-router-root",
                            "--project",
                            "home_renovation",
                            "--router-root",
                            str(target),
                            "--packet-types",
                            "insight,question,insight",
                        ]
                    )
            self.assertIn("duplicate values", str(ctx.exception))
            self.assertFalse((target / "router-contract.json").exists())


# =====================================================================
#  adopt-router-root tests (Phase 2)
# =====================================================================


def write_registry_legacy(root: Path) -> Path:
    """Write a registry with only inbox_path (no router_root_path) for legacy testing."""
    shared = {
        "defaults": {"min_keyword_hits": 2},
        "projects": {
            "home_renovation": {
                "display_name": "Home Renovation",
                "language": "en",
                "note_type": "project-idea",
                "keywords": ["renovation", "contractor", "budget"],
            }
        },
    }
    router_root = root / "repos" / "home-renovation" / "router"
    inbox_path = router_root / "inbox"
    inbox_path.mkdir(parents=True, exist_ok=True)
    # Content-based inference needs router-contract.json in the parent
    (router_root / "router-contract.json").write_text(
        json.dumps({"schema_version": "1", "project_key": "home_renovation",
                     "default_language": "en", "supported_packet_types": ["improvement_proposal", "question", "insight"]},
                    indent=2) + "\n",
        encoding="utf-8",
    )
    local = {
        "projects": {
            "home_renovation": {
                "inbox_path": str(inbox_path),
            }
        }
    }
    (root / "projects" / "registry.shared.json").write_text(json.dumps(shared), encoding="utf-8")
    (root / "projects" / "registry.local.json").write_text(json.dumps(local, indent=2), encoding="utf-8")
    return inbox_path


class AdoptRouterRootTests(unittest.TestCase):

    def test_adopt_preview_legacy(self) -> None:
        """Preview mode shows operations but creates nothing on disk."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            inbox_path = write_registry_legacy(root)
            with patch_cli_paths(root):
                with mock.patch("builtins.print") as mock_print:
                    rc = cli.main(["adopt-router-root", "--project", "home_renovation"])
            self.assertEqual(rc, 0)
            report = parse_print_json(mock_print)
            self.assertEqual(report["mode"], "preview")
            self.assertEqual(report["status"], "legacy")
            # Preview should not create new scaffold dirs
            self.assertFalse((inbox_path.parent / "outbox").exists())
            self.assertFalse((inbox_path.parent / "conformance").exists())

    def test_adopt_confirm_legacy(self) -> None:
        """Full adoption: scaffold created, registry rewritten, backup, doctor ok, journal written."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            inbox_path = write_registry_legacy(root)
            with patch_cli_paths(root):
                with mock.patch("builtins.print") as mock_print:
                    rc = cli.main(["adopt-router-root", "--project", "home_renovation", "--confirm"])
            self.assertEqual(rc, 0)
            report = parse_print_json(mock_print)
            self.assertEqual(report["mode"], "executed")
            self.assertEqual(report["doctor_status"], "ok")
            router_root = inbox_path.parent
            self.assertTrue((router_root / "router-contract.json").exists())
            self.assertTrue((router_root / "inbox").is_dir())
            self.assertTrue((router_root / "outbox").is_dir())
            self.assertTrue((router_root / "conformance").is_dir())
            # Registry updated
            local = json.loads((root / "projects" / "registry.local.json").read_text(encoding="utf-8"))
            hr = local["projects"]["home_renovation"]
            self.assertEqual(hr["router_root_path"], str(router_root))
            self.assertNotIn("inbox_path", hr)
            # Journal exists
            journal_path = root / "state" / "project_router" / "adoptions" / "home_renovation.json"
            self.assertTrue(journal_path.exists())
            # Backup exists
            backups = [f for f in (root / "projects").iterdir() if f.name.startswith("registry.local.json.pre-adopt")]
            self.assertTrue(len(backups) >= 1)

    def test_adopt_already_current(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root, include_router_root=True)
            router_root = root / "repos" / "home-renovation" / "project-router"
            write_router_contract(router_root)
            with patch_cli_paths(root):
                with mock.patch("builtins.print") as mock_print:
                    rc = cli.main(["adopt-router-root", "--project", "home_renovation"])
            self.assertEqual(rc, 0)
            report = parse_print_json(mock_print)
            self.assertEqual(report["status"], "already_current")

    def test_adopt_partial_scaffold(self) -> None:
        """Missing conformance pieces are created."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            inbox_path = write_registry_legacy(root)
            router_root = inbox_path.parent
            # Create partial scaffold: contract + inbox + outbox, but no conformance fixtures
            (router_root / "outbox").mkdir(parents=True, exist_ok=True)
            (router_root / "conformance").mkdir(parents=True, exist_ok=True)
            contract = {
                "schema_version": "1",
                "project_key": "home_renovation",
                "default_language": "en",
                "supported_packet_types": ["improvement_proposal", "question", "insight"],
            }
            (router_root / "router-contract.json").write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
            with patch_cli_paths(root):
                with mock.patch("builtins.print") as mock_print:
                    rc = cli.main(["adopt-router-root", "--project", "home_renovation", "--confirm"])
            self.assertEqual(rc, 0)
            self.assertTrue((router_root / "conformance" / "valid-packet.example.md").exists())
            self.assertTrue((router_root / "conformance" / "invalid-packet.example.md").exists())

    def test_adopt_explicit_router_root(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            inbox_path = write_registry_legacy(root)
            target = root / "new-target" / "project-router"
            with patch_cli_paths(root):
                with mock.patch("builtins.print") as mock_print:
                    rc = cli.main(["adopt-router-root", "--project", "home_renovation", "--router-root", str(target), "--confirm"])
            self.assertEqual(rc, 0)
            self.assertTrue((target / "router-contract.json").exists())
            local = json.loads((root / "projects" / "registry.local.json").read_text(encoding="utf-8"))
            self.assertEqual(local["projects"]["home_renovation"]["router_root_path"], str(target))

    def test_adopt_preserves_inbox_content(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            inbox_path = write_registry_legacy(root)
            # Put files in old inbox
            (inbox_path / "note1.md").write_text("# Note 1\n", encoding="utf-8")
            (inbox_path / "note2.md").write_text("# Note 2\n", encoding="utf-8")
            # Use a different target
            target = root / "new-loc" / "project-router"
            with patch_cli_paths(root):
                with mock.patch("builtins.print"):
                    rc = cli.main(["adopt-router-root", "--project", "home_renovation", "--router-root", str(target), "--confirm"])
            self.assertEqual(rc, 0)
            self.assertEqual((target / "inbox" / "note1.md").read_text(encoding="utf-8"), "# Note 1\n")
            self.assertEqual((target / "inbox" / "note2.md").read_text(encoding="utf-8"), "# Note 2\n")

    def test_adopt_inbox_collision_aborts(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            inbox_path = write_registry_legacy(root)
            (inbox_path / "note.md").write_text("old content", encoding="utf-8")
            target = root / "new-loc" / "project-router"
            (target / "inbox").mkdir(parents=True, exist_ok=True)
            (target / "inbox" / "note.md").write_text("different content", encoding="utf-8")
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main(["adopt-router-root", "--project", "home_renovation", "--router-root", str(target), "--confirm"])
            self.assertIn("collision", str(ctx.exception).lower())

    def test_adopt_rejects_placeholder(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root, include_router_root=True)
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit):
                    cli.main(["adopt-router-root", "--project", "home_renovation", "--router-root", "/ABSOLUTE/PATH/TO/project-router"])

    def test_adopt_unsafe_inference_aborts(self) -> None:
        """inbox_path parent without router-contract.json → SystemExit."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            # Write registry where inbox_path parent has no router-contract.json
            shared = {
                "defaults": {"min_keyword_hits": 2},
                "projects": {
                    "home_renovation": {
                        "display_name": "Home Renovation",
                        "language": "en",
                        "note_type": "project-idea",
                        "keywords": ["renovation"],
                    }
                },
            }
            inbox_path = root / "repos" / "home-renovation" / "custom-dir" / "inbox"
            inbox_path.mkdir(parents=True, exist_ok=True)
            local = {"projects": {"home_renovation": {"inbox_path": str(inbox_path)}}}
            (root / "projects" / "registry.shared.json").write_text(json.dumps(shared), encoding="utf-8")
            (root / "projects" / "registry.local.json").write_text(json.dumps(local, indent=2), encoding="utf-8")
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main(["adopt-router-root", "--project", "home_renovation", "--confirm"])
            self.assertIn("Cannot infer", str(ctx.exception))

    def test_adopt_rejects_non_protocol_dir(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry_legacy(root)
            target = root / "existing-stuff"
            target.mkdir(parents=True, exist_ok=True)
            (target / "random.txt").write_text("hello", encoding="utf-8")
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main(["adopt-router-root", "--project", "home_renovation", "--router-root", str(target), "--confirm"])
            self.assertIn("non-protocol content", str(ctx.exception))

    def test_adopt_journal_content(self) -> None:
        """Journal has all required fields."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            inbox_path = write_registry_legacy(root)
            with patch_cli_paths(root):
                with mock.patch("builtins.print"):
                    rc = cli.main(["adopt-router-root", "--project", "home_renovation", "--confirm"])
            self.assertEqual(rc, 0)
            journal_path = root / "state" / "project_router" / "adoptions" / "home_renovation.json"
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
            self.assertIn("detected_inputs", journal)
            self.assertIn("chosen_target", journal)
            self.assertIn("operations_executed", journal)
            self.assertIn("config_diff", journal)
            self.assertIn("doctor_result", journal)
            self.assertIn("downstream_agent_config", journal)
            self.assertIn("manual_follow_ups", journal)
            self.assertIn("registry_backup", journal)

    def test_adopt_doctor_failure_still_journals(self) -> None:
        """Outbox with invalid packet → exit 1, journal still written."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            inbox_path = write_registry_legacy(root)
            router_root = inbox_path.parent
            # Create an invalid outbox packet that will fail doctor
            (router_root / "outbox").mkdir(parents=True, exist_ok=True)
            (router_root / "outbox" / "20260313T100000Z--bad_packet.md").write_text(
                "---\nschema_version: \"1\"\npacket_id: \"bad_packet\"\n---\n\nBroken\n",
                encoding="utf-8",
            )
            with patch_cli_paths(root):
                with mock.patch("builtins.print") as mock_print:
                    rc = cli.main(["adopt-router-root", "--project", "home_renovation", "--confirm"])
            self.assertEqual(rc, 1)
            report = parse_print_json(mock_print)
            self.assertEqual(report["doctor_status"], "error")
            journal_path = root / "state" / "project_router" / "adoptions" / "home_renovation.json"
            self.assertTrue(journal_path.exists())

    def test_adopt_all_preview(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root, include_router_root=True)
            router_root = root / "repos" / "home-renovation" / "project-router"
            write_router_contract(router_root)
            with patch_cli_paths(root):
                with mock.patch("builtins.print") as mock_print:
                    rc = cli.main(["adopt-router-root", "--all"])
            self.assertEqual(rc, 0)
            report = parse_print_json(mock_print)
            self.assertEqual(report["mode"], "fleet_preview")
            self.assertIn("projects", report)

    def test_adopt_all_confirm_blocked(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root, include_router_root=True)
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main(["adopt-router-root", "--all", "--confirm"])
            self.assertIn("not supported in v1", str(ctx.exception))

    def test_adopt_normalizes_corrupted_router_root(self) -> None:
        """Corrupted router_root_path ending in /inbox is normalized before adoption."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            router_root = root / "repos" / "home-renovation" / "project-router"
            corrupted = router_root / "inbox"
            shared = {
                "defaults": {"min_keyword_hits": 2},
                "projects": {
                    "home_renovation": {
                        "display_name": "Home Renovation",
                        "language": "en",
                        "note_type": "project-idea",
                        "keywords": ["renovation"],
                    }
                },
            }
            local = {"projects": {"home_renovation": {"router_root_path": str(corrupted)}}}
            (root / "projects" / "registry.shared.json").write_text(json.dumps(shared), encoding="utf-8")
            (root / "projects" / "registry.local.json").write_text(json.dumps(local, indent=2), encoding="utf-8")
            corrupted.mkdir(parents=True, exist_ok=True)
            with patch_cli_paths(root):
                with mock.patch("builtins.print") as mock_print:
                    rc = cli.main(["adopt-router-root", "--project", "home_renovation", "--confirm"])
            self.assertEqual(rc, 0)
            report = parse_print_json(mock_print)
            self.assertEqual(report["mode"], "executed")
            # Target should be the parent, not the /inbox dir
            self.assertEqual(report["target_router_root"], str(router_root))
            # Registry should point to the normalized path
            reg = json.loads((root / "projects" / "registry.local.json").read_text(encoding="utf-8"))
            self.assertEqual(reg["projects"]["home_renovation"]["router_root_path"], str(router_root))

    def test_adopt_infers_from_custom_named_parent(self) -> None:
        """inbox_path inside a non-standard-named parent with router-contract.json → inferred."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            router_root = root / "repos" / "home-renovation" / "MyRouter"
            inbox = router_root / "inbox"
            inbox.mkdir(parents=True, exist_ok=True)
            (router_root / "router-contract.json").write_text(
                json.dumps({"schema_version": "1", "project_key": "home_renovation",
                             "default_language": "en", "supported_packet_types": ["insight"]}),
                encoding="utf-8",
            )
            shared = {
                "defaults": {"min_keyword_hits": 2},
                "projects": {"home_renovation": {"display_name": "Home Renovation", "language": "en",
                                                  "note_type": "project-idea", "keywords": ["renovation"]}},
            }
            local = {"projects": {"home_renovation": {"inbox_path": str(inbox)}}}
            (root / "projects" / "registry.shared.json").write_text(json.dumps(shared), encoding="utf-8")
            (root / "projects" / "registry.local.json").write_text(json.dumps(local, indent=2), encoding="utf-8")
            with patch_cli_paths(root):
                with mock.patch("builtins.print") as mock_print:
                    rc = cli.main(["adopt-router-root", "--project", "home_renovation", "--confirm"])
            self.assertEqual(rc, 0)
            report = parse_print_json(mock_print)
            self.assertEqual(report["target_router_root"], str(router_root))

    def test_init_rejects_file_target(self) -> None:
        """--router-root pointing to a file → clean SystemExit, not traceback."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            target = root / "some-file"
            target.write_text("not a directory", encoding="utf-8")
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main(["init-router-root", "--project", "home_renovation", "--router-root", str(target)])
            self.assertIn("not a file", str(ctx.exception).lower())


# =====================================================================
#  Parser/help coverage tests (Phase 4)
# =====================================================================


class ParserHelpTests(unittest.TestCase):

    def test_init_router_root_appears_in_help(self) -> None:
        result = subprocess.run(
            ["python3", str(Path(__file__).resolve().parents[1] / "scripts" / "project_router.py"), "--help"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("init-router-root", result.stdout)

    def test_adopt_router_root_appears_in_help(self) -> None:
        result = subprocess.run(
            ["python3", str(Path(__file__).resolve().parents[1] / "scripts" / "project_router.py"), "--help"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("adopt-router-root", result.stdout)

    def test_init_router_root_subcommand_help(self) -> None:
        result = subprocess.run(
            ["python3", str(Path(__file__).resolve().parents[1] / "scripts" / "project_router.py"), "init-router-root", "--help"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--project", result.stdout)
        self.assertIn("--router-root", result.stdout)

    def test_adopt_router_root_subcommand_help(self) -> None:
        result = subprocess.run(
            ["python3", str(Path(__file__).resolve().parents[1] / "scripts" / "project_router.py"), "adopt-router-root", "--help"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--project", result.stdout)
        self.assertIn("--all", result.stdout)


# =====================================================================
#  Error message hint tests (Phase 3)
# =====================================================================


class ErrorMessageHintTests(unittest.TestCase):

    def test_doctor_suggests_adopt(self) -> None:
        """Doctor error for missing router_root_path suggests adopt-router-root."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            # Registry with inbox_path only (no router_root_path)
            shared = {
                "defaults": {},
                "projects": {
                    "demo": {
                        "display_name": "Demo",
                        "language": "en",
                        "note_type": "project-idea",
                        "keywords": ["demo"],
                    }
                },
            }
            local = {"projects": {"demo": {"inbox_path": str(root / "repos" / "demo" / "project-router" / "inbox")}}}
            (root / "projects" / "registry.shared.json").write_text(json.dumps(shared), encoding="utf-8")
            (root / "projects" / "registry.local.json").write_text(json.dumps(local), encoding="utf-8")
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main(["doctor", "--project", "demo"])
            self.assertIn("adopt-router-root", str(ctx.exception))

    def test_dispatch_suggests_adopt(self) -> None:
        """Dispatch skip reason contains adopt-router-root hint."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            # Registry with no paths at all
            shared = {
                "defaults": {"min_keyword_hits": 1},
                "projects": {
                    "demo": {
                        "display_name": "Demo",
                        "language": "en",
                        "note_type": "project-idea",
                        "keywords": ["demo"],
                    }
                },
            }
            (root / "projects" / "registry.shared.json").write_text(json.dumps(shared), encoding="utf-8")
            (root / "projects" / "registry.local.json").write_text(json.dumps({"projects": {"demo": {}}}), encoding="utf-8")
            # Create a note that would dispatch to demo
            norm = root / "data" / "normalized" / "voicenotes" / "20260311T160000Z--vn_test.md"
            norm.write_text(
                "---\n"
                'source: "voicenotes"\n'
                'source_note_id: "vn_test"\n'
                'status: "classified"\n'
                'review_status: "approved"\n'
                'project: "demo"\n'
                'title: "Test note"\n'
                'created_at: "2026-03-11T16:00:00Z"\n'
                "---\n\nBody\n",
                encoding="utf-8",
            )
            # Create compiled artifact
            comp_dir = root / "data" / "compiled" / "voicenotes"
            comp_dir.mkdir(parents=True, exist_ok=True)
            comp = comp_dir / "20260311T160000Z--vn_test.md"
            comp.write_text(
                "---\n"
                'source: "voicenotes"\n'
                'source_note_id: "vn_test"\n'
                'status: "classified"\n'
                'review_status: "approved"\n'
                'project: "demo"\n'
                'title: "Test note"\n'
                'created_at: "2026-03-11T16:00:00Z"\n'
                'compiled_at: "2026-03-11T17:00:00Z"\n'
                "---\n\nCompiled body\n",
                encoding="utf-8",
            )
            with patch_cli_paths(root):
                with mock.patch("builtins.print") as mock_print:
                    cli.main(["dispatch", "--dry-run"])
            output = mock_print.call_args[0][0]
            self.assertIn("adopt-router-root", output)

    def test_load_registry_suggests_bootstrap(self) -> None:
        """Missing registry.local.json error suggests bootstrap_local.py."""
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            shared = {"defaults": {}, "projects": {}}
            (root / "projects" / "registry.shared.json").write_text(json.dumps(shared), encoding="utf-8")
            # No registry.local.json
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit) as ctx:
                    cli.load_registry(require_local=True)
            self.assertIn("bootstrap_local.py", str(ctx.exception))


# =====================================================================
#  Bootstrap path normalization tests (Phase 0)
# =====================================================================


class BootstrapLocalTests(unittest.TestCase):

    def _load_bootstrap(self):
        import importlib.util
        script_path = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap_local.py"
        spec = importlib.util.spec_from_file_location("bootstrap_local", str(script_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_bootstrap_normalizes_legacy_inbox_path(self) -> None:
        """inbox_path ending in /inbox → router_root_path with parent."""
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            (root / "projects").mkdir()
            shared = {
                "projects": {
                    "demo": {
                        "display_name": "Demo",
                        "language": "en",
                        "note_type": "project-idea",
                        "keywords": ["demo"],
                    }
                }
            }
            (root / "projects" / "registry.shared.json").write_text(json.dumps(shared), encoding="utf-8")
            # Existing local has legacy inbox_path only
            existing_local = {
                "projects": {
                    "demo": {
                        "inbox_path": str(root / "repos" / "demo" / "project-router" / "inbox")
                    }
                }
            }
            (root / "projects" / "registry.local.json").write_text(json.dumps(existing_local), encoding="utf-8")

            mod = self._load_bootstrap()
            original_shared = mod.REGISTRY_SHARED_PATH
            original_local = mod.REGISTRY_LOCAL_PATH
            try:
                mod.REGISTRY_SHARED_PATH = root / "projects" / "registry.shared.json"
                mod.REGISTRY_LOCAL_PATH = root / "projects" / "registry.local.json"
                # force=False: existing_value is used (not env). File exists so
                # we must set force=True but supply the existing value via env.
                # Simpler: use force=False — the file exists so it would return early.
                # Instead, pass force=True and set the env var to the inbox_path value.
                inbox = str(root / "repos" / "demo" / "project-router" / "inbox")
                with mock.patch.dict(os.environ, {"VN_ROUTER_ROOT_DEMO": inbox}):
                    payload, warnings, status = mod.build_registry_local(force=True)
            finally:
                mod.REGISTRY_SHARED_PATH = original_shared
                mod.REGISTRY_LOCAL_PATH = original_local

            demo = payload["projects"]["demo"]
            self.assertEqual(demo["router_root_path"], str(root / "repos" / "demo" / "project-router"))
            self.assertNotIn("inbox_path", demo)

    def test_bootstrap_normalizes_corrupted_router_root(self) -> None:
        """router_root_path ending in /inbox → normalized to parent."""
        with tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT) as tmp:
            root = Path(tmp)
            (root / "projects").mkdir()
            shared = {
                "projects": {
                    "demo": {
                        "display_name": "Demo",
                        "language": "en",
                        "note_type": "project-idea",
                        "keywords": ["demo"],
                    }
                }
            }
            (root / "projects" / "registry.shared.json").write_text(json.dumps(shared), encoding="utf-8")
            existing_local = {
                "projects": {
                    "demo": {
                        "router_root_path": str(root / "repos" / "demo" / "project-router" / "inbox")
                    }
                }
            }
            (root / "projects" / "registry.local.json").write_text(json.dumps(existing_local), encoding="utf-8")

            mod = self._load_bootstrap()
            original_shared = mod.REGISTRY_SHARED_PATH
            original_local = mod.REGISTRY_LOCAL_PATH
            try:
                mod.REGISTRY_SHARED_PATH = root / "projects" / "registry.shared.json"
                mod.REGISTRY_LOCAL_PATH = root / "projects" / "registry.local.json"
                corrupted = str(root / "repos" / "demo" / "project-router" / "inbox")
                with mock.patch.dict(os.environ, {"VN_ROUTER_ROOT_DEMO": corrupted}):
                    payload, warnings, status = mod.build_registry_local(force=True)
            finally:
                mod.REGISTRY_SHARED_PATH = original_shared
                mod.REGISTRY_LOCAL_PATH = original_local

            demo = payload["projects"]["demo"]
            self.assertEqual(demo["router_root_path"], str(root / "repos" / "demo" / "project-router"))


class FilesystemSourceTests(unittest.TestCase):
    """Tests for filesystem source ingestion, extraction, and pipeline integration."""

    def _setup(self):
        td = temporary_repo_dir()
        root = Path(td.name)
        prepare_repo(root)
        stack = patch_cli_paths(root)
        write_registry(root)
        return td, root, stack

    def _write_manifest(self, root, note_id="fs_20260316T143000Z_a1b2c3", text="Hello world", needs_extraction=False, blob_ext=".txt"):
        manifests_dir = root / "data" / "raw" / "filesystem" / "default" / "manifests"
        ts = "20260316T143000Z"
        manifest = {
            "manifest_version": 1,
            "source": "filesystem",
            "source_note_id": note_id,
            "inbox_key": "default",
            "evidence": {
                "ingest_event_id": "evt_test",
                "content_hash": "sha256:test123",
                "original_path_snapshot": "/tmp/test.txt",
                "file_stat": {"size_bytes": 100, "mtime": "2026-03-16T10:00:00Z", "mode": "0644"},
                "canonical_blob_ref": f"artifacts/{ts}--{note_id}{blob_ext}",
                "ingested_at": "2026-03-16T14:30:00Z",
                "duplicate_of": None,
                "same_content_as": [],
                "archive_status": "archived",
                "archive_path_snapshot": "/tmp/processed/test.txt",
                "extractor_attempts": [{"method": "stdlib_read", "timestamp": "2026-03-16T14:30:00Z", "success": True, "needs_ai": needs_extraction}],
                "errors": [],
            },
            "interpretation": {
                "extracted_text": text if not needs_extraction else "",
                "extraction_method": "stdlib_read" if not needs_extraction else None,
                "text_quality": "good" if not needs_extraction else "needs_extraction",
                "observations": {},
                "routing_hints": {},
                "confidence": 0.8 if not needs_extraction else 0.0,
                "review_annotations": {},
                "updated_at": "2026-03-16T14:30:00Z",
            },
        }
        path = manifests_dir / f"{ts}--{note_id}.manifest.json"
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return path

    def test_parse_source_filter_filesystem(self):
        self.assertEqual(cli.parse_source_filter("filesystem"), {"filesystem"})
        self.assertEqual(cli.parse_source_filter("fs"), {"filesystem"})

    def test_parse_source_filter_all_includes_filesystem(self):
        result = cli.parse_source_filter("all")
        self.assertIn("filesystem", result)
        self.assertIn("voicenotes", result)
        self.assertIn("project_router", result)

    def test_normalize_filesystem_text_file(self):
        td, root, stack = self._setup()
        try:
            self._write_manifest(root, text="Test content here")
            result = cli.main(["normalize", "--source", "filesystem"])
            self.assertEqual(result, 0)
            normalized = list((root / "data" / "normalized" / "filesystem").iterdir())
            self.assertEqual(len(normalized), 1)
            metadata, body = cli.read_note(normalized[0])
            self.assertEqual(metadata["source"], "filesystem")
            self.assertIn("Test content here", body)
            self.assertEqual(metadata["extraction_status"], "complete")
        finally:
            stack.close()
            td.cleanup()

    def test_normalize_filesystem_binary_placeholder(self):
        td, root, stack = self._setup()
        try:
            self._write_manifest(root, needs_extraction=True)
            result = cli.main(["normalize", "--source", "filesystem"])
            self.assertEqual(result, 0)
            normalized = list((root / "data" / "normalized" / "filesystem").iterdir())
            self.assertEqual(len(normalized), 1)
            metadata, body = cli.read_note(normalized[0])
            self.assertEqual(metadata["extraction_status"], "needs_extraction")
            self.assertIn("extraction pending", body)
        finally:
            stack.close()
            td.cleanup()

    def test_manifest_evidence_immutability(self):
        """Evidence survives interpretation updates."""
        td, root, stack = self._setup()
        try:
            manifest_path = self._write_manifest(root)
            original = cli.read_manifest(manifest_path)
            original_hash = original["evidence"]["content_hash"]
            new_interp = {
                "extracted_text": "Updated text",
                "extraction_method": "ai_assisted",
                "text_quality": "good",
                "observations": {},
                "routing_hints": {},
                "confidence": 0.9,
                "review_annotations": {},
                "updated_at": "2026-03-16T15:00:00Z",
            }
            cli.update_manifest_interpretation(manifest_path, new_interp, {"method": "ai_assisted", "timestamp": "2026-03-16T15:00:00Z", "success": True, "needs_ai": False})
            updated = cli.read_manifest(manifest_path)
            self.assertEqual(updated["evidence"]["content_hash"], original_hash)
            self.assertEqual(updated["interpretation"]["extracted_text"], "Updated text")
            self.assertEqual(len(updated["evidence"]["extractor_attempts"]), 2)
        finally:
            stack.close()
            td.cleanup()

    def test_manifest_interpretation_replaceable(self):
        """Re-extraction overwrites interpretation cleanly."""
        td, root, stack = self._setup()
        try:
            manifest_path = self._write_manifest(root)
            cli.update_manifest_interpretation(manifest_path, {
                "extracted_text": "New text",
                "extraction_method": "ai_assisted",
                "text_quality": "good",
                "observations": {"lang": "en"},
                "routing_hints": {},
                "confidence": 0.9,
                "review_annotations": {},
                "updated_at": "2026-03-16T16:00:00Z",
            }, {"method": "ai_assisted", "timestamp": "2026-03-16T16:00:00Z", "success": True, "needs_ai": False})
            manifest = cli.read_manifest(manifest_path)
            self.assertEqual(manifest["interpretation"]["extracted_text"], "New text")
            self.assertEqual(manifest["interpretation"]["observations"]["lang"], "en")
        finally:
            stack.close()
            td.cleanup()

    def test_triage_routes_filesystem_note(self):
        td, root, stack = self._setup()
        try:
            self._write_manifest(root, text="renovation contractor budget ideas")
            cli.main(["normalize", "--source", "filesystem"])
            result = cli.main(["triage", "--source", "filesystem"])
            self.assertEqual(result, 0)
            normalized = list((root / "data" / "normalized" / "filesystem").iterdir())
            self.assertEqual(len(normalized), 1)
            metadata, _ = cli.read_note(normalized[0])
            self.assertIn(metadata["status"], ("classified", "ambiguous", "needs_review", "pending_project"))
        finally:
            stack.close()
            td.cleanup()

    def test_status_includes_filesystem_counts(self):
        td, root, stack = self._setup()
        try:
            self._write_manifest(root)
            cli.main(["normalize", "--source", "filesystem"])
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                cli.main(["status"])
            output = json.loads(buf.getvalue())
            self.assertIn("filesystem", output["raw"])
            self.assertEqual(output["raw"]["filesystem"], 1)
            self.assertEqual(output["normalized"]["filesystem"], 1)
        finally:
            stack.close()
            td.cleanup()

    def test_extract_command_list_mode(self):
        td, root, stack = self._setup()
        try:
            self._write_manifest(root, needs_extraction=True)
            cli.main(["normalize", "--source", "filesystem"])
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                cli.main(["extract", "--source", "filesystem"])
            output = json.loads(buf.getvalue())
            self.assertEqual(output["count"], 1)
            self.assertEqual(output["pending_extraction"][0]["source_note_id"], "fs_20260316T143000Z_a1b2c3")
        finally:
            stack.close()
            td.cleanup()

    def test_extract_command_write_mode(self):
        td, root, stack = self._setup()
        try:
            manifest_path = self._write_manifest(root, needs_extraction=True)
            cli.main(["normalize", "--source", "filesystem"])
            result = cli.main(["extract", "--note-id", "fs_20260316T143000Z_a1b2c3", "--text", "Extracted by AI"])
            self.assertEqual(result, 0)
            normalized = list((root / "data" / "normalized" / "filesystem").iterdir())
            metadata, body = cli.read_note(normalized[0])
            self.assertEqual(metadata["extraction_status"], "complete")
            self.assertIn("Extracted by AI", body)
        finally:
            stack.close()
            td.cleanup()

    def test_extract_appends_to_evidence_attempts(self):
        td, root, stack = self._setup()
        try:
            manifest_path = self._write_manifest(root, needs_extraction=True)
            cli.main(["normalize", "--source", "filesystem"])
            cli.main(["extract", "--note-id", "fs_20260316T143000Z_a1b2c3", "--text", "AI text"])
            manifest = cli.read_manifest(manifest_path)
            self.assertEqual(len(manifest["evidence"]["extractor_attempts"]), 2)
            self.assertEqual(manifest["evidence"]["extractor_attempts"][1]["method"], "ai_assisted")
        finally:
            stack.close()
            td.cleanup()

    def test_remove_review_copies_includes_filesystem(self):
        td, root, stack = self._setup()
        try:
            review_dir = root / "data" / "review" / "filesystem" / "needs_extraction"
            test_file = review_dir / "test-note.md"
            test_file.write_text("---\ntitle: test\n---\ntest", encoding="utf-8")
            cli.remove_review_copies("test-note.md")
            self.assertFalse(test_file.exists())
        finally:
            stack.close()
            td.cleanup()

    def test_ingest_dry_run(self):
        td, root, stack = self._setup()
        try:
            inbox = root / "inbox"
            inbox.mkdir()
            (inbox / "test.txt").write_text("hello", encoding="utf-8")
            local_reg = {
                "projects": {},
                "sources": {"filesystem_inboxes": {"default": {"inbox_path": str(inbox)}}},
            }
            (root / "projects" / "registry.local.json").write_text(json.dumps(local_reg), encoding="utf-8")
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                result = cli.main(["ingest", "--integration", "filesystem", "--dry-run"])
            self.assertEqual(result, 0)
            output = json.loads(buf.getvalue())
            self.assertEqual(output["ingested"], 1)
            self.assertTrue((inbox / "test.txt").exists(), "dry run should not move file")
        finally:
            stack.close()
            td.cleanup()

    def test_ingest_creates_manifest_and_blob(self):
        td, root, stack = self._setup()
        try:
            inbox = root / "inbox"
            inbox.mkdir()
            (inbox / "test.txt").write_text("hello world", encoding="utf-8")
            local_reg = {
                "projects": {},
                "sources": {"filesystem_inboxes": {"default": {"inbox_path": str(inbox)}}},
            }
            (root / "projects" / "registry.local.json").write_text(json.dumps(local_reg), encoding="utf-8")
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                result = cli.main(["ingest", "--integration", "filesystem"])
            self.assertEqual(result, 0)
            output = json.loads(buf.getvalue())
            self.assertEqual(output["ingested"], 1)
            manifests_dir = root / "data" / "raw" / "filesystem" / "default" / "manifests"
            manifests = list(manifests_dir.glob("*.manifest.json"))
            self.assertEqual(len(manifests), 1)
            artifacts_dir = root / "data" / "raw" / "filesystem" / "default" / "artifacts"
            artifacts = list(artifacts_dir.glob("*"))
            self.assertEqual(len(artifacts), 1)
            self.assertFalse((inbox / "test.txt").exists(), "original should be archived")
            processed = list((inbox / "processed").rglob("test.txt"))
            self.assertEqual(len(processed), 1)
        finally:
            stack.close()
            td.cleanup()

    def test_dedupe_by_content_hash_without_collapsing_events(self):
        td, root, stack = self._setup()
        try:
            inbox = root / "inbox"
            inbox.mkdir()
            (inbox / "a.txt").write_text("same content", encoding="utf-8")
            local_reg = {
                "projects": {},
                "sources": {"filesystem_inboxes": {"default": {"inbox_path": str(inbox)}}},
            }
            (root / "projects" / "registry.local.json").write_text(json.dumps(local_reg), encoding="utf-8")
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                cli.main(["ingest", "--integration", "filesystem"])
            # Ingest a second file with same content
            (inbox / "b.txt").write_text("same content", encoding="utf-8")
            buf2 = io.StringIO()
            with redirect_stdout(buf2):
                cli.main(["ingest", "--integration", "filesystem"])
            manifests_dir = root / "data" / "raw" / "filesystem" / "default" / "manifests"
            manifests = list(manifests_dir.glob("*.manifest.json"))
            self.assertEqual(len(manifests), 2, "Two events even for same content")
            m1 = json.loads(manifests[0].read_text(encoding="utf-8"))
            m2 = json.loads(manifests[1].read_text(encoding="utf-8"))
            self.assertNotEqual(m1["source_note_id"], m2["source_note_id"])
        finally:
            stack.close()
            td.cleanup()

    def test_bootstrap_writes_sources_section(self):
        """bootstrap_local.py writes sources section when env var is set."""
        td = temporary_repo_dir()
        root = Path(td.name)
        try:
            import importlib
            mod = importlib.import_module("scripts.bootstrap_local")
            (root / "projects").mkdir(parents=True, exist_ok=True)
            shared = {"projects": {"demo": {"display_name": "Demo"}}}
            (root / "projects" / "registry.shared.json").write_text(json.dumps(shared), encoding="utf-8")
            original_shared = mod.REGISTRY_SHARED_PATH
            original_local = mod.REGISTRY_LOCAL_PATH
            try:
                mod.REGISTRY_SHARED_PATH = root / "projects" / "registry.shared.json"
                mod.REGISTRY_LOCAL_PATH = root / "projects" / "registry.local.json"
                with mock.patch.dict(os.environ, {"VN_ROUTER_ROOT_DEMO": str(root / "repos" / "demo"), "VN_FILESYSTEM_INBOX_DEFAULT": str(root / "inbox")}):
                    payload, warnings, status = mod.build_registry_local(force=True)
            finally:
                mod.REGISTRY_SHARED_PATH = original_shared
                mod.REGISTRY_LOCAL_PATH = original_local
            self.assertIn("sources", payload)
            self.assertIn("filesystem_inboxes", payload["sources"])
            self.assertEqual(payload["sources"]["filesystem_inboxes"]["default"]["inbox_path"], str(root / "inbox"))
        finally:
            td.cleanup()

    def test_extractor_markdown(self):
        from src.project_router.extractors import extract
        td = temporary_repo_dir()
        root = Path(td.name)
        try:
            test_file = root / "test.md"
            test_file.write_text("# Hello\n\nWorld", encoding="utf-8")
            result = extract(test_file)
            self.assertEqual(result.text, "# Hello\n\nWorld")
            self.assertEqual(result.extraction_method, "stdlib_read")
            self.assertFalse(result.needs_ai_extraction)
        finally:
            td.cleanup()

    def test_extractor_image(self):
        from src.project_router.extractors import extract
        td = temporary_repo_dir()
        root = Path(td.name)
        try:
            test_file = root / "test.png"
            # Minimal valid PNG header
            import struct
            header = b"\x89PNG\r\n\x1a\n"
            ihdr_data = struct.pack(">II", 100, 200) + b"\x08\x02\x00\x00\x00"
            import zlib
            ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
            ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
            test_file.write_bytes(header + ihdr)
            result = extract(test_file)
            self.assertTrue(result.needs_ai_extraction)
            self.assertEqual(result.extraction_method, "metadata_only")
            self.assertEqual(result.metadata.get("width"), 100)
            self.assertEqual(result.metadata.get("height"), 200)
        finally:
            td.cleanup()

    def test_extractor_graceful_degradation_missing_dep(self):
        """PDF extractor returns needs_ai when pymupdf missing."""
        from src.project_router.extractors._pdf import _HAS_PYMUPDF
        if _HAS_PYMUPDF:
            return  # Cannot test missing-dep path when dep is installed
        from src.project_router.extractors._pdf import extract_pdf
        td = temporary_repo_dir()
        root = Path(td.name)
        try:
            test_file = root / "test.pdf"
            test_file.write_bytes(b"%PDF-1.4 fake")
            result = extract_pdf(test_file)
            self.assertTrue(result.needs_ai_extraction)
            self.assertEqual(result.extraction_method, "unavailable")
        finally:
            td.cleanup()

    def test_extractor_unsupported_extension(self):
        from src.project_router.extractors import extract
        td = temporary_repo_dir()
        root = Path(td.name)
        try:
            test_file = root / "test.xyz"
            test_file.write_text("mystery", encoding="utf-8")
            result = extract(test_file)
            self.assertTrue(result.needs_ai_extraction)
            self.assertEqual(result.extraction_method, "unsupported")
        finally:
            td.cleanup()

    def test_extractor_csv(self):
        from src.project_router.extractors import extract
        td = temporary_repo_dir()
        root = Path(td.name)
        try:
            test_file = root / "test.csv"
            test_file.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
            result = extract(test_file)
            self.assertIn("a, b, c", result.text)
            self.assertEqual(result.extraction_method, "stdlib_csv")
            self.assertFalse(result.needs_ai_extraction)
        finally:
            td.cleanup()

    def test_extractor_json(self):
        from src.project_router.extractors import extract
        td = temporary_repo_dir()
        root = Path(td.name)
        try:
            test_file = root / "test.json"
            test_file.write_text('{"key": "value"}', encoding="utf-8")
            result = extract(test_file)
            self.assertIn('"key"', result.text)
            self.assertEqual(result.extraction_method, "stdlib_json")
        finally:
            td.cleanup()

    def test_extractor_html(self):
        from src.project_router.extractors import extract
        td = temporary_repo_dir()
        root = Path(td.name)
        try:
            test_file = root / "test.html"
            test_file.write_text("<p>Hello <b>world</b></p>", encoding="utf-8")
            result = extract(test_file)
            self.assertIn("Hello world", result.text)
            self.assertNotIn("<p>", result.text)
            self.assertEqual(result.extraction_method, "stdlib_html_strip")
        finally:
            td.cleanup()

    def test_load_filesystem_inboxes_rejects_relative_path(self):
        config = {"sources": {"filesystem_inboxes": {"default": {"inbox_path": "relative/path"}}}}
        with self.assertRaises(SystemExit) as ctx:
            cli.load_filesystem_inboxes(config)
        self.assertIn("absolute path", str(ctx.exception))

    def test_load_filesystem_inboxes_rejects_traversal(self):
        config = {"sources": {"filesystem_inboxes": {"default": {"inbox_path": "/tmp/../etc/passwd"}}}}
        with self.assertRaises(SystemExit) as ctx:
            cli.load_filesystem_inboxes(config)
        self.assertIn("unsafe path", str(ctx.exception))

    def test_load_filesystem_inboxes_rejects_unsafe_key(self):
        config = {"sources": {"filesystem_inboxes": {"../../etc": {"inbox_path": "/tmp/inbox"}}}}
        with self.assertRaises(SystemExit) as ctx:
            cli.load_filesystem_inboxes(config)
        self.assertIn("invalid", str(ctx.exception))

    def test_ingest_no_configured_inboxes(self):
        td, root, stack = self._setup()
        try:
            (root / "projects" / "registry.local.json").write_text(json.dumps({"projects": {}}), encoding="utf-8")
            with self.assertRaises(SystemExit) as ctx:
                cli.main(["ingest", "--integration", "filesystem"])
            self.assertIn("No filesystem inboxes configured", str(ctx.exception))
        finally:
            stack.close()
            td.cleanup()

    def test_ingest_missing_inbox_path_reports_error(self):
        td, root, stack = self._setup()
        try:
            local_reg = {
                "projects": {},
                "sources": {"filesystem_inboxes": {"default": {"inbox_path": str(root / "nonexistent")}}},
            }
            (root / "projects" / "registry.local.json").write_text(json.dumps(local_reg), encoding="utf-8")
            import io
            from contextlib import redirect_stdout, redirect_stderr
            buf = io.StringIO()
            err_buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(err_buf):
                result = cli.main(["ingest", "--integration", "filesystem"])
            self.assertEqual(result, 0)
            output = json.loads(buf.getvalue())
            self.assertEqual(output["errors"], 1)
            self.assertIn("error_details", output)
            self.assertIn("does not exist", err_buf.getvalue())
        finally:
            stack.close()
            td.cleanup()

    def test_ingest_skips_hidden_files_and_dirs(self):
        td, root, stack = self._setup()
        try:
            inbox = root / "inbox"
            inbox.mkdir()
            (inbox / ".DS_Store").write_text("", encoding="utf-8")
            (inbox / "subdir").mkdir()
            local_reg = {
                "projects": {},
                "sources": {"filesystem_inboxes": {"default": {"inbox_path": str(inbox)}}},
            }
            (root / "projects" / "registry.local.json").write_text(json.dumps(local_reg), encoding="utf-8")
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                cli.main(["ingest", "--integration", "filesystem", "--dry-run"])
            output = json.loads(buf.getvalue())
            self.assertEqual(output["ingested"], 0)
        finally:
            stack.close()
            td.cleanup()

    def test_extract_invalid_note_id_fails(self):
        td, root, stack = self._setup()
        try:
            with self.assertRaises(SystemExit):
                cli.main(["extract", "--note-id", "nonexistent_note", "--text", "hello"])
        finally:
            stack.close()
            td.cleanup()

    def test_extract_invalid_observations_json_fails(self):
        td, root, stack = self._setup()
        try:
            self._write_manifest(root, needs_extraction=True)
            cli.main(["normalize", "--source", "filesystem"])
            with self.assertRaises(SystemExit) as ctx:
                cli.main(["extract", "--note-id", "fs_20260316T143000Z_a1b2c3", "--text", "hello", "--observations", "not{json"])
            self.assertIn("Invalid --observations JSON", str(ctx.exception))
        finally:
            stack.close()
            td.cleanup()

    def test_dedupe_asserts_same_content_as_field(self):
        td, root, stack = self._setup()
        try:
            inbox = root / "inbox"
            inbox.mkdir()
            (inbox / "a.txt").write_text("same content", encoding="utf-8")
            local_reg = {
                "projects": {},
                "sources": {"filesystem_inboxes": {"default": {"inbox_path": str(inbox)}}},
            }
            (root / "projects" / "registry.local.json").write_text(json.dumps(local_reg), encoding="utf-8")
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                cli.main(["ingest", "--integration", "filesystem"])
            (inbox / "b.txt").write_text("same content", encoding="utf-8")
            buf2 = io.StringIO()
            with redirect_stdout(buf2):
                cli.main(["ingest", "--integration", "filesystem"])
            manifests_dir = root / "data" / "raw" / "filesystem" / "default" / "manifests"
            manifests = sorted(manifests_dir.glob("*.manifest.json"))
            self.assertEqual(len(manifests), 2)
            # The second-ingested manifest links back; check either since sort order isn't guaranteed
            all_same = []
            for mp in manifests:
                m = json.loads(mp.read_text(encoding="utf-8"))
                all_same.extend(m["evidence"]["same_content_as"])
            self.assertTrue(len(all_same) > 0, "At least one manifest should reference same_content_as")
        finally:
            stack.close()
            td.cleanup()

    def test_compile_filesystem_note(self):
        td, root, stack = self._setup()
        try:
            self._write_manifest(root, text="renovation contractor budget ideas for the home")
            cli.main(["normalize", "--source", "filesystem"])
            cli.main(["triage", "--source", "filesystem"])
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                result = cli.main(["compile", "--source", "filesystem"])
            self.assertEqual(result, 0)
            compiled = list((root / "data" / "compiled" / "filesystem").iterdir())
            self.assertEqual(len(compiled), 1)
            metadata, _ = cli.read_note(compiled[0])
            self.assertEqual(metadata.get("source"), "filesystem")
        finally:
            stack.close()
            td.cleanup()

    def test_normalize_needs_extraction_populates_review_queue(self):
        td, root, stack = self._setup()
        try:
            self._write_manifest(root, needs_extraction=True)
            cli.main(["normalize", "--source", "filesystem"])
            review_dir = root / "data" / "review" / "filesystem" / "needs_extraction"
            entries = list(review_dir.iterdir())
            self.assertEqual(len(entries), 1)
        finally:
            stack.close()
            td.cleanup()

    def test_ingest_inbox_key_specific(self):
        td, root, stack = self._setup()
        try:
            inbox = root / "inbox"
            inbox.mkdir()
            (inbox / "test.txt").write_text("hello", encoding="utf-8")
            local_reg = {
                "projects": {},
                "sources": {"filesystem_inboxes": {"default": {"inbox_path": str(inbox)}}},
            }
            (root / "projects" / "registry.local.json").write_text(json.dumps(local_reg), encoding="utf-8")
            with self.assertRaises(SystemExit) as ctx:
                cli.main(["ingest", "--integration", "filesystem", "--inbox", "nonexistent"])
            self.assertIn("Unknown inbox key", str(ctx.exception))
        finally:
            stack.close()
            td.cleanup()


    def test_dispatch_filesystem_note_copies_blob(self):
        """Dispatch of a filesystem note copies the original blob alongside the brief."""
        td, root, stack = self._setup()
        try:
            # Create a blob in artifacts
            artifacts_dir = root / "data" / "raw" / "filesystem" / "default" / "artifacts"
            blob_name = "20260316T143000Z--fs_20260316T143000Z_a1b2c3.pdf"
            (artifacts_dir / blob_name).write_bytes(b"%PDF-fake-content")

            # Write manifest pointing to that blob
            self._write_manifest(root, text="renovation contractor invoice for budget review", blob_ext=".pdf")

            # Full pipeline: normalize -> triage -> compile -> decide approve -> dispatch
            cli.main(["normalize", "--source", "filesystem"])
            cli.main(["triage", "--source", "filesystem"])
            cli.main(["compile", "--source", "filesystem"])

            # Find the normalized note and check its project assignment
            normalized = list((root / "data" / "normalized" / "filesystem").iterdir())
            self.assertEqual(len(normalized), 1)
            metadata, body = cli.read_note(normalized[0])

            # Force-approve for dispatch, then recompile (decide changes metadata → stale compiled)
            cli.main(["decide", "--source", "filesystem", "--note-id", "fs_20260316T143000Z_a1b2c3",
                       "--decision", "approve", "--final-project", "home_renovation"])
            cli.main(["compile", "--source", "filesystem"])

            # Set up downstream inbox
            router_root = root / "repos" / "home-renovation" / "project-router"
            inbox_dir = router_root / "inbox"
            inbox_dir.mkdir(parents=True, exist_ok=True)

            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                cli.main(["dispatch", "--source", "filesystem", "--confirm-user-approval",
                           "--note-id", "fs_20260316T143000Z_a1b2c3"])
            output = json.loads(buf.getvalue())
            self.assertGreaterEqual(output["dispatched"], 1)

            # Check that both .md brief AND .pdf blob were dispatched
            inbox_files = list(inbox_dir.iterdir())
            extensions = {f.suffix for f in inbox_files}
            self.assertIn(".md", extensions, "Brief should be dispatched")
            self.assertIn(".pdf", extensions, "Original blob should be dispatched alongside brief")

            # Verify the blob content
            pdf_files = [f for f in inbox_files if f.suffix == ".pdf"]
            self.assertEqual(len(pdf_files), 1)
            self.assertEqual(pdf_files[0].read_bytes(), b"%PDF-fake-content")
        finally:
            stack.close()
            td.cleanup()


def write_protocol_inbox_packet(root: Path, packet_id: str, *, title: str = "Test Packet", packet_type: str = "improvement_proposal", source_project: str = "my_project_router") -> Path:
    """Write a protocol-format packet into router/inbox/."""
    inbox = root / "router" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / f"20260316T100000Z--{packet_id}.md"
    path.write_text(
        "---\n"
        'schema_version: "1"\n'
        f'packet_id: "{packet_id}"\n'
        'created_at: "2026-03-16T10:00:00Z"\n'
        f'source_project: "{source_project}"\n'
        f'packet_type: "{packet_type}"\n'
        f'title: "{title}"\n'
        'language: "en"\n'
        'status: "open"\n'
        "---\n\n"
        f"# {title}\n\nBody content.\n",
        encoding="utf-8",
    )
    return path


def write_compiled_brief_inbox_packet(root: Path, packet_id: str, *, title: str = "Brief Title") -> Path:
    """Write a compiled-brief format packet into router/inbox/ (needs conversion)."""
    inbox = root / "router" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / f"20260316T100000Z--{packet_id}.md"
    path.write_text(
        "---\n"
        'source: "project_router"\n'
        'source_project: "my_project_router"\n'
        f'source_note_id: "{packet_id}"\n'
        'created_at: "2026-03-16T10:00:00Z"\n'
        'project: "project_router_template"\n'
        'classification: "maintainer-follow-up"\n'
        'capture_kind: "project_idea"\n'
        'intent: "actionable"\n'
        'confidence: 1.0\n'
        'inferred_keywords: ["template", "sync"]\n'
        'status: "to_review"\n'
        "---\n\n"
        f"# {title}\n\n## Project-ready brief\n\nSome brief content.\n",
        encoding="utf-8",
    )
    return path


def write_local_router_contract(root: Path) -> None:
    """Write a router-contract.json for the local router."""
    contract_path = root / "router" / "router-contract.json"
    contract_path.write_text(
        json.dumps({
            "schema_version": "1",
            "project_key": "project_router_template",
            "default_language": "en",
            "supported_packet_types": ["improvement_proposal", "question", "insight", "ack"],
        }, indent=2) + "\n",
        encoding="utf-8",
    )


class InboxConsumptionTests(unittest.TestCase):

    def test_inbox_intake_valid_packet(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_local_router_contract(root)
            pkt = write_protocol_inbox_packet(root, "pkt_valid")
            with patch_cli_paths(root), mock.patch("builtins.print") as mock_print:
                cli.inbox_intake_command(type("Args", (), {"dry_run": False})())
            result = parse_print_json(mock_print)
            self.assertEqual(result["ingested"], 1)
            self.assertEqual(result["skipped"], 0)
            self.assertEqual(result["errors"], 0)
            # Packet removed from inbox
            self.assertFalse(pkt.exists())
            # Archived
            archive = root / "router" / "archive" / "pkt_valid" / "original.md"
            self.assertTrue(archive.exists())
            # State created
            state_path = root / "state" / "project_router" / "inbox_status" / "pkt_valid.json"
            self.assertTrue(state_path.exists())
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "open")
            self.assertEqual(state["packet_id"], "pkt_valid")

    def test_inbox_intake_converts_brief(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_local_router_contract(root)
            pkt = write_compiled_brief_inbox_packet(root, "brief_001", title="Brief Title")
            with patch_cli_paths(root), mock.patch("builtins.print") as mock_print:
                cli.inbox_intake_command(type("Args", (), {"dry_run": False})())
            result = parse_print_json(mock_print)
            self.assertEqual(result["ingested"], 1)
            self.assertFalse(pkt.exists())
            state = json.loads((root / "state" / "project_router" / "inbox_status" / "brief_001.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "open")
            self.assertEqual(state["packet_type"], "improvement_proposal")

    def test_inbox_intake_invalid_stays(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_local_router_contract(root)
            # Write a packet missing required fields
            inbox = root / "router" / "inbox"
            bad = inbox / "20260316T100000Z--bad_pkt.md"
            bad.write_text("---\ntitle: \"Broken\"\n---\n\n# Broken\n", encoding="utf-8")
            with patch_cli_paths(root), mock.patch("builtins.print") as mock_print:
                cli.inbox_intake_command(type("Args", (), {"dry_run": False})())
            result = parse_print_json(mock_print)
            self.assertEqual(result["errors"], 1)
            # Bad packet stays in inbox
            self.assertTrue(bad.exists())
            # No archive created
            archive = root / "router" / "archive" / "bad_pkt" / "original.md"
            self.assertFalse(archive.exists())

    def test_inbox_intake_idempotent(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_local_router_contract(root)
            write_protocol_inbox_packet(root, "pkt_idem")
            with patch_cli_paths(root), mock.patch("builtins.print"):
                cli.inbox_intake_command(type("Args", (), {"dry_run": False})())
            # Run again
            with patch_cli_paths(root), mock.patch("builtins.print") as mock_print:
                cli.inbox_intake_command(type("Args", (), {"dry_run": False})())
            result = parse_print_json(mock_print)
            self.assertEqual(result["ingested"], 0)
            self.assertEqual(result["skipped"], 0)

    def test_inbox_intake_dry_run(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_local_router_contract(root)
            pkt = write_protocol_inbox_packet(root, "pkt_dry")
            with patch_cli_paths(root), mock.patch("builtins.print") as mock_print:
                cli.inbox_intake_command(type("Args", (), {"dry_run": True})())
            result = parse_print_json(mock_print)
            self.assertEqual(result["ingested"], 1)
            # Packet NOT removed from inbox
            self.assertTrue(pkt.exists())
            # No state created
            state_path = root / "state" / "project_router" / "inbox_status" / "pkt_dry.json"
            self.assertFalse(state_path.exists())

    def test_inbox_intake_ignores_gitkeep(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_local_router_contract(root)
            gitkeep = root / "router" / "inbox" / ".gitkeep"
            gitkeep.write_text("", encoding="utf-8")
            with patch_cli_paths(root), mock.patch("builtins.print") as mock_print:
                cli.inbox_intake_command(type("Args", (), {"dry_run": False})())
            result = parse_print_json(mock_print)
            self.assertEqual(result["ingested"], 0)
            self.assertTrue(gitkeep.exists())

    def test_inbox_status_lists_open(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_local_router_contract(root)
            write_protocol_inbox_packet(root, "pkt_open")
            with patch_cli_paths(root), mock.patch("builtins.print"):
                cli.inbox_intake_command(type("Args", (), {"dry_run": False})())
            with patch_cli_paths(root), mock.patch("builtins.print") as mock_print:
                cli.inbox_status_command(type("Args", (), {"all": False, "packet_id": None})())
            result = parse_print_json(mock_print)
            self.assertEqual(len(result["packets"]), 1)
            self.assertEqual(result["packets"][0]["status"], "open")

    def test_inbox_status_all(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_local_router_contract(root)
            write_protocol_inbox_packet(root, "pkt_for_ack")
            with patch_cli_paths(root), mock.patch("builtins.print"):
                cli.inbox_intake_command(type("Args", (), {"dry_run": False})())
            # Ack it to terminal state
            with patch_cli_paths(root), mock.patch("builtins.print"):
                cli.inbox_ack_command(type("Args", (), {"packet_id": "pkt_for_ack", "status": "applied", "notes": None, "ref": None})())
            # Default: terminal excluded
            with patch_cli_paths(root), mock.patch("builtins.print") as mock_print:
                cli.inbox_status_command(type("Args", (), {"all": False, "packet_id": None})())
            result = parse_print_json(mock_print)
            self.assertEqual(len(result["packets"]), 0)
            # --all: includes terminal
            with patch_cli_paths(root), mock.patch("builtins.print") as mock_print:
                cli.inbox_status_command(type("Args", (), {"all": True, "packet_id": None})())
            result = parse_print_json(mock_print)
            self.assertEqual(len(result["packets"]), 1)
            self.assertEqual(result["packets"][0]["status"], "applied")

    def test_inbox_ack_applied_outbox(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_local_router_contract(root)
            write_protocol_inbox_packet(root, "pkt_apply", title="Apply Me")
            with patch_cli_paths(root), mock.patch("builtins.print"):
                cli.inbox_intake_command(type("Args", (), {"dry_run": False})())
            with patch_cli_paths(root), mock.patch("builtins.print") as mock_print:
                cli.inbox_ack_command(type("Args", (), {"packet_id": "pkt_apply", "status": "applied", "notes": "Done", "ref": "https://example.com/pr/1"})())
            result = parse_print_json(mock_print)
            self.assertEqual(result["new_status"], "applied")
            # State updated
            state = json.loads((root / "state" / "project_router" / "inbox_status" / "pkt_apply.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "applied")
            # Outbox ack packet generated
            outbox_files = list((root / "router" / "outbox").glob("*--ack_pkt_apply.md"))
            self.assertEqual(len(outbox_files), 1)
            meta, body = cli.read_note(outbox_files[0])
            self.assertEqual(meta["packet_type"], "ack")
            self.assertEqual(meta["related_packet_id"], "pkt_apply")
            self.assertEqual(meta["resolution"], "applied")
            self.assertEqual(meta["implementation_ref"], "https://example.com/pr/1")

    def test_inbox_ack_rejected(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_local_router_contract(root)
            write_protocol_inbox_packet(root, "pkt_reject")
            with patch_cli_paths(root), mock.patch("builtins.print"):
                cli.inbox_intake_command(type("Args", (), {"dry_run": False})())
            with patch_cli_paths(root), mock.patch("builtins.print") as mock_print:
                cli.inbox_ack_command(type("Args", (), {"packet_id": "pkt_reject", "status": "rejected", "notes": "Not relevant", "ref": None})())
            result = parse_print_json(mock_print)
            self.assertEqual(result["new_status"], "rejected")
            outbox_files = list((root / "router" / "outbox").glob("*--ack_pkt_reject.md"))
            self.assertEqual(len(outbox_files), 1)

    def test_inbox_ack_in_progress_no_outbox(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_local_router_contract(root)
            write_protocol_inbox_packet(root, "pkt_wip")
            with patch_cli_paths(root), mock.patch("builtins.print"):
                cli.inbox_intake_command(type("Args", (), {"dry_run": False})())
            with patch_cli_paths(root), mock.patch("builtins.print") as mock_print:
                cli.inbox_ack_command(type("Args", (), {"packet_id": "pkt_wip", "status": "in_progress", "notes": None, "ref": None})())
            result = parse_print_json(mock_print)
            self.assertEqual(result["new_status"], "in_progress")
            state = json.loads((root / "state" / "project_router" / "inbox_status" / "pkt_wip.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "in_progress")
            # No outbox packet for intermediate state
            outbox_files = list((root / "router" / "outbox").glob("*--ack_pkt_wip.md"))
            self.assertEqual(len(outbox_files), 0)

    def test_inbox_ack_blocks_invalid_transition(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_local_router_contract(root)
            write_protocol_inbox_packet(root, "pkt_done")
            with patch_cli_paths(root), mock.patch("builtins.print"):
                cli.inbox_intake_command(type("Args", (), {"dry_run": False})())
            with patch_cli_paths(root), mock.patch("builtins.print"):
                cli.inbox_ack_command(type("Args", (), {"packet_id": "pkt_done", "status": "applied", "notes": None, "ref": None})())
            # Try to re-ack terminal state
            with patch_cli_paths(root):
                with self.assertRaises(SystemExit):
                    cli.inbox_ack_command(type("Args", (), {"packet_id": "pkt_done", "status": "rejected", "notes": None, "ref": None})())

    def test_status_includes_inbox(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            prepare_repo(root)
            write_registry(root)
            write_local_router_contract(root)
            write_protocol_inbox_packet(root, "pkt_status_test")
            with patch_cli_paths(root), mock.patch("builtins.print"):
                cli.inbox_intake_command(type("Args", (), {"dry_run": False})())
            with patch_cli_paths(root), mock.patch("builtins.print") as mock_print:
                cli.status_command(type("Args", (), {"source": None})())
            result = parse_print_json(mock_print)
            self.assertIn("inbox", result)
            self.assertEqual(result["inbox"].get("open", 0), 1)


if __name__ == "__main__":
    unittest.main()
