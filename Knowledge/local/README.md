# Knowledge/local

This directory is for your private knowledge content. It is `private_owned` and never synced from the template upstream.

## Structure

| Path | Purpose |
|------|---------|
| `ADR/` | Your project-specific Architecture Decision Records, numbered 100+ |
| `Roadmap.md` | Your project-specific roadmap and priorities |
| `notes/` | Operational scratch notes, session logs, and temporary references |

## Guidelines

- Your ADRs start at **100** to avoid conflicts with template ADRs (000--099).
- Follow the same ADR format as `Knowledge/ADR/TEMPLATE.md`.
- Keep operational notes in `notes/` -- in the standard ownership model they stay `private_owned` and survive template sync.
- This entire directory survives template sync without conflicts.
