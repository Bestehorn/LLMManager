#!/usr/bin/env bash
# scripts/setup-hooks.sh — ENABLE the project's version-controlled git hooks.
# Run once per clone, from the main checkout (not a worktree).
#
# The hooks themselves are tracked files in `.githooks/` (committed to the
# repo, shared with everyone — they run ruff (format + check) at line-length
# 100, this project's toolchain). This script does NOT generate hook content —
# it just points git at that directory and makes the hooks runnable. It is a
# small per-clone step because of two git facts:
#
#   1. A fresh clone does NOT inherit `core.hooksPath`. The setting lives in
#      `.git/config`, which is not part of what gets cloned, and stock git has
#      no post-clone hook to set it automatically — so each clone must run this
#      once.
#   2. Some environments set a SYSTEM-level hooks dir (e.g. a corporate tool
#      such as git-defender writes `core.hooksPath` into the system gitconfig).
#      Setting it in this repo's LOCAL config overrides the system value for
#      THIS repo only, so every git operation — terminal, IDE, GUI client, and
#      automated agents — uses the project's tracked hooks with no per-command
#      flag. (Trade-off: the system hooks tool no longer runs for this repo.)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HOOKS_DIR="$PROJECT_ROOT/.githooks"

if [ ! -d "$HOOKS_DIR" ]; then
    echo "ERROR: tracked hooks directory not found at $HOOKS_DIR" >&2
    echo "It should be committed to the repo (created during project setup)." >&2
    exit 1
fi

# Point git at the tracked hooks dir, LOCAL scope, RELATIVE path.
# Relative is correct for a TRACKED dir: git resolves core.hooksPath from the
# working-tree root, so it also resolves correctly inside git worktrees (each
# worktree checks out its own .githooks/). Local scope overrides any
# system-level core.hooksPath for this repo only.
git -C "$PROJECT_ROOT" config --local core.hooksPath .githooks
echo "Set local core.hooksPath -> .githooks (overrides any system/global value for this repo)"

# Best-effort: ensure the hooks are executable in this working copy. The
# executable bit is also stored in the index (100755) so fresh clones get it,
# but set it here too in case the working tree was created with filemode off.
chmod +x "$HOOKS_DIR"/* 2>/dev/null || true

# Report what is enabled.
echo "Enabled tracked git hooks from .githooks/:"
for h in "$HOOKS_DIR"/*; do
    [ -f "$h" ] || continue
    case "$(basename "$h")" in
        *.sample|*.md|README*) continue ;;
    esac
    echo "  - $(basename "$h")"
done

PREV_HOOKS="$(git -C "$PROJECT_ROOT" config --system --get core.hooksPath 2>/dev/null || true)"
if [ -n "$PREV_HOOKS" ]; then
    echo "NOTE: overriding system core.hooksPath ($PREV_HOOKS) for this repo only;"
    echo "      a system hooks tool (e.g. git-defender) will not run here."
fi
