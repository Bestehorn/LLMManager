#!/usr/bin/env bash
# issue-loop-gate.sh — Stop hook for the issue-work-orchestrator.
#
# Wire as a Stop hook in .claude/settings.json. It enforces the orchestrator's core
# rule mechanically: while an orchestrator run is ACTIVE and there are still workable
# (open, not-in-progress) issues in the backlog, the agent MUST keep working — it may
# NOT end the turn to ask "which issue next?" or "should I continue?". If it tries to
# stop in that state, this hook BLOCKS turn-end (exit 2) and tells it to select the
# next issue and continue.
#
# It reads the orchestrator's resume_state.md
# (.claude/agent-state/issue-work-orchestrator/resume_state.md):
#   - Status:                IN_PROGRESS | COMPLETED | BLOCKED
#   - WORKABLE_ISSUES_REMAIN: yes | no    (maintained by LOAD_ISSUES/SELECT)
#   - AWAITING_USER:          <reason>    (set ONLY for a genuine escalation/poll wait)
#
# It blocks only when Status=IN_PROGRESS AND WORKABLE_ISSUES_REMAIN=yes AND there is no
# legitimate AWAITING_USER reason. Outside an active orchestrator run it is a no-op.
# Claude Code overrides a Stop hook after several consecutive blocks, so this can never
# wedge a session.
set -u

cat >/dev/null   # drain stdin (hook JSON); decision is file-based below.

state=".claude/agent-state/issue-work-orchestrator/resume_state.md"
[[ -n "${CLAUDE_PROJECT_DIR:-}" && -f "$CLAUDE_PROJECT_DIR/$state" ]] && state="$CLAUDE_PROJECT_DIR/$state"
[[ -f "$state" ]] || exit 0   # no orchestrator run -> nothing to enforce

field() { grep -iE "^[*-]?[[:space:]]*$1:" "$state" | tail -1 | sed -E "s/.*$1:[[:space:]]*//I" | tr -d '\r'; }

status="$(field 'Status')"
remain="$(field 'WORKABLE_ISSUES_REMAIN')"
awaiting="$(field 'AWAITING_USER')"

# Only enforce while the run is in progress.
grep -qiE 'IN_PROGRESS' <<<"$status" || exit 0

# A genuine, recorded escalation or approval-poll wait is the one allowed pause.
if [[ -n "$awaiting" && "$awaiting" != "none" && "$awaiting" != "-" ]]; then
    exit 0
fi

# If workable issues remain, stopping now is the forbidden "ask which next" behavior.
if grep -qiE '^(yes|true)$' <<<"$remain"; then
    echo "issue-loop-gate: the backlog still has workable (open, not-in-progress) issues and the orchestrator run is IN_PROGRESS." >&2
    echo "Do NOT stop to ask which issue to work next or whether to continue — that decision is the agent's, not the user's." >&2
    echo "Select the next-highest-priority workable issue yourself (LOAD_ISSUES -> SELECT) and keep working. Stop only at DONE (no workable issue) or a genuine, recorded escalation (set AWAITING_USER with a reason)." >&2
    exit 2
fi

exit 0
