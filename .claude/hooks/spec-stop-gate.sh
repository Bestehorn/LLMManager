#!/usr/bin/env bash
# spec-stop-gate.sh — Stop hook for the spec/TDD workflow.
#
# Wire as a Stop hook in .claude/settings.json. It reads the hook JSON on stdin and
# BLOCKS turn-end (exit 2) when the spec workflow is mid-implementation and the work
# is not honestly proven, i.e. any of:
#   - a task is marked complete ([x]) in tasks.md but has no green evidence capture;
#   - the latest evidence capture shows a failing / errored suite;
#   - a green capture contains skipped/xfail tests (vacuous-green dodge).
# When blocking, it prints (stderr) what remains so the agent keeps working instead of
# stopping on an unproven "done". Exit 0 allows the turn to end.
#
# It is intentionally conservative: it only blocks while CURRENT_SPEC is set and the
# phase is IMPLEMENT/VERIFY. Outside the workflow it is a no-op. Claude Code overrides
# a Stop hook after several consecutive blocks, so this cannot wedge a session.

set -u

cat >/dev/null   # drain stdin (hook JSON); decisions are file-based below.

# Any agent driving the spec/TDD engine writes a workflow_state.md under its own
# agent-state dir (spec-conductor, issue-work-orchestrator, ...). Use the most
# recently modified one as the active workflow.
base=".claude/agent-state"
[[ -n "${CLAUDE_PROJECT_DIR:-}" && -d "$CLAUDE_PROJECT_DIR/$base" ]] && base="$CLAUDE_PROJECT_DIR/$base"
state_file="$(ls -t "$base"/*/workflow_state.md 2>/dev/null | head -1)"
[[ -n "$state_file" && -f "$state_file" ]] || exit 0   # no active workflow

phase="$(grep -iE '^[*-]?[[:space:]]*Phase:' "$state_file" | tail -1 | sed -E 's/.*Phase:[[:space:]]*//')"
status="$(grep -iE '^[*-]?[[:space:]]*Status:' "$state_file" | tail -1 | sed -E 's/.*Status:[[:space:]]*//')"
spec_dir="$(grep -iE '^[*-]?[[:space:]]*CURRENT_SPEC:' "$state_file" | tail -1 | sed -E 's/.*CURRENT_SPEC:[[:space:]]*//' | tr -d '\r')"

# Once the workflow is COMPLETED, never block.
grep -qiE 'COMPLETED' <<<"$status" && exit 0

case "$phase" in
  *IMPLEMENT*|*VERIFY*) : ;;
  *) exit 0 ;;
esac

[[ -n "$spec_dir" ]] || exit 0
[[ -n "${CLAUDE_PROJECT_DIR:-}" && -d "$CLAUDE_PROJECT_DIR/$spec_dir" ]] && spec_dir="$CLAUDE_PROJECT_DIR/$spec_dir"
tasks="$spec_dir/tasks.md"
[[ -f "$tasks" ]] || exit 0

problems=""

# 1. Every completed task ([x]) must have a green evidence capture.
#    Task IDs are the leading number of a checked task line: "- [x] 3.2 ..." -> 3.2
while IFS= read -r line; do
  id="$(sed -E 's/^[[:space:]]*-[[:space:]]*\[[xX]\][[:space:]]*([0-9]+(\.[0-9]+)?).*/\1/' <<<"$line")"
  [[ "$id" == "$line" ]] && continue           # no numeric id parsed
  # implementation tasks produce green evidence; pure test-writing tasks produce red.
  # Accept either a green capture (impl) or a red capture (test task) as "has evidence".
  if [[ ! -f "$spec_dir/evidence/green/${id}.txt" && ! -f "$spec_dir/evidence/red/${id}.txt" ]]; then
    problems+="  - task ${id} is marked complete but has no evidence capture (evidence/green/${id}.txt or evidence/red/${id}.txt)."$'\n'
  fi
done < <(grep -E '^[[:space:]]*-[[:space:]]*\[[xX]\]' "$tasks")

# 2. The most recent green/regress capture must not show failures.
latest_green="$(ls -t "$spec_dir"/evidence/green/*.txt "$spec_dir"/evidence/regress/*.txt 2>/dev/null | head -1)"
if [[ -n "$latest_green" ]]; then
  if grep -qiE '[1-9][0-9]* failed|[1-9][0-9]* error' "$latest_green"; then
    problems+="  - latest test capture ($latest_green) shows failures/errors — the suite is not green."$'\n'
  fi
  if grep -qiE 'skipped|xfail|xpassed' "$latest_green"; then
    problems+="  - latest test capture ($latest_green) contains skipped/xfail tests — resolve them rather than stopping."$'\n'
  fi
fi

if [[ -n "$problems" ]]; then
  echo "spec-stop-gate: not safe to stop — the implementation is not yet proven:" >&2
  printf '%s' "$problems" >&2
  echo "Continue: finish the task, run its tests, capture the evidence, and only mark it complete when green." >&2
  exit 2
fi

exit 0
