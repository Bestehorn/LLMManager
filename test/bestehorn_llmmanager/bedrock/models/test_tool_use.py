"""
Tests for the ToolUse typed tool-call object (issue #31).
"""

from bestehorn_llmmanager.bedrock.models.tool_use import ToolUse


class TestToolUseFromBlock:
    """Build ToolUse from a raw toolUse block payload."""

    def test_from_tool_use_block_full(self):
        payload = {"toolUseId": "t-1", "name": "get_weather", "input": {"city": "Berlin"}}
        tool_use = ToolUse.from_tool_use_block(tool_use_block=payload)
        assert tool_use.tool_use_id == "t-1"
        assert tool_use.name == "get_weather"
        assert tool_use.input == {"city": "Berlin"}

    def test_from_tool_use_block_missing_input_defaults_empty(self):
        payload = {"toolUseId": "t-2", "name": "ping"}
        tool_use = ToolUse.from_tool_use_block(tool_use_block=payload)
        assert tool_use.input == {}

    def test_from_tool_use_block_none_input_defaults_empty(self):
        payload = {"toolUseId": "t-3", "name": "ping", "input": None}
        tool_use = ToolUse.from_tool_use_block(tool_use_block=payload)
        assert tool_use.input == {}

    def test_is_frozen(self):
        tool_use = ToolUse(tool_use_id="t-1", name="n", input={})
        import dataclasses

        import pytest

        with pytest.raises(dataclasses.FrozenInstanceError):
            tool_use.name = "other"  # type: ignore[misc]
