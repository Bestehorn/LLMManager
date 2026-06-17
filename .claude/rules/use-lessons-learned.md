# Use and Maintain the Lessons-Learned Log

`docs/lessons-learned.md` is the project's running record of non-obvious gotchas and
their resolutions. Treat it as required reading and required writing.

- **Before** non-trivial work, read `docs/lessons-learned.md` to avoid repeating a
  known mistake.
- **After** resolving a non-obvious problem (a subtle bug, a CI quirk, an AWS Bedrock
  behavior, a setuptools-scm/`_version.py` surprise), append an entry.

Entry format:
```markdown
## YYYY-MM-DD — <short title>
- **Context**: what you were doing
- **Lesson**: what was non-obvious / what went wrong
- **Action**: the fix, and how to avoid it next time
```

Keep entries concise and factual. This file is referenced by `.claude/rules/pre-work.md`.
