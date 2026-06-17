# Tests Must Pass — Fix the Root Cause

Tests are a correctness contract. An activity is never complete with failing tests.

- NEVER make a test pass by skipping it, marking it `xfail`/`skip`, deleting it,
  loosening an assertion to triviality, or commenting it out. Fix the underlying cause
  — whether that is the implementation or a genuinely wrong test.
- When a test fails, determine whether it is a bug in the code, a bug in the test, or a
  wrong assumption, then fix the real cause and re-run until green.
- Do not bypass the pre-commit hook with `--no-verify`/`-n` (enforced by
  `.claude/hooks/spec-tdd-gate.sh`).
- Skipped tests are debt: minimize them, and justify any that remain in your report.

**This is a hard rule, partially enforced**: the spec/TDD stop and commit gates
(`.claude/hooks/spec-stop-gate.sh`, `.claude/hooks/spec-tdd-gate.sh`) block turn-end and
commits when an in-progress task lacks fresh green evidence or the latest run is red /
contains skipped/xfail tests. Coverage target is 80% (`--cov-fail-under=80`).
