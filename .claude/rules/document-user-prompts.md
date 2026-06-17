# Document Significant User Prompts and Decisions

When the user gives a directive that shapes the project (a design decision, a constraint,
a "from now on always…" rule, a non-obvious requirement), capture it durably so it is not
lost across sessions.

- Spec-level decisions go in the relevant `.claude/specs/<feature>/` artifacts and the
  append-only `DL-NNN` decision log (see `.claude/rules/agent-state-convention.md`).
- Cross-cutting standards the user wants enforced everywhere belong in a rule file under
  `.claude/rules/` (and, if short and universal, summarized in `CLAUDE.md`).
- Project-level facts not derivable from the code go in `docs/` (e.g. `ProjectPlan.md`,
  `lessons-learned.md`).

The goal is that a future session — Kiro or Claude Code — can reconstruct *why* a choice
was made, not just *what* the code does.
