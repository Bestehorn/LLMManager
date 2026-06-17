---
description: Start a new spec — interview the user to author an evidence-grounded initial prompt for a feature or bugfix, then write prompt.md/prompt-discussion.md under .claude/specs/<feature>/.
argument-hint: [short description of the feature or bug, e.g. "fix the customer count showing 0"]
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, WebSearch, WebFetch, Agent(spec-researcher)
---

You are starting the PROMPT_AUTHORING phase of the spec-driven workflow for this
request: **$ARGUMENTS**

Read and follow the procedure in `.claude/specs/_workflow/phases/spec-phase-prompt.md`
exactly (the one-question-at-a-time, clarity-first, evidence-grounded interview with
`qa_log.md` persistence). If that file is not present, follow the embedded interview
protocol from the `spec-prompt-author-agent` instead.

Conduct the interview yourself in this session (do not delegate the interview — a
subagent cannot run a multi-turn conversation). You MAY delegate scoped, read-only
research to the `spec-researcher` subagent to ground your questions.

Determine whether this is a FEATURE or a BUGFIX. Slugify a `<feature>` name and write
under `.claude/specs/<feature>/`: `prompt.md`, `prompt-discussion.md`, `qa_log.md`.
Append a `DL-NNN` entry per `.claude/rules/agent-state-convention.md`. Never touch
`.kiro/`.

When the prompt is finalized, stop and tell the user it is ready, and that they can
carry it forward end-to-end with `claude --agent spec-conductor` (which will resume
from this prompt) or step through with `/spec-review`, `/spec-tasks`,
`/spec-implement`.
