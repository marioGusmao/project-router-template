# Project Router Interface

This directory is the local repository-facing contract for Project Router.

## Structure

| Surface | Purpose | Committed |
|---------|---------|-----------|
| `router-contract.json` | Protocol declaration (schema version, project key, supported packet types) | Yes |
| `inbox/` | Packets intended for this repository, awaiting consumption | No (gitignored) |
| `outbox/` | Packets authored by this repository for Project Router to ingest | No (gitignored) |
| `archive/` | Preserved originals of consumed inbox packets | No (gitignored, local-only) |
| `conformance/` | Example packets used by `doctor` for validation | Yes |

## Consumption Lifecycle

Packets arrive in `inbox/` via dispatch from the central router. The consumption flow is:

```
inbox/ → inbox-intake → archive/ + state/
                          ↓
                    inbox-status (review)
                          ↓
                    inbox-ack (decide)
                          ↓ (terminal states only)
                    outbox/ (ack packet)
```

### Status transitions

```
open → in_progress → applied | blocked | rejected
```

- `open`: packet ingested, awaiting review.
- `in_progress`: work underway, no outbox packet yet.
- `applied`: changes implemented — ack packet emitted to `outbox/`.
- `blocked`: cannot proceed — ack packet emitted with reason.
- `rejected`: not applicable — ack packet emitted with reason.

## Packet Format

All packets are Markdown files with YAML frontmatter:

```markdown
---
schema_version: "1"
packet_id: "some_unique_id"
created_at: "2026-03-16T18:52:47Z"
source_project: "origin_project_key"
packet_type: "improvement_proposal"
title: "Short descriptive title"
language: "en"
status: "open"
---

# Title

Body content here.
```

### Required fields

`schema_version`, `packet_id`, `created_at`, `source_project`, `packet_type`, `title`, `language`, `status`

### Filename convention

`{ISO_TIMESTAMP}--{PACKET_ID}.md` (e.g., `20260316T185247Z--my_packet_id.md`)

## Commands

```bash
# Ingest and archive inbox packets
python3 scripts/project_router.py inbox-intake
python3 scripts/project_router.py inbox-intake --dry-run

# List open inbox packet states
python3 scripts/project_router.py inbox-status
python3 scripts/project_router.py inbox-status --all
python3 scripts/project_router.py inbox-status --packet-id <id>

# Acknowledge a packet (record decision)
python3 scripts/project_router.py inbox-ack --packet-id <id> --status applied
python3 scripts/project_router.py inbox-ack --packet-id <id> --status blocked --notes "reason"
python3 scripts/project_router.py inbox-ack --packet-id <id> --status in_progress
python3 scripts/project_router.py inbox-ack --packet-id <id> --status applied --ref "https://github.com/..."

# Validate structure and packet schema
python3 scripts/project_router.py doctor --router-root router/
```

## Rules

- Keep authored packets in `outbox/` as Markdown files with YAML frontmatter.
- Use `{created_at}--{packet_id}.md` filenames.
- Do not place generated runtime artifacts here.
- `doctor` validates the structure and packet schema without mutating files.
- Never modify `archive/` contents after ingestion — originals are preserved for audit.
- Never auto-apply inbox packets — always require user confirmation.
