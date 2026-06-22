# Adversarial Refutation Report — issue #39 (Bedrock Converse prompt-caching parity)

Verifier: adversarial-verifier. All commands run inside the worktree venv
(`venv/Scripts/python`, Python 3.14.2) at
`D:\Users\bestem\CodeWorkspace\LLMManager\.claude\worktrees\issue-39`.

## 1. Independent full-suite re-run (not trusting prior evidence)

| Run | Command | Result | Capture |
|-----|---------|--------|---------|
| Single-process | `python -m pytest test/bestehorn_llmmanager/ -p no:cacheprovider -q -p no:randomly` | 2833 passed, 7 skipped, 0 failed, EXIT=0 (325.52s) | `full-suite.txt` |
| xdist `-n auto` (post-restore) | `python -m pytest test/bestehorn_llmmanager/ -p no:cacheprovider -n auto -q` | 2833 passed, 7 skipped, 0 failed (220.51s) | `full-suite-restored-xdist.txt` |

The 7 skips are pre-existing and unrelated to issue #39 (six `test_constants.py`
"Python doesn't enforce Final immutability" skips + catalog integration data-gated
skips). No issue-39 test is skipped/xfail/deleted/commented-out. No FAILED/ERROR.

## 2. Coverage of the changed code

| Command | Result |
|---------|--------|
| focused tests `--cov=...cache_point --cov=...cache_detail --cov-report=term-missing` | cache_point.py 16/16 = **100%**, cache_detail.py 10/10 = **100%** |
| `--cov=...bedrock_response --cov=...event_handlers` (whole test files) | event_handlers.py **100%**; bedrock_response.py 94% — the only NEW uncovered lines are the defensive `except` returns at 377-378 (BedrockResponse.get_cache_details) and 1459-1460 (StreamingResponse.get_cache_details) |

Net: every functional line of the new code (happy path, empty, failed, no-data,
streaming, streaming-empty, tool passthrough) is executed by tests. See finding F1
for the two defensive `except` lines.

## 3. Kill-the-mutant — does each test actually pin its behavior?

Every mutant below produced an **AssertionError / `Failed: DID NOT RAISE` /
runtime TypeError in the code under test** — never an ImportError/CollectionError —
so each paired test fails for the right reason. All mutants restored afterward;
final tree verified mutation-free.

| Mutant | What was broken | Paired test(s) | Result | Capture |
|--------|-----------------|----------------|--------|---------|
| M1 | cache_point.py: dropped the `ttl not in _VALID_CACHE_TTLS` raise | `test_invalid_ttl_rejected`, `TestAddCachePointTTL::test_cache_point_invalid_ttl_rejected` | 2 FAILED (DID NOT RAISE) → caught | `mutant-1-ttl-validation.txt` |
| M2 | cache_point.py: dropped the `cache_type not in _VALID_CACHE_TYPES` raise | `test_invalid_type_rejected`, `TestAddCachePointTTL::test_cache_point_invalid_type_rejected` | 2 FAILED (DID NOT RAISE) → caught | `mutant-2-type-validation.txt` |
| M3 | cache_point.py: never write ttl into the block | 6 FAILED across all 3 claim areas incl. tool-config passthrough | caught | `mutant-3-ttl-never-included.txt` |
| M4 | cache_point.py: removed `if ttl is not None` guard (always process ttl) | `test_default_without_ttl_omits_ttl_key`, `test_default_cache_point_unchanged_without_ttl` | 2 FAILED → caught | `mutant-4-backward-compat-default.txt` |
| M4b | cache_point.py: set `ttl` key unconditionally (even None) | same backward-compat pair | 2 FAILED (block carried `ttl: None`) → caught | `mutant-4b-default-block-ttl-key.txt` |
| M5 | bedrock_response.py: removed the `not self.success` guard in `get_cache_details()` | `test_failed_response_returns_empty` | 1 FAILED → caught | `mutant-5-success-guard.txt` |
| M6 | bedrock_response.py: removed BOTH `or []` and the try/except | `test_no_cache_details_returns_empty` | 1 FAILED (uncaught TypeError on absent cacheDetails) → caught | `mutant-6-or-empty-fallback.txt` |
| M7 | event_handlers.py: dropped the `usage.get(FIELD_CACHE_DETAILS, [])` wiring | `test_extract_token_usage_full` | 1 FAILED → caught | `mutant-7-streaming-wiring.txt` |
| M8 | bedrock_response.py: StreamingResponse.get_cache_details reads WRONG_KEY | `test_streaming_cache_details` | 1 FAILED → caught | `mutant-8-streaming-getcachedetails.txt` |
| M9 | llm_manager.py: strip cachePoint tool entries instead of verbatim forward | `test_build_converse_request_tool_config_with_cache_point` | 1 FAILED → caught | `mutant-9-toolconfig-passthrough.txt` |
| M10 | __init__.py: dropped `build_cache_point` from `__all__` | `test_init.py::test_all_exports` | 1 FAILED → caught | `mutant-10-init-all-exports.txt` |

