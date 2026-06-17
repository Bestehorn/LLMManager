#!/usr/bin/env bash
# spec-tdd-gate.sh — PreToolUse(Bash) gate for the spec/TDD workflow.
#
# Wire as a PreToolUse hook with matcher "Bash" in .claude/settings.json. It reads the
# hook JSON on stdin, inspects the Bash command, and BLOCKS (exit 2) when:
#   (a) the command bypasses verification: `git commit --no-verify` / `-n`, or
#   (b) the command is `git commit` while the active spec has no fresh GREEN evidence
#       for the task currently in progress.
# Otherwise it allows the command (exit 0).
#
# Rationale: commits must be backed by passing tests with captured evidence. This is
# the enforced floor under the conductor's prompt-level discipline. Exit 2 feeds the
# stderr message back to Claude so it knows why it was blocked and what to do.
#
# Detection of "the active spec" and "current task" is best-effort and file-based:
# the conductor records them in .claude/agent-state/spec-conductor/workflow_state.md
# (CURRENT_SPEC=<dir>, CURRENT_TASK=<id>). If no spec workflow is active, the gate
# only enforces the --no-verify ban and otherwise allows the commit.

set -u

input="$(cat)"

# Extract the Bash command from the hook JSON. Prefer jq; fall back to grep.
cmd=""
if command -v jq >/dev/null 2>&1; then
  cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)"
fi
if [[ -z "$cmd" ]]; then
  cmd="$(printf '%s' "$input" | grep -oE '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed -E 's/.*:[[:space:]]*"(.*)"/\1/')"
fi

# Only act on git commit commands.
if ! grep -qE '(^|[;&| ])git[[:space:]]+commit([[:space:]]|$)' <<<"$cmd"; then
  exit 0
fi

# (a) Ban verification bypass outright.
if grep -qE '(--no-verify|[[:space:]]-n([[:space:]]|$))' <<<"$cmd"; then
  echo "spec-tdd-gate: 'git commit --no-verify'/-n is forbidden — commits must pass the pre-commit hook and be backed by green test evidence. Fix the failing checks instead of bypassing them." >&2
  exit 2
fi

# Locate the active spec workflow's state. Any agent that drives the spec/TDD
# engine writes a workflow_state.md under its own agent-state dir (the
# spec-conductor, the issue-work-orchestrator, etc.). Pick the most recently
# modified one as the active workflow.
base=".claude/agent-state"
[[ -n "${CLAUDE_PROJECT_DIR:-}" && -d "$CLAUDE_PROJECT_DIR/$base" ]] && base="$CLAUDE_PROJECT_DIR/$base"
state_file="$(ls -t "$base"/*/workflow_state.md 2>/dev/null | head -1)"

if [[ -z "$state_file" || ! -f "$state_file" ]]; then
  # No active spec workflow — nothing more to enforce here.
  exit 0
fi

phase="$(grep -iE '^[*-]?[[:space:]]*Phase:' "$state_file" | tail -1 | sed -E 's/.*Phase:[[:space:]]*//')"
spec_dir="$(grep -iE '^[*-]?[[:space:]]*CURRENT_SPEC:' "$state_file" | tail -1 | sed -E 's/.*CURRENT_SPEC:[[:space:]]*//' | tr -d '\r')"
task_id="$(grep -iE '^[*-]?[[:space:]]*CURRENT_TASK:' "$state_file" | tail -1 | sed -E 's/.*CURRENT_TASK:[[:space:]]*//' | tr -d '\r')"

# Only gate commits during implementation/verification.
case "$phase" in
  *IMPLEMENT*|*VERIFY*) : ;;
  *) exit 0 ;;
esac

if [[ -z "$spec_dir" || -z "$task_id" ]]; then
  # Can't identify the task; do not hard-block, but warn (non-blocking exit 0).
  exit 0
fi
[[ -n "${CLAUDE_PROJECT_DIR:-}" && -d "$CLAUDE_PROJECT_DIR/$spec_dir" ]] && spec_dir="$CLAUDE_PROJECT_DIR/$spec_dir"

green="$spec_dir/evidence/green/${task_id}.txt"
if [[ ! -f "$green" ]]; then
  echo "spec-tdd-gate: no green evidence for task '$task_id' at $green — run the paired tests and capture a passing result before committing." >&2
  exit 2
fi

# The green capture must actually be passing and free of skip/xfail dodges.
if grep -qiE 'failed|error' "$green" && ! grep -qiE '0 failed|no failures|[1-9][0-9]* passed' "$green"; then
  echo "spec-tdd-gate: green evidence for task '$task_id' shows failures — not safe to commit." >&2
  exit 2
fi
if grep -qiE 'skipped|xfail|xpassed' "$green"; then
  echo "spec-tdd-gate: green evidence for task '$task_id' contains skipped/xfail tests — resolve them, do not commit around them." >&2
  exit 2
fi

exit 0
