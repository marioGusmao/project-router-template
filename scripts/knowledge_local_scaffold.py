#!/usr/bin/env python3
"""Shared helpers for the Knowledge/local scaffold."""

from __future__ import annotations

from dataclasses import dataclass
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "Knowledge" / "Templates" / "local"
TARGET_ROOT = ROOT / "Knowledge" / "local"


@dataclass(frozen=True)
class ScaffoldComparison:
    rel_path: str
    status: str


def compare_scaffold(repo_root: Path = ROOT) -> list[ScaffoldComparison]:
    source_root = repo_root / "Knowledge" / "Templates" / "local"
    target_root = repo_root / "Knowledge" / "local"
    if not source_root.exists():
        raise FileNotFoundError(f"Missing Knowledge scaffold source: {source_root}")

    results: list[ScaffoldComparison] = []
    for source in sorted(source_root.rglob("*")):
        if source.is_dir():
            continue
        rel_path = source.relative_to(source_root).as_posix()
        target = target_root / rel_path
        if not target.exists():
            status = "missing"
        elif target.read_bytes() == source.read_bytes():
            status = "same"
        else:
            status = "different"
        results.append(ScaffoldComparison(rel_path=rel_path, status=status))
    return results


def materialize_scaffold(
    repo_root: Path = ROOT,
    *,
    overwrite: bool = False,
) -> dict[str, list[str]]:
    source_root = repo_root / "Knowledge" / "Templates" / "local"
    target_root = repo_root / "Knowledge" / "local"
    if not source_root.exists():
        raise FileNotFoundError(f"Missing Knowledge scaffold source: {source_root}")

    created: list[str] = []
    updated: list[str] = []
    skipped: list[str] = []

    for source in sorted(source_root.rglob("*")):
        relative = source.relative_to(source_root)
        target = target_root / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(source, target)
            created.append(str(target.relative_to(repo_root)))
            continue

        if target.read_bytes() == source.read_bytes():
            continue

        if overwrite:
            shutil.copy2(source, target)
            updated.append(str(target.relative_to(repo_root)))
        else:
            skipped.append(str(target.relative_to(repo_root)))

    return {"created": created, "updated": updated, "skipped": skipped}
