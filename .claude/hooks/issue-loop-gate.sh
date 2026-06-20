#!/usr/bin/env bash
# issue-loop-gate.sh — Stop hook for the issue-work-orchestrator.
#
# Enforces the orchestrator's core rule mechanically: while an orchestrator run is ACTIVE
# and workable (open, not-in-progress) issues remain, the agent MUST keep working — it
# may NOT end the turn to ask "which issue next?" or "should I continue?". If it tries to
# stop in that state, this hook BLOCKS turn-end (exit 2) and tells it to select the next
# issue and continue.
#
# Session-identity aware (supports multiple concurrent runs in one clone): it reads the
# `session_id` and `stop_hook_active` the harness passes on stdin, maps the session to
# its run via registry.json, and reads ONLY that run's
# runs/<run-id>/resume_state.md. It blocks only when, for THIS run:
#   Status=IN_PROGRESS AND WORKABLE_ISSUES_REMAIN=yes AND AWAITING_USER is none.
# Outside an orchestrator session (no registry entry / no state) it is a no-op.
#
# Loop-safety: if `stop_hook_active` is already true (the turn is continuing because of a
# prior Stop-hook block), it exits 0 so it can never wedge a session.
set -u

input="$(cat)"

jqget() { command -v jq >/dev/null 2>&1 && printf '%s' "$input" | jq -r "$1" 2>/dev/null; }
field_json() { # $1 = key; jq with grep/sed fallback
    local v; v="$(jqget ".$1 // empty")"
    [[ -n "$v" ]] && { printf '%s' "$v"; return; }
    printf '%s' "$input" | grep -oE "\"$1\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | head -1 | sed -E 's/.*"([^"]*)"$/\1/'
}

# Loop-safety guard: do not re-block a turn already continued by a Stop hook.
stop_active="$(field_json stop_hook_active)"
[[ "$stop_active" == "true" ]] && exit 0

sid="$(field_json session_id)"
[[ -z "$sid" ]] && exit 0   # cannot identify the run -> do not interfere

base=".claude/agent-state/issue-work-orchestrator"
[[ -n "${CLAUDE_PROJECT_DIR:-}" && -d "$CLAUDE_PROJECT_DIR/$base" ]] && base="$CLAUDE_PROJECT_DIR/$base"
reg="$base/registry.json"
[[ -f "$reg" ]] || exit 0   # no orchestrator runs registered

# Resolve this session's run_id / state_dir from the registry.
run_dir=""
if command -v jq >/dev/null 2>&1; then
    sd="$(jq -r --arg s "$sid" '.[$s].state_dir // empty' "$reg" 2>/dev/null)"
    [[ -n "$sd" ]] && run_dir="$base/$sd"
fi
# Fallback: derive runs/<first-8-of-sid>/ if the registry has no usable state_dir.
[[ -z "$run_dir" ]] && run_dir="$base/runs/${sid:0:8}"

state="$run_dir/resume_state.md"
[[ -f "$state" ]] || exit 0   # this session is not an active orchestrator run

field() { grep -iE "^[*-]?[[:space:]]*$1:" "$state" | tail -1 | sed -E "s/.*$1:[[:space:]]*//I" | tr -d '\r'; }
status="$(field 'Status')"; remain="$(field 'WORKABLE_ISSUES_REMAIN')"; awaiting="$(field 'AWAITING_USER')"

grep -qiE 'IN_PROGRESS' <<<"$status" || exit 0
if [[ -n "$awaiting" && "$awaiting" != "none" && "$awaiting" != "-" ]]; then
    exit 0   # a genuine, recorded escalation/approval wait is the one allowed pause
fi
if grep -qiE '^(yes|true)$' <<<"$remain"; then
    echo "issue-loop-gate: run ${sid:0:8} is IN_PROGRESS and workable (open, not-in-progress) issues remain." >&2
    echo "Do NOT stop to ask which issue to work next or whether to continue — that is the agent's decision, not the user's." >&2
    echo "Select the next-highest-priority unlocked workable issue yourself (LOAD_ISSUES -> SELECT) and keep working. Stop only at DONE (no workable issue) or a genuine recorded escalation (set AWAITING_USER with a reason in this run's resume_state.md)." >&2
    exit 2
fi
exit 0
