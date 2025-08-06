"""
Cache Point Manager for intelligent cache point insertion and optimization.

This module handles the automatic placement of cache points in messages
based on configured strategies and content analysis.
"""

import logging
from typing import Any, Dict, List, Optional

from ..models.cache_structures import (
    CacheAvailabilityTracker,
    CacheConfig,
    CachePointInfo,
    CacheStrategy,
)
from ..models.llm_manager_constants import ConverseAPIFields


class CachePointManager:
    """
    Manages automatic cache point insertion and optimization.

    This class analyzes message content and intelligently places cache points
    based on the configured strategy to maximize cache efficiency.
    """

    def __init__(self, cache_config: CacheConfig) -> None:
        """
        Initialize the cache point manager.

        Args:
            cache_config: Cache configuration
        """
        self._config = cache_config
        self._logger = logging.getLogger(__name__)
        self._availability_tracker = CacheAvailabilityTracker(
            blacklist_duration_minutes=cache_config.blacklist_duration_minutes
        )

    def inject_cache_points(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        region: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Inject cache points into messages based on strategy.

        Args:
            messages: List of message dictionaries
            model: Optional model identifier for availability checking
            region: Optional region for availability checking

        Returns:
            Messages with cache points injected
        """
        if not self._config.enabled:
            return messages

        # Check if caching is supported for this model/region
        if model and region and self._config.cache_availability_check:
            cache_support = self._availability_tracker.is_cache_supported(model, region)
            if cache_support is False:
                self._logger.debug(
                    f"Caching not supported for {model} in {region}, skipping injection"
                )
                return messages

        # Process each message
        processed_messages = []
        for message in messages:
            processed_message = self._process_message(message)
            processed_messages.append(processed_message)

        return processed_messages

    def _process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single message to inject cache points.

        Args:
            message: Message dictionary

        Returns:
            Message with cache points injected
        """
        # Skip if message doesn't have content
        if ConverseAPIFields.CONTENT not in message:
            return message

        content_blocks = message[ConverseAPIFields.CONTENT]

        # Skip if no content blocks or already has cache points
        if not content_blocks or self._has_cache_points(content_blocks):
            return message

        # Apply strategy-specific injection
        if self._config.strategy == CacheStrategy.CONSERVATIVE:
            modified_content = self._inject_conservative(content_blocks)
        elif self._config.strategy == CacheStrategy.AGGRESSIVE:
            modified_content = self._inject_aggressive(content_blocks)
        else:  # CacheStrategy.CUSTOM
            modified_content = self._inject_custom(content_blocks)

        # Create a new message with modified content
        return {**message, ConverseAPIFields.CONTENT: modified_content}

    def _has_cache_points(self, content_blocks: List[Dict[str, Any]]) -> bool:
        """Check if content blocks already contain cache points."""
        return any(ConverseAPIFields.CACHE_POINT in block for block in content_blocks)

    def _inject_conservative(self, content_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Conservative strategy: Single cache point after substantial shared content.

        Args:
            content_blocks: List of content blocks

        Returns:
            Content blocks with cache point injected
        """
        # Estimate tokens and find optimal placement
        estimated_tokens = 0
        optimal_position = -1

        for i, block in enumerate(content_blocks):
            block_tokens = self._estimate_block_tokens(block)
            estimated_tokens += block_tokens

            # Place cache point after we've accumulated enough tokens
            if estimated_tokens >= self._config.cache_point_threshold and optimal_position == -1:
                # Look ahead to see if there's more cacheable content
                remaining_tokens = sum(
                    self._estimate_block_tokens(content_blocks[j])
                    for j in range(i + 1, len(content_blocks))
                )

                # If remaining content is minimal, place cache point here
                if remaining_tokens < self._config.cache_point_threshold:
                    optimal_position = i + 1
                    break

                # If we're at 80% of content, place cache point
                elif (estimated_tokens + remaining_tokens) > 0:
                    ratio = estimated_tokens / (estimated_tokens + remaining_tokens)
                    if ratio > 0.8:
                        optimal_position = i + 1
                        break

        # If we found a good position, inject cache point
        if optimal_position > 0 and optimal_position < len(content_blocks):
            modified_blocks = content_blocks[:optimal_position]
            modified_blocks.append(self._create_cache_point_block())
            modified_blocks.extend(content_blocks[optimal_position:])

            self._logger.debug(
                f"Injected cache point at position {optimal_position} "
                f"(~{estimated_tokens} tokens cached)"
            )

            return modified_blocks

        return content_blocks

    def _inject_aggressive(self, content_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Aggressive strategy: Multiple cache points for granular control.

        Args:
            content_blocks: List of content blocks

        Returns:
            Content blocks with multiple cache points injected
        """
        modified_blocks = []
        accumulated_tokens = 0
        cache_threshold = max(500, self._config.cache_point_threshold // 2)  # Lower threshold

        for i, block in enumerate(content_blocks):
            modified_blocks.append(block)
            block_tokens = self._estimate_block_tokens(block)
            accumulated_tokens += block_tokens

            # Add cache point after significant content blocks
            if (
                accumulated_tokens >= cache_threshold
                and i < len(content_blocks) - 1  # Not the last block
                and self._is_cacheable_block(block)
            ):

                modified_blocks.append(self._create_cache_point_block())
                accumulated_tokens = 0  # Reset counter

        return modified_blocks

    def _inject_custom(self, content_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Custom strategy: Apply user-defined rules.

        Args:
            content_blocks: List of content blocks

        Returns:
            Content blocks with cache points based on custom rules
        """
        rules = self._config.custom_rules

        # Default to conservative if no rules specified
        if not rules:
            return self._inject_conservative(content_blocks)

        modified_blocks = []
        accumulated_tokens = 0

        # Custom threshold
        cache_threshold = rules.get("cache_text_blocks_over", self._config.cache_point_threshold)
        cache_all_images = rules.get("cache_all_images", False)

        for i, block in enumerate(content_blocks):
            modified_blocks.append(block)
            block_tokens = self._estimate_block_tokens(block)
            accumulated_tokens += block_tokens

            # Check if we should add cache point
            should_cache = False

            # Cache after images if rule is set
            if cache_all_images and ConverseAPIFields.IMAGE in block:
                should_cache = True

            # Cache after accumulating enough tokens
            elif accumulated_tokens >= cache_threshold:
                should_cache = True

            if should_cache and i < len(content_blocks) - 1:
                modified_blocks.append(self._create_cache_point_block())
                accumulated_tokens = 0

        return modified_blocks

    def _estimate_block_tokens(self, block: Dict[str, Any]) -> int:
        """
        Estimate the number of tokens in a content block.

        Args:
            block: Content block

        Returns:
            Estimated token count
        """
        # Text blocks: rough estimate of 4 characters per token
        if ConverseAPIFields.TEXT in block:
            text = block[ConverseAPIFields.TEXT]
            return len(text) // 4

        # Image blocks: fixed estimate
        elif ConverseAPIFields.IMAGE in block:
            return 450  # Approximate tokens for an image

        # Document blocks: higher estimate
        elif ConverseAPIFields.DOCUMENT in block:
            return 1000  # Approximate tokens for a document

        # Video blocks: very high estimate
        elif ConverseAPIFields.VIDEO in block:
            return 2000  # Approximate tokens for a video

        # Other blocks: minimal tokens
        return 10

    def _is_cacheable_block(self, block: Dict[str, Any]) -> bool:
        """
        Determine if a block is worth caching.

        Args:
            block: Content block

        Returns:
            True if block should be followed by a cache point
        """
        # Images and documents are always cacheable
        if ConverseAPIFields.IMAGE in block or ConverseAPIFields.DOCUMENT in block:
            return True

        # Long text blocks are cacheable
        if ConverseAPIFields.TEXT in block:
            tokens = self._estimate_block_tokens(block)
            return tokens >= self._config.cache_point_threshold

        return False

    def _create_cache_point_block(self) -> Dict[str, Any]:
        """Create a cache point content block."""
        return {ConverseAPIFields.CACHE_POINT: {"type": "default"}}

    def optimize_cache_placement(
        self, conversation_history: List[Dict[str, Any]]
    ) -> List[CachePointInfo]:
        """
        Analyze conversation history to optimize cache placement.

        Args:
            conversation_history: List of previous messages

        Returns:
            List of recommended cache point positions
        """
        cache_points = []

        # Analyze patterns in conversation history
        # This is a placeholder for more sophisticated analysis
        for i, message in enumerate(conversation_history):
            if ConverseAPIFields.CONTENT in message:
                content_blocks = message[ConverseAPIFields.CONTENT]
                for j, block in enumerate(content_blocks):
                    if ConverseAPIFields.CACHE_POINT in block:
                        cache_points.append(
                            CachePointInfo(
                                position=j,
                                cache_type=block[ConverseAPIFields.CACHE_POINT].get(
                                    "type", "default"
                                ),
                                estimated_tokens=self._estimate_tokens_before_position(
                                    content_blocks, j
                                ),
                            )
                        )

        return cache_points

    def _estimate_tokens_before_position(
        self, content_blocks: List[Dict[str, Any]], position: int
    ) -> int:
        """Estimate tokens before a given position."""
        return sum(
            self._estimate_block_tokens(content_blocks[i])
            for i in range(min(position, len(content_blocks)))
        )

    def validate_cache_configuration(self, request: Dict[str, Any]) -> List[str]:
        """
        Validate cache configuration in a request.

        Args:
            request: Request dictionary

        Returns:
            List of validation warnings
        """
        warnings: List[str] = []

        # Check if messages exist
        if ConverseAPIFields.MESSAGES not in request:
            return warnings

        messages = request[ConverseAPIFields.MESSAGES]
        total_cache_points = 0

        for message in messages:
            if ConverseAPIFields.CONTENT in message:
                content_blocks = message[ConverseAPIFields.CONTENT]
                cache_points_in_message = sum(
                    1 for block in content_blocks if ConverseAPIFields.CACHE_POINT in block
                )
                total_cache_points += cache_points_in_message

                # Warn about multiple cache points in conservative mode
                if (
                    cache_points_in_message > 1
                    and self._config.strategy == CacheStrategy.CONSERVATIVE
                ):
                    warnings.append(
                        f"Multiple cache points ({cache_points_in_message}) found in message "
                        f"with CONSERVATIVE strategy"
                    )

        # Warn if no cache points with caching enabled
        if total_cache_points == 0 and self._config.enabled:
            warnings.append("Caching is enabled but no cache points found in messages")

        return warnings

    def remove_cache_points(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove all cache points from messages.

        This is used for fallback when caching is not supported.

        Args:
            messages: List of message dictionaries

        Returns:
            Messages with cache points removed
        """
        cleaned_messages = []

        for message in messages:
            if ConverseAPIFields.CONTENT not in message:
                cleaned_messages.append(message)
                continue

            # Filter out cache point blocks
            cleaned_content = [
                block
                for block in message[ConverseAPIFields.CONTENT]
                if ConverseAPIFields.CACHE_POINT not in block
            ]

            cleaned_message = {**message, ConverseAPIFields.CONTENT: cleaned_content}
            cleaned_messages.append(cleaned_message)

        return cleaned_messages

    def get_availability_tracker(self) -> CacheAvailabilityTracker:
        """Get the cache availability tracker instance."""
        return self._availability_tracker
