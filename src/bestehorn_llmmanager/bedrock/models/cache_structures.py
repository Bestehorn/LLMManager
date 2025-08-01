"""
Cache-related data structures for LLM Manager.

This module contains data structures for configuring and managing
the caching functionality in the LLM Manager system.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class CacheStrategy(Enum):
    """
    Defines intelligent cache placement strategies.

    Attributes:
        CONSERVATIVE: Cache only obvious repeated content (default)
        AGGRESSIVE: Maximize caching opportunities
        CUSTOM: User-defined rules
    """

    CONSERVATIVE = "conservative"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


class CacheErrorHandling(Enum):
    """
    Defines how cache-related errors should be handled.

    Attributes:
        GRACEFUL_DEGRADATION: Silently disable caching and continue (default)
        WARN_AND_CONTINUE: Log warning but continue without caching
        FAIL_FAST: Fail immediately (useful for testing)
    """

    GRACEFUL_DEGRADATION = "graceful"
    WARN_AND_CONTINUE = "warn"
    FAIL_FAST = "fail"


@dataclass
class CacheConfig:
    """
    Configuration for cache behavior in LLM Manager.

    Attributes:
        enabled: Whether caching is enabled (default: False)
        strategy: Cache placement strategy (default: CONSERVATIVE)
        error_handling: How to handle cache-related errors (default: GRACEFUL_DEGRADATION)
        auto_cache_system_messages: Whether to automatically cache system messages
        cache_point_threshold: Minimum tokens to consider for caching
        max_cache_ttl: Maximum time-to-live for cache entries (in seconds)
        cache_availability_check: Whether to pre-check cache support
        blacklist_duration_minutes: How long to remember unsupported combinations
        log_cache_failures: Whether to log cache-related failures
        custom_rules: Custom rules for CUSTOM strategy
        custom_unsupported_models: List of models known not to support caching
    """

    enabled: bool = False  # Caching is OFF by default
    strategy: CacheStrategy = CacheStrategy.CONSERVATIVE
    error_handling: CacheErrorHandling = CacheErrorHandling.GRACEFUL_DEGRADATION
    auto_cache_system_messages: bool = True
    cache_point_threshold: int = 100
    max_cache_ttl: Optional[int] = None
    cache_availability_check: bool = True
    blacklist_duration_minutes: int = 60
    log_cache_failures: bool = True
    custom_rules: Dict[str, Any] = field(default_factory=dict)
    custom_unsupported_models: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.cache_point_threshold < 0:
            raise ValueError("cache_point_threshold must be non-negative")

        if self.blacklist_duration_minutes < 0:
            raise ValueError("blacklist_duration_minutes must be non-negative")

        if self.max_cache_ttl is not None and self.max_cache_ttl < 0:
            raise ValueError("max_cache_ttl must be non-negative")


@dataclass
class CachePointInfo:
    """
    Information about a cache point in a message.

    Attributes:
        position: Index position in content blocks
        cache_type: Type of cache point (default: "default")
        estimated_tokens: Estimated tokens before this cache point
        is_auto_inserted: Whether this was automatically inserted
    """

    position: int
    cache_type: str = "default"
    estimated_tokens: int = 0
    is_auto_inserted: bool = False


@dataclass
class CacheMetrics:
    """
    Metrics for cache performance tracking.

    Attributes:
        cache_hit_ratio: Ratio of cache hits to total requests
        cache_savings_tokens: Total tokens saved by caching
        cache_savings_cost: Estimated cost savings
        latency_reduction_ms: Latency reduction in milliseconds
        total_cache_hits: Total number of cache hits
        total_cache_misses: Total number of cache misses
    """

    cache_hit_ratio: float = 0.0
    cache_savings_tokens: int = 0
    cache_savings_cost: float = 0.0
    latency_reduction_ms: int = 0
    total_cache_hits: int = 0
    total_cache_misses: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary format."""
        return {
            "cache_hit_ratio": self.cache_hit_ratio,
            "cache_savings_tokens": self.cache_savings_tokens,
            "cache_savings_cost": f"${self.cache_savings_cost:.2f}",
            "latency_reduction_ms": self.latency_reduction_ms,
            "total_cache_hits": self.total_cache_hits,
            "total_cache_misses": self.total_cache_misses,
        }


class CacheAvailabilityTracker:
    """
    Tracks which model/region combinations support caching.

    This class maintains a memory of which combinations have been tested
    and whether they support caching, to avoid repeated failed attempts.
    """

    def __init__(self, blacklist_duration_minutes: int = 60) -> None:
        """
        Initialize the availability tracker.

        Args:
            blacklist_duration_minutes: How long to remember unsupported combinations
        """
        self._unsupported_combos: Dict[Tuple[str, str], datetime] = {}
        self._supported_combos: Set[Tuple[str, str]] = set()
        self._blacklist_duration = timedelta(minutes=blacklist_duration_minutes)

    def is_cache_supported(self, model: str, region: str) -> Optional[bool]:
        """
        Check if caching is supported for a model/region combination.

        Args:
            model: Model identifier
            region: AWS region

        Returns:
            True if supported, False if not, None if unknown
        """
        combo = (model, region)

        # Check if we know it's supported
        if combo in self._supported_combos:
            return True

        # Check if we know it's unsupported (with expiry)
        if combo in self._unsupported_combos:
            blacklist_time = self._unsupported_combos[combo]
            if datetime.now() - blacklist_time < self._blacklist_duration:
                return False
            else:
                # Expired, remove from blacklist
                del self._unsupported_combos[combo]

        return None  # Unknown, need to try

    def mark_supported(self, model: str, region: str) -> None:
        """
        Mark a model/region combination as supporting caching.

        Args:
            model: Model identifier
            region: AWS region
        """
        combo = (model, region)
        self._supported_combos.add(combo)

        # Remove from unsupported if present
        if combo in self._unsupported_combos:
            del self._unsupported_combos[combo]

    def mark_unsupported(self, model: str, region: str) -> None:
        """
        Mark a model/region combination as not supporting caching.

        Args:
            model: Model identifier
            region: AWS region
        """
        combo = (model, region)
        self._unsupported_combos[combo] = datetime.now()

        # Remove from supported if present
        if combo in self._supported_combos:
            self._supported_combos.remove(combo)

    def clear_blacklist(self) -> None:
        """Clear the blacklist of unsupported combinations."""
        self._unsupported_combos.clear()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about tracked combinations.

        Returns:
            Dictionary with tracking statistics
        """
        return {
            "supported_combinations": len(self._supported_combos),
            "blacklisted_combinations": len(self._unsupported_combos),
            "total_tracked": len(self._supported_combos) + len(self._unsupported_combos),
        }


# Constants for cache-related errors
CACHE_UNSUPPORTED_ERRORS = (
    "ValidationException",
    "InvalidRequestException",
)

# Constants for cache analysis
CACHE_COST_PER_1K_TOKENS = 0.03  # Example cost, adjust based on actual pricing
