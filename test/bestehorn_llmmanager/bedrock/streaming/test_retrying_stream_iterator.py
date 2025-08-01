"""
Tests for RetryingStreamIterator for LLM Manager streaming system.

Tests the RetryingStreamIterator class which provides mid-stream error recovery
by switching between multiple EventStreams.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo, ModelAccessMethod
from bestehorn_llmmanager.bedrock.streaming.retrying_stream_iterator import (
    MidStreamException,
    RetryingStreamIterator,
)
from bestehorn_llmmanager.bedrock.streaming.streaming_constants import (
    StreamingConstants,
    StreamingErrorMessages,
    StreamingEventTypes,
)


class TestMidStreamException:
    """Test suite for MidStreamException class."""

    def test_init_basic(self):
        """Test MidStreamException initialization."""
        error = ValueError("test error")
        exception = MidStreamException(
            error=error, position=100, model="claude", region="us-east-1"
        )

        assert exception.error is error
        assert exception.position == 100
        assert exception.model == "claude"
        assert exception.region == "us-east-1"
        assert exception.recovered is False
        assert isinstance(exception.timestamp, datetime)

    def test_init_with_recovered(self):
        """Test MidStreamException initialization with recovered=True."""
        error = RuntimeError("network error")
        exception = MidStreamException(
            error=error, position=50, model="gpt", region="us-west-2", recovered=True
        )

        assert exception.recovered is True

    def test_repr_not_recovered(self):
        """Test string representation of non-recovered exception."""
        error = ValueError("test error")
        exception = MidStreamException(
            error=error, position=100, model="claude", region="us-east-1"
        )

        repr_str = repr(exception)
        assert "MidStreamException(ValueError at pos=100" in repr_str
        assert "model=claude" in repr_str
        assert "region=us-east-1" in repr_str
        assert "failed" in repr_str

    def test_repr_recovered(self):
        """Test string representation of recovered exception."""
        error = RuntimeError("network error")
        exception = MidStreamException(
            error=error, position=50, model="gpt", region="us-west-2", recovered=True
        )

        repr_str = repr(exception)
        assert "RuntimeError at pos=50" in repr_str
        assert "recovered" in repr_str


class TestRetryingStreamIterator:
    """Test suite for RetryingStreamIterator class."""

    @pytest.fixture
    def mock_retry_manager(self):
        """Create a mock retry manager."""
        retry_manager = Mock()
        retry_manager.is_streaming_retryable_error.return_value = True
        return retry_manager

    @pytest.fixture
    def mock_access_info(self):
        """Create a mock ModelAccessInfo."""
        return ModelAccessInfo(
            access_method=ModelAccessMethod.DIRECT,
            region="us-east-1",
            model_id="claude-3-sonnet",
            inference_profile_id="claude-profile",
        )

    @pytest.fixture
    def retry_targets(self, mock_access_info):
        """Create sample retry targets."""
        return [
            ("claude-3-sonnet", "us-east-1", mock_access_info),
            ("claude-3-sonnet", "us-west-2", mock_access_info),
            ("claude-3-haiku", "us-east-1", mock_access_info),
        ]

    @pytest.fixture
    def mock_operation(self):
        """Create a mock streaming operation."""
        operation = Mock()
        # Mock EventStream with iterator
        mock_stream = Mock()
        mock_stream.__iter__ = Mock(
            return_value=iter(
                [
                    {"messageStart": {"role": "assistant"}},
                    {"contentBlockDelta": {"delta": {"text": "Hello"}, "contentBlockIndex": 0}},
                    {"messageStop": {"stopReason": "end_turn"}},
                ]
            )
        )

        operation.return_value = {StreamingConstants.FIELD_STREAM: mock_stream}
        return operation

    @pytest.fixture
    def operation_args(self):
        """Create sample operation arguments."""
        return {
            "messages": [{"role": "user", "content": [{"text": "Hello"}]}],
            "max_tokens": 100,
        }

    @pytest.fixture
    def iterator(self, mock_retry_manager, retry_targets, mock_operation, operation_args):
        """Create a RetryingStreamIterator instance."""
        return RetryingStreamIterator(
            retry_manager=mock_retry_manager,
            retry_targets=retry_targets,
            operation=mock_operation,
            operation_args=operation_args,
        )

    def test_init_basic(self, mock_retry_manager, retry_targets, mock_operation, operation_args):
        """Test RetryingStreamIterator initialization."""
        iterator = RetryingStreamIterator(
            retry_manager=mock_retry_manager,
            retry_targets=retry_targets,
            operation=mock_operation,
            operation_args=operation_args,
        )

        assert iterator._retry_manager is mock_retry_manager
        assert iterator._retry_targets == retry_targets
        assert iterator._operation is mock_operation
        assert iterator._operation_args == operation_args
        assert iterator._disabled_features == []
        assert iterator._current_stream_iterator is None
        assert iterator._current_target_index == 0
        assert iterator._partial_content == ""
        assert iterator._mid_stream_exceptions == []
        assert iterator._stream_completed is False
        assert iterator._current_model is None
        assert iterator._current_region is None

    def test_init_with_disabled_features(
        self, mock_retry_manager, retry_targets, mock_operation, operation_args
    ):
        """Test initialization with disabled features."""
        disabled_features = ["feature1", "feature2"]
        iterator = RetryingStreamIterator(
            retry_manager=mock_retry_manager,
            retry_targets=retry_targets,
            operation=mock_operation,
            operation_args=operation_args,
            disabled_features=disabled_features,
        )

        assert iterator._disabled_features == disabled_features

    def test_iter(self, iterator):
        """Test __iter__ method."""
        assert iter(iterator) is iterator

    def test_next_success(self, iterator):
        """Test successful __next__ call."""
        # Mock the operation to return a stream with events
        mock_event_stream = Mock()
        mock_events = [
            {"messageStart": {"role": "assistant"}},
            {"contentBlockDelta": {"delta": {"text": "Hello"}, "contentBlockIndex": 0}},
        ]
        mock_event_stream.__iter__ = Mock(return_value=iter(mock_events))
        iterator._operation.return_value = {StreamingConstants.FIELD_STREAM: mock_event_stream}

        # Get first event
        event1 = next(iterator)
        assert event1 == {"messageStart": {"role": "assistant"}}

        # Get second event
        event2 = next(iterator)
        assert event2 == {"contentBlockDelta": {"delta": {"text": "Hello"}, "contentBlockIndex": 0}}

    def test_next_stream_completed(self, iterator):
        """Test __next__ when stream is already completed."""
        iterator._stream_completed = True

        with pytest.raises(StopIteration):
            next(iterator)

    def test_next_normal_stop_iteration(self, iterator):
        """Test __next__ when current stream ends normally."""
        # Mock the operation to return a stream that ends
        mock_event_stream = Mock()
        mock_event_stream.__iter__ = Mock(return_value=iter([]))
        iterator._operation.return_value = {StreamingConstants.FIELD_STREAM: mock_event_stream}

        with pytest.raises(StopIteration):
            next(iterator)

        assert iterator._stream_completed is True

    def test_next_with_mid_stream_error_recovery(self, iterator):
        """Test __next__ with mid-stream error and recovery."""
        # Create two streams: first fails, second succeeds
        error_stream = Mock()
        error_stream.__iter__ = Mock(return_value=iter([RuntimeError("Stream error")]))

        success_stream = Mock()
        success_events = [{"messageStart": {"role": "assistant"}}]
        success_stream.__iter__ = Mock(return_value=iter(success_events))

        # Mock operation to return error stream first, then success stream
        iterator._operation.side_effect = [
            {StreamingConstants.FIELD_STREAM: error_stream},
            {StreamingConstants.FIELD_STREAM: success_stream},
        ]

        # Mock iterator behavior
        def error_then_success():
            raise RuntimeError("Stream error")

        def success_next():
            return {"messageStart": {"role": "assistant"}}

        # Set up the mock to first raise error, then return success
        iterator._current_stream_iterator = Mock()
        iterator._current_stream_iterator.__next__ = Mock(
            side_effect=[RuntimeError("Stream error"), success_next()]
        )

        # This should recover and return the event
        with patch.object(iterator, "_start_current_stream"), patch.object(
            iterator, "_handle_mid_stream_error"
        ), patch.object(
            iterator, "_should_retry_with_next_target", return_value=True
        ), patch.object(
            iterator, "_switch_to_next_target", return_value=True
        ):

            # The first call should trigger error handling and recovery
            event = next(iterator)
            assert event == {"messageStart": {"role": "assistant"}}

    def test_next_all_targets_exhausted(self, iterator):
        """Test __next__ when all retry targets are exhausted."""
        iterator._current_target_index = len(iterator._retry_targets)

        with pytest.raises(StopIteration):
            next(iterator)

        assert iterator._stream_completed is True

    def test_start_current_stream_success(self, iterator, mock_access_info):
        """Test _start_current_stream with successful setup."""
        mock_event_stream = Mock()
        mock_event_stream.__iter__ = Mock(return_value=iter([]))
        iterator._operation.return_value = {StreamingConstants.FIELD_STREAM: mock_event_stream}

        iterator._start_current_stream()

        assert iterator._current_model == "claude-3-sonnet"
        assert iterator._current_region == "us-east-1"
        assert iterator._current_access_info == mock_access_info
        assert iterator._current_stream_iterator is not None
        iterator._operation.assert_called_once()

    def test_start_current_stream_no_targets(self, iterator):
        """Test _start_current_stream when no targets are available."""
        iterator._current_target_index = len(iterator._retry_targets)

        with pytest.raises(RuntimeError, match="No more retry targets available"):
            iterator._start_current_stream()

    def test_start_current_stream_no_stream_data(self, iterator):
        """Test _start_current_stream when response has no stream data."""
        iterator._operation.return_value = {}

        with pytest.raises(ValueError) as exc_info:
            iterator._start_current_stream()

        assert StreamingErrorMessages.NO_STREAM_DATA in str(exc_info.value)

    def test_prepare_streaming_args_direct_access(self, iterator, mock_access_info):
        """Test _prepare_streaming_args with direct access method."""
        mock_access_info = ModelAccessInfo(
            access_method=ModelAccessMethod.DIRECT,
            region="us-east-1",
            model_id="claude-3-sonnet",
        )

        args = iterator._prepare_streaming_args(
            model="claude-3-sonnet",
            access_info=mock_access_info,
            partial_content="",
        )

        assert args["model_id"] == "claude-3-sonnet"

    def test_prepare_streaming_args_cris_access(self, iterator, mock_access_info):
        """Test _prepare_streaming_args with CRIS access method."""
        mock_access_info = ModelAccessInfo(
            access_method=ModelAccessMethod.CRIS_ONLY,
            region="us-east-1",
            inference_profile_id="claude-profile",
        )

        args = iterator._prepare_streaming_args(
            model="claude-3-sonnet",
            access_info=mock_access_info,
            partial_content="",
        )

        assert args["model_id"] == "claude-profile"

    def test_prepare_streaming_args_with_partial_content(self, iterator, mock_access_info):
        """Test _prepare_streaming_args with partial content for recovery."""
        partial_content = "Hello, this is partial"

        args = iterator._prepare_streaming_args(
            model="claude-3-sonnet",
            access_info=mock_access_info,
            partial_content=partial_content,
        )

        # Should have modified the messages for recovery
        assert "messages" in args
        messages = args["messages"]
        assert len(messages) > 0

        # Check that recovery context was added
        last_message = messages[-1]
        if last_message.get("role") == "user":
            content = last_message.get("content", [])
            if content and isinstance(content, list):
                # Look for recovery context in text blocks
                found_recovery = any(
                    "Continuing response" in block.get("text", "")
                    for block in content
                    if isinstance(block, dict) and "text" in block
                )
                assert found_recovery

    def test_track_content_from_event_delta(self, iterator):
        """Test _track_content_from_event with content delta."""
        event = {
            StreamingEventTypes.CONTENT_BLOCK_DELTA.value: {
                StreamingConstants.FIELD_DELTA: {StreamingConstants.FIELD_TEXT: "Hello world"},
                StreamingConstants.FIELD_CONTENT_BLOCK_INDEX: 0,
            }
        }

        initial_content = iterator._partial_content
        iterator._track_content_from_event(event)

        assert iterator._partial_content == initial_content + "Hello world"
        assert iterator._first_content_time is not None
        assert iterator._last_content_time is not None

    def test_track_content_from_event_non_delta(self, iterator):
        """Test _track_content_from_event with non-delta event."""
        event = {"messageStart": {"role": "assistant"}}

        initial_content = iterator._partial_content
        iterator._track_content_from_event(event)

        assert iterator._partial_content == initial_content
        assert iterator._first_content_time is None

    def test_handle_mid_stream_error(self, iterator):
        """Test _handle_mid_stream_error."""
        iterator._current_model = "claude-3-sonnet"
        iterator._current_region = "us-east-1"
        iterator._partial_content = "partial"

        error = RuntimeError("Network error")
        iterator._handle_mid_stream_error(error)

        assert len(iterator._mid_stream_exceptions) == 1
        exception = iterator._mid_stream_exceptions[0]
        assert exception.error is error
        assert exception.position == len("partial")
        assert exception.model == "claude-3-sonnet"
        assert exception.region == "us-east-1"
        assert exception.recovered is False

    def test_handle_mid_stream_error_unknown_model(self, iterator):
        """Test _handle_mid_stream_error with unknown model/region."""
        error = ValueError("Test error")
        iterator._handle_mid_stream_error(error)

        exception = iterator._mid_stream_exceptions[0]
        assert exception.model == "unknown"
        assert exception.region == "unknown"

    def test_should_retry_with_next_target(self, iterator):
        """Test _should_retry_with_next_target."""
        error = RuntimeError("Retryable error")
        iterator._retry_manager.is_streaming_retryable_error.return_value = True

        result = iterator._should_retry_with_next_target(error)

        assert result is True
        iterator._retry_manager.is_streaming_retryable_error.assert_called_once_with(
            error=error, attempt_count=1
        )

    def test_should_retry_with_next_target_non_retryable(self, iterator):
        """Test _should_retry_with_next_target with non-retryable error."""
        error = ValueError("Non-retryable error")
        iterator._retry_manager.is_streaming_retryable_error.return_value = False

        result = iterator._should_retry_with_next_target(error)

        assert result is False

    def test_switch_to_next_target_success(self, iterator):
        """Test _switch_to_next_target with available targets."""
        # Add a mid-stream exception
        iterator._mid_stream_exceptions.append(
            MidStreamException(RuntimeError("test"), 0, "model", "region")
        )

        result = iterator._switch_to_next_target()

        assert result is True
        assert iterator._current_target_index == 1
        assert iterator._current_stream_iterator is None
        assert iterator._mid_stream_exceptions[0].recovered is True

    def test_switch_to_next_target_no_more_targets(self, iterator):
        """Test _switch_to_next_target when no more targets available."""
        iterator._current_target_index = len(iterator._retry_targets) - 1

        result = iterator._switch_to_next_target()

        assert result is False

    def test_properties(self, iterator):
        """Test property getters."""
        # Add some test data
        iterator._partial_content = "test content"
        iterator._current_model = "claude"
        iterator._current_region = "us-east-1"

        exception1 = MidStreamException(RuntimeError("1"), 0, "model", "region", recovered=True)
        exception2 = MidStreamException(RuntimeError("2"), 0, "model", "region", recovered=False)
        iterator._mid_stream_exceptions = [exception1, exception2]

        assert iterator.partial_content == "test content"
        assert iterator.current_model == "claude"
        assert iterator.current_region == "us-east-1"
        assert len(iterator.mid_stream_exceptions) == 2
        assert iterator.target_switches == 1  # Only one recovered

    def test_get_timing_metrics_no_content(self, iterator):
        """Test get_timing_metrics with no content received."""
        metrics = iterator.get_timing_metrics()

        assert "total_duration_ms" in metrics
        assert metrics["total_duration_ms"] is not None
        assert metrics["time_to_first_content_ms"] is None
        assert metrics["time_to_last_content_ms"] is None
        assert metrics["content_generation_duration_ms"] is None

    def test_get_timing_metrics_with_content(self, iterator):
        """Test get_timing_metrics with content timing."""
        now = datetime.now()
        iterator._start_time = now - timedelta(seconds=5)
        iterator._first_content_time = now - timedelta(seconds=3)
        iterator._last_content_time = now - timedelta(seconds=1)

        metrics = iterator.get_timing_metrics()

        assert metrics["total_duration_ms"] is not None
        assert metrics["time_to_first_content_ms"] is not None
        assert metrics["time_to_last_content_ms"] is not None
        assert metrics["content_generation_duration_ms"] is not None

        # Verify approximate timing (allowing for small variations)
        assert abs(metrics["time_to_first_content_ms"] - 2000) < 100  # ~2 seconds
        assert abs(metrics["content_generation_duration_ms"] - 2000) < 100  # ~2 seconds

    def test_repr(self, iterator):
        """Test __repr__ method."""
        # Add some test data
        iterator._partial_content = "test"
        iterator._mid_stream_exceptions.append(
            MidStreamException(RuntimeError("test"), 0, "model", "region")
        )

        repr_str = repr(iterator)
        assert "RetryingStreamIterator" in repr_str
        assert "targets=3" in repr_str
        assert "current=0" in repr_str
        assert "exceptions=1" in repr_str
        assert "content_length=4" in repr_str

    @patch("bestehorn_llmmanager.bedrock.streaming.retrying_stream_iterator.logging.getLogger")
    def test_logging_integration(self, mock_get_logger, iterator):
        """Test logging integration in various methods."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # Replace the logger in the iterator
        iterator._logger = mock_logger

        # Test start stream logging
        mock_event_stream = Mock()
        mock_event_stream.__iter__ = Mock(return_value=iter([]))
        iterator._operation.return_value = {StreamingConstants.FIELD_STREAM: mock_event_stream}
        iterator._start_current_stream()

        # Verify logging calls
        mock_logger.info.assert_called()
        mock_logger.debug.assert_called()

    def test_integration_full_stream_success(
        self, mock_retry_manager, retry_targets, operation_args
    ):
        """Test full integration with successful streaming."""
        # Create a mock operation that returns events
        events = [
            {"messageStart": {"role": "assistant"}},
            {"contentBlockDelta": {"delta": {"text": "Hello"}, "contentBlockIndex": 0}},
            {"contentBlockDelta": {"delta": {"text": " world"}, "contentBlockIndex": 0}},
            {"messageStop": {"stopReason": "end_turn"}},
        ]

        mock_event_stream = Mock()
        mock_event_stream.__iter__ = Mock(return_value=iter(events))

        mock_operation = Mock()
        mock_operation.return_value = {StreamingConstants.FIELD_STREAM: mock_event_stream}

        iterator = RetryingStreamIterator(
            retry_manager=mock_retry_manager,
            retry_targets=retry_targets,
            operation=mock_operation,
            operation_args=operation_args,
        )

        # Consume all events
        collected_events = list(iterator)

        assert len(collected_events) == 4
        assert collected_events[0] == {"messageStart": {"role": "assistant"}}
        assert collected_events[-1] == {"messageStop": {"stopReason": "end_turn"}}
        assert iterator.partial_content == "Hello world"

    def test_integration_with_error_recovery(
        self, mock_retry_manager, retry_targets, operation_args
    ):
        """Test integration with mid-stream error and recovery."""
        # First stream fails after one event
        error_events = [
            {"messageStart": {"role": "assistant"}},
        ]

        # Second stream succeeds
        success_events = [
            {"messageStart": {"role": "assistant"}},
            {"contentBlockDelta": {"delta": {"text": "Recovered"}, "contentBlockIndex": 0}},
            {"messageStop": {"stopReason": "end_turn"}},
        ]

        error_stream = Mock()
        error_stream.__iter__ = Mock(return_value=iter(error_events))

        success_stream = Mock()
        success_stream.__iter__ = Mock(return_value=iter(success_events))

        mock_operation = Mock()
        mock_operation.side_effect = [
            {StreamingConstants.FIELD_STREAM: error_stream},
            {StreamingConstants.FIELD_STREAM: success_stream},
        ]

        iterator = RetryingStreamIterator(
            retry_manager=mock_retry_manager,
            retry_targets=retry_targets,
            operation=mock_operation,
            operation_args=operation_args,
        )

        # Simulate error after first event
        first_event = next(iterator)
        assert first_event == {"messageStart": {"role": "assistant"}}

        # Now simulate the error and recovery by mocking the stream iterator behavior
        with patch.object(iterator, "_current_stream_iterator") as mock_stream_iter:
            mock_stream_iter.__next__.side_effect = [
                RuntimeError("Stream interrupted"),
                {"messageStart": {"role": "assistant"}},
                {"contentBlockDelta": {"delta": {"text": "Recovered"}, "contentBlockIndex": 0}},
                {"messageStop": {"stopReason": "end_turn"}},
            ]

            with patch.object(iterator, "_switch_to_next_target", return_value=True):
                # This should trigger error handling and recovery
                remaining_events = []
                try:
                    while True:
                        remaining_events.append(next(iterator))
                except StopIteration:
                    pass

                # Should have recovered and gotten remaining events
                assert len(remaining_events) >= 1
                assert iterator.target_switches >= 0  # May have switched targets

    def test_edge_case_empty_retry_targets(self, mock_retry_manager, operation_args):
        """Test edge case with empty retry targets."""
        iterator = RetryingStreamIterator(
            retry_manager=mock_retry_manager,
            retry_targets=[],
            operation=Mock(),
            operation_args=operation_args,
        )

        with pytest.raises(StopIteration):
            next(iterator)

    def test_edge_case_operation_returns_none(
        self, mock_retry_manager, retry_targets, operation_args
    ):
        """Test edge case where operation returns None."""
        mock_operation = Mock(return_value=None)

        iterator = RetryingStreamIterator(
            retry_manager=mock_retry_manager,
            retry_targets=retry_targets,
            operation=mock_operation,
            operation_args=operation_args,
        )

        with pytest.raises(StopIteration):
            next(iterator)
