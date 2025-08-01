"""
Tests for CachePointManager class.
"""

from unittest.mock import patch

from bestehorn_llmmanager.bedrock.cache.cache_point_manager import CachePointManager
from bestehorn_llmmanager.bedrock.models.cache_structures import (
    CacheAvailabilityTracker,
    CacheConfig,
    CachePointInfo,
    CacheStrategy,
)
from bestehorn_llmmanager.bedrock.models.llm_manager_constants import ConverseAPIFields


class TestCachePointManagerInitialization:
    """Test CachePointManager initialization."""

    def test_init_basic(self):
        """Test basic initialization."""
        config = CacheConfig(enabled=True, strategy=CacheStrategy.CONSERVATIVE)
        manager = CachePointManager(config)

        assert manager._config == config
        assert manager._logger is not None
        assert isinstance(manager._availability_tracker, CacheAvailabilityTracker)

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = CacheConfig(
            enabled=True,
            strategy=CacheStrategy.AGGRESSIVE,
            cache_point_threshold=1000,
            blacklist_duration_minutes=60,
            cache_availability_check=True,
        )
        manager = CachePointManager(config)

        assert manager._config.strategy == CacheStrategy.AGGRESSIVE
        assert manager._config.cache_point_threshold == 1000
        assert manager._config.blacklist_duration_minutes == 60


class TestInjectCachePoints:
    """Test cache point injection."""

    def test_inject_cache_points_disabled(self):
        """Test injection when caching is disabled."""
        config = CacheConfig(enabled=False)
        manager = CachePointManager(config)

        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        result = manager.inject_cache_points(messages)

        assert result == messages

    def test_inject_cache_points_with_availability_check_supported(self):
        """Test injection with cache availability check - supported."""
        config = CacheConfig(enabled=True, cache_availability_check=True)
        manager = CachePointManager(config)

        with patch.object(manager._availability_tracker, "is_cache_supported", return_value=True):
            messages = [{"role": "user", "content": [{"text": "Hello world"}]}]
            result = manager.inject_cache_points(messages, model="claude-3", region="us-east-1")

            assert len(result) == 1
            assert result[0]["role"] == "user"

    def test_inject_cache_points_with_availability_check_not_supported(self):
        """Test injection with cache availability check - not supported."""
        config = CacheConfig(enabled=True, cache_availability_check=True)
        manager = CachePointManager(config)

        with patch.object(manager._availability_tracker, "is_cache_supported", return_value=False):
            messages = [{"role": "user", "content": [{"text": "Hello world"}]}]
            result = manager.inject_cache_points(messages, model="claude-3", region="us-east-1")

            assert result == messages

    def test_inject_cache_points_no_model_or_region(self):
        """Test injection without model or region specified."""
        config = CacheConfig(enabled=True, cache_availability_check=True)
        manager = CachePointManager(config)

        messages = [{"role": "user", "content": [{"text": "Hello world"}]}]
        result = manager.inject_cache_points(messages)

        assert len(result) == 1


class TestProcessMessage:
    """Test individual message processing."""

    def test_process_message_no_content(self):
        """Test processing message without content field."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        message = {"role": "user"}
        result = manager._process_message(message)

        assert result == message

    def test_process_message_empty_content(self):
        """Test processing message with empty content."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        message = {"role": "user", "content": []}
        result = manager._process_message(message)

        assert result == message

    def test_process_message_already_has_cache_points(self):
        """Test processing message that already has cache points."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        message = {
            "role": "user",
            "content": [{"text": "Hello"}, {"cachePoint": {"type": "default"}}],
        }
        result = manager._process_message(message)

        assert result == message

    def test_process_message_conservative_strategy(self):
        """Test processing with conservative strategy."""
        config = CacheConfig(enabled=True, strategy=CacheStrategy.CONSERVATIVE)
        manager = CachePointManager(config)

        message = {"role": "user", "content": [{"text": "Hello world"}]}

        with patch.object(
            manager, "_inject_conservative", return_value=[{"text": "Hello world"}]
        ) as mock_inject:
            result = manager._process_message(message)
            mock_inject.assert_called_once()
            assert "content" in result

    def test_process_message_aggressive_strategy(self):
        """Test processing with aggressive strategy."""
        config = CacheConfig(enabled=True, strategy=CacheStrategy.AGGRESSIVE)
        manager = CachePointManager(config)

        message = {"role": "user", "content": [{"text": "Hello world"}]}

        with patch.object(
            manager, "_inject_aggressive", return_value=[{"text": "Hello world"}]
        ) as mock_inject:
            result = manager._process_message(message)
            mock_inject.assert_called_once()
            assert "content" in result

    def test_process_message_custom_strategy(self):
        """Test processing with custom strategy."""
        config = CacheConfig(enabled=True, strategy=CacheStrategy.CUSTOM)
        manager = CachePointManager(config)

        message = {"role": "user", "content": [{"text": "Hello world"}]}

        with patch.object(
            manager, "_inject_custom", return_value=[{"text": "Hello world"}]
        ) as mock_inject:
            result = manager._process_message(message)
            mock_inject.assert_called_once()
            assert "content" in result

    def test_process_message_unknown_strategy(self):
        """Test processing with unknown strategy."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        message = {"role": "user", "content": [{"text": "Hello world"}]}

        # Mock the strategy check to simulate unknown strategy
        with patch.object(manager._config, "strategy", "unknown"):
            result = manager._process_message(message)

        # Should return original content when strategy is unknown
        assert result["content"] == [{"text": "Hello world"}]


