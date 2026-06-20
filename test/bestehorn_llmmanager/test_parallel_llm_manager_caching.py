"""
Tests for prompt caching on the parallel fan-out path (issue #29).

Covers the three change-requests:
- CR-1: ``ParallelLLMManager`` accepts ``cache_config`` and forwards it to the internal
  ``LLMManager`` so the existing cache-point injection activates for parallel requests.
- CR-2: caller-placed cache points on a ``BedrockConverseRequest`` survive the parallel
  submission path (``messages``/``system`` are passed through unchanged).
- CR-3: per-request cache tokens and an aggregate cache hit ratio are surfaced on the
  parallel result.

Backward compatibility: with ``cache_config=None`` the parallel path is byte-identical to
today (no cache-point manager, caching disabled).
"""

from unittest.mock import MagicMock, patch

from bestehorn_llmmanager.bedrock.models.bedrock_response import BedrockResponse
from bestehorn_llmmanager.bedrock.models.cache_structures import CacheConfig, CacheStrategy
from bestehorn_llmmanager.bedrock.models.parallel_structures import (
    BedrockConverseRequest,
    ParallelResponse,
)
from bestehorn_llmmanager.parallel_llm_manager import ParallelLLMManager


def _make_response(
    *,
    request_id: str,
    cache_read: int = 0,
    cache_write: int = 0,
    input_tokens: int = 100,
    output_tokens: int = 10,
) -> BedrockResponse:
    """Build a successful BedrockResponse-like mock with the given usage tokens."""
    response = MagicMock(spec=BedrockResponse)
    response.success = True
    response.get_usage.return_value = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cache_read_tokens": cache_read,
        "cache_write_tokens": cache_write,
    }
    response.get_cache_read_tokens.return_value = cache_read
    response.get_cache_write_tokens.return_value = cache_write
    response.get_metrics.return_value = {"api_latency_ms": 5.0}
    response.get_warnings.return_value = []
    response.get_last_error.return_value = None
    return response


class TestParallelManagerCacheConfigForwarding:
    """CR-1: cache_config is forwarded to the internal LLMManager."""

    @patch("bestehorn_llmmanager.llm_manager.BedrockModelCatalog")
    def test_cache_config_enabled_is_forwarded_and_activates_injection(self, mock_catalog_cls):
        """Constructing with cache_config(enabled=True) gives the internal manager an
        enabled cache config and a constructed CachePointManager."""
        mock_catalog_cls.return_value = MagicMock()
        cache_config = CacheConfig(enabled=True, strategy=CacheStrategy.CONSERVATIVE)

        manager = ParallelLLMManager(
            models=["Claude Sonnet 4 20250514"],
            regions=["us-east-1"],
            cache_config=cache_config,
        )

        internal = manager.get_underlying_llm_manager()
        assert internal._cache_config is cache_config
        assert internal._cache_config.enabled is True
        # The injection path is gated on a constructed CachePointManager.
        assert internal._cache_point_manager is not None

    @patch("bestehorn_llmmanager.llm_manager.BedrockModelCatalog")
    def test_cache_config_none_keeps_caching_disabled(self, mock_catalog_cls):
        """Backward-compat: omitting cache_config => internal manager has caching
        disabled and no CachePointManager (byte-identical to today)."""
        mock_catalog_cls.return_value = MagicMock()

        manager = ParallelLLMManager(
            models=["Claude Sonnet 4 20250514"],
            regions=["us-east-1"],
        )

        internal = manager.get_underlying_llm_manager()
        assert internal._cache_config.enabled is False
        assert internal._cache_point_manager is None


