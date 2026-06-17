---
description: Generate or regenerate tasks.md (test-first, dependency-ordered, every property/acceptance-criterion has a test task) for an existing spec, then run a light review pass.
argument-hint: [feature slug, e.g. customer-count-fix]
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent(spec-author, spec-review-agent, test-architect)
---

Generate (or regenerate) `tasks.md` for the spec at `.claude/specs/$ARGUMENTS/` (if no
slug is given, use the most recently modified spec under `.claude/specs/`).

Preconditions: `requirements.md`/`bugfix.md` and `design.md` exist. If `design.md`
lacks the mandatory `## Correctness Properties` or `## Acceptance Criteria Mapping`
sections, stop and tell the user to run the design phase first (via
`claude --agent spec-conductor` or by fixing the design).

Follow `.claude/specs/_workflow/phases/spec-phase-tasks.md`: invoke `spec-author` to
write `tasks.md` with test-first ordering and a test task for every Correctness
Property and every acceptance-criteria row (and every bugfix regression clause). On
regeneration, preserve the completion state of unchanged tasks.

Then run ONE light review pass (`spec-review-agent` report-only + `test-architect`),
write the per-reviewer files + `review/review-latest.md`, append a `DL-NNN` entry, and
print the combined A+B count and the coverage report. Tell the user whether tasks are
ready for `/spec-implement`. Never touch `.kiro/`.