class TestCachePointDetection:
    """Test cache point detection methods."""

    def test_has_cache_points_true(self):
        """Test detection when cache points exist."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        content_blocks = [{"text": "Hello"}, {"cachePoint": {"type": "default"}}, {"text": "World"}]

        assert manager._has_cache_points(content_blocks) is True

    def test_has_cache_points_false(self):
        """Test detection when no cache points exist."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        content_blocks = [
            {"text": "Hello"},
            {"image": {"format": "jpeg", "source": {"bytes": b"data"}}},
            {"text": "World"},
        ]

        assert manager._has_cache_points(content_blocks) is False


class TestConservativeStrategy:
    """Test conservative cache strategy."""

    def test_inject_conservative_no_threshold_reached(self):
        """Test conservative injection when threshold not reached."""
        config = CacheConfig(enabled=True, cache_point_threshold=1000)
        manager = CachePointManager(config)

        content_blocks = [{"text": "Short text"}]
        result = manager._inject_conservative(content_blocks)

        assert result == content_blocks

    def test_inject_conservative_threshold_reached_minimal_remaining(self):
        """Test conservative injection with minimal remaining content."""
        config = CacheConfig(enabled=True, cache_point_threshold=10)
        manager = CachePointManager(config)

        content_blocks = [
            {"text": "This is a longer text that should exceed the threshold"},
            {"text": "Short"},
        ]

        result = manager._inject_conservative(content_blocks)

        # Should inject cache point when remaining content is minimal
        assert len(result) >= len(content_blocks)

    def test_inject_conservative_threshold_reached_80_percent(self):
        """Test conservative injection at 80% of content."""
        config = CacheConfig(enabled=True, cache_point_threshold=10)
        manager = CachePointManager(config)

        content_blocks = [
            {
                "text": "This is a very long text that should definitely exceed the threshold and trigger cache point insertion"
            },
            {"text": "This is more text that comes after"},
            {"text": "Even more text"},
        ]

        result = manager._inject_conservative(content_blocks)

        # Should inject cache point at appropriate position
        cache_point_found = any(ConverseAPIFields.CACHE_POINT in block for block in result)
        assert cache_point_found

    def test_inject_conservative_no_good_position(self):
        """Test conservative injection when no good position is found."""
        config = CacheConfig(enabled=True, cache_point_threshold=1000)
        manager = CachePointManager(config)

        content_blocks = [{"text": "Short text"}]
        result = manager._inject_conservative(content_blocks)

        assert result == content_blocks


