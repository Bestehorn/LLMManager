"""
Tests for the canonical stop-reason model (issue #37).

`StopReasonEnum` must cover all 9 Bedrock Converse ``stopReason`` values and be the single
source of truth shared by the core ``ConverseAPIFields`` and the streaming
``StreamingConstants``. ``StopReasonClassifier`` categorizes each value for retry/failover
decisions.
"""

from bestehorn_llmmanager.bedrock.models.llm_manager_constants import ConverseAPIFields
from bestehorn_llmmanager.bedrock.models.stop_reason import (
    StopReasonCategory,
    StopReasonClassifier,
    StopReasonEnum,
)
from bestehorn_llmmanager.bedrock.streaming.streaming_constants import StreamingConstants

# The authoritative Bedrock Converse StopReason enum (boto3 bedrock-runtime service model).
BEDROCK_STOP_REASONS = {
    "end_turn",
    "tool_use",
    "max_tokens",
    "stop_sequence",
    "guardrail_intervened",
    "content_filtered",
    "malformed_model_output",
    "malformed_tool_use",
    "model_context_window_exceeded",
}


class TestStopReasonEnumCoversBedrock:
    def test_enum_equals_bedrock_set(self):
        assert {r.value for r in StopReasonEnum} == BEDROCK_STOP_REASONS

    def test_previously_missing_values_present(self):
        values = {r.value for r in StopReasonEnum}
        for v in (
            "guardrail_intervened",
            "malformed_model_output",
            "malformed_tool_use",
            "model_context_window_exceeded",
        ):
            assert v in values


class TestCoreAndStreamingUnified:
    """The core + streaming stop-reason constants derive from the canonical enum."""

    def test_core_constants_match_enum(self):
        assert ConverseAPIFields.STOP_REASON_END_TURN == StopReasonEnum.END_TURN.value
        assert ConverseAPIFields.STOP_REASON_MAX_TOKENS == StopReasonEnum.MAX_TOKENS.value
        assert ConverseAPIFields.STOP_REASON_STOP_SEQUENCE == StopReasonEnum.STOP_SEQUENCE.value
        assert ConverseAPIFields.STOP_REASON_TOOL_USE == StopReasonEnum.TOOL_USE.value
        assert (
            ConverseAPIFields.STOP_REASON_CONTENT_FILTERED == StopReasonEnum.CONTENT_FILTERED.value
        )
        # Newly added on the core side:
        assert (
            ConverseAPIFields.STOP_REASON_GUARDRAIL_INTERVENED
            == StopReasonEnum.GUARDRAIL_INTERVENED.value
        )
        assert (
            ConverseAPIFields.STOP_REASON_MALFORMED_MODEL_OUTPUT
            == StopReasonEnum.MALFORMED_MODEL_OUTPUT.value
        )
        assert (
            ConverseAPIFields.STOP_REASON_MALFORMED_TOOL_USE
            == StopReasonEnum.MALFORMED_TOOL_USE.value
        )
        assert (
            ConverseAPIFields.STOP_REASON_MODEL_CONTEXT_WINDOW_EXCEEDED
            == StopReasonEnum.MODEL_CONTEXT_WINDOW_EXCEEDED.value
        )

    def test_streaming_constants_match_enum(self):
        assert StreamingConstants.STOP_REASON_END_TURN == StopReasonEnum.END_TURN.value
        assert (
            StreamingConstants.STOP_REASON_GUARDRAIL_INTERVENED
            == StopReasonEnum.GUARDRAIL_INTERVENED.value
        )
        # Streaming now also carries the malformed/context values (parity with core):
        assert (
            StreamingConstants.STOP_REASON_MALFORMED_MODEL_OUTPUT
            == StopReasonEnum.MALFORMED_MODEL_OUTPUT.value
        )
        assert (
            StreamingConstants.STOP_REASON_MODEL_CONTEXT_WINDOW_EXCEEDED
            == StopReasonEnum.MODEL_CONTEXT_WINDOW_EXCEEDED.value
        )

    def test_core_and_streaming_agree_on_every_shared_value(self):
        """Every core STOP_REASON_* constant equals the streaming one of the same name."""
        for enum_member in StopReasonEnum:
            name = f"STOP_REASON_{enum_member.name}"
            assert getattr(ConverseAPIFields, name) == getattr(StreamingConstants, name), name