## 4. Per-claim verdicts

| Claim | Behavior/property | Verdict |
|-------|-------------------|---------|
| **Claim 1 — Cache-point TTL** | `add_cache_point(ttl=)` validates ttl (M1) and type (M2); ttl is included when valid (M3); identical legacy block when ttl omitted (M4, M4b); centralized in `build_cache_point`. | **FAILED-TO-REFUTE** (claim survives) |
| **Claim 2 — Tool-definition caching** | `build_cache_point(...)` appended to `toolConfig.tools` is forwarded verbatim by `_build_converse_request` (M9), with the ttl intact (M3). | **FAILED-TO-REFUTE** |
| **Claim 3 — `usage.cacheDetails[]` parsing** | `BedrockResponse.get_cache_details()` parses (covered), is empty on failed (M5) / absent (M6); `StreamingResponse.get_cache_details()` parses streaming data (M8); streaming usage normalizer threads `cache_details` (M7). | **FAILED-TO-REFUTE** |
| **Exports** | `CachePointTTLEnum`, `CacheDetail`, `build_cache_point` in `__all__` and importable (M10). | **FAILED-TO-REFUTE** |

## 5. Vacuity / dodge / red-for-right-reason audit

- No skip/xfail/commented-out/deleted tests in any issue-39 file.
- Assertions are exact-dict / tuple-list / `pytest.raises(..., match=)` — not
  `is not None`/`hasattr`-only. `test_init` combines `in __all__` + `hasattr`
  (M10 confirms it is non-vacuous). `test_is_frozen` asserts mutation raises
  AttributeError (meaningful).
- No Hypothesis `@given` tests in this deterministic feature → property-stress N/A.
- No `evidence/red/` dir (issue-orchestrator run, not formal spec-conductor TDD);
  the mutation matrix above is the red-state proof and every red was an assertion/
  raise/runtime failure in the code under test, never a load error.

## 6. Quality gates

| Gate | Command | Result | Capture |
|------|---------|--------|---------|
| ruff format | `ruff format src/ test/ scripts/ --check` | 254 files already formatted | `ruff-format.txt` |
| ruff check | `ruff check src/ test/ scripts/` | All checks passed! | `ruff-check.txt` |
| mypy | `mypy --exclude="_version" src/` | Success: no issues found in 108 source files | `mypy.txt` |

## 7. Findings

- **F1 (LOW / B-level)** — The two defensive `except (KeyError, TypeError,
  AttributeError): return []` branches in `get_cache_details` (bedrock_response.py
  377-378 and 1459-1460) are not exercised by any test (no test feeds a malformed
  `usage`/`usage_info` that throws). Functional behavior is fully pinned; this is
  belt-and-suspenders error handling only. M6 also shows the `or []` and the
  try/except are partially redundant for the absent-key case (each alone, plus the
  net behavior, is what the test pins). Not a refutation; an optional hardening test
  could cover the except branch.

## 8. Tree restoration

- All 11 mutations (M1, M2, M3, M4, M4b, M5, M6, M7, M8, M9, M10) reverted.
- `grep MUTANT/WRONG_KEY` over tracked diff and untracked new files: CLEAN.
- `git diff --stat -- src/ test/`: purely additive (229 insertions, 5 deletions —
  the 5 deletions are the original feature edit in message_builder.py replacing the
  inline `{"type": cache_type}` literal with `build_cache_point(...)`), matching the
  implementation as first read. `git status` shows only the expected modified files
  + 3 new files + the spec dir.
- Suite green again post-restore: focused 73 passed (`focused-suite-restored.txt`);
  full xdist 2833 passed / 7 skipped / 0 failed (`full-suite-restored-xdist.txt`).

## FINAL VERDICT

**VERIFIED** — 0 of 11 mutation-backed claim checks refuted; coverage of the new
code is 100% on both new model files and 100% on the changed event_handlers lines,
with only two defensive `except` lines in bedrock_response uncovered (F1, low). All
three feature claims plus the public exports survive adversarial refutation.
