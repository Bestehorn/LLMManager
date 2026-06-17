# Evidence, Not Guessing

Every claim you make to the user about actual behavior must be backed by evidence:
command output, file contents, test results, or a documentation lookup.

- Do not assert that something "works", "passes", "is fixed", or "is configured" unless
  you have just observed it. Run the command and read the output
  (`.claude/rules/no-output-shortening.md`).
- Do not invent an API signature, a config key, or a model id from memory — look it up
  (the codebase, `pyproject.toml`, or the doc MCP servers per
  `.claude/rules/use-doc-mcp-servers.md`).
- Avoid hedge words ("should work", "probably", "I think it does X") when describing
  real behavior. Either you verified it — say so and show the proof — or you have not —
  say that plainly and go verify.
- If a test fails, report the failure with the output. If a step was skipped, say so.
  When something is done and verified, state it plainly without hedging.
