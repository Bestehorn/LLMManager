# Remote CI Must Pass

Pushing is not the end of a task — green remote CI is. After any push, drive the GitHub
Actions workflow (`.github/workflows/ci.yml`) to a terminal state and make it green.

- After `git push`, find the run and poll it to completion via the wrapper
  (`python scripts/github_wrapper.py list-runs` / `get-run`).
- If CI fails, fetch the failing logs (`get-logs <run_id> --failed-only`), reproduce the
  failure locally in the venv, fix the root cause, push again, and re-monitor.
- Never abandon a red pipeline, never `--no-verify`, never disable or delete a CI check
  to make it green.
- The CI workflow runs: lint (ruff format --check, ruff check, mypy), the test
  matrix (pytest with coverage across Python 3.10–3.14), build (check-manifest, twine),
  and CodeQL security analysis.

The `/git-push` slash command automates this monitor-and-fix loop.