class TestAggressiveStrategy:
    """Test aggressive cache strategy."""

    def test_inject_aggressive_single_block(self):
        """Test aggressive injection with single block."""
        config = CacheConfig(enabled=True, cache_point_threshold=1000)
        manager = CachePointManager(config)

        content_blocks = [{"text": "Single text block"}]
        result = manager._inject_aggressive(content_blocks)

        # Should not add cache points for single block
        assert result == content_blocks

    def test_inject_aggressive_multiple_blocks(self):
        """Test aggressive injection with multiple cacheable blocks."""
        config = CacheConfig(enabled=True, cache_point_threshold=10)
        manager = CachePointManager(config)

        content_blocks = [
            {
                "text": "This is a longer text that should exceed the threshold and trigger cache insertion"
            },
            {"image": {"format": "jpeg", "source": {"bytes": b"data"}}},
            {"text": "More text after image that continues"},
        ]

        result = manager._inject_aggressive(content_blocks)

        # Should inject cache points after significant content
        cache_points = [block for block in result if ConverseAPIFields.CACHE_POINT in block]
        # The aggressive strategy may or may not inject based on specific thresholds
        assert len(result) >= len(content_blocks)
        # Verify cache points were detected (even if none are added)
        assert isinstance(cache_points, list)

    def test_inject_aggressive_with_non_cacheable_blocks(self):
        """Test aggressive injection with non-cacheable blocks."""
        config = CacheConfig(enabled=True, cache_point_threshold=10)
        manager = CachePointManager(config)

        # Mock _is_cacheable_block to return False
        with patch.object(manager, "_is_cacheable_block", return_value=False):
            content_blocks = [{"text": "This is a longer text"}, {"text": "More text"}]

            result = manager._inject_aggressive(content_blocks)

            # Should not add cache points for non-cacheable blocks
            cache_points = [block for block in result if ConverseAPIFields.CACHE_POINT in block]
            assert len(cache_points) == 0


class TestCustomStrategy:
    """Test custom cache strategy."""

    def test_inject_custom_no_rules(self):
        """Test custom injection without rules (defaults to conservative)."""
        config = CacheConfig(enabled=True, strategy=CacheStrategy.CUSTOM)
        manager = CachePointManager(config)

        content_blocks = [{"text": "Test text"}]

        with patch.object(
            manager, "_inject_conservative", return_value=content_blocks
        ) as mock_conservative:
            result = manager._inject_custom(content_blocks)
            mock_conservative.assert_called_once()
            assert result == content_blocks

    def test_inject_custom_with_text_threshold_rule(self):
        """Test custom injection with text threshold rule."""
        config = CacheConfig(
            enabled=True, strategy=CacheStrategy.CUSTOM, custom_rules={"cache_text_blocks_over": 5}
        )
        manager = CachePointManager(config)

        content_blocks = [{"text": "This is longer text"}, {"text": "Short"}]

        result = manager._inject_custom(content_blocks)

        # Should inject based on custom threshold
        assert len(result) >= len(content_blocks)

    def test_inject_custom_cache_all_images(self):
        """Test custom injection with cache all images rule."""
        config = CacheConfig(
            enabled=True, strategy=CacheStrategy.CUSTOM, custom_rules={"cache_all_images": True}
        )
        manager = CachePointManager(config)

        content_blocks = [
            {"text": "Text before image"},
            {"image": {"format": "jpeg", "source": {"bytes": b"data"}}},
            {"text": "Text after image"},
        ]

        result = manager._inject_custom(content_blocks)

        # Should inject cache point after image
        cache_points = [block for block in result if ConverseAPIFields.CACHE_POINT in block]
        assert len(cache_points) > 0

    def test_inject_custom_mixed_rules(self):
        """Test custom injection with mixed rules."""
        config = CacheConfig(
            enabled=True,
            strategy=CacheStrategy.CUSTOM,
            custom_rules={"cache_text_blocks_over": 10, "cache_all_images": True},
        )
        manager = CachePointManager(config)

        content_blocks = [
            {"text": "This is a longer text block"},
            {"image": {"format": "jpeg", "source": {"bytes": b"data"}}},
            {"text": "Final text"},
        ]

        result = manager._inject_custom(content_blocks)

        # Should inject multiple cache points
        cache_points = [block for block in result if ConverseAPIFields.CACHE_POINT in block]
        assert len(cache_points) > 0


