"""
Multi-turn reasoning round-trip test for issue #32 (mocked, no AWS).

Verifies that a reasoning block parsed from a model response can be echoed back into a
subsequent turn with its signature preserved verbatim — the property that makes
multi-turn extended-thinking conversations valid. Exercises the public surface
(LLMManager.converse + MessageBuilder.add_reasoning_content + BedrockResponse.get_reasoning)
end to end with a mocked Bedrock client.
"""

from unittest.mock import Mock, patch

import pytest

from bestehorn_llmmanager import LLMManager, create_assistant_message, create_user_message
from bestehorn_llmmanager.bedrock.models.llm_manager_constants import ConverseAPIFields


@pytest.fixture
def mock_bedrock_catalog():
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
    with patch(
        "bestehorn_llmmanager.llm_manager.BedrockModelCatalog",
        return_value=mock_bedrock_catalog,
    ):
        return LLMManager(models=["Claude Haiku 4 5 20251001"], regions=["us-east-1"])


class TestReasoningRoundTripMocked:
    """Parse reasoning from turn 1, echo it back unmodified into turn 2."""

    def test_signature_preserved_across_turns(self, manager):
        reasoning_turn = {
            "output": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "reasoningContent": {
                                "reasoningText": {
                                    "text": "Let me reason about this.",
                                    "signature": "sig-multiturn-123",
                                }
                            }
                        },
                        {"text": "Partial answer."},
                    ],
                }
            },
            "stopReason": "end_turn",
        }
        final_turn = {
            "output": {"message": {"role": "assistant", "content": [{"text": "Done."}]}},
            "stopReason": "end_turn",
        }
        mock_client = Mock()
        mock_client.converse.side_effect = [reasoning_turn, final_turn]

        # Extended thinking is enabled via additional_model_request_fields (already
        # supported by the library) — passed through to the mocked client here.
        thinking_fields = {"thinking": {"type": "enabled", "budget_tokens": 1024}}

        with patch.object(manager._auth_manager, "get_bedrock_client", return_value=mock_client):
            first_message = create_user_message().add_text("Solve this.").build()
            first = manager.converse(
                messages=[first_message],
                additional_model_request_fields=thinking_fields,
            )

            reasoning = first.get_reasoning()
            assert reasoning is not None
            assert reasoning.signature == "sig-multiturn-123"

            # Echo the reasoning back unmodified, plus a follow-up user turn.
            assistant_turn = (
                create_assistant_message()
                .add_reasoning_content(text=reasoning.text, signature=reasoning.signature)
                .add_text("Partial answer.")
                .build()
            )
            follow_up = create_user_message().add_text("Now finish.").build()

            # The echoed block carries the signature verbatim.
            reasoning_block = assistant_turn[ConverseAPIFields.CONTENT][0][
                ConverseAPIFields.REASONING_CONTENT
            ][ConverseAPIFields.REASONING_TEXT]
            assert reasoning_block[ConverseAPIFields.REASONING_SIGNATURE] == "sig-multiturn-123"
            assert reasoning_block[ConverseAPIFields.TEXT] == "Let me reason about this."

            second = manager.converse(
                messages=[first_message, assistant_turn, follow_up],
                additional_model_request_fields=thinking_fields,
            )
            assert second.success is True
            assert second.get_content() == "Done."

        # Verify the echoed-back reasoning reached the API on the second call.
        assert mock_client.converse.call_count == 2
        second_call_messages = mock_client.converse.call_args_list[1].kwargs["messages"]
        echoed = second_call_messages[1][ConverseAPIFields.CONTENT][0]
        assert (
            echoed[ConverseAPIFields.REASONING_CONTENT][ConverseAPIFields.REASONING_TEXT][
                ConverseAPIFields.REASONING_SIGNATURE
            ]
            == "sig-multiturn-123"
        )
