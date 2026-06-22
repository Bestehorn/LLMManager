# Decision Log

## DL-001 — 2026-06-22 — issue-work-orchestrator — phase:FIX

**Decision:** Implement the three guardrail capabilities as: (1) `MessageBuilder.add_guard_content(text, qualifiers=None)` producing a `guardContent` block (`{guardContent: {text: {text, qualifiers?}}}`), with a new `GuardContentQualifierEnum` (grounding_source|query|guard_content) validating qualifiers; (2) `BedrockResponse.get_guardrail_trace()` + `StreamingResponse.get_guardrail_trace()` returning the `trace.guardrail` assessment dict; (3) a `stream_processing_mode` parameter on `converse_stream()` (and `_build_converse_request`) that injects `streamProcessingMode` into `guardrailConfig`.
**Driver:** Issue #38 desired behavior + AWS shapes: GuardrailConverseContentBlock (text|image union), GuardrailConverseTextBlock (text + qualifiers grounding_source|query|guard_content), GuardrailStreamConfiguration (streamProcessingMode sync|async), ConverseTrace (trace.guardrail assessment).
**Alternatives considered:** (a) Model the full guardrail trace assessment as nested typed dataclasses — rejected: the assessment shape is large and variable (content/topic/word/sensitiveInformation/contextualGrounding/automatedReasoning policies + invocationMetrics + guardrailCoverage); a single accessor returning the raw dict satisfies the issue's "typed accessor" (one accessor exposing the assessment) without an over-engineered model that would drift from the API. (b) A separate `stream_processing_mode` top-level request field — rejected: per the API it is a member of the streaming `guardrailConfig`, so it is merged into that config (creating one if absent).
**Evidence:** AWS MCP reads (GuardrailConverseContentBlock, GuardrailConverseTextBlock, GuardrailStreamConfiguration). Red→green: 14 tests fail before impl, 15 focused pass after (guard-content build + qualifier validation, trace accessor non-streaming+streaming, stream-mode injection into/creating guardrailConfig + omitted-by-default). ruff+mypy clean (106 source files).
**Supersedes:** none
**Artifacts touched:** `message_builder.py` (+add_guard_content), `message_builder_enums.py` (+GuardContentQualifierEnum), `bedrock/models/bedrock_response.py` (+get_guardrail_trace on BedrockResponse and StreamingResponse), `llm_manager.py` (stream_processing_mode on converse_stream/_build_converse_request → guardrailConfig.streamProcessingMode), `bedrock/models/llm_manager_constants.py` (+GUARD_CONTENT_TEXT/GUARD_CONTENT_QUALIFIERS/TRACE/GUARDRAIL/STREAM_PROCESSING_MODE), `__init__.py` (export GuardContentQualifierEnum), tests (`test_message_builder.py`, `test_bedrock_response.py`, `test_LLMManager.py`, `test_init.py`), `docs/forLLMConsumption.md`.

## DL-002 — 2026-06-22 — issue-work-orchestrator — phase:DOCUMENT

**Decision:** `get_guardrail_trace()` returns the raw `trace.guardrail` dict (None when trace/guardrail absent or response unsuccessful); it does not synthesize typed policy objects.
**Driver:** Issue #38 "typed get_guardrail_trace() accessor" — interpreted as a single typed accessor surfacing the assessment, consistent with the project's other dict-returning accessors (get_usage/get_metrics/get_performance_config).
**Alternatives considered:** Build per-policy dataclasses — deferred: would add a large, fast-drifting model surface; the raw assessment dict is fully usable and matches the API. Noted on the issue so a follow-up can add richer typing if a concrete consumer needs it.
**Evidence:** `TestBedrockResponseGuardrailTrace` (non-streaming + streaming, absent, trace-without-guardrail, no-data, failed-response).
**Supersedes:** none
**Artifacts touched:** `bedrock/models/bedrock_response.py`, `docs/forLLMConsumption.md`.

## DL-003 — 2026-06-22 — issue-work-orchestrator — phase:PROOF_GATE

**Decision:** Added `test_get_guardrail_trace_failed_response` to cover the `not self.success` guard in `get_guardrail_trace()`, closing the M5 coverage gap the adversarial verifier flagged (the guard existed and was correct, but no test exercised the failed-with-trace-data path).
**Driver:** Adversarial-verifier finding M5 (LOW): removing the success guard left all tests green, so the failed-response None behavior was unproven.
**Alternatives considered:** Leave as-is — rejected: the verifier's other 7 claims all survived; closing the single coverage gap is cheap and makes the failed-response behavior falsifiable.
**Evidence:** New test asserts `BedrockResponse(success=False, response_data={trace.guardrail})​.get_guardrail_trace() is None`; 7 TestBedrockResponseGuardrailTrace tests pass; ruff clean.
**Supersedes:** none
**Artifacts touched:** `test/bestehorn_llmmanager/bedrock/models/test_bedrock_response.py`.