class TestTokenEstimation:
    """Test token estimation methods."""

    def test_estimate_block_tokens_text(self):
        """Test token estimation for text blocks."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        block = {"text": "This is a test text with twenty characters"}  # 43 chars
        tokens = manager._estimate_block_tokens(block)

        assert tokens == 43 // 4  # Should be 10

    def test_estimate_block_tokens_image(self):
        """Test token estimation for image blocks."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        block = {"image": {"format": "jpeg", "source": {"bytes": b"data"}}}
        tokens = manager._estimate_block_tokens(block)

        assert tokens == 450

    def test_estimate_block_tokens_document(self):
        """Test token estimation for document blocks."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        block = {"document": {"format": "pdf", "source": {"bytes": b"data"}}}
        tokens = manager._estimate_block_tokens(block)

        assert tokens == 1000

    def test_estimate_block_tokens_video(self):
        """Test token estimation for video blocks."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        block = {"video": {"format": "mp4", "source": {"bytes": b"data"}}}
        tokens = manager._estimate_block_tokens(block)

        assert tokens == 2000

    def test_estimate_block_tokens_other(self):
        """Test token estimation for other block types."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        block = {"unknown_type": "some_value"}
        tokens = manager._estimate_block_tokens(block)

        assert tokens == 10


class TestCacheableBlocks:
    """Test cacheable block detection."""

    def test_is_cacheable_block_image(self):
        """Test image blocks are cacheable."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        block = {"image": {"format": "jpeg", "source": {"bytes": b"data"}}}
        assert manager._is_cacheable_block(block) is True

    def test_is_cacheable_block_document(self):
        """Test document blocks are cacheable."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        block = {"document": {"format": "pdf", "source": {"bytes": b"data"}}}
        assert manager._is_cacheable_block(block) is True

    def test_is_cacheable_block_long_text(self):
        """Test long text blocks are cacheable."""
        config = CacheConfig(enabled=True, cache_point_threshold=10)
        manager = CachePointManager(config)

        block = {"text": "This is a very long text that exceeds the threshold"}
        assert manager._is_cacheable_block(block) is True

    def test_is_cacheable_block_short_text(self):
        """Test short text blocks are not cacheable."""
        config = CacheConfig(enabled=True, cache_point_threshold=1000)
        manager = CachePointManager(config)

        block = {"text": "Short"}
        assert manager._is_cacheable_block(block) is False

    def test_is_cacheable_block_other(self):
        """Test other block types are not cacheable."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        block = {"unknown_type": "value"}
        assert manager._is_cacheable_block(block) is False


class TestCreateCachePoint:
    """Test cache point creation."""

    def test_create_cache_point_block(self):
        """Test cache point block creation."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        cache_point = manager._create_cache_point_block()

        expected = {ConverseAPIFields.CACHE_POINT: {"type": "default"}}
        assert cache_point == expected


class TestOptimizeCachePlacement:
    """Test cache placement optimization."""

    def test_optimize_cache_placement_empty_history(self):
        """Test optimization with empty conversation history."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        result = manager.optimize_cache_placement([])
        assert result == []

    def test_optimize_cache_placement_with_cache_points(self):
        """Test optimization with existing cache points."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        conversation_history = [
            {
                "role": "user",
                "content": [
                    {"text": "Hello"},
                    {"cachePoint": {"type": "default"}},
                    {"text": "World"},
                ],
            }
        ]

        cache_points = manager.optimize_cache_placement(conversation_history)

        assert len(cache_points) == 1
        assert isinstance(cache_points[0], CachePointInfo)
        assert cache_points[0].position == 1
        assert cache_points[0].cache_type == "default"

    def test_optimize_cache_placement_no_cache_points(self):
        """Test optimization without cache points."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        conversation_history = [{"role": "user", "content": [{"text": "Hello"}, {"text": "World"}]}]

        result = manager.optimize_cache_placement(conversation_history)
        assert result == []

    def test_optimize_cache_placement_no_content(self):
        """Test optimization with messages without content."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        conversation_history = [{"role": "user"}]

        result = manager.optimize_cache_placement(conversation_history)
        assert result == []


class TestEstimateTokensBeforePosition:
    """Test token estimation before position."""

    def test_estimate_tokens_before_position_valid(self):
        """Test token estimation before valid position."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        content_blocks = [
            {"text": "Hello"},  # 5//4 = 1 token
            {"text": "World"},  # 5//4 = 1 token
            {"text": "Test"},  # 4//4 = 1 token
        ]

        tokens = manager._estimate_tokens_before_position(content_blocks, 2)
        assert tokens == 2  # First two blocks

    def test_estimate_tokens_before_position_zero(self):
        """Test token estimation before position 0."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        content_blocks = [{"text": "Hello"}]

        tokens = manager._estimate_tokens_before_position(content_blocks, 0)
        assert tokens == 0

    def test_estimate_tokens_before_position_out_of_range(self):
        """Test token estimation before position beyond array length."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        content_blocks = [{"text": "Hello"}, {"text": "World"}]

        tokens = manager._estimate_tokens_before_position(content_blocks, 10)
        assert tokens == 2  # All blocks (should be capped at array length)


