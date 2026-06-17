# Never Set Shell Environment Variables

This system hosts multiple projects. Setting shell environment variables leaks state
across projects and causes cross-project breakage.

- NEVER `set`, `setx`, `export`, or `$env:VAR=...` an environment variable —
  especially `AWS_PROFILE`, `AWS_REGION`, `AWS_DEFAULT_REGION`, `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `GITHUB_TOKEN`, `GH_TOKEN`,
  `GITLAB_TOKEN`.
- Pass profile/region explicitly to boto3 sessions and CLI commands
  (`boto3.Session(profile_name=..., region_name=...)`).
- Read credentials from project-local files (`config/`, `credentials/`).

**This is a hard rule, enforced**: the `PreToolUse` hook
`.claude/hooks/no-env-vars.sh` blocks any Bash command that exports one of the
protected variables (exit code 2).

CLARIFICATION: the `env` blocks inside `.mcp.json` and `.claude/settings.json` are NOT
shell environment variables — they are scoped configuration for a specific subprocess
(an MCP server) or for Claude Code itself, and do not pollute global shell state. Leave
them intact.
