# Agent State & Decision-Log Convention (ALL agents)

This rule is shared by EVERY custom agent in this project — the spec-workflow
agents AND the ported agents (dead-code, doc-review, ci-worker, issue-housekeeping,
issue-intake, product-management, the cv/* suite). It is installed at
`.claude/rules/agent-state-convention.md` (no `paths:` frontmatter → always loaded)
and is pointed to from the project's root `CLAUDE.md`, so every agent observes it
without its own body being edited.

It codifies two things that the agents already do informally, and makes them
uniform and mandatory: (1) where agent state lives, and (2) an append-only,
cross-agent **decision log** so decisions and the discussion behind them are
preserved for later agents and future sessions.

## 1. State directory

Every agent keeps its resume/log artifacts under:

```
.claude/agent-state/<agent-name>/
```

`<agent-name>` is the agent's canonical name (its `name:` frontmatter, e.g.
`spec-conductor`, `dead-code-removal-agent`, `cv-editor`). Typical artifacts:
`resume_state.md` (Status + phase + counters + git HEAD + source mtimes),
`iteration_log.md`, `evidence_ledger.md`, and any agent-specific logs. Create the
directory (and missing parents) on first use. Archive a completed/stale artifact by
suffixing an ISO timestamp (e.g. `resume_state.2026-06-09T14-02-11Z.md`); never
delete history. `.claude/agent-state/` is gitignored (per-run runtime state).

The spec-workflow master state lives at
`.claude/agent-state/spec-conductor/workflow_state.md`.

## 2. The decision log (mandatory for all agents)

Whenever an agent makes a **non-trivial decision** — a design choice, a
classification, a fix approach, a candidate selection, a convergence/exit call, an
escalation — it appends one entry to a decision log. This is the durable record
other agents and later sessions read to understand *why* the project is the way it
is. It is NOT optional and it is NOT only for the spec agents.

### Where to write

- If the agent is operating in a **spec context** (a `.claude/specs/<feature>/`
  directory is the subject of the work), append to:
  `.claude/specs/<feature>/decisions/decision-log.md`.
- Otherwise (an agent with no spec context, e.g. dead-code or doc-review on a
  general run), append to:
  `.claude/agent-state/<agent-name>/decision-log.md`.

Create the file with an `# Decision Log` header on first use.

### Entry schema (fixed, append-only)

```markdown
## DL-<nnn> — <ISO-timestamp> — <agent-name> — phase:<PHASE-or-"n/a">

**Decision:** <one sentence: what was decided>
**Driver:** <what forced it — requirement IDs, finding IDs (A2/B1), user answer Q###, a failing test, an MCP source>
**Alternatives considered:** <one line each, or "none">
**Evidence:** <path:line | command output ref (evidence/...) | review/<r>/iteration-NN.md#A2 | MCP/web citation>
**Supersedes:** <DL-mmm, or "none">
**Artifacts touched:** <files written/edited>
```

### Rules

1. **Append-only.** Never edit or delete a prior entry. To change a past decision,
   write a NEW entry whose `Supersedes:` points at the old `DL-mmm`.
2. **Monotonic IDs.** `DL-001`, `DL-002`, … never reused, never rewound. The next
   number is `max(existing DL-NNN) + 1` — scan the file to determine it (the file is
   authoritative; do not restart at 001 on a resumed session).
3. **Evidence required.** Every entry cites concrete evidence (this reuses the
   project's No-Guessing rule). A decision with no citable driver/evidence is itself
   a defect — gather the evidence or do not record the decision as made.
4. **Granularity.** Record decisions, not narration. One entry per decision; do not
   log every file read. The conductor writes an entry at each phase transition and
   after each applied finding-batch; a reviewer writes an entry for each material
   classification call it could not derive mechanically; an implementer writes an
   entry per task for the approach taken (citing the design section it implements).

### For the ported agents (no body rewrite)

The ported agents already maintain `.claude/agent-state/<agent>/` state. This rule
ADDS the decision-log requirement to them uniformly: when any of them makes a
decision of the kind listed above, it appends a `DL-NNN` entry per the schema, to
the spec `decisions/decision-log.md` if a spec context exists, else to its own
state dir. No change to their prompt bodies is needed — they inherit this because
the rule is always-loaded and referenced from `CLAUDE.md`.