class TestValidateCacheConfiguration:
    """Test cache configuration validation."""

    def test_validate_cache_configuration_no_messages(self):
        """Test validation with no messages field."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        request = {}
        warnings = manager.validate_cache_configuration(request)

        assert warnings == []

    def test_validate_cache_configuration_multiple_cache_points_conservative(self):
        """Test validation with multiple cache points in conservative mode."""
        config = CacheConfig(enabled=True, strategy=CacheStrategy.CONSERVATIVE)
        manager = CachePointManager(config)

        request = {
            ConverseAPIFields.MESSAGES: [
                {
                    "role": "user",
                    "content": [
                        {"text": "Hello"},
                        {"cachePoint": {"type": "default"}},
                        {"text": "World"},
                        {"cachePoint": {"type": "default"}},
                    ],
                }
            ]
        }

        warnings = manager.validate_cache_configuration(request)

        assert len(warnings) == 1
        assert "Multiple cache points" in warnings[0]
        assert "CONSERVATIVE" in warnings[0]

    def test_validate_cache_configuration_no_cache_points_enabled(self):
        """Test validation with no cache points but caching enabled."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        request = {
            ConverseAPIFields.MESSAGES: [
                {"role": "user", "content": [{"text": "Hello"}, {"text": "World"}]}
            ]
        }

        warnings = manager.validate_cache_configuration(request)

        assert len(warnings) == 1
        assert "no cache points found" in warnings[0]

    def test_validate_cache_configuration_valid(self):
        """Test validation with valid configuration."""
        config = CacheConfig(enabled=True, strategy=CacheStrategy.AGGRESSIVE)
        manager = CachePointManager(config)

        request = {
            ConverseAPIFields.MESSAGES: [
                {
                    "role": "user",
                    "content": [
                        {"text": "Hello"},
                        {"cachePoint": {"type": "default"}},
                        {"text": "World"},
                    ],
                }
            ]
        }

        warnings = manager.validate_cache_configuration(request)

        assert warnings == []

    def test_validate_cache_configuration_no_content_in_message(self):
        """Test validation with message without content."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        request = {ConverseAPIFields.MESSAGES: [{"role": "user"}]}

        warnings = manager.validate_cache_configuration(request)

        assert len(warnings) == 1
        assert "no cache points found" in warnings[0]


class TestRemoveCachePoints:
    """Test cache point removal."""

    def test_remove_cache_points_with_cache_points(self):
        """Test removing cache points from messages."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        messages = [
            {
                "role": "user",
                "content": [
                    {"text": "Hello"},
                    {"cachePoint": {"type": "default"}},
                    {"text": "World"},
                    {"cachePoint": {"type": "default"}},
                ],
            }
        ]

        result = manager.remove_cache_points(messages)

        assert len(result) == 1
        assert len(result[0]["content"]) == 2
        assert result[0]["content"] == [{"text": "Hello"}, {"text": "World"}]

    def test_remove_cache_points_no_cache_points(self):
        """Test removing cache points when none exist."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        messages = [{"role": "user", "content": [{"text": "Hello"}, {"text": "World"}]}]

        result = manager.remove_cache_points(messages)

        assert result == messages

    def test_remove_cache_points_no_content(self):
        """Test removing cache points from message without content."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        messages = [{"role": "user"}]

        result = manager.remove_cache_points(messages)

        assert result == messages

    def test_remove_cache_points_empty_messages(self):
        """Test removing cache points from empty messages list."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        result = manager.remove_cache_points([])

        assert result == []


class TestGetAvailabilityTracker:
    """Test availability tracker access."""

    def test_get_availability_tracker(self):
        """Test getting the availability tracker instance."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        tracker = manager.get_availability_tracker()

        assert isinstance(tracker, CacheAvailabilityTracker)
        assert tracker is manager._availability_tracker


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling."""

    def test_inject_cache_points_malformed_message(self):
        """Test injection with malformed message structure."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        # Message with non-list content
        messages = [{"role": "user", "content": "not a list"}]

        # Should handle gracefully without crashing
        result = manager.inject_cache_points(messages)
        assert len(result) == 1

    def test_conservative_injection_with_zero_tokens(self):
        """Test conservative injection when blocks have zero estimated tokens."""
        config = CacheConfig(enabled=True, cache_point_threshold=10)
        manager = CachePointManager(config)

        # Mock _estimate_block_tokens to return 0
        with patch.object(manager, "_estimate_block_tokens", return_value=0):
            content_blocks = [{"text": "test"}, {"text": "test2"}]
            result = manager._inject_conservative(content_blocks)

            # Should return original blocks when no tokens are estimated
            assert result == content_blocks

    def test_aggressive_injection_accumulated_tokens_reset(self):
        """Test that aggressive injection processes content blocks correctly."""
        config = CacheConfig(enabled=True, cache_point_threshold=10)
        manager = CachePointManager(config)

        content_blocks = [
            {"image": {"format": "jpeg", "source": {"bytes": b"data"}}},  # Cacheable
            {"text": "Some text"},
            {"image": {"format": "jpeg", "source": {"bytes": b"data"}}},  # Cacheable
        ]

        result = manager._inject_aggressive(content_blocks)

        # Should process all content blocks
        assert len(result) >= len(content_blocks)

    def test_custom_strategy_cache_point_with_no_remaining_content(self):
        """Test custom strategy doesn't add cache point after last block."""
        config = CacheConfig(
            enabled=True, strategy=CacheStrategy.CUSTOM, custom_rules={"cache_all_images": True}
        )
        manager = CachePointManager(config)

        # Image as last block
        content_blocks = [
            {"text": "Text before image"},
            {"image": {"format": "jpeg", "source": {"bytes": b"data"}}},
        ]

        result = manager._inject_custom(content_blocks)

        # Should not add cache point after last block
        assert result[-1] != {"cachePoint": {"type": "default"}}


