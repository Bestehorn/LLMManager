#!/usr/bin/env bash
# no-env-vars.sh — PreToolUse(Bash) gate enforcing .claude/rules/no-environment-vars.md
#
# This system hosts multiple projects. Setting shell environment variables such as
# AWS_PROFILE / AWS_REGION / AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / GITHUB_TOKEN /
# GITLAB_TOKEN leaks state across projects and causes cross-project breakage. This hook
# reads the hook JSON on stdin, inspects the Bash command, and BLOCKS (exit 2) when the
# command tries to set one of those variables via `export`, `setx`, `set VAR=`, or
# PowerShell `$env:VAR=`. Exit 2 feeds the stderr message back to Claude.
#
# It does NOT block reading those variables, nor inline single-command assignments that
# do not persist (those are rare in this project's workflow); it targets the persisting /
# exporting forms that pollute the session. The `env` blocks inside .mcp.json and
# .claude/settings.json are NOT shell env vars and are unaffected.

set -u

input="$(cat)"

cmd=""
if command -v jq >/dev/null 2>&1; then
  cmd="$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null)"
fi
if [[ -z "$cmd" ]]; then
  cmd="$(printf '%s' "$input" | grep -oE '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed -E 's/.*:[[:space:]]*"(.*)"/\1/')"
fi

[[ -z "$cmd" ]] && exit 0

# The protected variable names (AWS_* family plus the git host tokens).
vars='AWS_PROFILE|AWS_REGION|AWS_DEFAULT_REGION|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|AWS_SESSION_TOKEN|GITHUB_TOKEN|GH_TOKEN|GITLAB_TOKEN'

# export VAR=... | export VAR (bash/sh) ; setx VAR ... (Windows) ; set VAR=... (cmd) ;
# $env:VAR = ... (PowerShell)
if grep -qiE "(^|[;&|[:space:]])(export|setx)[[:space:]]+($vars)\b" <<<"$cmd" \
   || grep -qiE "(^|[;&|[:space:]])set[[:space:]]+($vars)=" <<<"$cmd" \
   || grep -qiE "\\\$env:($vars)[[:space:]]*=" <<<"$cmd"; then
  echo "no-env-vars: setting a shell environment variable (AWS_*/GITHUB_TOKEN/GITLAB_TOKEN) is forbidden — it leaks state across the projects on this machine. Pass profile/region explicitly to boto3/CLI and read credentials from config/ and credentials/. See .claude/rules/no-environment-vars.md." >&2
  exit 2
fi

exit 0
