---
description: Push the current branch and monitor GitHub CI to a terminal state, fixing failures until green.
allowed-tools: Bash, Read, Edit, Grep, Glob
---
Shared git workflow — PUSH + CI MONITOR stage. USE THE VENV for any local check. Read complete
output. This project is hosted on **GitHub** (`Bestehorn/LLMManager`); all remote API operations go
through `scripts/github_wrapper.py` (gh/glab are not used — see
`.claude/rules/use-git-wrapper-scripts.md`).

1. **Pre-push integrity**: ensure the working tree is committed and the local pre-commit hook passed
   (NEVER `--no-verify`). Integrate the remote first (`/git-rebase` if behind).
2. **Push**: `git push origin <branch>`.
3. **Determine CI status and monitor to a terminal state** via the wrapper:
   - `python scripts/github_wrapper.py list-runs --limit 5` to find the run for your branch/SHA.
   - Poll `python scripts/github_wrapper.py get-run <run_id>` until the run reaches a terminal
     conclusion (success / failure / cancelled).
4. **If CI fails**: fetch the failing logs
   (`python scripts/github_wrapper.py get-logs <run_id> --failed-only`), reproduce locally in the
   venv, FIX the root cause, commit, push again, and re-monitor.
   - Never abandon a red pipeline. Never `--no-verify`. Never disable/delete a failing check.
5. **Loop** steps 2–4 until CI is green.
6. Report: branch, final commit SHA, the CI run id and its terminal conclusion, and any fixes made.

The wrapper reads its token from `credentials/github-pat.txt` (gitignored). If that file still holds
the placeholder, stop and tell the user to paste a real PAT. CI workflow definition:
`.github/workflows/ci.yml`. Line length 100; exclude `src/bestehorn_llmmanager/_version.py`.
