## Summary

Describe the change in a few lines.

## Why

Explain the problem or motivation.

## Validation

List the checks you ran:

- [ ] `python3 scripts/check_agent_surface_parity.py --pre-publish`
- [ ] `python3 scripts/check_repo_ownership.py`
- [ ] `python3 -m pytest tests/test_project_router.py -q`

## Safety Checklist

- [ ] No local secrets or runtime artifacts were committed
- [ ] No real VoiceNotes exports, transcripts, or compiled notes were committed
- [ ] No machine-specific inbox paths were introduced
- [ ] `.agents/`, `.codex/skills/`, and `.claude/skills/` remain aligned when applicable

## Notes

Add follow-ups, tradeoffs, or review guidance if needed.
