from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_TMP_ROOT = REPO_ROOT / ".tmp-tests"
TEST_TMP_ROOT.mkdir(exist_ok=True)


def temporary_repo_dir():
    return tempfile.TemporaryDirectory(dir=TEST_TMP_ROOT)


def copy_scripts(root: Path, *script_names: str) -> None:
    scripts_dir = root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    for name in script_names:
        shutil.copy2(REPO_ROOT / "scripts" / name, scripts_dir / name)


def write_manifest(root: Path, rules: list[dict[str, str]]) -> None:
    governance_dir = root / "repo-governance"
    governance_dir.mkdir(parents=True, exist_ok=True)
    (governance_dir / "ownership.manifest.json").write_text(
        json.dumps(
            {
                "classes": {
                    "template_owned": "template",
                    "private_owned": "private",
                    "shared_review": "review",
                    "local_only": "local",
                },
                "rules": rules,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_contracts(root: Path, surfaces: list[dict[str, object]]) -> None:
    governance_dir = root / "repo-governance"
    governance_dir.mkdir(parents=True, exist_ok=True)
    (governance_dir / "customization-contracts.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "surfaces": surfaces,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def init_git_repo(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, capture_output=True, text=True, check=True)
    subprocess.run(["git", "config", "user.email", "tests@example.com"], cwd=root, capture_output=True, text=True, check=True)
    subprocess.run(["git", "config", "user.name", "Template Tests"], cwd=root, capture_output=True, text=True, check=True)


class TemplateGovernanceTests(unittest.TestCase):
    def test_shared_surfaces_state_downstream_read_only_default(self) -> None:
        agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
        claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        session_opener = (REPO_ROOT / ".agents" / "skills" / "project-router-session-opener" / "SKILL.md").read_text(encoding="utf-8")
        inbox_consumer = (REPO_ROOT / ".agents" / "skills" / "project-router-inbox-consumer" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("read-only by default", agents)
        self.assertIn("project-router` inbox/outbox", agents)
        self.assertIn("read-only by default", claude)
        self.assertIn("project-router` inbox/outbox", claude)
        self.assertIn("read-only by default", session_opener)
        self.assertIn("project-router` inbox/outbox", session_opener)
        self.assertIn("read-only by default", inbox_consumer)
        self.assertIn("project-router` inbox/outbox", inbox_consumer)

    def test_workflow_uses_runner_temp_for_diff_only_output(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "template-upstream-sync.yml").read_text(encoding="utf-8")
        self.assertIn("$RUNNER_TEMP/template-sync-diffs.diff", workflow)
        self.assertNotIn(": > sync-diffs.txt", workflow)
        self.assertIn("render_template_sync_pr_body.py", workflow)
        self.assertIn("--body-file", workflow)

    def test_render_template_sync_pr_body_includes_diff_section_only_when_needed(self) -> None:
        script = REPO_ROOT / "scripts" / "render_template_sync_pr_body.py"
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            diff_file = root / "diff.patch"
            output = root / "body.md"

            diff_file.write_text("", encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
                    str(script),
                    "--release-tag",
                    "v1.2.3",
                    "--release-url",
                    "https://example.test/release",
                    "--diff-file",
                    str(diff_file),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            body = output.read_text(encoding="utf-8")
            self.assertIn("Template upstream update from [v1.2.3](https://example.test/release).", body)
            self.assertNotIn("## Diff-only review", body)

            diff_file.write_text("--- a/.gitignore\n+++ b/.gitignore\n@@ -1 +1 @@\n-old\n+new\n", encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
                    str(script),
                    "--release-tag",
                    "v1.2.3",
                    "--release-url",
                    "https://example.test/release",
                    "--diff-file",
                    str(diff_file),
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            body = output.read_text(encoding="utf-8")
            self.assertIn("## Diff-only review", body)
            self.assertIn("```diff", body)
            self.assertIn("+++ b/.gitignore", body)

    def test_check_sync_manifest_alignment_requires_contract_registry_coverage(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            copy_scripts(root, "check_repo_ownership.py", "check_sync_manifest_alignment.py")
            init_git_repo(root)
            (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            (root / ".github" / "workflows" / "template-upstream-sync.yml").write_text(
                textwrap.dedent(
                    """
                    name: sync
                    jobs:
                      sync:
                        steps:
                          - run: |
                              overwrite_paths=(
                                src
                                .github/ISSUE_TEMPLATE
                              )
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            write_manifest(
                root,
                [
                    {"pattern": "src/**", "ownership": "template_owned", "sync_policy": "template_sync"},
                    {"pattern": ".github/ISSUE_TEMPLATE/**", "ownership": "shared_review", "sync_policy": "review_required"},
                ],
            )
            write_contracts(
                root,
                [
                    {
                        "pattern": "src/**",
                        "ownership": "template_owned",
                        "sync_policy": "template_sync",
                        "customization_model": "overwrite",
                        "private_overlay": None,
                        "bootstrap_source": None,
                        "agent_load_rule": None,
                        "migration_policy": "silent_ok",
                        "validator_hooks": [],
                    },
                ],
            )
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, capture_output=True, text=True, check=True)
            result = subprocess.run(
                ["python3", str(root / "scripts" / "check_sync_manifest_alignment.py")],
                cwd=root,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Sync path missing from customization contract registry: .github/ISSUE_TEMPLATE", result.stderr)

    def test_check_sync_manifest_alignment_requires_workflow_coverage_for_tracked_synced_files(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            copy_scripts(root, "check_repo_ownership.py", "check_sync_manifest_alignment.py")
            init_git_repo(root)
            (root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
            (root / ".github" / "workflows" / "template-upstream-sync.yml").write_text(
                textwrap.dedent(
                    """
                    name: sync
                    jobs:
                      sync:
                        steps:
                          - run: |
                              overwrite_paths=(
                                src
                              )
                              managed_block_files=(
                                README.md
                              )
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )
            write_manifest(
                root,
                [
                    {"pattern": "src/**", "ownership": "template_owned", "sync_policy": "template_sync"},
                    {"pattern": "README.md", "ownership": "shared_review", "sync_policy": "review_required"},
                    {"pattern": "requirements-extractors.txt", "ownership": "template_owned", "sync_policy": "template_sync"},
                ],
            )
            write_contracts(
                root,
                [
                    {
                        "pattern": "src/**",
                        "ownership": "template_owned",
                        "sync_policy": "template_sync",
                        "customization_model": "overwrite",
                        "private_overlay": None,
                        "bootstrap_source": None,
                        "agent_load_rule": None,
                        "migration_policy": "silent_ok",
                        "validator_hooks": [],
                    },
                    {
                        "pattern": "README.md",
                        "ownership": "shared_review",
                        "sync_policy": "review_required",
                        "customization_model": "managed_blocks",
                        "private_overlay": None,
                        "bootstrap_source": None,
                        "agent_load_rule": None,
                        "migration_policy": "review_required",
                        "validator_hooks": [],
                    },
                    {
                        "pattern": "requirements-extractors.txt",
                        "ownership": "template_owned",
                        "sync_policy": "template_sync",
                        "customization_model": "overwrite",
                        "private_overlay": None,
                        "bootstrap_source": None,
                        "agent_load_rule": None,
                        "migration_policy": "silent_ok",
                        "validator_hooks": [],
                    },
                ],
            )
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "README.md").write_text("# Readme\n", encoding="utf-8")
            (root / "requirements-extractors.txt").write_text("pymupdf>=1.24.0\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, capture_output=True, text=True, check=True)
            result = subprocess.run(
                ["python3", str(root / "scripts" / "check_sync_manifest_alignment.py")],
                cwd=root,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "Tracked synced file is not covered by workflow sync paths: requirements-extractors.txt",
                result.stderr,
            )

    def test_check_customization_contracts_fails_on_rejects_and_conflict_markers(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            copy_scripts(root, "check_repo_ownership.py", "check_customization_contracts.py")
            (root / "README.md").write_text(
                "<<<<<<< HEAD\nlocal\n=======\nupstream\n>>>>>>> branch\n",
                encoding="utf-8",
            )
            (root / "broken.patch.rej").write_text("reject", encoding="utf-8")
            write_manifest(
                root,
                [
                    {"pattern": "README.md", "ownership": "shared_review", "sync_policy": "review_required"},
                ],
            )
            write_contracts(
                root,
                [
                    {
                        "pattern": "README.md",
                        "ownership": "shared_review",
                        "sync_policy": "review_required",
                        "customization_model": "managed_blocks",
                        "private_overlay": None,
                        "bootstrap_source": None,
                        "agent_load_rule": None,
                        "migration_policy": "review_required",
                        "validator_hooks": [],
                    },
                ],
            )
            result = subprocess.run(
                ["python3", str(root / "scripts" / "check_customization_contracts.py")],
                cwd=root,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("README.md: contains unresolved git conflict markers", result.stderr)
            self.assertIn("broken.patch.rej: reject artifact must be resolved before merge", result.stderr)

    def test_check_customization_contracts_enforces_release_notes_for_changed_paths(self) -> None:
        with temporary_repo_dir() as tmp:
            root = Path(tmp)
            copy_scripts(root, "check_repo_ownership.py", "check_customization_contracts.py")
            scripts_dir = root / "scripts"
            scripts_dir.mkdir(exist_ok=True)
            (scripts_dir / "do_work.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
            write_manifest(
                root,
                [
                    {"pattern": "scripts/**", "ownership": "template_owned", "sync_policy": "template_sync"},
                    {"pattern": "CHANGELOG.md", "ownership": "template_owned", "sync_policy": "template_sync"},
                ],
            )
            write_contracts(
                root,
                [
                    {
                        "pattern": "scripts/**",
                        "ownership": "template_owned",
                        "sync_policy": "template_sync",
                        "customization_model": "overwrite",
                        "private_overlay": None,
                        "bootstrap_source": None,
                        "agent_load_rule": None,
                        "migration_policy": "requires_release_note",
                        "validator_hooks": [],
                    },
                    {
                        "pattern": "CHANGELOG.md",
                        "ownership": "template_owned",
                        "sync_policy": "template_sync",
                        "customization_model": "overwrite",
                        "private_overlay": None,
                        "bootstrap_source": None,
                        "agent_load_rule": None,
                        "migration_policy": "silent_ok",
                        "validator_hooks": [],
                    },
                ],
            )
            result = subprocess.run(
                [
                    "python3",
                    str(root / "scripts" / "check_customization_contracts.py"),
                    "--changed-path",
                    "scripts/do_work.py",
                ],
                cwd=root,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Changed paths require a CHANGELOG.md update: scripts/**", result.stderr)

            result = subprocess.run(
                [
                    "python3",
                    str(root / "scripts" / "check_customization_contracts.py"),
                    "--changed-path",
                    "scripts/do_work.py",
                    "--changed-path",
                    "CHANGELOG.md",
                ],
                cwd=root,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
