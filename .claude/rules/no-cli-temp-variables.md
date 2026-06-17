# No Ad-hoc Temporary Variables in CLI Commands

Prefer a single pipeline or inlined literals over inventing one-off shell variables.

- If a variable is genuinely unavoidable, use `$v1`/`$v2`/`$v3` for scalars and
  `$l1`/`$l2`/`$l3` for collections.
- If you would need more than three, write a real script under `tmp/` instead.

NOTE: In Claude Code this is a **cleanliness** rule, not an approval-system workaround.
Claude Code does not re-prompt on new shell variable names (that motivation was
Kiro-specific). Keep commands readable and reproducible; clean up any `tmp/` scripts
afterward (see `.claude/rules/file-organization.md`).
