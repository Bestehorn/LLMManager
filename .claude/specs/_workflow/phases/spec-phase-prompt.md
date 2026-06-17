# Phase Fragment: PROMPT_AUTHORING

This procedure is followed by `spec-conductor` (as part of the full pipeline) and by
the `/spec-new` command (standalone). It produces the initial prompt that drives the
whole spec. It is conducted by the MAIN session (the conductor or the command's
session), because a delegated subagent cannot run a multi-turn user interview.

Installed location in a project: `.claude/specs/_workflow/phases/spec-phase-prompt.md`.

## Goal

Through a structured interview, converge with the user on a precise, evidence-grounded
initial prompt for the feature/bugfix, and write:
- `.claude/specs/<feature>/prompt.md` — the final prompt.
- `.claude/specs/<feature>/prompt-discussion.md` — the synthesized decision record.
- `.claude/specs/<feature>/qa_log.md` — the append-only Q&A transcript.

## The Questioning Protocol (strict)

1. **One question per message.** Never present a numbered list for bulk answering.
   (The sole exception is the very first question: the feature/topic name.)
2. **Clarity-first ordering.** Maintain an internal queue ordered by decreasing
   clarity impact: scope/approach/fundamental-constraint questions before detail
   questions; ask the question whose answer resolves or obsoletes the most others
   next. Re-evaluate the queue after every answer (remove obsoleted questions, add
   newly-opened ones). Do not announce the re-evaluation.
3. **Closed-form preferred**, in this order: (a) Yes/No framed as a concrete proposal;
   (b) 2–5 numbered options, each with its one-line consequence, and YOUR recommended
   option with evidence; (c) constrained-open with bounds + an example; (d) open
   (last resort, with context).
4. **Evidence-grounded.** Before asking, do the research to make the question
   concrete. Delegate stateless research to the `spec-researcher` subagent (e.g.
   "how is auth configured in src/?") and fold its cited findings into the question.
   Never ask a question whose answer is already determinable from the codebase,
   steering rules, or a prior answer — state the determination and move on.

## Q&A persistence (so the interview survives interruption)

`qa_log.md` is append-only with monotonic `Q001`, `Q002`, … :
- BEFORE emitting a question, append its block (`Status: EMITTED`, the verbatim
  question, its evidence basis, options, your recommendation).
- IMMEDIATELY on receiving the answer, append the answer block (`Status: ANSWERED`,
  verbatim answer, one-line resolution) before doing any work triggered by it.
- On resume, scan `qa_log.md`: continue numbering from the last `Qnnn`; if the last
  question is `EMITTED` without an `ANSWERED`, treat the user's current message as its
  answer (or re-emit it verbatim if the user said "resume"); never re-ask an answered
  question. Emit a one-line "resumed; decisions so far: …" before the next question.

## Phases of the interview

0. **Topic.** First question: the feature/topic name. Slugify it to `<feature>`;
   create `.claude/specs/<feature>/`. If a seed idea/file came with the invocation,
   read it and skip asking for the idea.
1. **Intent.** Problem solved, users/consumers, inputs/outputs, explicit
   out-of-scope, constraints (perf/security/compat). Determine FEATURE vs BUGFIX.
2. **Research & validate.** As intent firms up, search the codebase for existing
   patterns and duplication, query MCP servers for best practices, present findings
   as context for the next question.
3. **Draft & confirm.** Draft `prompt.md` and present it; iterate one question at a
   time on the draft. The prompt must state: the goal, the FEATURE/BUGFIX kind, the
   concrete scope and out-of-scope, the codebase integration points (cited), the
   constraints, and an explicit instruction that the spec must include a Testing
   Strategy + Correctness Properties and that implementation is test-first with
   evidence-based proof.

## On completion

Write `prompt.md` and `prompt-discussion.md` (organized by decision: the question,
the evidence gathered, the user's answer, the resolution). Append a `DL-NNN` entry
recording the prompt is finalized. The conductor then transitions to REQUIREMENTS;
`/spec-new` stops here and tells the user the prompt is ready (and that
`claude --agent spec-conductor` will carry it forward, or `/spec-review` etc.).
