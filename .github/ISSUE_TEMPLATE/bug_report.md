---
name: Bug report
about: Report a reproducible problem in the template, CLI, docs, or workflow
title: "[Bug] "
labels: bug
assignees: ""
---

## Summary

Describe the problem in one or two sentences.

## Current Behavior

What happened?

## Expected Behavior

What should have happened instead?

## Reproduction

List the exact commands or steps:

1. 
2. 
3. 

## Validation

Include any relevant output from:

```bash
python3 scripts/check_agent_surface_parity.py --pre-publish
python3 scripts/check_repo_ownership.py
python3 -m pytest tests/test_project_router.py -q
```

## Notes

- Do not paste secrets or personal data
- Do not attach real VoiceNotes exports or local-only config
- If the issue depends on private downstream behavior, describe it generically
