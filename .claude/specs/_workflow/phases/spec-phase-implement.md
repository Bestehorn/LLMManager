# Phase Fragment: IMPLEMENT_LOOP + VERIFY + EVIDENCE_REPORT

Followed by `spec-conductor` (and the `/spec-implement` command). Turns an approved
spec into evidence-proven code, test-first. Installed at
`.claude/specs/_workflow/phases/spec-phase-implement.md`.

The non-negotiable rule of this phase: **the implementer never certifies its own
work.** `spec-implementer` writes tests and code; the CONDUCTOR runs the tests and
captures evidence; the `adversarial-verifier` independently grades it. No claim of
"works/passes" exists without captured command output under `evidence/`.

## Preconditions

- Requirements/design/tasks reviews have passed the readiness gate (0 A+B + coverage).
  (`/spec-implement` first checks `review/review-latest.md` shows 0 A+B and
  test-architect `TEST-READY`; if not, it runs the review loop or refuses with the
  open findings.)
- The venv exists and is active (create it per use-venv if missing). Establish the
  exact test command (e.g. `pytest -n auto -q`) and record it.
- Spec-drift guard: during this phase the `spec-implementer` MUST NOT edit
  `requirements.md`/`design.md`/`tasks.md`. Enforce with the TDD-gate hook and/or
  `permissions.deny` on those paths.

## IMPLEMENT_LOOP — per task, in tasks.md order

For each unchecked task:

### TEST task
1. Invoke `spec-implementer` to write the test(s) ONLY for the named Property /
   acceptance criterion. It must make the symbols importable (minimal stub signature
   in `src/` if needed) but MUST NOT implement the behavior.
2. **Conductor runs the tests** via Bash, capturing COMPLETE output (no tail/head) to
   `evidence/red/<task>.txt`.
3. **Assert RED-FOR-THE-RIGHT-REASON** (run the pre-filter
   `.claude/hooks/red-for-right-reason.sh evidence/red/<task>.txt`, or check
   inline): the failure must be an `AssertionError` / Hypothesis "Falsifying example",
   and must NOT be dominated by `ImportError`/`ModuleNotFoundError`/`CollectionError`/
   `SyntaxError`/`fixture '...' not found`. If green, or red for the wrong reason,
   reject and re-invoke `spec-implementer` to fix the test. Append a `DL-NNN` entry.

### IMPL task
1. Invoke `spec-implementer` to write the MINIMAL code to pass the paired tests,
   without touching unrelated tests and without suppressions.
2. **Conductor runs the paired tests** → `evidence/green/<task>.txt` (must be green).
3. **Conductor runs the FULL suite** → `evidence/regress/<task>.txt` (must show no
   regressions).
4. Only when both captures are green: mark the task `[x]` in `tasks.md` and append a
   `DL-NNN` entry citing the design section implemented.
5. If green cannot be reached after the implementer's attempts, leave the task
   unchecked; loop with more evidence or escalate (one batched message).

When all tasks are `[x]`, transition to VERIFY.

## VERIFY — adversarial

1. Invoke `adversarial-verifier`. It re-runs the whole suite itself and tries to
   REFUTE every "works" claim: kill-the-mutant (revert/stub the impl → the paired
   test must then fail), vacuity/dodge scan (skipped/xfail/assert-nothing), property
   stress (more Hypothesis examples), coverage of the changed code, and a
   red-for-right-reason audit of `evidence/red/*`. It writes
   `evidence/verify/refutation-report.md` + captures, and restores the tree.
2. Re-invoke the full reviewer panel against the IMPLEMENTED diff (design drift
   surfaces as fresh A/B on the code).
3. If the verifier `REFUTED` any claim, or any reviewer raises A/B on the code:
   uncheck the affected tasks and return to IMPLEMENT_LOOP. Else → EVIDENCE_REPORT.

## EVIDENCE_REPORT

Assemble `evidence/REPORT.md`:
- For each requirement → its Correctness Properties → the test(s) proving them → the
  quoted red→green command output → the verifier's failed refutation attempts.
- Final full-suite result and coverage of the change, quoted from captures.
- The `git diff --stat` of the implementation.
Set `workflow_state.md` to `Status: COMPLETED`. The final user-facing message quotes
the report's summary table — every "passes" is a quoted command, never an assertion.

## Commit gating

The TDD-gate hook blocks `git commit` (and `--no-verify`) unless the current task has
a fresh green capture. Commits happen only after a task's `evidence/green` +
`evidence/regress` are green. (Pushing is out of scope here; if the project's
git-push command/CI applies, the remote-ci-must-pass rule governs it.)
