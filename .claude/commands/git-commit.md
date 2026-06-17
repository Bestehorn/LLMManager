---
description: Stage and commit changes safely (gitignore compliance, integrate remote, honor the pre-commit hook).
allowed-tools: Bash, Read, Edit, Grep, Glob
---
Shared git workflow — COMMIT stage. USE THE VENV for any check you run. Read complete output.

1. **Gitignore compliance**: run `git status` and review what would be staged. Never stage
   secrets, generated files, or anything matching `.gitignore` (credentials/, config/gitlab.json,
   config/aws_accounts.json, `src/bestehorn_llmmanager/_version.py`, tmp/, *.zip, coverage
   artifacts). If something sensitive is untracked-but-not-ignored, add it to `.gitignore` first.
2. **Integrate the remote first**: `git fetch origin` then bring the branch up to date
   (`git rebase origin/main`, resolving any conflicts line-by-line — never blanket-accept one side).
3. **Stage deliberately**: stage only the files belonging to this change (`git add <paths>`),
   not `git add -A` blindly.
4. **Commit**: write a clear message. The repo's pre-commit hook (`.git/hooks/pre-commit`, installed
   by `scripts/setup-hooks.sh`) runs black + isort + flake8 on commit.
   - NEVER use `--no-verify` / `-n`. If the hook fails, FIX the reported issues (run black/isort to
     auto-format, fix flake8 findings) and re-commit.
5. Report the commit SHA and what was committed.

Do not push here — use `/git-push` for that. Line length 100; exclude
`src/bestehorn_llmmanager/_version.py` from all checks.
