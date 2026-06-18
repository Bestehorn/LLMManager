# No AI Attribution; Descriptive Names Only (ALL agents, always loaded)

This rule is shared by EVERY agent and by the main session. It is installed at
`.claude/rules/no-ai-attribution.md` (no `paths:` frontmatter → always loaded) and is
pointed to from the project's root `CLAUDE.md`. It governs every name and every piece of
text that goes onto the repository or its tracker.

## The rule

**Never attribute work to Claude, an AI, an assistant, or a tool, anywhere. Never put
"claude" (or "AI", "assistant", "bot", "LLM", "Anthropic", "Copilot", a model name,
etc.) into any name or message you create.** Whether a change was made by a human or by
an agent is irrelevant to the repository and must not appear in it.

This applies to ALL of the following, with NO exceptions:

- **Commit messages** — no `Co-Authored-By: Claude …`, no `🤖 Generated with Claude
  Code`, no "authored by Claude", no AI/tool trailer or footer of any kind. The commit
  message describes the change and nothing about who or what produced it.
- **Pull/merge request titles and bodies** — same: no "Generated with Claude Code",
  no 🤖 line, no AI attribution. Describe the change, the root cause, the fix, and the
  evidence — not the author.
- **Issue titles, bodies, and comments** — no AI attribution, no "filed/fixed/triaged
  by <agent>" sign-off, no 🤖 line.
- **Branch names** — descriptive of the work or the issue (e.g.
  `issue-53-relevance-exclusion-fix`, `fix-customer-count-zero`,
  `feature-multi-trend-export`). NEVER the Claude-Code auto-generated style
  (`claude/<adjective>-<name>`, `claude/admiring-wozniak-26094b`, etc.) and never any
  name containing "claude"/"ai"/"bot".
- **Worktree directory names** — likewise descriptive (the orchestrator uses
  `.claude/worktrees/issue-<N>/`, which is a fixed path under the tool's config dir, not
  an identity label — that is fine; what is forbidden is inventing a `claude/…`-style or
  AI-themed NAME for a branch/worktree).
- **Tags, stashes, and any other git ref or label** you create.

> Note: the `.claude/` configuration directory itself (e.g. `.claude/agents/`,
> `.claude/specs/`, `.claude/worktrees/`) is the tool's fixed config location and is not
> covered by this rule — those paths are infrastructure, not names you are choosing for
> work products. This rule is about the NAMES and MESSAGES you author for commits,
> PRs/MRs, issues, branches, worktrees, and tags.

## Naming standard (positive form)

Every name you create MUST describe what the thing does or the issue it addresses:
- Branches/worktrees: `<type>-<issue-or-topic>-<short-slug>`, e.g.
  `fix-issue-77-invoke-grant`, `refactor-s3-request-scoping`. Prefer including the issue
  number when the work maps to one issue.
- Commit subjects: imperative, ≤72 chars, describing the change
  (`fix(relevance): drop IRRELEVANT insights despite keyword match`).
- PR/MR titles: the outcome (`Fix off-topic topic leak in MultiDoc relevance filter`).

## Overriding the tool defaults (IMPORTANT)

Claude Code and some git integrations add AI attribution BY DEFAULT — a
`Co-Authored-By: Claude` / `🤖 Generated with Claude Code` trailer on commits and PRs,
and a `claude/<adjective>-<surname>` auto-name when a branch/worktree is created without
an explicit name. You MUST suppress these:
- When committing, write ONLY your descriptive message; do not append, and actively
  remove, any AI/tool trailer or co-author line.
- When opening a PR/MR, the body is exactly your description + evidence; strip any
  auto-added "Generated with …" line.
- When creating a branch or worktree, ALWAYS pass an explicit descriptive name; never
  let the tool assign a `claude/…` name. If you find yourself on an auto-named
  `claude/*` branch, rename it to a descriptive name before pushing.

## Self-check before any commit / PR / issue / branch

Before you create a commit, PR/MR, issue, comment, branch, or worktree, scan the name
and the full text for: `claude`, `Claude`, `AI`, `assistant`, `bot`, `LLM`, `Anthropic`,
`Copilot`, `🤖`, `Co-Authored-By`, `Generated with`, `Co-authored`. If any appears as
attribution or in a name, remove it and restate descriptively. A name or message that
identifies the author as an AI/tool is a defect — fix it before the artifact is created.