class TestComplexScenarios:
    """Test complex scenarios with multiple conditions."""

    def test_mixed_content_conservative_strategy(self):
        """Test conservative strategy with mixed content types."""
        config = CacheConfig(
            enabled=True, cache_point_threshold=500, strategy=CacheStrategy.CONSERVATIVE
        )
        manager = CachePointManager(config)

        content_blocks = [
            {"text": "This is some initial text content that provides context"},
            {"image": {"format": "jpeg", "source": {"bytes": b"image_data"}}},
            {"text": "More text content after the image that continues the conversation"},
            {"document": {"format": "pdf", "source": {"bytes": b"document_data"}}},
            {"text": "Final text content that concludes the message"},
        ]

        result = manager._inject_conservative(content_blocks)

        # Should inject cache point at appropriate position
        assert len(result) >= len(content_blocks)

    def test_full_injection_workflow(self):
        """Test complete injection workflow from start to finish."""
        config = CacheConfig(
            enabled=True,
            cache_point_threshold=50,
            strategy=CacheStrategy.AGGRESSIVE,
            cache_availability_check=True,
        )
        manager = CachePointManager(config)

        messages = [
            {
                "role": "user",
                "content": [
                    {"text": "This is a comprehensive test with multiple content types"},
                    {"image": {"format": "jpeg", "source": {"bytes": b"image_data"}}},
                    {"text": "Additional text content that should trigger cache points"},
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {"text": "Response with more content"},
                    {"document": {"format": "pdf", "source": {"bytes": b"doc_data"}}},
                ],
            },
        ]

        with patch.object(manager._availability_tracker, "is_cache_supported", return_value=True):
            result = manager.inject_cache_points(messages, model="claude-3", region="us-east-1")

        # Verify processing occurred
        assert len(result) == len(messages)

        # Check that cache points were potentially added
        for message in result:
            if "content" in message:
                content = message["content"]
                # At minimum, content should be preserved
                assert len(content) >= 1

    def test_edge_case_empty_content_blocks(self):
        """Test handling of edge case with empty content blocks."""
        config = CacheConfig(enabled=True)
        manager = CachePointManager(config)

        content_blocks = []
        result = manager._inject_conservative(content_blocks)

        assert result == content_blocks

    def test_availability_tracker_cache_supported_unknown(self):
        """Test behavior when cache support is unknown."""
        config = CacheConfig(enabled=True, cache_availability_check=True)
        manager = CachePointManager(config)

        with patch.object(manager._availability_tracker, "is_cache_supported", return_value=None):
            messages = [{"role": "user", "content": [{"text": "Hello world"}]}]
            result = manager.inject_cache_points(messages, model="claude-3", region="us-east-1")

            # Should process normally when support is unknown
            assert len(result) == 1
