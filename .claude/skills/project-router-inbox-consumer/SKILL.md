---
name: project-router-inbox-consumer
description: Consume incoming packets from this repository's router/inbox/ by running inbox-intake, reviewing each item, and acknowledging with inbox-ack. Never auto-apply packets.
---

# Project Router Inbox Consumer

Use this workflow to process packets that have arrived in this repository's `router/inbox/`.

## Mandatory Rules

- Never auto-apply packets. Always present each packet to the user and wait for an explicit decision.
- Never modify `router/archive/` contents after ingestion — the archive preserves originals.
- Treat `inbox-intake` as a safe ingestion step (validates, archives, creates state).
- Treat `inbox-ack --status in_progress` as a non-terminal intermediate state.
- Treat `inbox-ack --status applied|blocked|rejected` as terminal — generates an outbox ack packet.
- Use `--ref` to link external tracking references (e.g., PR URLs, issue links) when acknowledging.

## Consumption Flow

1. Run `python3 scripts/project_router.py inbox-intake` to validate and archive incoming packets.
2. Run `python3 scripts/project_router.py inbox-status` to list open packets.
3. For each open packet:
   - Read the archived original at `router/archive/<packet_id>/original.md`.
   - Present the packet title, type, source project, and body to the user.
   - Ask the user for a decision: `applied`, `blocked`, `rejected`, or `in_progress`.
4. Record the decision with:
   - `python3 scripts/project_router.py inbox-ack --packet-id <id> --status <status>`
   - Add `--notes "..."` for context and `--ref <url>` for external tracking.
5. After all packets are processed, run `python3 scripts/project_router.py inbox-status --all` to confirm.

## Per-Item Presentation Format

For each packet, present:

```
Packet: <packet_id>
Type: <packet_type>
From: <source_project>
Title: <title>
Created: <created_at>

<body summary or first few lines>
```

Then ask: "What would you like to do with this packet? (applied / in_progress / blocked / rejected)"

## Status Lifecycle

```
open → in_progress → applied | blocked | rejected
```

Terminal states (`applied`, `blocked`, `rejected`) generate an ack packet in `router/outbox/`.
