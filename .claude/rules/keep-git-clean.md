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
- The clean end-state is **per run**: each run leaves no worktree, branch, or lock of
  its own behind. Assert cleanliness on the run's OWN working area.
- **Do NOT move the shared local `main` branch.** When multiple runs may share one clone
  (e.g. the issue-work-orchestrator), a run NEVER `git checkout main`s or fast-forwards
  the shared local `main` — the developer and sibling runs depend on it. Fetch and base
  new worktrees on `origin/<main>`, and verify merges with
  `git merge-base --is-ancestor <sha> origin/<main>` instead of advancing local `main`.
  (A solo workflow with no concurrent runs may sync local `main`, but the
  fetch-and-branch-off-origin pattern is always safe and is the default.)
- Never leave a detached HEAD, a half-finished rebase/merge, or an orphaned worktree.
  If a git operation is interrupted, the next action is to bring the tree back to a
  clean, known state before doing anything else.

## Concurrency-safe maintenance (avoid the one real git-corruption hazard)

The single genuine corruption risk when several worktrees/runs share one object store is
concurrent auto-gc/maintenance, which `git fetch` can trigger by default. Set this ONCE
on the clone (idempotent) before running concurrent work, and it applies clone-wide:

```
git config gc.auto 0
git config maintenance.auto false
git config gc.autoDetach false
```

Pass `--no-auto-gc` on every fetch (`git fetch origin --prune --no-auto-gc`). NEVER use
`--prune=now` or a manual `git gc` while any worktree operation may be in flight. (Note:
`--no-auto-maintenance` is NOT a valid `git fetch` flag on git ≥ 2.51 — use `--no-auto-gc`
plus the persistent config.) Run a single quiescent `git gc` only between backlog passes
with no run active.

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
