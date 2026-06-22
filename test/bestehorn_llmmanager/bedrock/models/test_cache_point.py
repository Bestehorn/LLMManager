"""Unit tests for the cache-point factory and CacheDetail typed object (issue #39)."""

import pytest

from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import RequestValidationError
from bestehorn_llmmanager.bedrock.models.cache_detail import CacheDetail
from bestehorn_llmmanager.bedrock.models.cache_point import build_cache_point
from bestehorn_llmmanager.message_builder_enums import CachePointTTLEnum


class TestBuildCachePoint:
    """build_cache_point() shape + validation."""

    def test_default_without_ttl_omits_ttl_key(self):
        block = build_cache_point()
        assert block == {"cachePoint": {"type": "default"}}
        assert "ttl" not in block["cachePoint"]

    def test_ttl_5m_is_included(self):
        block = build_cache_point(ttl="5m")
        assert block == {"cachePoint": {"type": "default", "ttl": "5m"}}

    def test_ttl_1h_is_included(self):
        block = build_cache_point(ttl="1h")
        assert block == {"cachePoint": {"type": "default", "ttl": "1h"}}

    def test_ttl_enum_value_accepted(self):
        block = build_cache_point(ttl=CachePointTTLEnum.ONE_HOUR)
        assert block == {"cachePoint": {"type": "default", "ttl": "1h"}}

    def test_invalid_ttl_rejected(self):
        with pytest.raises(RequestValidationError, match="ttl"):
            build_cache_point(ttl="30m")

    def test_invalid_type_rejected(self):
        with pytest.raises(RequestValidationError, match="type"):
            build_cache_point(cache_type="ephemeral")


class TestCacheDetail:
    """CacheDetail.from_cache_detail() parsing."""

    def test_parses_input_tokens_and_ttl(self):
        detail = CacheDetail.from_cache_detail(cache_detail={"inputTokens": 1024, "ttl": "1h"})
        assert detail.input_tokens == 1024
        assert detail.ttl == "1h"

    def test_missing_fields_default(self):
        detail = CacheDetail.from_cache_detail(cache_detail={})
        assert detail.input_tokens == 0
        assert detail.ttl == ""

    def test_is_frozen(self):
        detail = CacheDetail(input_tokens=10, ttl="5m")
        with pytest.raises(AttributeError):
            detail.input_tokens = 20  # type: ignore[misc]
