---
description: Autonomously work the open-issue backlog end to end — select the highest-priority not-in-progress issue, fix it via the spec/TDD cycle with proof, open a PR, drive CI green, merge, clean up, close, and repeat. Resumable.
argument-hint: "[optional: a specific issue number to start with, or blank to work the whole backlog]"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, WebSearch, WebFetch, Agent(spec-author, spec-researcher, spec-review-agent, test-architect, standards-reviewer, best-practice-reviewer, security-reviewer, devops-iac-reviewer, adversarial-verifier, spec-implementer)
---

Run the autonomous issue-work lifecycle for this project, following the agent
definition in `.claude/agents/issue-work-orchestrator.md` exactly. (This command runs
the orchestrator's logic in the current session; for a dedicated long run you may
instead launch `claude --agent issue-work-orchestrator`.)

First, **resume check**: read
`.claude/agent-state/issue-work-orchestrator/resume_state.md`. If it exists and shows
`Status: IN_PROGRESS`, CONTINUE the recorded outer phase for the recorded current issue
(re-attach to any in-flight worktree / branch / PR) — do not restart the backlog. If it
shows `Status: COMPLETED`, archive it and start fresh.

If $ARGUMENTS names a specific issue number, prioritize that issue first; otherwise work
the whole backlog by impact/urgency/severity.

Then run the lifecycle from `issue-work-orchestrator.md`: Discovery (venv, ISSUE_MECHANISM
via the wrapper script, in-progress convention, merge authority, clean tree) → the outer
loop LOAD_ISSUES → SELECT → PREPARE (worktree + branch) → CLASSIFY (Type1/Type2) → FIX
(embedded spec/TDD core, proof with evidence) → PROOF_GATE → DOCUMENT → PR (rebase,
line-by-line conflict resolution, push, open, self-approve+merge if allowed, monitor CI)
→ MERGE_CLEANUP → RESOLVE → refresh, until no not-in-progress open issue remains.

Honor all the mandates in the agent definition: wrapper-only remote ops, evidence-not-
assertion (the implementer never certifies its own work; the adversarial-verifier
refutes), no workarounds, never overwrite others' changes, checkpoint after every step,
escalate only once when genuinely blocked, and never touch `.kiro/`.
