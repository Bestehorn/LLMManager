"""
Typed tool-use (function-calling) request parsed from a Bedrock Converse response.

Defines :class:`ToolUse`, the typed view of a ``toolUse`` content block a model emits
when it wants a tool run, so callers can read the tool id/name/input without
hand-navigating the raw response dictionary.

Reference: AWS Bedrock Runtime ``ToolUseBlock``
https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolUseBlock.html
"""

from dataclasses import dataclass
from typing import Any, Dict

from .llm_manager_constants import ConverseAPIFields


@dataclass(frozen=True)
class ToolUse:
    """
    A single tool-use (function-call) request emitted by the model.

    Attributes:
        tool_use_id: The ID for the tool request (echo it back on the matching
            ``toolResult``).
        name: The name of the tool the model wants to use.
        input: The parsed input arguments to pass to the tool (a JSON object).
    """

    tool_use_id: str
    name: str
    input: Dict[str, Any]

    @classmethod
    def from_tool_use_block(cls, tool_use_block: Dict[str, Any]) -> "ToolUse":
        """
        Build a :class:`ToolUse` from the payload under a block's ``toolUse`` key.

        Args:
            tool_use_block: The ``ToolUseBlock`` payload — the value under the
                ``toolUse`` key of a content block (``{"toolUseId", "name", "input"}``).

        Returns:
            The typed :class:`ToolUse`. Missing ``input`` defaults to an empty dict.
        """
        return cls(
            tool_use_id=tool_use_block.get(ConverseAPIFields.TOOL_USE_ID, ""),
            name=tool_use_block.get(ConverseAPIFields.TOOL_NAME, ""),
            input=tool_use_block.get(ConverseAPIFields.TOOL_INPUT, {}) or {},
        )