class TestParallelManagerCachePointPassthrough:
    """CR-2: caller-placed cache points survive the parallel submission path."""

    def test_caller_cache_point_preserved_in_converse_args(self):
        """A caller-placed cachePoint block in messages is passed through verbatim by
        BedrockConverseRequest.to_converse_args() in the same position."""
        messages = [
            {
                "role": "user",
                "content": [
                    {"text": "stable prefix"},
                    {"cachePoint": {"type": "default"}},
                    {"text": "variable suffix"},
                ],
            }
        ]
        system = [{"text": "system instruction"}]
        request = BedrockConverseRequest(messages=messages, system=system)

        args = request.to_converse_args()

        # Messages (incl. the cachePoint block, in position) and system pass through unchanged.
        assert args["messages"] == messages
        assert args["messages"][0]["content"][1] == {"cachePoint": {"type": "default"}}
        assert args["system"] == system

    @patch("bestehorn_llmmanager.llm_manager.BedrockModelCatalog")
    @patch("bestehorn_llmmanager.llm_manager.LLMManager.converse")
    def test_parallel_path_forwards_caller_cache_point_to_converse(
        self, mock_converse, mock_catalog_cls
    ):
        """When a parallel request carries a caller-placed cachePoint, the messages
        reaching converse() preserve that cache point in position."""
        mock_catalog_cls.return_value = MagicMock()
        seen = {}

        def capture(**kwargs):
            seen["messages"] = kwargs.get("messages")
            return _make_response(request_id="r")

        mock_converse.side_effect = capture

        messages = [
            {
                "role": "user",
                "content": [
                    {"text": "stable prefix"},
                    {"cachePoint": {"type": "default"}},
                    {"text": "variable suffix"},
                ],
            }
        ]
        manager = ParallelLLMManager(
            models=["Claude Sonnet 4 20250514"],
            regions=["us-east-1"],
            cache_config=CacheConfig(enabled=True),
        )
        request = BedrockConverseRequest(messages=messages)
        manager.converse_parallel(requests=[request])

        assert seen["messages"] is not None
        # The caller-placed cache point survived to converse() in the same position.
        assert {"cachePoint": {"type": "default"}} in seen["messages"][0]["content"]
        assert seen["messages"][0]["content"][1] == {"cachePoint": {"type": "default"}}


class TestParallelResponseCacheMetrics:
    """CR-3: per-request cache tokens + aggregate cache hit ratio on the parallel result."""

    def test_total_tokens_used_includes_cache_tokens(self):
        """The existing aggregate includes cache read/write tokens across the batch."""
        resp = ParallelResponse(
            success=True,
            request_responses={
                "a": _make_response(request_id="a", cache_read=0, cache_write=4096),
                "b": _make_response(request_id="b", cache_read=4096, cache_write=0),
            },
        )

        totals = resp.get_total_tokens_used()
        assert totals["cache_write_tokens"] == 4096
        assert totals["cache_read_tokens"] == 4096

    def test_get_cache_metrics_derives_hit_ratio(self):
        """CR-3: get_cache_metrics() exposes read/write totals and a derived hit ratio.

        First request writes the cache (miss), the next two read it (hits) => 2/3 hits.
        """
        resp = ParallelResponse(
            success=True,
            request_responses={
                "a": _make_response(request_id="a", cache_read=0, cache_write=4096),
                "b": _make_response(request_id="b", cache_read=4096, cache_write=0),
                "c": _make_response(request_id="c", cache_read=4096, cache_write=0),
            },
        )

        metrics = resp.get_cache_metrics()
        assert metrics.cache_savings_tokens == 4096 * 2  # tokens served from cache
        assert metrics.total_cache_hits == 2
        assert metrics.total_cache_misses == 1
        assert abs(metrics.cache_hit_ratio - (2 / 3)) < 1e-9

    def test_get_cache_metrics_zero_when_caching_disabled(self):
        """With caching disabled (no cache tokens), metrics are all zero — exactly as
        today (CR-3 backward-compat)."""
        resp = ParallelResponse(
            success=True,
            request_responses={
                "a": _make_response(request_id="a", cache_read=0, cache_write=0),
                "b": _make_response(request_id="b", cache_read=0, cache_write=0),
            },
        )

        metrics = resp.get_cache_metrics()
        assert metrics.cache_hit_ratio == 0.0
        assert metrics.total_cache_hits == 0
        assert metrics.cache_savings_tokens == 0
