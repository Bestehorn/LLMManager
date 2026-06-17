# Use the Git Host Wrapper Script for Remote Operations

This project is hosted on **GitHub** (`Bestehorn/LLMManager`). All GitHub API
operations — issues, pull requests, CI/workflow runs, merges — go through
`scripts/github_wrapper.py`, which reads its token from `credentials/github-pat.txt`
(gitignored) and auto-detects owner/repo from `.git/config`.

- Do NOT use `gh`, `glab`, raw `curl`, or `requests` against `api.github.com` directly.
  (`gh` is not installed in this environment and the wrapper centralizes auth/behavior.)
- Plain local git is fine: `git status`, `git add`, `git commit`, `git fetch`,
  `git rebase`, `git push`, `git worktree`.
- Example: `python scripts/github_wrapper.py list-runs --limit 5`.

The wrapper is currently a skeleton — implement the subcommands an agent needs the first
time it needs them (the docstring lists the required REST endpoints). If the credential
file still contains the placeholder, paste a real PAT before remote operations will work.

See also `.claude/rules/remote-ci-must-pass.md`. The `/git-push` and `/issues-work`
workflows depend on this wrapper.
