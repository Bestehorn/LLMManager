"""
Helper for building Bedrock Converse ``cachePoint`` blocks (issue #39).

Provides :func:`build_cache_point`, the single place that constructs a
``CachePointBlock`` (``{"cachePoint": {"type": ..., "ttl"?: ...}}``) and validates its
``type`` and optional ``ttl`` against the API's allowed values. It is reused by both
:meth:`MessageBuilder.add_cache_point` (cache points inside message content) and tool-
definition caching (a ``cachePoint`` appended to ``toolConfig.tools``), so the two paths
can never construct divergent or invalid blocks.

References:
- CachePointBlock (type: ``default``; ttl: ``5m`` | ``1h``):
  https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_CachePointBlock.html
- Tool (a ``cachePoint`` is a valid ``Tool`` union member):
  https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Tool.html
"""

from typing import Any, Dict, Optional

from ...message_builder_enums import CachePointTTLEnum
from ..exceptions.llm_manager_exceptions import RequestValidationError
from .llm_manager_constants import ConverseAPIFields

# The CachePointBlock.type field currently accepts only "default".
_VALID_CACHE_TYPES = frozenset({ConverseAPIFields.CACHE_TYPE_DEFAULT})
# CachePointBlock.ttl accepts the CachePointTTLEnum values ("5m", "1h").
_VALID_CACHE_TTLS = frozenset(member.value for member in CachePointTTLEnum)


def build_cache_point(
    cache_type: str = ConverseAPIFields.CACHE_TYPE_DEFAULT,
    ttl: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a validated ``cachePoint`` block.

    Args:
        cache_type: The cache point type. Only ``"default"`` is valid.
        ttl: Optional cache TTL. When provided it must be ``"5m"`` or ``"1h"``
            (a :class:`CachePointTTLEnum` value); when ``None`` the ``ttl`` key is
            omitted and Bedrock uses the default caching behavior for ``cache_type``.

    Returns:
        A ``{"cachePoint": {"type": <type>[, "ttl": <ttl>]}}`` dict. This shape is valid
        both as a message content block and as a ``Tool`` union member in
        ``toolConfig.tools``.

    Raises:
        RequestValidationError: If ``cache_type`` is not ``"default"`` or ``ttl`` is a
            value other than ``"5m"`` / ``"1h"``.
    """
    if cache_type not in _VALID_CACHE_TYPES:
        raise RequestValidationError(
            f"Invalid cache point type {cache_type!r}; valid values: {sorted(_VALID_CACHE_TYPES)}"
        )

    cache_point: Dict[str, Any] = {ConverseAPIFields.CACHE_TYPE: cache_type}

    if ttl is not None:
        ttl_value = ttl.value if isinstance(ttl, CachePointTTLEnum) else ttl
        if ttl_value not in _VALID_CACHE_TTLS:
            raise RequestValidationError(
                f"Invalid cache point ttl {ttl!r}; valid values: {sorted(_VALID_CACHE_TTLS)}"
            )
        cache_point[ConverseAPIFields.CACHE_TTL] = ttl_value

    return {ConverseAPIFields.CACHE_POINT: cache_point}
