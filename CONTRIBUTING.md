# Contributing

Thanks for contributing to Project Router Template.

This repository is the shareable template upstream for the workflow. Please keep contributions neutral, reusable, and safe for a public GitHub template.

## What To Contribute

- Bug fixes in the CLI, sync client, tests, docs, and governance tooling
- Improvements to neutral routing examples and contributor documentation
- Improvements to agent-surface parity and template safety checks
- Small, reviewable pull requests with clear intent

## What Not To Commit

- `.env.local`
- `projects/registry.local.json`
- `data/`
- `state/`
- Real VoiceNotes exports, transcripts, compiled notes, or downstream inbox paths
- Personal or branded project-specific routing packs that belong in a private derived repo

## Before Opening A Pull Request

Run the relevant checks locally:

```bash
python3 scripts/check_agent_surface_parity.py --pre-publish
python3 scripts/check_repo_ownership.py
python3 -m pytest tests/test_project_router.py -q
```

If your change affects workflow documentation, skills, or safety rules, keep the `.agents/`, `.codex/skills/`, and `.claude/skills/` surfaces aligned.

## Pull Request Guidelines

- Open the PR from a branch or fork; do not target `main` with direct pushes
- Use a focused Conventional Commit-style title when possible, such as `fix:`, `docs:`, `test:`, or `chore:`
- Explain the problem, the proposed change, and how you validated it
- Call out any follow-up work or known limitations

## Safety Rules For Contributors

- Never auto-dispatch notes
- Never delete or overwrite canonical raw JSON
- Never commit local secrets or runtime artifacts
- Never change the public template to depend on personal machine paths
- Keep local/private behavior in derived repositories, not in this upstream template

## Reporting Ideas Without Code

If you do not want to open a pull request, open an issue with:

- the current behavior
- the proposed improvement
- any relevant logs, failing commands, or reproduction steps

That is enough for maintainers to triage the request.