class TestStopReasonClassifier:
    """Retry/failover categorization for each stop reason."""

    def test_terminal_reasons_not_retryable(self):
        for reason in (
            StopReasonEnum.END_TURN,
            StopReasonEnum.TOOL_USE,
            StopReasonEnum.STOP_SEQUENCE,
            StopReasonEnum.MAX_TOKENS,
        ):
            assert StopReasonClassifier.categorize(reason) == StopReasonCategory.TERMINAL
            assert StopReasonClassifier.is_terminal(reason)
            assert not StopReasonClassifier.is_retryable(reason)

    def test_model_context_window_exceeded_retries_different_target(self):
        reason = StopReasonEnum.MODEL_CONTEXT_WINDOW_EXCEEDED
        assert StopReasonClassifier.categorize(reason) == StopReasonCategory.RETRY_DIFFERENT_TARGET
        assert StopReasonClassifier.is_retryable(reason)
        # It must NOT be classified as a plain same-target retry: a model whose context
        # window was exceeded will reject the same oversized input again.
        assert not StopReasonClassifier.is_terminal(reason)

    def test_malformed_reasons_are_retryable(self):
        for reason in (
            StopReasonEnum.MALFORMED_MODEL_OUTPUT,
            StopReasonEnum.MALFORMED_TOOL_USE,
        ):
            assert StopReasonClassifier.is_retryable(reason)
            assert not StopReasonClassifier.is_terminal(reason)

    def test_guardrail_and_content_filtered_categorized(self):
        for reason in (
            StopReasonEnum.GUARDRAIL_INTERVENED,
            StopReasonEnum.CONTENT_FILTERED,
        ):
            # These are not normal completion; a different target may behave differently.
            assert not StopReasonClassifier.is_terminal(reason)

    def test_classifier_accepts_raw_string(self):
        """categorize() also accepts the raw API string (what get_stop_reason returns)."""
        assert (
            StopReasonClassifier.categorize("model_context_window_exceeded")
            == StopReasonCategory.RETRY_DIFFERENT_TARGET
        )
        assert StopReasonClassifier.categorize("end_turn") == StopReasonCategory.TERMINAL

    def test_unknown_value_is_unknown_category(self):
        """An unrecognized stop reason is categorized UNKNOWN (forward-compatible, not a crash)."""
        assert StopReasonClassifier.categorize("some_future_reason") == StopReasonCategory.UNKNOWN
        assert StopReasonClassifier.categorize(None) == StopReasonCategory.UNKNOWN


class TestBedrockResponseStopReasonCategory:
    """BedrockResponse surfaces the canonical category for its raw stop reason."""

    def test_get_stop_reason_category(self):
        from bestehorn_llmmanager.bedrock.models.bedrock_response import BedrockResponse

        response = BedrockResponse(
            success=True,
            response_data={ConverseAPIFields.STOP_REASON: "model_context_window_exceeded"},
        )
        assert response.get_stop_reason() == "model_context_window_exceeded"
        assert response.get_stop_reason_category() == StopReasonCategory.RETRY_DIFFERENT_TARGET

    def test_get_stop_reason_category_terminal(self):
        from bestehorn_llmmanager.bedrock.models.bedrock_response import BedrockResponse

        response = BedrockResponse(
            success=True,
            response_data={ConverseAPIFields.STOP_REASON: "end_turn"},
        )
        assert response.get_stop_reason_category() == StopReasonCategory.TERMINAL

    def test_get_stop_reason_category_none_when_absent(self):
        from bestehorn_llmmanager.bedrock.models.bedrock_response import BedrockResponse

        response = BedrockResponse(success=True, response_data={})
        assert response.get_stop_reason_category() == StopReasonCategory.UNKNOWN
