# Private Claude Rules

<!-- Add Claude-specific operating rules below. These are loaded via @import in CLAUDE.md. -->
<!-- Examples: extra safety rules, workflow preferences, local naming conventions. -->
<!-- Leave empty if no Claude-specific overrides are needed. -->

## Inbox Consumption Commands

```bash
# Ingest and archive inbox packets
python3 scripts/project_router.py inbox-intake
python3 scripts/project_router.py inbox-intake --dry-run

# List open inbox packet states
python3 scripts/project_router.py inbox-status
python3 scripts/project_router.py inbox-status --all
python3 scripts/project_router.py inbox-status --packet-id <id>

# Acknowledge a packet (record decision)
python3 scripts/project_router.py inbox-ack --packet-id <id> --status <applied|blocked|rejected|in_progress>
python3 scripts/project_router.py inbox-ack --packet-id <id> --status applied --ref <url> --notes "reason"
```
