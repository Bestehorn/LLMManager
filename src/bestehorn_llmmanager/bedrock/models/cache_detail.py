"""
Typed per-TTL cache-write detail parsed from a Bedrock Converse response (issue #39).

Defines :class:`CacheDetail`, the typed view of a single ``CacheDetail`` object returned
inside ``usage.cacheDetails`` — the breakdown of cache-creation (write) tokens by TTL
duration — so callers can read how many tokens were written at each TTL without
hand-navigating the raw usage dict.

References:
- TokenUsage.cacheDetails (Array of CacheDetail; sorted by TTL, 1h before 5m):
  https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_TokenUsage.html
- CacheDetail (inputTokens: int; ttl: ``5m`` | ``1h``):
  https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_CacheDetail.html
"""

from dataclasses import dataclass
from typing import Any, Dict

from .llm_manager_constants import ConverseAPIFields


@dataclass(frozen=True)
class CacheDetail:
    """
    Cache-creation metrics for a single TTL duration.

    Attributes:
        input_tokens: Number of tokens written to cache with this TTL (cache-creation
            tokens). Defaults to 0 if absent.
        ttl: The TTL duration these cached tokens were written with (``"5m"`` or
            ``"1h"``). Empty string if absent.
    """

    input_tokens: int = 0
    ttl: str = ""

    @classmethod
    def from_cache_detail(cls, cache_detail: Dict[str, Any]) -> "CacheDetail":
        """
        Build a :class:`CacheDetail` from a raw ``CacheDetail`` dict.

        Args:
            cache_detail: A single ``CacheDetail`` object from ``usage.cacheDetails``.

        Returns:
            The typed :class:`CacheDetail`. Missing fields default to 0 / "".
        """
        return cls(
            input_tokens=cache_detail.get(ConverseAPIFields.CACHE_DETAIL_INPUT_TOKENS, 0),
            ttl=cache_detail.get(ConverseAPIFields.CACHE_DETAIL_TTL, ""),
        )
