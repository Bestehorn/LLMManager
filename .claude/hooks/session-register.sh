#!/usr/bin/env bash
# session-register.sh — SessionStart hook. Records this session's identity so the
# issue-work-orchestrator and the gate hooks can tell WHICH run owns the session
# (resolving the "who is doing what" ambiguity when several runs share one clone).
#
# Wire as a SessionStart hook in .claude/settings.json. Claude Code passes session_id,
# cwd, source, and hook_event_name on stdin. This hook upserts an entry keyed by
# session_id into the orchestrator's registry.json so:
#   - the running agent can read registry.json to learn its own session_id / run_id and
#     create its runs/<run-id>/ state subtree;
#   - the Stop/PreToolUse gate hooks can map the current session_id back to its run and
#     read ONLY that run's state (instead of guessing by global file recency).
#
# It is intentionally minimal and non-blocking: SessionStart hooks cannot block, and a
# best-effort registry write must never break session startup. If jq is unavailable it
# falls back to a grep/sed extraction. It does NOT decide run ownership of issues (that
# is the agent's locking job) — it only records identity.
#
# No environment variable carries the session id (none exists); identity flows via the
# stdin session_id + this on-disk registry, consistent with the no-environment-vars rule.
set -u

input="$(cat)"

# Extract session_id and cwd (jq preferred; grep/sed fallback).
sid=""; cwd=""
if command -v jq >/dev/null 2>&1; then
    sid="$(printf '%s' "$input" | jq -r '.session_id // empty' 2>/dev/null)"
    cwd="$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)"
fi
if [[ -z "$sid" ]]; then
    sid="$(printf '%s' "$input" | grep -oE '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed -E 's/.*"([^"]*)"$/\1/')"
fi
[[ -z "$sid" ]] && exit 0   # nothing to record; do not disturb startup
if [[ -z "$cwd" ]]; then
    cwd="$(printf '%s' "$input" | grep -oE '"cwd"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed -E 's/.*"([^"]*)"$/\1/')"
fi

reg_dir=".claude/agent-state/issue-work-orchestrator"
[[ -n "${CLAUDE_PROJECT_DIR:-}" && -d "$CLAUDE_PROJECT_DIR" ]] && reg_dir="$CLAUDE_PROJECT_DIR/$reg_dir"
mkdir -p "$reg_dir" 2>/dev/null || exit 0
reg="$reg_dir/registry.json"
[[ -f "$reg" ]] || echo '{}' > "$reg"

run_id="${sid:0:8}"
ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"

# Upsert the entry. Use jq if available; else only create the file if missing (the agent
# will reconcile/fill its own entry from session_id on first read — the hook's job is
# just to guarantee the session_id is on disk keyed for lookup).
if command -v jq >/dev/null 2>&1; then
    tmp="$reg.tmp.$$"
    if jq --arg sid "$sid" --arg rid "$run_id" --arg cwd "$cwd" --arg ts "$ts" '
        .[$sid] = ((.[$sid] // {}) + {
            session_id: $sid, run_id: $rid, cwd: $cwd,
            state_dir: ("runs/" + $rid + "/"),
            status: ((.[$sid].status) // "starting"),
            started_at: ((.[$sid].started_at) // $ts),
            last_heartbeat: $ts })' "$reg" > "$tmp" 2>/dev/null; then
        mv "$tmp" "$reg" 2>/dev/null || rm -f "$tmp"
    else
        rm -f "$tmp"
    fi
fi

exit 0
