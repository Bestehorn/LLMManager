# Phase Fragment: REQUIREMENTS + DESIGN

Followed by `spec-conductor`. Generates the requirements and design artifacts by
delegating to `spec-author`. Installed at
`.claude/specs/_workflow/phases/spec-phase-design.md`.

## REQUIREMENTS

Invoke `spec-author` (Agent tool) with: the spec directory, `prompt.md` as input, and
the feature kind.
- FEATURE → it writes `requirements.md`: a Feature Overview, a Glossary, and numbered
  Requirements, each a User Story plus EARS acceptance criteria (every criterion uses
  exactly one EARS pattern: ubiquitous / `WHILE` / `WHEN` / `WHERE` / `IF…THEN`, with
  `SHALL`). Criteria are concrete and testable; no hedge words.
- BUGFIX → it writes `bugfix.md`: Introduction; `### Current Behavior (Defect)`,
  `### Expected Behavior (Correct)`, `### Unchanged Behavior (Regression Prevention)`
  — all numbered EARS statements, the defect and regression clauses citing code at
  file:line.

After it returns, append a `DL-NNN` entry (requirements generated) and transition to
DESIGN.

## DESIGN

Invoke `spec-author` to write `design.md` from the requirements. The design MUST
contain these sections (the conductor rejects a design missing any and re-delegates):
- **Overview**, **Architecture**, **Component Design** (each component cites the
  existing codebase pattern it follows at file:line; deviations flagged).
- **## Testing Strategy** — the layers that apply (unit / integration /
  property-based via Hypothesis / IaC-CDK), and where each lives under `test/`.
- **## Correctness Properties** — one `### Property N: <name>` per property,
  annotated `**Validates: <requirement IDs>**`, stated in prose then as a Hypothesis
  `@given(...)` sketch with a real assertion. EVERY requirement is covered by ≥1
  property.
- **## Security Considerations** — trust boundaries, inputs to validate, secrets
  handling, least-privilege IAM (for CDK), explicit out-of-scope.
- **## DevOps & Operability** — deployment mechanism, observability (logs/metrics/
  alarms), rollback/failure behavior.
- **## Acceptance Criteria Mapping** — a table mapping every acceptance criterion (or
  bugfix EARS statement, including each regression clause) → design component → how
  it is validated (test/property).

After it returns, append a `DL-NNN` entry (design generated) and transition to
DESIGN_REVIEW_LOOP (see `spec-phase-review.md`).

## Notes

- The conductor never writes these files itself; `spec-author` does. The conductor
  only verifies the mandatory sections are present before moving on.
- All codebase claims in the design are evidence-cited; external-technology choices
  are MCP/web-cited (the author consults them, the best-practice-reviewer audits them
  in the next phase).
