---
description: Run coverage analysis and add tests until the configured 80% threshold is met.
allowed-tools: Bash, Read, Edit, Grep, Glob
---
Ported from `.kiro/hooks/test-coverage.kiro.hook` and `test-automation.kiro.hook`. USE THE
VENV for all steps. Read complete output (no tail/head/Select-Object).

1. **Run coverage analysis**:
   `venv\Scripts\activate & pytest test/ --cov=bestehorn_llmmanager --cov-report=term-missing --cov-report=html`
   Note the current coverage percentage and which files/lines are uncovered.
2. **Check the target**: read `[tool.pytest.ini_options]` in `pyproject.toml` —
   `--cov-fail-under=80`. Determine if current coverage meets it.
3. **Identify gaps**, prioritizing critical paths:
   - `LLMManager.invoke()` / `invoke_with_retry()` / streaming
   - `MessageBuilder` fluent interface (`add_text`, `add_image`, `add_document`, `add_video`)
   - `ParallelLLMManager`
   - `UnifiedModelManager` / `ModelManager` / `CRISManager` availability + fallback logic
   - the catalog system (`BedrockCatalog`, `APIFetcher`, `CacheManager`, `BundledLoader`, `Transformer`)
   - error-handling paths and exception classes
   - edge cases: empty inputs, invalid model IDs, network failures, throttling, cache miss/hit, malformed responses
4. **Add tests** until the threshold is met:
   - Unit tests in `test/bestehorn_llmmanager/` (mirrors `src/`); for `src/bestehorn_llmmanager/x.py`
     create `test/bestehorn_llmmanager/test_x.py`.
   - Integration tests needing AWS Bedrock go in `test/integration/`.
   - Use pytest fixtures (`test/conftest.py`, `test/integration/conftest.py`) and `hypothesis`
     for property-based testing where applicable.
5. **Verify**: re-run with `--cov-fail-under=80` until coverage increases and all new tests pass.
6. **Quality-check the new tests**:
   `black test/ --check --extend-exclude="src/bestehorn_llmmanager/_version.py"`,
   `isort test/ --check-only --skip="src/bestehorn_llmmanager/_version.py"`,
   `flake8 test/ --max-line-length=100 --extend-ignore=E203,W503`.
7. **Report**: initial vs final coverage, tests added (by category: unit / integration /
   property-based / edge), files created/modified, functions now covered, and any remaining
   gaps with justification.

Do not consider this complete until coverage ≥ 80% and all tests pass.

**Project-specific notes**: always exclude `src/bestehorn_llmmanager/_version.py`; line length
100; coverage package path `bestehorn_llmmanager`; Windows activation `venv\Scripts\activate`.
