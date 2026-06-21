"""
Typed content-block classification for Bedrock Converse responses.

Defines :class:`ResponseContentType`, an enumeration of the member kinds of the Bedrock
Converse ``ContentBlock`` union, plus a classifier that maps a raw response content-block
dict to its type. This is the type vocabulary used by
:meth:`BedrockResponse.get_content_blocks` and the type-specific accessors built on it,
so callers can handle any modality (text, tool use, reasoning, image, citations, ...)
without hand-navigating the raw response dictionary.

Reference: AWS Bedrock Runtime ``ContentBlock`` union
https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ContentBlock.html
"""

from enum import Enum
from typing import Any, Dict, Optional

from .llm_manager_constants import ConverseAPIFields


class ResponseContentType(str, Enum):
    """
    Enumeration of Bedrock Converse ``ContentBlock`` union member kinds.

    Each value is the JSON key that identifies the union member within a single content
    block (a ``ContentBlock`` is a union, so exactly one of these keys is present in a
    well-formed block). ``UNKNOWN`` is used for a block whose discriminating key is not
    one this library recognizes, so forward-compatibility is preserved when AWS adds new
    block types.

    The string values intentionally equal the corresponding
    :class:`~bestehorn_llmmanager.bedrock.models.llm_manager_constants.ConverseAPIFields`
    field constants, so the enum doubles as the field key when reading a block.
    """

    TEXT = ConverseAPIFields.TEXT
    TOOL_USE = ConverseAPIFields.TOOL_USE
    TOOL_RESULT = ConverseAPIFields.TOOL_RESULT
    REASONING_CONTENT = ConverseAPIFields.REASONING_CONTENT
    IMAGE = ConverseAPIFields.IMAGE
    DOCUMENT = ConverseAPIFields.DOCUMENT
    VIDEO = ConverseAPIFields.VIDEO
    CITATIONS_CONTENT = ConverseAPIFields.CITATIONS_CONTENT
    GUARD_CONTENT = ConverseAPIFields.GUARD_CONTENT
    CACHE_POINT = ConverseAPIFields.CACHE_POINT
    AUDIO = ConverseAPIFields.AUDIO
    SEARCH_RESULT = ConverseAPIFields.SEARCH_RESULT
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        """Return the string value of the enum."""
        return self.value

    @classmethod
    def from_block(cls, block: Any) -> "ResponseContentType":
        """
        Classify a single response content block by its discriminating union key.

        The first recognized key present in the block determines its type. Recognized
        keys are checked in a fixed, deterministic order so classification is stable.
        ``block`` is typed ``Any`` because response content lists may legitimately
        contain non-dict junk (defensively tolerated) — those classify as ``UNKNOWN``.

        Args:
            block: A single content-block dict from a Converse response message (or any
                value; non-dict values classify as ``UNKNOWN``).

        Returns:
            The matching :class:`ResponseContentType`, or :attr:`ResponseContentType.UNKNOWN`
            if the block is not a dict or contains no recognized discriminating key.
        """
        if not isinstance(block, dict):
            return cls.UNKNOWN

        for content_type in cls._ordered_known_types():
            if content_type.value in block:
                return content_type

        return cls.UNKNOWN

    @classmethod
    def _ordered_known_types(cls) -> tuple["ResponseContentType", ...]:
        """
        Return the recognized (non-UNKNOWN) content types in deterministic check order.

        Returns:
            Tuple of every member except :attr:`UNKNOWN`, in declaration order.
        """
        return tuple(member for member in cls if member is not cls.UNKNOWN)


def get_block_type(block: Optional[Dict[str, Any]]) -> ResponseContentType:
    """
    Convenience wrapper to classify a content block, tolerating ``None``.

    Args:
        block: A single content-block dict, or ``None``.

    Returns:
        The block's :class:`ResponseContentType`, or :attr:`ResponseContentType.UNKNOWN`
        when ``block`` is ``None`` or not a dict.
    """
    if block is None:
        return ResponseContentType.UNKNOWN
    return ResponseContentType.from_block(block=block)
