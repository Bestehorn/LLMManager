# Decision Log

## DL-001 — 2026-06-22 — issue-work-orchestrator — phase:CLASSIFY

**Decision:** Issue #39 is a Type-2 feature (Converse prompt-caching parity) with three independent, additive sub-features — cache-point TTL, tool-definition caching, and `cacheDetails[]` parsing — implemented test-first on a worktree off origin/main 7377e3c.
**Driver:** Issue #39 body + checklist (4 work items); AWS docs confirm the three API shapes (see DL-002).
**Alternatives considered:** Split into 3 PRs — rejected: the three sub-features share the cache-point constants and a single docs section, are small, and naturally ship together as one parity change (mirrors how #38 bundled add_guard_content + trace + streamProcessingMode).
**Evidence:** Issue #39 (gh get-issue 39); current gaps cited at `message_builder.py:772-804` (no ttl), `bedrock_response.py:284-356` (no cacheDetails), `llm_manager.py:1159-1160` (toolConfig passthrough only).
**Supersedes:** none
**Artifacts touched:** (planning only)

## DL-002 — 2026-06-22 — issue-work-orchestrator — phase:CLASSIFY


**Decision:** Model the API shapes exactly as the docs specify: `CachePointBlock` = `{type: "default" (only valid), ttl?: "5m"|"1h"}`; tool caching = appending a `{"cachePoint": {...}}` entry (a valid `Tool` union member) to `toolConfig.tools`; `usage.cacheDetails[]` = array of `{inputTokens: int, ttl: "5m"|"1h"}`.
**Driver:** AWS Bedrock API reference, verified via aws-documentation MCP this session.
**Alternatives considered:** Allow arbitrary `type` strings — rejected: docs list `default` as the only valid value; validating prevents silently sending a request Bedrock will reject.
**Evidence:** MCP reads — CachePointBlock (type: default; ttl: 5m|1h), Tool (cachePoint union member), TokenUsage.cacheDetails (Array of CacheDetail), CacheDetail (inputTokens:int required, ttl:5m|1h required).
**Supersedes:** none
**Artifacts touched:** (planning only)

## DL-003 — 2026-06-22 — issue-work-orchestrator — phase:FIX

**Decision:** Centralize cache-point construction in a single `build_cache_point(cache_type, ttl)` factory (`bedrock/models/cache_point.py`) reused by both `MessageBuilder.add_cache_point` and tool-definition caching, rather than duplicating the dict-building/validation in each call site. Tool caching needs NO new request-builder code: a caller appends `build_cache_point(...)` to `toolConfig.tools` and `_build_converse_request` forwards `tool_config` verbatim (already true at `llm_manager.py:1159-1160`).
**Driver:** DRY + coding-standards (one validation path, string constants); issue #39 checklist items 1–2; the existing verbatim tool_config passthrough.
**Alternatives considered:** Add a `cache_tools=True` flag to converse() that auto-injects a cache point — rejected: placement of a tool cache point is caller-semantic (which prefix to cache), the explicit append matches how message cache points already work, and it avoids a new public parameter. Recorded the explicit-append approach in docs instead.
**Evidence:** `test/bestehorn_llmmanager/bedrock/models/test_cache_point.py` (factory shape/validation), `TestAddCachePointTTL` (builder ttl + backward-compat), `test_build_converse_request_tool_config_with_cache_point` (tools passthrough) — 25 focused tests pass.
**Supersedes:** none
**Artifacts touched:** `bedrock/models/cache_point.py`, `message_builder.py`, `message_builder_enums.py`, `bedrock/models/llm_manager_constants.py`.

## DL-004 — 2026-06-22 — issue-work-orchestrator — phase:FIX

**Decision:** Parse `usage.cacheDetails[]` into a frozen `CacheDetail` typed object via `get_cache_details()` on BOTH `BedrockResponse` and `StreamingResponse`; thread it through the streaming usage normalizer (`event_handlers._extract_token_usage` → `usage_info["cache_details"]`) so streaming reaches parity with non-streaming.
**Driver:** Issue #39 checklist item 3; TokenUsage.cacheDetails (MCP, DL-002); existing per-modality typed-object convention (`Citation`, `ToolUse`, `ReasoningContent`).
**Alternatives considered:** Return raw dicts — rejected: every other parsed sub-object in this package is a frozen dataclass with a `from_*` classmethod; consistency + typed access wins. Update the two existing exact-dict streaming-usage assertions to include the additive `cache_details` key (not a weakening — the field is intentionally added).
**Evidence:** `TestBedrockResponseCacheDetails` (parse, empty, failed, no-data, streaming, streaming-empty); `test_extract_token_usage_full` extended; full unit suite green (see evidence/verify/full-suite.txt).
**Supersedes:** none
**Artifacts touched:** `bedrock/models/cache_detail.py`, `bedrock/models/bedrock_response.py`, `bedrock/streaming/event_handlers.py`, `bedrock/streaming/streaming_constants.py`, `__init__.py`.
