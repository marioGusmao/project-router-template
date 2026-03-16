# Project Router Interface

This directory is the local repository-facing contract for Project Router.

## Structure

- `router-contract.json`: minimal protocol declaration for this repository
- `inbox/`: packets intended for this repository
- `outbox/`: packets authored by this repository for Project Router to ingest
- `conformance/`: example packets used by `python3 scripts/project_router.py doctor`

## Rules

- Keep authored packets in `outbox/` as Markdown files with YAML frontmatter.
- Use `{created_at}--{packet_id}.md` filenames.
- Do not place generated runtime artifacts here.
- `doctor` validates the structure and packet schema without mutating files.
