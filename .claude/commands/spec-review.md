---
description: Run one adversarial review-panel pass over an existing spec (requirements/design or tasks) and report the combined A+B defect count and test-coverage report.
argument-hint: [feature slug, e.g. customer-count-fix]
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, WebSearch, WebFetch, Agent(spec-review-agent, test-architect, standards-reviewer, best-practice-reviewer, security-reviewer, devops-iac-reviewer)
---

Run a single review-panel pass over the spec at `.claude/specs/$ARGUMENTS/` (if no
slug is given, use the most recently modified spec under `.claude/specs/`).

Follow `.claude/specs/_workflow/phases/spec-phase-review.md`, the "`/spec-review`
standalone behavior" section: perform exactly ONE iteration of the appropriate panel:
- If `design.md` is the latest artifact under review: the FULL panel
  (`spec-review-agent` in report-only mode, `test-architect`, `standards-reviewer`,
  `best-practice-reviewer`, `security-reviewer`, `devops-iac-reviewer`).
- If `tasks.md` is being reviewed: the LIGHT panel (`spec-review-agent` report-only +
  `test-architect`).

Invoke each reviewer (parallel Agent calls are fine); each writes
`review/<reviewer>/iteration-NN.md`. Then aggregate yourself: dedup + conflict-resolve,
write `review/review-latest.md`, and append a `DL-NNN` entry.

Do NOT revise the spec (no `spec-author` call) — this command only reports. Print:
the combined **A+B count**, the per-reviewer breakdown, the `test-architect` Coverage
Report (COVERED vs GAP requirement rows), and whether the readiness gate (0 A+B + zero
coverage GAPs) is met. If not met, list the A/B findings the user (or the conductor)
must resolve. Never touch `.kiro/`.
