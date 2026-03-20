# Private Claude Rules

<!-- Add Claude-specific operating rules below. These are loaded via @import in CLAUDE.md. -->
<!-- Examples: extra safety rules, workflow preferences, local naming conventions. -->
<!-- Leave empty if no Claude-specific overrides are needed. -->

## Template Update Check

At the start of a new conversation in a private-derived repository, run:

```bash
python3 scripts/project_router.py template-update-status --check-remote
```

If the command reports `update_available`, tell the user which template version is installed, which release is latest, and ask whether they want to review/update before continuing. Do not auto-run the sync workflow or merge anything on the user's behalf.
