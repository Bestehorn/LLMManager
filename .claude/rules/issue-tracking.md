# Issue Tracking: Checklists, Metadata, and Live Updates (ALL agents, always loaded)

This rule is shared by EVERY agent that touches the issue tracker (issue-intake,
issue-housekeeping, product-management, the issue-work-orchestrator). It is installed at
`.claude/rules/issue-tracking.md` (no `paths:` frontmatter → always loaded) and is
referenced from the project's root `CLAUDE.md`. All tracker operations go through the
project's git wrapper script (`use-git-wrapper-scripts`).

The goal: the issue is the durable, shared record of the work. At any moment, ANY other
agent or human must be able to pick up the issue and continue with minimal lost context
— because progress, decisions, questions, answers, and remaining work are all kept ON
THE ISSUE, updated continuously, not just at the end.

## Best-effort + graceful degradation (GitHub vs GitLab differ)

Issue trackers differ (GitHub, GitLab, others) and not every issue has every feature.
Use whatever the wrapper/host supports; if a specific field or capability is absent for
this host or this issue, skip it cleanly and note that in the agent's log — never treat
a missing optional field as a blocker. The guidance below is the target; apply the parts
the host supports.

## Checklists / work-item lists

- **When filing** an issue whose work naturally decomposes, INCLUDE a structured
  checklist of work items (e.g. GitLab task-list `- [ ] item` entries, which surface as
  "0 of N checklist items completed"; GitHub task lists likewise). One item per concrete
  step a later session would take.
- **During implementation**, USE the checklist: tick items off (`- [x]`) via the wrapper
  as each is genuinely completed (with evidence), and add newly-discovered items rather
  than leaving the list stale. The checklist state on the issue should always reflect
  reality. Historically agents ignored these lists entirely — that is the gap this rule
  closes: the checklist is a living progress record, not decoration.

## Live updates during work (resume-anywhere)

While working an issue, post progress to the issue continuously, not only at the end:
- A short status comment at each meaningful step (what was done, what's next, links to
  the branch/PR/evidence), so the issue alone is enough for another agent to resume.
- Update the checklist as items complete.
- Record the current branch/worktree/PR and the location of the spec/evidence.
The bias is toward over-documenting the issue: if the session is interrupted, the issue
must carry enough context to continue without re-deriving the investigation.

## Questions and answers ALWAYS go on the issue

Any question put to the user about an issue — and the user's answer — MUST be recorded
on the issue (as a comment), verbatim, with enough context to be understood later. A
decision made via a Q&A is part of the issue's history; never let it live only in a
transient chat. (This complements the agent decision log, `DL-NNN`.)

## Metadata fields (set what the host supports)

- **Assignee:** when starting work, assign the issue to the working identity (the
  agent/bot/user account in use) so others see it is being worked. This is also the
  "in progress" claim.
- **Start date / "in progress" timestamp:** record when work started (a start-date
  field if the host has one, else a dated "started" comment).
- **Time tracking:** track the time spent fixing/completing the issue and record it in
  the host's time-tracking field on completion (e.g. GitLab `/spend`); if the host has
  no such field, note elapsed time in the closing comment.
- **Parent / epic / linked issue:** if the issue has a parent (epic, parent issue,
  linked tracking issue), set the corresponding field/link so the hierarchy is intact.
- **State / labels:** move the issue through the host's states (in-progress → closed)
  and apply the project's conventional labels.

## Closing

When the work is done and merged, close the issue with a final comment that links the
merged PR/MR and the evidence, ensures the checklist is fully ticked (or remaining items
are explicitly deferred with a reason), and records the time spent. Leave the issue as a
complete, self-contained record of what was done and proven.
