from __future__ import annotations

import json
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
        root / "data" / "normalized" / "voicenotes",
        root / "data" / "normalized" / "project_router",
        root / "data" / "compiled" / "voicenotes",
        root / "data" / "compiled" / "project_router",
        root / "data" / "review" / "voicenotes" / "ambiguous",
        root / "data" / "review" / "voicenotes" / "needs_review",
        root / "data" / "review" / "voicenotes" / "pending_project",
        root / "data" / "review" / "project_router" / "parse_errors",
        root / "data" / "review" / "project_router" / "needs_review",
        root / "data" / "review" / "project_router" / "pending_project",
        root / "data" / "dispatched",
        root / "data" / "processed",
        root / "projects",
        root / "state" / "decisions",
        root / "state" / "discoveries",
        root / "state" / "project_router",
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
        "DISCOVERY_REPORT_PATH": state / "discoveries" / "pending_project_latest.json",
        "REGISTRY_LOCAL_PATH": root / "projects" / "registry.local.json",
        "REGISTRY_SHARED_PATH": root / "projects" / "registry.shared.json",
        "REGISTRY_EXAMPLE_PATH": root / "projects" / "registry.example.json",
        "ENV_LOCAL_PATH": root / ".env.local",
        "ENV_PATH": root / ".env",
        "LOCAL_ROUTER_DIR": root / "project-router",
    }
    for key, value in patches.items():
        stack.enter_context(mock.patch.object(cli, key, value))
    return stack


def write_registry(root: Path, *, include_router_root: bool = True) -> Path:
    shared = {
        "defaults": {"auto_dispatch_threshold": 0.9, "min_keyword_hits": 2},
        "projects": {
            "home_renovation": {
                "display_name": "Home Renovation",
                "language": "en",
                "note_type": "project-idea",
                "auto_dispatch_threshold": 0.9,
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
            self.assertEqual(metadata["raw_payload_path"], str(raw_path))
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
            router_root = root / "project-router"
            write_router_contract(router_root, project_key="project_router_template")
            write_outbox_packet(router_root, "self_pkt", "# Self\n\nBody\n", project_key="project_router_template")
            with patch_cli_paths(root):
                cli.scan_outboxes_command(type("Args", (), {"include_self": True, "strict": False})())
            raw_path = root / "data" / "raw" / "project_router" / "project_router_template" / "20260313T100000Z--self_pkt.json"
            self.assertTrue(raw_path.exists())


if __name__ == "__main__":
    unittest.main()
