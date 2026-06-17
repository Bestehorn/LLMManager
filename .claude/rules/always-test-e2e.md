# Always Prove It End-to-End

A change is not done when the code compiles or a unit test passes in isolation — it is
done when you have demonstrated the behavior works in the realest way available.

- Prefer running the actual flow over asserting it from inspection. For this library,
  that means exercising the public surface (`LLMManager`, `ParallelLLMManager`,
  `MessageBuilder`, the catalog system) through tests, not just the internals.
- Add a test that reproduces the bug/feature symptom and watch it go from red to green.
- AWS-dependent behavior: cover it with mocked unit tests AND, where feasible, an
  integration test under `test/integration/` (marked with the appropriate `aws_*`
  markers so it can be skipped without credentials). Note any path you could only verify
  with mocks.
- Capture the evidence (command + output) so the proof is reproducible, per
  `.claude/rules/no-guessing.md`.
