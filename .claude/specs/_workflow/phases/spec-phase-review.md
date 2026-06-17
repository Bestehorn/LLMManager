# Phase Fragment: REVIEW LOOPS (design + tasks)

Followed by `spec-conductor` (DESIGN_REVIEW_LOOP and TASKS_REVIEW_LOOP) and by the
`/spec-review` command (a single panel pass). Installed at
`.claude/specs/_workflow/phases/spec-phase-review.md`.

This is the convergence engine: an adversarial panel reviews the spec, the conductor
aggregates findings and applies the readiness gate, and `spec-author` revises until
the gate passes. The conductor owns the loop and the exit predicate — the reviewers
only detect and classify defects.

## Finding severities (uniform across all reviewers)

- **A** — execution blocker. **B** — intent deviation / gap. **C** — clarification /
  risk. **D** — nit. Only **A + B** block readiness. C/D are recorded, never gate.

## The loop (one iteration = NN)

### DESIGN_REVIEW_LOOP — full panel
Invoke all six reviewers (you MAY issue them as parallel Agent calls), each reading
`requirements.md`/`bugfix.md` + `design.md`, each writing
`review/<reviewer>/iteration-NN.md`:
- `spec-review-agent` (invoke in **report-only** mode — its internal
  `consecutive_clean_AB>=5` verdict is informational; the conductor owns the exit),
- `test-architect`, `standards-reviewer`, `best-practice-reviewer`,
  `security-reviewer`, `devops-iac-reviewer`.

### TASKS_REVIEW_LOOP — light panel
Invoke only `spec-review-agent` (report-only) + `test-architect`, reading `tasks.md`
(+ requirements/design). Focus: dependency-safe ordering, test-first ordering, and a
test task for every Correctness Property and every acceptance-criteria row.

## Aggregation (conductor does this itself)

1. Read every `review/<reviewer>/iteration-NN.md`.
2. Collect all findings; dedup near-identical ones across reviewers; conflict-resolve
   (if two reviewers disagree, keep the stricter and note the conflict).
3. Compute the combined **A+B count**.
4. Write `review/review-latest.md` = the deduped union (the stable pointer) and append
   a `DL-NNN` entry (iteration NN: combined A+B = n, by reviewer).

## Readiness gate (BOTH must hold)

- **Negative gate:** combined A+B == 0, AND iteration >= 1, AND every reviewer's
  `iteration-NN.md` was produced against the CURRENT `design.md`/`tasks.md`
  (verify via mtime / git hash recorded in each reviewer's resume_state — reject a
  clean verdict computed against a stale artifact and re-run that reviewer).
- **Positive gate:** `test-architect`'s Coverage Report has zero GAP rows (≥1 property
  per requirement; 100% of acceptance-criteria rows mapped to a test/test-task) and a
  `TEST-READY` verdict.

If both hold → the phase is approved (DESIGN_REVIEW → TASKS; TASKS_REVIEW →
IMPLEMENT_LOOP).

## Otherwise — revise and loop

Invoke `spec-author` with the aggregated A+B findings (and any test-architect
coverage GAPs) to edit `design.md` (or `requirements.md`/`tasks.md` as the finding
dictates). Increment NN and repeat the panel. Append a `DL-NNN` entry per applied
finding-batch.

## Cap and oscillation (never spin)

- **Cap = 8 iterations** per loop.
- **Oscillation:** if combined A+B does not strictly decrease across 3 consecutive
  iterations (use the reviewers' recurring-finding annotations to detect the same
  findings reappearing), stop early.
- On cap or oscillation: do NOT loop silently. Consolidate the still-open A/B findings
  into `open-questions.md` and escalate to the user in ONE batched, clarity-first
  message (one numbered set; each item with options + your recommendation). Resume
  when the user answers; record answers as `DL-NNN` entries and feed them to
  `spec-author`.

## `/spec-review` standalone behavior

When run as the `/spec-review` command (not inside the conductor), perform exactly
ONE panel iteration over the current spec, write the per-reviewer files +
`review/review-latest.md`, print the combined A+B count and the test-architect
Coverage Report, and stop (no author revision). This gives the user an on-demand
review without running the whole loop.
