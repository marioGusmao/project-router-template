from __future__ import annotations

import json
import shutil
import subprocess
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
            router_root = root / "project-router"
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
                    "<!-- repository-mode:begin -->\nTemplate mode.\n<!-- repository-mode:end -->\n",
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


if __name__ == "__main__":
    unittest.main()
