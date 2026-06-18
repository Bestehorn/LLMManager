# Keep Git Clean and Up-to-Date (ALL agents, always loaded)

This rule is shared by EVERY agent and the main session. It is installed at
`.claude/rules/keep-git-clean.md` (no `paths:` frontmatter → always loaded) and is
pointed to from the project's root `CLAUDE.md`. It governs the state of the local git
working tree, branches, and worktrees at all times.

## The standard

The local git repository must never be left in a messy or stale state. At every phase
boundary, and ALWAYS when an issue/PR/task reaches a terminal state, the working tree
must be clean (`git status --porcelain` empty) except for files that are deliberately
in progress, and there must be no stale branches or worktrees left behind.

## What to commit vs. what never to commit

When deciding whether a changed/untracked file belongs in the repository:

- **COMMIT** (these belong in version control): source code, tests, configuration
  (`pyproject.toml`, `.pre-commit-config.yaml`, CI config), documentation, IaC/CDK
  code, scripts, the tracked git hooks (`.githooks/`), spec artifacts the project keeps
  under version control, and `.gitignore`/`.gitattributes` updates.
- **NEVER COMMIT** (auto-generated, transient, or machine-local): build artifacts and
  compiled output (`build/`, `dist/`, `*.egg-info/`, `*.pyc`, `__pycache__/`,
  `*.so`), caches (`.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.hypothesis/`),
  coverage output (`.coverage`, `htmlcov/`), virtual environments (`venv/`, `.venv/`),
  editor/OS cruft, secrets and credentials, anything under `tmp/`, generated version
  files (`src/_version.py`), and per-run agent state (`.claude/agent-state/`,
  `.claude/worktrees/`).

The general principle: **auto-generated and temporary files are never committed;
everything else that is part of the project IS committed.** If a file that should
never be committed is not already covered by `.gitignore`, ADD it to `.gitignore`
(rather than just leaving it untracked) so the tree stays clean for everyone.

Decision procedure before any commit:
1. `git status` and review EVERY changed/untracked path.
2. For each: classify as COMMIT or NEVER-COMMIT per the lists above.
3. Stage the COMMIT set; for any NEVER-COMMIT file not yet ignored, add a `.gitignore`
   entry. Do not `git add -A` blindly — that risks committing generated/temp files.
4. Confirm `git status` shows only intended changes before committing.

## Worktrees and branches

- Per-issue/per-task worktrees and branches are EPHEMERAL. When the work reaches a
  terminal state (merged, abandoned, or escalated), remove the worktree
  (`git worktree remove <path>`) and delete the local branch (`git branch -d/-D`),
  and verify with `git worktree list` and a directory check that nothing is left
  behind. A merged fix must not leave its worktree directory or branch lingering.
- After cleanup, the main checkout is on the main branch, synced with the remote, and
  `git status` is clean.
- Never leave a detached HEAD, a half-finished rebase/merge, or an orphaned worktree.
  If a git operation is interrupted, the next action is to bring the tree back to a
  clean, known state before doing anything else.

## Stay up-to-date

Integrate remote changes regularly (fetch + fast-forward/rebase) so local work never
drifts far from the remote — this minimizes conflicts and prevents overwriting others'
changes. Any conflict is resolved per the line-by-line merge discipline (delegate to
the `code-merge-reviewer` agent where it is installed; never blind "take theirs/ours").

## Self-check

Before ending any phase or marking any issue/PR/task done, verify: working tree clean
(or only intended in-progress files present), no stray generated/temp files staged, no
stale worktrees or branches, main checkout synced with the remote. A messy or stale git
state is a defect — fix it before proceeding.
