# Private Codex Rules

<!-- Add Codex-specific operating rules below. Referenced by prose instruction in AGENTS.md. -->
<!-- Examples: extra safety rules, workflow preferences, local naming conventions. -->
<!-- Leave empty if no Codex-specific overrides are needed. -->

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

## Template Update Check

At the start of a new conversation in this private-derived repository, run:

```bash
python3 scripts/project_router.py template-update-status --check-remote
```

If the command reports `update_available`, tell the user which template version is installed, which release is latest, and ask whether they want to review/update before continuing. Do not auto-run the sync workflow or merge anything on the user's behalf.
