# Phase Fragment: TASKS

Followed by `spec-conductor` (and the `/spec-tasks` command). Generates/regenerates
`tasks.md` by delegating to `spec-author`. Installed at
`.claude/specs/_workflow/phases/spec-phase-tasks.md`.

## Procedure

Invoke `spec-author` with `requirements.md`/`bugfix.md` + `design.md` (especially the
`## Correctness Properties` and `## Acceptance Criteria Mapping`). It writes
`tasks.md` with:

- **Checkbox tasks** (`- [ ] N. ...`, subtasks `- [ ] N.M ...`), grouped into phases,
  **dependency-ordered** so partial completion leaves the tree in a safe state.
- **Test-first ordering (mandatory):** for each behavior, the task "write failing
  test(s) for Property N / acceptance criterion X" comes BEFORE the task "implement
  to make those tests pass". Mixing them or putting impl first is wrong.
- **Full coverage:** every Correctness Property and every acceptance-criteria row
  (including every bugfix "Unchanged Behavior" regression clause) has a corresponding
  test task. Each task names the file(s) it touches and the requirement ID(s) it
  serves.
- A final **end-to-end verification** task (the VERIFY phase / adversarial proof).

After it returns, append a `DL-NNN` entry and transition to TASKS_REVIEW_LOOP
(`spec-phase-review.md`, light panel). 

## Regeneration / sync

When invoked to regenerate (e.g. requirements/design changed during a review loop, or
`/spec-tasks` run again), preserve the completion state of tasks whose meaning is
unchanged (keep `[x]`), add tasks for new requirements/properties, and mark tasks
whose underlying requirement was removed as obsolete (strike or remove with a
`DL-NNN` note) — do not silently drop history.

## `/spec-tasks` standalone behavior

Generate or regenerate `tasks.md` for the named spec, then run ONE light review pass
(`spec-review-agent` report-only + `test-architect`) and print the combined A+B count
and coverage report, then stop. The user can then run `/spec-implement` or the full
conductor.
