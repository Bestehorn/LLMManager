"""
End-to-end (mocked) tool-use round-trip test for issue #31.

Exercises the full public surface — MessageBuilder.add_tool_use / add_tool_result and
BedrockResponse.get_tool_uses / has_tool_use — across a two-turn tool loop driven through
LLMManager.converse with a mocked Bedrock client (no AWS). The first model turn requests
a tool; the caller runs the tool, appends a toolResult, and the second model turn returns
the final answer.
"""

from unittest.mock import Mock, patch

import pytest

from bestehorn_llmmanager import (
    LLMManager,
    RolesEnum,
    ToolResultStatusEnum,
    ToolUse,
    create_assistant_message,
    create_user_message,
)
from bestehorn_llmmanager.bedrock.models.llm_manager_constants import ConverseAPIFields


@pytest.fixture
def mock_bedrock_catalog():
    """A catalog that resolves the test model with direct access."""
    catalog = Mock()
    catalog.get_model_info.return_value = Mock(
        model_id="test-model-id",
        has_direct_access=True,
        has_regional_cris=False,
        has_global_cris=False,
        regional_cris_profile_id=None,
        global_cris_profile_id=None,
    )
    catalog.is_model_available.return_value = True
    return catalog


@pytest.fixture
def manager(mock_bedrock_catalog):
    """A basic LLMManager wired to the mocked catalog."""
    with patch(
        "bestehorn_llmmanager.llm_manager.BedrockModelCatalog",
        return_value=mock_bedrock_catalog,
    ):
        return LLMManager(models=["Claude Haiku 4 5 20251001"], regions=["us-east-1"])


class TestToolUseRoundTripMocked:
    """A full request -> toolUse -> toolResult -> final-answer loop, mocked."""

    def test_tool_loop(self, manager):
        tool_use_turn = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {"text": "Let me check the weather."},
                        {
                            "toolUse": {
                                "toolUseId": "tool-77",
                                "name": "get_weather",
                                "input": {"city": "Paris"},
                            }
                        },
                    ],
                }
            },
            "stopReason": "tool_use",
        }
        final_turn = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [{"text": "It is 18 degrees in Paris."}],
                }
            },
            "stopReason": "end_turn",
        }

        mock_client = Mock()
        mock_client.converse.side_effect = [tool_use_turn, final_turn]

        tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": "get_weather",
                        "description": "Get the weather for a city.",
                        "inputSchema": {
                            "json": {
                                "type": "object",
                                "properties": {"city": {"type": "string"}},
                                "required": ["city"],
                            }
                        },
                    }
                }
            ]
        }

        with patch.object(manager._auth_manager, "get_bedrock_client", return_value=mock_client):
            # Turn 1: the user asks; the model requests the tool.
            first_message = create_user_message().add_text("What is the weather in Paris?").build()
            first = manager.converse(messages=[first_message], tool_config=tool_config)

            assert first.success is True
            assert first.has_tool_use() is True
            tool_uses = first.get_tool_uses()
            assert len(tool_uses) == 1
            tool_use = tool_uses[0]
            assert isinstance(tool_use, ToolUse)
            assert tool_use.name == "get_weather"
            assert tool_use.input == {"city": "Paris"}

            # The caller "runs" the tool, then replays the assistant turn and the result.
            assistant_turn = (
                create_assistant_message()
                .add_text("Let me check the weather.")
                .add_tool_use(
                    tool_use_id=tool_use.tool_use_id,
                    name=tool_use.name,
                    input=tool_use.input,
                )
                .build()
            )
            tool_result_turn = (
                create_user_message()
                .add_tool_result(
                    tool_use_id=tool_use.tool_use_id,
                    content={"temp_c": 18},
                    status=ToolResultStatusEnum.SUCCESS,
                )
                .build()
            )

            # The replayed turns are well-formed.
            assert assistant_turn[ConverseAPIFields.ROLE] == RolesEnum.ASSISTANT.value
            tr = tool_result_turn[ConverseAPIFields.CONTENT][0][ConverseAPIFields.TOOL_RESULT]
            assert tr[ConverseAPIFields.TOOL_USE_ID] == "tool-77"
            assert tr[ConverseAPIFields.TOOL_RESULT_STATUS] == "success"
            assert tr[ConverseAPIFields.TOOL_RESULT_CONTENT] == [
                {ConverseAPIFields.TOOL_RESULT_JSON: {"temp_c": 18}}
            ]

            # Turn 2: send the loop back; the model returns the final answer.
            second = manager.converse(
                messages=[first_message, assistant_turn, tool_result_turn],
                tool_config=tool_config,
            )

            assert second.success is True
            assert second.has_tool_use() is False
            assert second.get_tool_uses() == []
            assert second.get_content() == "It is 18 degrees in Paris."

        assert mock_client.converse.call_count == 2
