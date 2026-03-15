#!/usr/bin/env python3
"""Promote a derived template copy into a private operational repository."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from knowledge_local_scaffold import SOURCE_ROOT as KNOWLEDGE_TEMPLATE_LOCAL_DIR
from knowledge_local_scaffold import materialize_scaffold


ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"
README_PT_PATH = ROOT / "README.pt-PT.md"
AGENTS_PATH = ROOT / "AGENTS.md"
CLAUDE_PATH = ROOT / "CLAUDE.md"
TEMPLATE_META_PATH = ROOT / "template.meta.json"
TEMPLATE_BASE_PATH = ROOT / "template-base.json"
PRIVATE_META_PATH = ROOT / "private.meta.json"

MARKER_NAME = "repository-mode"
ONBOARDING_MARKER_NAME = "template-onboarding"
CONTRACT_MARKER_NAME = "customization-contract"
SYNC_BRANCH = "chore/template-sync"
SYNC_WORKFLOW_PATH = ".github/workflows/template-upstream-sync.yml"
PROMOTION_COMMAND = "python3 scripts/bootstrap_private_repo.py"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--template-repo",
        help="GitHub repository slug for the shared upstream template (OWNER/REPO).",
    )
    parser.add_argument(
        "--private-repo-name",
        help="Name for the derived private repository. Defaults to the current repo name.",
    )
    parser.add_argument(
        "--template-commit",
        help="Template commit SHA to record in template-base.json. Defaults to the current HEAD when available.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow promotion even when the current origin remote still matches the template upstream.",
    )
    return parser.parse_args(argv)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def git_output(*args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except FileNotFoundError:
        print(f"WARNING: git is not installed — cannot run 'git {' '.join(args)}'", file=sys.stderr)
        return None
    except subprocess.CalledProcessError:
        return None


def parse_github_repo_slug(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.strip()
    if re.fullmatch(r"[^/\s]+/[^/\s]+", value):
        return value
    match = re.search(r"github\.com[:/](?P<slug>[^/\s]+/[^/\s]+?)(?:\.git)?$", value)
    if match:
        return match.group("slug")
    return None


def current_origin_repo_slug() -> str | None:
    return parse_github_repo_slug(git_output("config", "--get", "remote.origin.url"))


def replace_managed_block(path: Path, replacement: str, marker_name: str = MARKER_NAME) -> None:
    start_marker = f"<!-- {marker_name}:begin -->"
    end_marker = f"<!-- {marker_name}:end -->"
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"Managed block {marker_name!r} not found in {path}.")
    managed_block = f"{start_marker}\n{replacement.rstrip()}\n{end_marker}"
    path.write_text(pattern.sub(lambda _: managed_block, text, count=1), encoding="utf-8")


def resolve_template_metadata() -> dict[str, Any]:
    if not TEMPLATE_META_PATH.exists():
        raise SystemExit(f"Missing template metadata file: {TEMPLATE_META_PATH}")
    template_meta = read_json(TEMPLATE_META_PATH)
    if not template_meta.get("version"):
        raise SystemExit("template.meta.json must define a version before a private repo can be promoted.")
    return template_meta


def resolve_template_repo(args: argparse.Namespace, template_meta: dict[str, Any]) -> str:
    candidates = [
        args.template_repo,
        (read_json(TEMPLATE_BASE_PATH).get("template_repo") if TEMPLATE_BASE_PATH.exists() else None),
        template_meta.get("template_repo"),
    ]
    for candidate in candidates:
        slug = parse_github_repo_slug(str(candidate) if candidate else None)
        if slug:
            return slug
    raise SystemExit(
        "Template upstream repository is unknown. Set template.meta.json.template_repo or pass --template-repo OWNER/REPO."
    )


def resolve_private_repo_name(args: argparse.Namespace, template_repo: str) -> str:
    if args.private_repo_name:
        return args.private_repo_name.strip()
    origin_slug = current_origin_repo_slug()
    if origin_slug and origin_slug != template_repo:
        return origin_slug.split("/", 1)[1]
    return ROOT.name


def build_private_meta(
    *,
    template_meta: dict[str, Any],
    template_repo: str,
    private_repo_name: str,
    promoted_at: str,
) -> dict[str, Any]:
    existing = read_json(PRIVATE_META_PATH) if PRIVATE_META_PATH.exists() else {}
    payload = dict(existing)
    payload.update(
        {
            "repo_role": "private-derived",
            "private_repo_name": private_repo_name,
            "derived_from_template": template_meta.get("template_name", "project-router-template"),
            "template_repo": template_repo,
            "template_version_at_promotion": template_meta.get("version"),
            "promotion_script": PROMOTION_COMMAND,
            "promoted_at": existing.get("promoted_at") or promoted_at,
            "last_promoted_at": promoted_at,
            "upstream_sync_branch": SYNC_BRANCH,
            "upstream_sync_workflow": SYNC_WORKFLOW_PATH,
        }
    )
    return payload


def build_template_base(
    *,
    template_meta: dict[str, Any],
    template_repo: str,
    template_commit: str,
    timestamp: str,
) -> dict[str, Any]:
    existing = read_json(TEMPLATE_BASE_PATH) if TEMPLATE_BASE_PATH.exists() else {}
    version = str(template_meta.get("version") or "")
    tag = f"v{version}" if version else ""
    payload = dict(existing)
    payload.update(
        {
            "template_repo": template_repo,
            "template_base_version": version,
            "template_base_tag": tag,
            "template_base_commit": template_commit,
            "last_template_sync_at": timestamp,
        }
    )
    return payload


def private_readme_block(template_name: str, template_repo: str) -> str:
    return (
        f"This repository is a private operational Project Router repo for VoiceNotes derived from the shared `{template_name}` "
        f"upstream.\n\n"
        f"The upstream relationship is tracked in `private.meta.json` and `template-base.json`, and updates from "
        f"`{template_repo}` should arrive through reviewed `{SYNC_BRANCH}` pull requests rather than manual copy-paste."
    )


def private_readme_pt_block(template_name: str, template_repo: str) -> str:
    return (
        f"Este repositório é um repositório operacional privado do Project Router for VoiceNotes derivado do upstream "
        f"partilhado `{template_name}`.\n\n"
        f"A relação com o upstream fica registada em `private.meta.json` e `template-base.json`, e as atualizações de "
        f"`{template_repo}` devem entrar por pull requests revistos na branch `{SYNC_BRANCH}`, não por copy-paste manual."
    )


def private_agents_block(template_name: str, template_repo: str) -> str:
    return (
        "## Repository Mode\n"
        f"- Current mode: private derived repository.\n"
        f"- Treat this repository as the operational home for private routing packs, branded docs, and project wording.\n"
        f"- Keep the upstream link to `{template_name}` via `private.meta.json` and `template-base.json`.\n"
        f"- Pull shared updates from `{template_repo}` through reviewed `{SYNC_BRANCH}` pull requests, not by rewriting "
        "private-owned or local-only files by hand."
    )


def private_claude_block(template_name: str, template_repo: str) -> str:
    return (
        "## Repository Mode\n\n"
        "- Current role: private derived repository.\n"
        "- This copy is the operational home for private routing packs, branded wording, and day-to-day note handling.\n"
        f"- Keep the upstream relationship to `{template_name}` in `private.meta.json` and `template-base.json`.\n"
        f"- Expect shared updates from `{template_repo}` to arrive via reviewed `{SYNC_BRANCH}` pull requests."
    )


def private_onboarding_block() -> str:
    return (
        "## Private Repo First Steps\n\n"
        "If this is a private-derived operational copy:\n\n"
        "1. Run `python3 scripts/bootstrap_local.py`.\n"
        "2. Run `python3 scripts/project_router.py context`.\n"
        "3. Review `Knowledge/local/Roadmap.md` and adapt it to your project.\n"
    )


def private_onboarding_pt_block() -> str:
    return (
        "## Primeiros Passos No Repositório Privado\n\n"
        "Se esta cópia já é um repositório operacional privado derivado:\n\n"
        "1. Corre `python3 scripts/bootstrap_local.py`.\n"
        "2. Corre `python3 scripts/project_router.py context`.\n"
        "3. Revê `Knowledge/local/Roadmap.md` e adapta-o ao teu projeto.\n"
    )


def seed_private_knowledge_local() -> list[str]:
    if not KNOWLEDGE_TEMPLATE_LOCAL_DIR.exists():
        raise SystemExit(f"Missing Knowledge scaffold source: {KNOWLEDGE_TEMPLATE_LOCAL_DIR}")
    return materialize_scaffold(ROOT, overwrite=False)["created"]


def promote_repository(args: argparse.Namespace) -> dict[str, Any]:
    template_meta = resolve_template_metadata()
    template_repo = resolve_template_repo(args, template_meta)
    origin_slug = current_origin_repo_slug()
    if origin_slug == template_repo and not args.force:
        raise SystemExit(
            "Current origin remote still points to the template upstream. Run this in a derived repository, or pass --force if that is intentional."
        )

    # Pre-validate: all target files and managed block markers must exist before any mutations
    required_files = [README_PATH, README_PT_PATH, AGENTS_PATH, CLAUDE_PATH]
    missing = [str(p) for p in required_files if not p.exists()]
    if missing:
        raise SystemExit(f"Cannot promote: missing required files: {', '.join(missing)}")
    marker_checks = [
        (README_PATH, MARKER_NAME),
        (README_PT_PATH, MARKER_NAME),
        (AGENTS_PATH, MARKER_NAME),
        (CLAUDE_PATH, MARKER_NAME),
        (README_PATH, ONBOARDING_MARKER_NAME),
        (README_PT_PATH, ONBOARDING_MARKER_NAME),
        (AGENTS_PATH, CONTRACT_MARKER_NAME),
        (CLAUDE_PATH, CONTRACT_MARKER_NAME),
    ]
    missing_markers = []
    for path, marker in marker_checks:
        text = path.read_text(encoding="utf-8")
        start_marker = f"<!-- {marker}:begin -->"
        end_marker = f"<!-- {marker}:end -->"
        if start_marker not in text:
            missing_markers.append(f"{path.name} ({marker} begin)")
        if end_marker not in text:
            missing_markers.append(f"{path.name} ({marker} end)")
    if missing_markers:
        raise SystemExit(f"Cannot promote: missing managed block markers: {', '.join(missing_markers)}")

    promoted_at = iso_now()
    private_repo_name = resolve_private_repo_name(args, template_repo)
    template_commit = args.template_commit or git_output("rev-parse", "HEAD") or ""

    replace_managed_block(
        README_PATH,
        private_readme_block(str(template_meta.get("template_name", ROOT.name)), template_repo),
    )
    replace_managed_block(
        README_PT_PATH,
        private_readme_pt_block(str(template_meta.get("template_name", ROOT.name)), template_repo),
    )
    replace_managed_block(
        AGENTS_PATH,
        private_agents_block(str(template_meta.get("template_name", ROOT.name)), template_repo),
    )
    replace_managed_block(
        CLAUDE_PATH,
        private_claude_block(str(template_meta.get("template_name", ROOT.name)), template_repo),
    )
    replace_managed_block(
        README_PATH,
        private_onboarding_block(),
        marker_name=ONBOARDING_MARKER_NAME,
    )
    replace_managed_block(
        README_PT_PATH,
        private_onboarding_pt_block(),
        marker_name=ONBOARDING_MARKER_NAME,
    )

    write_json(
        PRIVATE_META_PATH,
        build_private_meta(
            template_meta=template_meta,
            template_repo=template_repo,
            private_repo_name=private_repo_name,
            promoted_at=promoted_at,
        ),
    )
    write_json(
        TEMPLATE_BASE_PATH,
        build_template_base(
            template_meta=template_meta,
            template_repo=template_repo,
            template_commit=template_commit,
            timestamp=promoted_at,
        ),
    )

    # Seed Knowledge/local/ scaffold (always non-destructive, regardless of --force)
    seeded_files = seed_private_knowledge_local()

    files_updated = [
        str(path.relative_to(ROOT))
        for path in (
            README_PATH,
            README_PT_PATH,
            AGENTS_PATH,
            CLAUDE_PATH,
            PRIVATE_META_PATH,
            TEMPLATE_BASE_PATH,
        )
    ]
    files_updated.extend(seeded_files)

    return {
        "private_repo_name": private_repo_name,
        "template_repo": template_repo,
        "template_version": template_meta.get("version"),
        "files_updated": files_updated,
        "next_steps": [
            "Review the tracked docs and metadata changes.",
            "Run python3 scripts/bootstrap_local.py for machine-local config.",
            "Run python3 -m pytest tests/test_project_router.py -v.",
            "Run python3 scripts/check_agent_surface_parity.py.",
            "Run python3 scripts/check_repo_ownership.py.",
            "Run python3 scripts/check_sync_manifest_alignment.py.",
            "Run python3 scripts/check_customization_contracts.py.",
            "Customize Knowledge/local/Roadmap.md for your project roadmap.",
            "Run python3 scripts/refresh_knowledge_local.py.",
            "Run python3 scripts/check_managed_blocks.py.",
            "Run python3 scripts/check_knowledge_structure.py.",
            "Run python3 scripts/check_adr_related_links.py.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = promote_repository(args)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
