---
paths:
  - "cdk/**"
  - "**/cdk.json"
  - "**/app.py"
---

# Per-Worktree Virtual Environment (when running code/CDK from worktrees)

This rule applies to projects that **execute code or infrastructure-as-code from inside a
git worktree** while concurrent runs share one clone — most importantly AWS/CDK projects
(`cdk synth`/`cdk deploy`) and any project that imports an editable-installed package.
It is installed at `.claude/rules/per-worktree-venv.md`. For pure-library projects that
only ever run tests from the main checkout, this rule is not needed.

## Why (the trap a worktree does NOT close)

A git worktree isolates the working tree, index, and branch — but a single shared venv
does NOT. A `pip install -e` writes ONE editable `.pth` pinned to the absolute path of
the checkout it was run in. Code/CDK run from a worktree on that shared venv import the
**other** checkout's `src`/`cdk`. (Field-proven: a worktree `cdk deploy` on a shared venv
silently shipped the MAIN checkout's CDK; a worktree given its OWN venv deployed
correctly. `pytest` usually escapes because it front-loads the rootdir on `sys.path`; CDK
synth/deploy does not.) And re-running `pip install -e` against the shared venv to "fix"
imports rewrites that single `.pth` last-writer-wins, corrupting every other concurrent
run.

## The rule

1. **Each worktree that will run code/CDK gets its OWN venv.** In PREPARE, after
   `git worktree add`, create `<worktree>/venv` and `pip install -e ".[dev,cdk]"` (the
   project's extras) INSIDE the worktree, so its `.pth` and any generated version file
   are worktree-local.
2. **Invoke tools by the worktree's ABSOLUTE interpreter**, never by relying on an
   activated environment: `<worktree>/venv/Scripts/python.exe -m <tool>` (Windows) or
   `<worktree>/venv/bin/python -m <tool>` (*nix), with `cwd = <worktree>`. Do NOT rely on
   `Activate.ps1` / `VIRTUAL_ENV` — auto-activation is cwd-dependent and racy across
   concurrent runs.
3. **NEVER "fix" imports by re-running `pip install -e` against the SHARED venv.** That
   rewrites the one shared `.pth` and breaks every other concurrent run. The fix is the
   worktree's own venv, always.
4. **Authoritative self-check (not a vacuous one).** `import src` / `import cdk` from the
   worktree cwd can pass *vacuously* (cwd wins on `sys.path`). The real verification is
   (a) read the worktree venv's `__editable__*.pth` / `*.pth` and confirm it contains the
   **worktree** path (not the main checkout), and (b) for CDK, a real `cdk synth` that
   resolves `cdk.__file__` under the worktree. Make this a **resume precondition** too —
   a crashed PREPARE can leave a half-built or absent worktree venv.
5. **Teardown order (Windows).** In MERGE_CLEANUP, delete `<worktree>/venv` BEFORE
   `git worktree remove` — locked DLLs (e.g. PySide6) otherwise make the removal fail and
   leave a stale worktree. Alternatively use **out-of-tree** worktrees (a sibling
   directory) to dodge the locked-DLL removal problem entirely.
6. **Bound concurrency and isolate the pip cache.** A full `[dev,gui,cdk]` venv can be
   ~1.5 GB; N concurrent worktree venvs cost N × that on one disk. Declare a
   `MAX_CONCURRENT_WORKTREE_RUNS` bound tied to host RAM/disk (record it in the run
   environment), and pass an explicit `pip --cache-dir <worktree>/.pipcache` (or
   `--no-cache-dir`) to avoid the shared pip-cache concurrent-write race. Do NOT set
   `PIP_CACHE_DIR` — environment variables are forbidden (`no-environment-vars`); pass
   the flag on the command instead.

## Self-check before relying on worktree execution
Confirm: the worktree venv exists; its `.pth` points at the worktree (not the main
checkout); a real `cdk synth`/import resolves under the worktree; the shared venv was not
re-installed against. If any fails, rebuild the worktree venv before running code/CDK.
