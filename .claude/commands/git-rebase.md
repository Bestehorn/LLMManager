---
description: Rebase the current branch onto the latest origin/main with line-by-line conflict resolution.
allowed-tools: Bash, Read, Edit, Grep, Glob
---
Shared git workflow — REBASE stage. Read complete output.

1. **Fetch**: `git fetch origin`.
2. **Rebase** the current branch onto the integration branch: `git rebase origin/main`.
3. **Resolve conflicts line-by-line**: for every conflicted file, read both sides and produce a
   correct merge that preserves the intent of BOTH changes. Never blanket `--theirs`/`--ours` and
   never discard someone else's work. After resolving each file: `git add <file>` then
   `git rebase --continue`.
4. **Verify nothing broke**: after the rebase completes, run the test suite in the venv
   (`venv\Scripts\activate & pytest test/`) and the CI checks (`/run-ci`) — a clean rebase that
   breaks tests is not done.
5. If the rebase must be aborted for safety, `git rebase --abort`, report why, and stop.

Report the result (commits replayed, conflicts resolved, test status). Never force-resolve blindly;
exclude `src/bestehorn_llmmanager/_version.py` from checks.
