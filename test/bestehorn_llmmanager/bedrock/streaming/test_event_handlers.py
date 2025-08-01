"""
Tests for AWS Bedrock streaming event handlers.

Tests the StreamEventHandler class which processes different streaming event types
from AWS Bedrock Converse Stream API.
"""

from unittest.mock import MagicMock, patch

import pytest

from bestehorn_llmmanager.bedrock.streaming.event_handlers import StreamEventHandler
from bestehorn_llmmanager.bedrock.streaming.streaming_constants import (
    StreamingConstants,
    StreamingErrorMessages,
    StreamingEventTypes,
)


class TestStreamEventHandler:
    """Test suite for StreamEventHandler class."""

    @pytest.fixture
    def handler(self):
        """Create a StreamEventHandler instance for testing."""
        return StreamEventHandler()

    @pytest.fixture
    def sample_message_start_event(self):
        """Sample messageStart event."""
        return {StreamingConstants.FIELD_ROLE: "assistant"}

    @pytest.fixture
    def sample_content_block_start_event(self):
        """Sample contentBlockStart event."""
        return {
            StreamingConstants.FIELD_START: {
                StreamingConstants.FIELD_TOOL_USE: {
                    StreamingConstants.FIELD_TOOL_USE_ID: "tool123",
                    StreamingConstants.FIELD_NAME: "get_weather",
                }
            },
            StreamingConstants.FIELD_CONTENT_BLOCK_INDEX: 0,
        }

    @pytest.fixture
    def sample_content_block_delta_event(self):
        """Sample contentBlockDelta event."""
        return {
            StreamingConstants.FIELD_DELTA: {
                StreamingConstants.FIELD_TEXT: "Hello world",
                StreamingConstants.FIELD_TOOL_USE: {
                    StreamingConstants.FIELD_INPUT: '{"location": "Boston"}'
                },
                StreamingConstants.FIELD_REASONING_CONTENT: {
                    StreamingConstants.FIELD_TEXT: "Let me think about this"
                },
                StreamingConstants.FIELD_CITATION: {
                    StreamingConstants.FIELD_TITLE: "Sample Source"
                },
            },
            StreamingConstants.FIELD_CONTENT_BLOCK_INDEX: 0,
        }

    @pytest.fixture
    def sample_content_block_stop_event(self):
        """Sample contentBlockStop event."""
        return {StreamingConstants.FIELD_CONTENT_BLOCK_INDEX: 0}

    @pytest.fixture
    def sample_message_stop_event(self):
        """Sample messageStop event."""
        return {
            StreamingConstants.FIELD_STOP_REASON: StreamingConstants.STOP_REASON_END_TURN,
            StreamingConstants.FIELD_ADDITIONAL_MODEL_RESPONSE_FIELDS: {"key": "value"},
        }

    @pytest.fixture
    def sample_metadata_event(self):
        """Sample metadata event."""
        return {
            StreamingConstants.FIELD_USAGE: {
                StreamingConstants.FIELD_INPUT_TOKENS: 100,
                StreamingConstants.FIELD_OUTPUT_TOKENS: 50,
                StreamingConstants.FIELD_TOTAL_TOKENS: 150,
                StreamingConstants.FIELD_CACHE_READ_INPUT_TOKENS: 10,
                StreamingConstants.FIELD_CACHE_WRITE_INPUT_TOKENS: 5,
            },
            StreamingConstants.FIELD_METRICS: {StreamingConstants.FIELD_LATENCY_MS: 250},
            StreamingConstants.FIELD_TRACE: {"trace_id": "123"},
            StreamingConstants.FIELD_PERFORMANCE_CONFIG: {"config": "value"},
        }

    @pytest.fixture
    def sample_error_event(self):
        """Sample error event."""
        return {
            StreamingConstants.FIELD_MESSAGE: "Internal server error",
            StreamingConstants.FIELD_ORIGINAL_STATUS_CODE: 500,
            StreamingConstants.FIELD_ORIGINAL_MESSAGE: "Server error",
        }

    def test_init(self):
        """Test StreamEventHandler initialization."""
        handler = StreamEventHandler()
        assert handler._logger is not None
        assert handler._logger.name == "bestehorn_llmmanager.bedrock.streaming.event_handlers"

    def test_handle_message_start_valid(self, handler, sample_message_start_event):
        """Test handling valid messageStart event."""
        result = handler.handle_message_start(sample_message_start_event)

        assert result[StreamingConstants.FIELD_ROLE] == "assistant"
        assert result["event_type"] == StreamingEventTypes.MESSAGE_START

    def test_handle_message_start_invalid_format(self, handler):
        """Test handling messageStart event with invalid format."""
        with pytest.raises(ValueError) as exc_info:
            handler.handle_message_start("invalid")

        assert StreamingErrorMessages.INVALID_STREAM_EVENT.format(event="invalid") in str(
            exc_info.value
        )

    def test_handle_message_start_missing_role(self, handler):
        """Test handling messageStart event with missing role."""
        event = {}
        with pytest.raises(ValueError) as exc_info:
            handler.handle_message_start(event)

        assert StreamingErrorMessages.MALFORMED_EVENT_DATA.format(data=event) in str(exc_info.value)

    @patch("bestehorn_llmmanager.bedrock.streaming.event_handlers.logging.getLogger")
    def test_handle_message_start_logging(
        self, mock_get_logger, handler, sample_message_start_event
    ):
        """Test logging in handle_message_start."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        handler._logger = mock_logger

        handler.handle_message_start(sample_message_start_event)

        mock_logger.debug.assert_called_once_with("Message started with role: assistant")

    def test_handle_content_block_start_valid(self, handler, sample_content_block_start_event):
        """Test handling valid contentBlockStart event."""
        result = handler.handle_content_block_start(sample_content_block_start_event)

        assert StreamingConstants.FIELD_START in result
        assert result[StreamingConstants.FIELD_CONTENT_BLOCK_INDEX] == 0
        assert result["event_type"] == StreamingEventTypes.CONTENT_BLOCK_START

    def test_handle_content_block_start_minimal(self, handler):
        """Test handling contentBlockStart event with minimal data."""
        event = {}
        result = handler.handle_content_block_start(event)

        assert result[StreamingConstants.FIELD_START] == {}
        assert result[StreamingConstants.FIELD_CONTENT_BLOCK_INDEX] == 0
        assert result["event_type"] == StreamingEventTypes.CONTENT_BLOCK_START

    def test_handle_content_block_start_invalid_format(self, handler):
        """Test handling contentBlockStart event with invalid format."""
        with pytest.raises(ValueError) as exc_info:
            handler.handle_content_block_start("invalid")

        assert StreamingErrorMessages.INVALID_STREAM_EVENT.format(event="invalid") in str(
            exc_info.value
        )

    @patch("bestehorn_llmmanager.bedrock.streaming.event_handlers.logging.getLogger")
    def test_handle_content_block_start_with_tool_logging(
        self, mock_get_logger, handler, sample_content_block_start_event
    ):
        """Test logging in handle_content_block_start with tool use."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        handler._logger = mock_logger

        handler.handle_content_block_start(sample_content_block_start_event)

        mock_logger.debug.assert_called_once_with("Tool use started: get_weather (ID: tool123)")

    def test_handle_content_block_delta_valid(self, handler, sample_content_block_delta_event):
        """Test handling valid contentBlockDelta event."""
        result = handler.handle_content_block_delta(sample_content_block_delta_event)

        assert StreamingConstants.FIELD_DELTA in result
        assert result[StreamingConstants.FIELD_CONTENT_BLOCK_INDEX] == 0
        assert result["event_type"] == StreamingEventTypes.CONTENT_BLOCK_DELTA
        assert "content" in result
        # Content should include text and reasoning text
        assert "Hello worldLet me think about this" in result["content"]

    def test_handle_content_block_delta_invalid_format(self, handler):
        """Test handling contentBlockDelta event with invalid format."""
        with pytest.raises(ValueError) as exc_info:
            handler.handle_content_block_delta("invalid")

        assert StreamingErrorMessages.INVALID_STREAM_EVENT.format(event="invalid") in str(
            exc_info.value
        )

    def test_handle_content_block_delta_minimal(self, handler):
        """Test handling contentBlockDelta event with minimal data."""
        event = {}
        result = handler.handle_content_block_delta(event)

        assert result[StreamingConstants.FIELD_DELTA] == {"content": ""}
        assert result[StreamingConstants.FIELD_CONTENT_BLOCK_INDEX] == 0
        assert result["event_type"] == StreamingEventTypes.CONTENT_BLOCK_DELTA
        assert result["content"] == ""

    def test_handle_content_block_stop_valid(self, handler, sample_content_block_stop_event):
        """Test handling valid contentBlockStop event."""
        result = handler.handle_content_block_stop(sample_content_block_stop_event)

        assert result[StreamingConstants.FIELD_CONTENT_BLOCK_INDEX] == 0
        assert result["event_type"] == StreamingEventTypes.CONTENT_BLOCK_STOP

    def test_handle_content_block_stop_invalid_format(self, handler):
        """Test handling contentBlockStop event with invalid format."""
        with pytest.raises(ValueError) as exc_info:
            handler.handle_content_block_stop("invalid")

        assert StreamingErrorMessages.INVALID_STREAM_EVENT.format(event="invalid") in str(
            exc_info.value
        )

    @patch("bestehorn_llmmanager.bedrock.streaming.event_handlers.logging.getLogger")
    def test_handle_content_block_stop_logging(
        self, mock_get_logger, handler, sample_content_block_stop_event
    ):
        """Test logging in handle_content_block_stop."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        handler._logger = mock_logger

        handler.handle_content_block_stop(sample_content_block_stop_event)

        mock_logger.debug.assert_called_once_with("Content block 0 completed")

    def test_handle_message_stop_valid(self, handler, sample_message_stop_event):
        """Test handling valid messageStop event."""
        result = handler.handle_message_stop(sample_message_stop_event)

        assert (
            result[StreamingConstants.FIELD_STOP_REASON] == StreamingConstants.STOP_REASON_END_TURN
        )
        assert result[StreamingConstants.FIELD_ADDITIONAL_MODEL_RESPONSE_FIELDS] == {"key": "value"}
        assert result["event_type"] == StreamingEventTypes.MESSAGE_STOP

    def test_handle_message_stop_minimal(self, handler):
        """Test handling messageStop event with minimal data."""
        event = {}
        result = handler.handle_message_stop(event)

        assert result[StreamingConstants.FIELD_STOP_REASON] is None
        assert result[StreamingConstants.FIELD_ADDITIONAL_MODEL_RESPONSE_FIELDS] is None
        assert result["event_type"] == StreamingEventTypes.MESSAGE_STOP

    def test_handle_message_stop_invalid_format(self, handler):
        """Test handling messageStop event with invalid format."""
        with pytest.raises(ValueError) as exc_info:
            handler.handle_message_stop("invalid")

        assert StreamingErrorMessages.INVALID_STREAM_EVENT.format(event="invalid") in str(
            exc_info.value
        )

    @patch("bestehorn_llmmanager.bedrock.streaming.event_handlers.logging.getLogger")
    def test_handle_message_stop_logging(self, mock_get_logger, handler, sample_message_stop_event):
        """Test logging in handle_message_stop."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        handler._logger = mock_logger

        handler.handle_message_stop(sample_message_stop_event)

        mock_logger.debug.assert_called_once_with("Message stopped with reason: end_turn")

    def test_handle_metadata_valid(self, handler, sample_metadata_event):
        """Test handling valid metadata event."""
        result = handler.handle_metadata(sample_metadata_event)

        assert StreamingConstants.FIELD_USAGE in result
        assert result[StreamingConstants.FIELD_USAGE]["input_tokens"] == 100
        assert result[StreamingConstants.FIELD_USAGE]["output_tokens"] == 50
        assert result[StreamingConstants.FIELD_USAGE]["total_tokens"] == 150
        assert result[StreamingConstants.FIELD_USAGE]["cache_read_tokens"] == 10
        assert result[StreamingConstants.FIELD_USAGE]["cache_write_tokens"] == 5
        assert result[StreamingConstants.FIELD_METRICS] == {
            StreamingConstants.FIELD_LATENCY_MS: 250
        }
        assert result["event_type"] == StreamingEventTypes.METADATA
        assert result["latency_ms"] == 250

    def test_handle_metadata_minimal(self, handler):
        """Test handling metadata event with minimal data."""
        event = {}
        result = handler.handle_metadata(event)

        expected_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cache_read_tokens": 0,
            "cache_write_tokens": 0,
        }
        assert result[StreamingConstants.FIELD_USAGE] == expected_usage
        assert result[StreamingConstants.FIELD_METRICS] == {}
        assert result["event_type"] == StreamingEventTypes.METADATA
        assert result["latency_ms"] is None

    def test_handle_metadata_invalid_format(self, handler):
        """Test handling metadata event with invalid format."""
        with pytest.raises(ValueError) as exc_info:
            handler.handle_metadata("invalid")

        assert StreamingErrorMessages.INVALID_STREAM_EVENT.format(event="invalid") in str(
            exc_info.value
        )

    @patch("bestehorn_llmmanager.bedrock.streaming.event_handlers.logging.getLogger")
    def test_handle_metadata_logging(self, mock_get_logger, handler, sample_metadata_event):
        """Test logging in handle_metadata."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        handler._logger = mock_logger

        handler.handle_metadata(sample_metadata_event)

        mock_logger.debug.assert_called_once_with("Received metadata: 150 tokens, 250 ms latency")

    def test_handle_error_event_general(self, handler, sample_error_event):
        """Test handling general error event."""
        result = handler.handle_error_event(
            sample_error_event, StreamingEventTypes.INTERNAL_SERVER_EXCEPTION
        )

        assert result[StreamingConstants.FIELD_MESSAGE] == "Internal server error"
        assert result["event_type"] == StreamingEventTypes.INTERNAL_SERVER_EXCEPTION
        assert result["is_error"] is True

    def test_handle_error_event_model_stream_error(self, handler, sample_error_event):
        """Test handling model stream error event."""
        result = handler.handle_error_event(
            sample_error_event, StreamingEventTypes.MODEL_STREAM_ERROR_EXCEPTION
        )

        assert result[StreamingConstants.FIELD_MESSAGE] == "Internal server error"
        assert result["event_type"] == StreamingEventTypes.MODEL_STREAM_ERROR_EXCEPTION
        assert result["is_error"] is True
        assert result[StreamingConstants.FIELD_ORIGINAL_STATUS_CODE] == 500
        assert result[StreamingConstants.FIELD_ORIGINAL_MESSAGE] == "Server error"

    def test_handle_error_event_no_message(self, handler):
        """Test handling error event with no message."""
        event = {}
        result = handler.handle_error_event(event, StreamingEventTypes.VALIDATION_EXCEPTION)

        assert result[StreamingConstants.FIELD_MESSAGE] == "Unknown error"
        assert result["event_type"] == StreamingEventTypes.VALIDATION_EXCEPTION
        assert result["is_error"] is True

    def test_handle_error_event_invalid_format(self, handler):
        """Test handling error event with invalid format."""
        with pytest.raises(ValueError) as exc_info:
            handler.handle_error_event("invalid", StreamingEventTypes.INTERNAL_SERVER_EXCEPTION)

        assert StreamingErrorMessages.INVALID_STREAM_EVENT.format(event="invalid") in str(
            exc_info.value
        )

    @patch("bestehorn_llmmanager.bedrock.streaming.event_handlers.logging.getLogger")
    def test_handle_error_event_logging(self, mock_get_logger, handler, sample_error_event):
        """Test logging in handle_error_event."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        handler._logger = mock_logger

        handler.handle_error_event(
            sample_error_event, StreamingEventTypes.INTERNAL_SERVER_EXCEPTION
        )

        mock_logger.error.assert_called_once_with(
            f"Streaming error ({StreamingEventTypes.INTERNAL_SERVER_EXCEPTION}): Internal server error"
        )

    def test_process_delta_content_text_only(self, handler):
        """Test processing delta content with text only."""
        delta = {StreamingConstants.FIELD_TEXT: "Hello world"}
        result = handler._process_delta_content(delta)

        assert result["content"] == "Hello world"
        assert StreamingConstants.FIELD_TEXT in result

    def test_process_delta_content_tool_use(self, handler):
        """Test processing delta content with tool use."""
        delta = {
            StreamingConstants.FIELD_TOOL_USE: {
                StreamingConstants.FIELD_INPUT: '{"location": "Boston"}'
            }
        }
        result = handler._process_delta_content(delta)

        assert result["tool_input"] == '{"location": "Boston"}'
        assert result["content"] == ""

    def test_process_delta_content_reasoning(self, handler):
        """Test processing delta content with reasoning."""
        delta = {
            StreamingConstants.FIELD_REASONING_CONTENT: {
                StreamingConstants.FIELD_TEXT: "Let me think"
            }
        }
        result = handler._process_delta_content(delta)

        assert result["reasoning_text"] == "Let me think"
        assert result["content"] == "Let me think"

    def test_process_delta_content_citation(self, handler):
        """Test processing delta content with citation."""
        delta = {StreamingConstants.FIELD_CITATION: {StreamingConstants.FIELD_TITLE: "Source"}}
        result = handler._process_delta_content(delta)

        assert result["citation_title"] == "Source"
        assert result["content"] == ""

    def test_process_delta_content_combined(self, handler):
        """Test processing delta content with multiple content types."""
        delta = {
            StreamingConstants.FIELD_TEXT: "Hello ",
            StreamingConstants.FIELD_REASONING_CONTENT: {StreamingConstants.FIELD_TEXT: "world"},
            StreamingConstants.FIELD_TOOL_USE: {StreamingConstants.FIELD_INPUT: '{"key": "value"}'},
            StreamingConstants.FIELD_CITATION: {StreamingConstants.FIELD_TITLE: "Test"},
        }
        result = handler._process_delta_content(delta)

        assert result["content"] == "Hello world"
        assert result["tool_input"] == '{"key": "value"}'
        assert result["reasoning_text"] == "world"
        assert result["citation_title"] == "Test"

    def test_extract_token_usage_full(self, handler):
        """Test extracting token usage with all fields."""
        usage = {
            StreamingConstants.FIELD_INPUT_TOKENS: 100,
            StreamingConstants.FIELD_OUTPUT_TOKENS: 50,
            StreamingConstants.FIELD_TOTAL_TOKENS: 150,
            StreamingConstants.FIELD_CACHE_READ_INPUT_TOKENS: 10,
            StreamingConstants.FIELD_CACHE_WRITE_INPUT_TOKENS: 5,
        }
        result = handler._extract_token_usage(usage)

        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 50
        assert result["total_tokens"] == 150
        assert result["cache_read_tokens"] == 10
        assert result["cache_write_tokens"] == 5

    def test_extract_token_usage_minimal(self, handler):
        """Test extracting token usage with missing fields."""
        usage = {}
        result = handler._extract_token_usage(usage)

        assert result["input_tokens"] == 0
        assert result["output_tokens"] == 0
        assert result["total_tokens"] == 0
        assert result["cache_read_tokens"] == 0
        assert result["cache_write_tokens"] == 0

    def test_get_event_handler_all_types(self, handler):
        """Test getting event handlers for all event types."""
        event_types = [
            StreamingEventTypes.MESSAGE_START,
            StreamingEventTypes.CONTENT_BLOCK_START,
            StreamingEventTypes.CONTENT_BLOCK_DELTA,
            StreamingEventTypes.CONTENT_BLOCK_STOP,
            StreamingEventTypes.MESSAGE_STOP,
            StreamingEventTypes.METADATA,
            StreamingEventTypes.INTERNAL_SERVER_EXCEPTION,
            StreamingEventTypes.MODEL_STREAM_ERROR_EXCEPTION,
            StreamingEventTypes.VALIDATION_EXCEPTION,
            StreamingEventTypes.THROTTLING_EXCEPTION,
            StreamingEventTypes.SERVICE_UNAVAILABLE_EXCEPTION,
        ]

        for event_type in event_types:
            handler_method = handler.get_event_handler(event_type)
            assert callable(handler_method)

    def test_get_event_handler_invalid_type(self, handler):
        """Test getting event handler for invalid event type."""
        with pytest.raises(ValueError) as exc_info:
            handler.get_event_handler("invalid_type")

        assert "Unsupported event type: invalid_type" in str(exc_info.value)

    def test_get_event_handler_execute(self, handler, sample_message_start_event):
        """Test executing event handler returned by get_event_handler."""
        handler_method = handler.get_event_handler(StreamingEventTypes.MESSAGE_START)
        result = handler_method(sample_message_start_event)

        assert result[StreamingConstants.FIELD_ROLE] == "assistant"
        assert result["event_type"] == StreamingEventTypes.MESSAGE_START

    def test_error_handlers_lambda_execution(self, handler, sample_error_event):
        """Test that lambda error handlers work correctly."""
        error_types = [
            StreamingEventTypes.INTERNAL_SERVER_EXCEPTION,
            StreamingEventTypes.MODEL_STREAM_ERROR_EXCEPTION,
            StreamingEventTypes.VALIDATION_EXCEPTION,
            StreamingEventTypes.THROTTLING_EXCEPTION,
            StreamingEventTypes.SERVICE_UNAVAILABLE_EXCEPTION,
        ]

        for error_type in error_types:
            handler_method = handler.get_event_handler(error_type)
            result = handler_method(sample_error_event)

            assert result["event_type"] == error_type
            assert result["is_error"] is True
            assert result[StreamingConstants.FIELD_MESSAGE] == "Internal server error"

    def test_process_delta_content_empty_delta(self, handler):
        """Test processing empty delta content."""
        result = handler._process_delta_content({})

        assert result["content"] == ""
        assert "tool_input" not in result
        assert "reasoning_text" not in result
        assert "citation_title" not in result

    def test_handle_content_block_start_without_tool(self, handler):
        """Test handling contentBlockStart event without tool use."""
        event = {
            StreamingConstants.FIELD_START: {"some_field": "value"},
            StreamingConstants.FIELD_CONTENT_BLOCK_INDEX: 1,
        }

        result = handler.handle_content_block_start(event)

        assert result[StreamingConstants.FIELD_START] == {"some_field": "value"}
        assert result[StreamingConstants.FIELD_CONTENT_BLOCK_INDEX] == 1
        assert result["event_type"] == StreamingEventTypes.CONTENT_BLOCK_START
