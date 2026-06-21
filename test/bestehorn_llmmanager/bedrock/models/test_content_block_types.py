"""
Tests for the ResponseContentType enum and block classifier (issue #41).
"""

import pytest

from bestehorn_llmmanager.bedrock.models.content_block_types import (
    ResponseContentType,
    get_block_type,
)


class TestResponseContentTypeClassification:
    """Classify each recognized ContentBlock union member."""

    @pytest.mark.parametrize(
        "block,expected",
        [
            ({"text": "hello"}, ResponseContentType.TEXT),
            (
                {"toolUse": {"toolUseId": "t1", "name": "calc", "input": {}}},
                ResponseContentType.TOOL_USE,
            ),
            ({"toolResult": {"toolUseId": "t1", "content": []}}, ResponseContentType.TOOL_RESULT),
            (
                {"reasoningContent": {"reasoningText": {"text": "because"}}},
                ResponseContentType.REASONING_CONTENT,
            ),
            ({"image": {"format": "png", "source": {"bytes": b"x"}}}, ResponseContentType.IMAGE),
            (
                {"document": {"format": "pdf", "name": "d", "source": {}}},
                ResponseContentType.DOCUMENT,
            ),
            ({"video": {"format": "mp4", "source": {}}}, ResponseContentType.VIDEO),
            (
                {"citationsContent": {"content": [], "citations": []}},
                ResponseContentType.CITATIONS_CONTENT,
            ),
            ({"guardContent": {"text": {"text": "g"}}}, ResponseContentType.GUARD_CONTENT),
            ({"cachePoint": {"type": "default"}}, ResponseContentType.CACHE_POINT),
            ({"audio": {"format": "wav", "source": {}}}, ResponseContentType.AUDIO),
            ({"searchResult": {}}, ResponseContentType.SEARCH_RESULT),
        ],
    )
    def test_from_block_recognizes_each_type(self, block, expected):
        """Each known union member key classifies to its enum value."""
        assert ResponseContentType.from_block(block=block) is expected

    def test_from_block_unknown_key(self):
        """A block with no recognized key is UNKNOWN (forward-compatible)."""
        assert ResponseContentType.from_block(block={"brandNewBlock": {}}) is (
            ResponseContentType.UNKNOWN
        )

    def test_from_block_non_dict(self):
        """A non-dict block is UNKNOWN, not an error."""
        assert ResponseContentType.from_block(block="not_a_dict") is ResponseContentType.UNKNOWN
        assert ResponseContentType.from_block(block=[]) is ResponseContentType.UNKNOWN

    def test_enum_value_equals_field_key(self):
        """The enum value is exactly the JSON discriminating key."""
        assert ResponseContentType.TEXT.value == "text"
        assert ResponseContentType.TOOL_USE.value == "toolUse"
        assert ResponseContentType.REASONING_CONTENT.value == "reasoningContent"
        assert ResponseContentType.CITATIONS_CONTENT.value == "citationsContent"
        assert str(ResponseContentType.IMAGE) == "image"

    def test_ordered_known_types_excludes_unknown(self):
        """The internal check order never includes UNKNOWN."""
        ordered = ResponseContentType._ordered_known_types()
        assert ResponseContentType.UNKNOWN not in ordered
        assert ResponseContentType.TEXT in ordered
        assert len(ordered) == len(list(ResponseContentType)) - 1


class TestGetBlockTypeHelper:
    """The get_block_type() convenience wrapper."""

    def test_classifies_dict(self):
        assert get_block_type(block={"text": "hi"}) is ResponseContentType.TEXT

    def test_none_is_unknown(self):
        assert get_block_type(block=None) is ResponseContentType.UNKNOWN
