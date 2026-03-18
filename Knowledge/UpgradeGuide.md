# Template Upgrade Guide

How to receive, review, and merge template upstream updates in your private derived repository.

For the ownership model and surface table, see [CustomizationContract.md](CustomizationContract.md). For the architectural rationale, see [ADR-006](ADR/006-template-upgrade-process.md).

## Recognizing Updates

Template updates arrive as **draft pull requests** on the `chore/template-sync` branch. The workflow runs weekly (Monday 9am UTC) or on manual dispatch.

The PR title includes the upstream release tag, for example: `chore(template-sync): update template to project-router-template-v0.6.0`.

## What the Sync Does

The workflow uses a 7-step approach (passes 0 through 5, including a 0.5 backup step):

1. **Pass 0 — Migrate:** Inserts `customization-contract` markers if missing (for old repos).
2. **Pass 0.5 — Backup:** Saves a copy of CLAUDE.md and AGENTS.md before overwrite so the contract blocks can be restored later.
3. **Pass 1 — Overwrite:** Replaces `template_owned` paths and AI files with upstream content.
4. **Pass 2 — Restore:** Restores the `customization-contract` block in CLAUDE.md and AGENTS.md from the pre-overwrite backup (preserving your `@import` references).
5. **Pass 3 — Managed blocks:** Updates content inside `repository-mode` and `template-onboarding` markers in README files, preserving your branding and content outside the markers.
6. **Pass 4 — Extensible:** Syncs skill directories without deleting your local additions.
7. **Pass 5 — Diff-only:** Generates diffs for `.gitignore`, `CONTRIBUTING.md`, and `.github/pull_request_template.md`, then renders them into the PR body for manual review.

## Merging the Sync PR

1. **Review the PR diff.** Focus on:
   - Safety Rules changes (always accept — they are authoritative).
   - New commands or conventions in CLAUDE.md/AGENTS.md.
   - New or modified scripts under `scripts/`.
   - New ADRs under `Knowledge/ADR/`.
   - When crossing from pre-`v0.5.x` derived repos, verify tracked root-file migrations landed in the PR (for example `VERSION` to `version.txt`, plus new files such as `requirements-extractors.txt`).

2. **Check the diff-only section.** Review the `Diff-only review` section in the PR body for `.gitignore`, `CONTRIBUTING.md`, and `.github/pull_request_template.md`.

3. **Merge the PR.** The draft PR is ready to merge when you are satisfied with the changes.

4. **After merging**, run:
   ```bash
   python3 scripts/refresh_knowledge_local.py --apply-missing
   python3 scripts/check_customization_contracts.py
   python3 -m pytest tests/test_project_router.py -v
   ```

## Resolving Conflicts

Conflicts are rare because of the surface-aware sync model:
- **AI files (CLAUDE.md, AGENTS.md):** Full overwrite + contract restore means no merge conflicts. If your `customization-contract` block was modified, the local version is preserved.
- **README managed blocks:** Content inside markers is replaced; content outside is yours. Conflicts only arise if you edited inside a managed block.
- **Skill directories:** No conflicts — rsync without `--delete` only adds/updates.
- **Overwrite paths:** No conflicts — full replacement.

If a conflict does occur:
1. Keep the upstream version of managed/overwrite content.
2. Move your customizations to the appropriate overlay (`Knowledge/local/AI/`, local skill additions, etc.).
3. Run `check_managed_blocks.py` to verify marker integrity.

## Rollback

If a sync PR introduces issues after merging:

```bash
git revert <merge-commit-sha>
```

This reverts the sync cleanly. Your private content in `Knowledge/local/` is unaffected.

## Branch Protection

For `shared_review` to provide real protection, enable branch protection on `main`:
- Require PR reviews before merging.
- Require status checks to pass (CI jobs).
- Do not allow direct pushes.

This is a user responsibility — the template cannot enforce GitHub repository settings from `doctor`, so configure these protections directly in GitHub.

## Prerequisites

- The repository must have been promoted with `bootstrap_private_repo.py`.
- `template-base.json` must exist with a valid `template_repo` slug.
- The `TEMPLATE_UPSTREAM_TOKEN` secret (or default `github.token`) must have read access to the upstream repository releases API.
