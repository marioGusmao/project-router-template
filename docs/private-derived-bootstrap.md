# Private Derived Repo Bootstrap

Use this flow after creating a new repository from the public template and before adding private routing packs or branded operational wording.

## Goal

Promote a fresh derived copy into a private operational repository without weakening the neutral upstream template.

## Command

```bash
python3 scripts/bootstrap_private_repo.py
```

Optional flags:

- `--template-repo OWNER/REPO` to override the upstream template slug
- `--private-repo-name my-private-repo` to override the derived repo name stored in metadata
- `--template-commit <sha>` to pin a specific template commit in `template-base.json`
- `--force` to allow promotion even when the current `origin` still points at the template upstream

## What It Changes

- rewrites the managed `repository-mode` block in `README.md`
- rewrites the managed `repository-mode` block in `README.pt-PT.md`
- rewrites the managed `template-onboarding` block in `README.md`
- rewrites the managed `template-onboarding` block in `README.pt-PT.md`
- rewrites the managed `repository-mode` block in `AGENTS.md`
- rewrites the managed `repository-mode` block in `CLAUDE.md`
- creates or updates `private.meta.json`
- creates or updates `template-base.json`
- materializes `Knowledge/local/` from `Knowledge/Templates/local/` when files are missing

The script does not touch:

- `.env.local`
- `projects/registry.local.json`
- `data/`
- `state/`
- downstream repositories

## Generated Metadata

`private.meta.json` records that the repository is now the private operational home and keeps the promotion timestamp plus sync workflow references.

`template-base.json` records the template upstream slug, version, tag, commit, and last sync timestamp so `.github/workflows/template-upstream-sync.yml` can resolve the upstream release source.

## Recommended Follow-Up

```bash
python3 scripts/bootstrap_local.py
python3 scripts/refresh_knowledge_local.py
python3 -m pytest tests/test_project_router.py -v
python3 scripts/check_agent_surface_parity.py
python3 scripts/check_repo_ownership.py
python3 scripts/check_sync_manifest_alignment.py
python3 scripts/check_managed_blocks.py
python3 scripts/check_customization_contracts.py
python3 scripts/check_knowledge_structure.py
python3 scripts/check_adr_related_links.py
```

After that, customize `projects/registry.shared.json` and private docs according to the ownership manifest.
Private operating rules live in `Knowledge/local/AI/` (loaded via `@import` in CLAUDE.md and prose in AGENTS.md).
Local skill additions in `.claude/skills/`, `.codex/skills/`, or `.agents/skills/` are preserved during sync but do not require parity mirroring across surfaces.
Then adapt `Knowledge/local/Roadmap.md` and add any project-specific ADRs under `Knowledge/local/ADR/`.
