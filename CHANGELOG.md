# Changelog

All notable changes to the shared Project Router starter will be documented in this file.

## Unreleased

- Fixed template sync diff-only handling so review output lives outside the repo and is rendered in the sync PR body.
- Tightened contract validation with conflict-marker detection, reject-file detection, and release-note enforcement for upgrade-governance surfaces.
- Added regression tests for template sync governance tooling.

## 0.1.0 - 2026-03-12

- Split the repository model into a neutral template upstream and a private daily repo.
- Added registry overlay support with candidate-level dispatch validation.
- Moved the VoiceNotes API client into `src/project_router/sync_client.py`.
- Added bootstrap, parity, and ownership governance tooling.
