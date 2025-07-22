"""
RetryingStreamIterator for LLM Manager streaming system.
Provides mid-stream error recovery by switching between multiple EventStreams.
"""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..models.access_method import ModelAccessInfo
from .streaming_constants import (
    StreamingConstants,
    StreamingErrorMessages,
    StreamingLogMessages,
)


class MidStreamException:
    """
    Represents an exception that occurred during streaming and was handled.

    Attributes:
        error: The original exception that occurred
        position: Character position where the error occurred
        model: Model ID where the error occurred
        region: Region where the error occurred
        timestamp: When the error occurred
        recovered: Whether the error was successfully recovered from
    """

    def __init__(
        self, error: Exception, position: int, model: str, region: str, recovered: bool = False
    ) -> None:
        """
        Initialize mid-stream exception tracking.

        Args:
            error: The original exception
            position: Character position where error occurred
            model: Model ID where error occurred
            region: Region where error occurred
            recovered: Whether error was successfully recovered
        """
        self.error = error
        self.position = position
        self.model = model
        self.region = region
        self.timestamp = datetime.now()
        self.recovered = recovered

    def __repr__(self) -> str:
        """Return string representation of the mid-stream exception."""
        status = "recovered" if self.recovered else "failed"
        return (
            f"MidStreamException({type(self.error).__name__} at pos={self.position}, "
            f"model={self.model}, region={self.region}, {status})"
        )


class RetryingStreamIterator:
    """
    Iterator that provides mid-stream error recovery for streaming responses.

    This class manages multiple EventStreams and switches between them when
    mid-stream errors occur, providing seamless recovery with partial content
    preservation.
    """

    def __init__(
        self,
        retry_manager: Any,  # StreamingRetryManager - avoid circular import
        retry_targets: List[Tuple[str, str, ModelAccessInfo]],
        operation: Callable[..., Any],
        operation_args: Dict[str, Any],
        disabled_features: Optional[List[str]] = None,
    ) -> None:
        """
        Initialize the retrying stream iterator.

        Args:
            retry_manager: StreamingRetryManager instance for retry logic
            retry_targets: List of (model, region, access_info) combinations
            operation: Function to execute streaming operations
            operation_args: Base arguments for streaming operations
            disabled_features: List of features to disable for compatibility
        """
        self._retry_manager = retry_manager
        self._retry_targets = retry_targets
        self._operation = operation
        self._operation_args = operation_args
        self._disabled_features = disabled_features or []

        # State tracking
        self._current_stream_iterator: Optional[Any] = None
        self._current_target_index = 0
        self._partial_content = ""
        self._mid_stream_exceptions: List[MidStreamException] = []
        self._stream_completed = False
        self._logger = logging.getLogger(__name__)

        # Timing tracking
        self._start_time = datetime.now()
        self._first_content_time: Optional[datetime] = None
        self._last_content_time: Optional[datetime] = None

        # Current stream metadata
        self._current_model: Optional[str] = None
        self._current_region: Optional[str] = None
        self._current_access_info: Optional[ModelAccessInfo] = None

    def __iter__(self) -> "RetryingStreamIterator":
        """Return self as iterator."""
        return self

    def __next__(self) -> Dict[str, Any]:
        """
        Get the next streaming event with mid-stream error recovery.

        Returns:
            Next streaming event dictionary

        Raises:
            StopIteration: When streaming completes or all retries exhausted
        """
        if self._stream_completed:
            raise StopIteration

        while self._current_target_index < len(self._retry_targets):
            try:
                # Ensure we have an active stream
                if not self._current_stream_iterator:
                    self._start_current_stream()

                # Type check for current stream iterator
                if self._current_stream_iterator is None:
                    raise RuntimeError("Failed to initialize stream iterator")

                # Get next event from current stream
                event: Dict[str, Any] = next(self._current_stream_iterator)

                # Track content for recovery context
                self._track_content_from_event(event=event)

                return event

            except StopIteration:
                # Current stream ended normally
                self._stream_completed = True
                raise

            except Exception as error:
                # Mid-stream error occurred!
                self._handle_mid_stream_error(error=error)

                # Check if we should retry with next target
                if self._should_retry_with_next_target(error=error):
                    if self._switch_to_next_target():
                        continue  # Try next stream

                # No more targets or non-retryable error
                self._stream_completed = True
                raise StopIteration

        # No more retry targets available
        self._stream_completed = True
        self._logger.warning("All streaming retry targets exhausted")
        raise StopIteration

    def _start_current_stream(self) -> None:
        """
        Start streaming with the current retry target.

        Raises:
            Exception: If stream setup fails
        """
        if self._current_target_index >= len(self._retry_targets):
            raise RuntimeError("No more retry targets available")

        model, region, access_info = self._retry_targets[self._current_target_index]
        self._current_model = model
        self._current_region = region
        self._current_access_info = access_info

        self._logger.info(StreamingLogMessages.STREAM_STARTED.format(model=model, region=region))

        # Prepare operation arguments with recovery context
        prepared_args = self._prepare_streaming_args(
            model=model, access_info=access_info, partial_content=self._partial_content
        )

        # Execute streaming operation
        aws_response = self._operation(region=region, **prepared_args)

        # Extract and set up EventStream
        event_stream = aws_response.get(StreamingConstants.FIELD_STREAM)
        if not event_stream:
            raise ValueError(StreamingErrorMessages.NO_STREAM_DATA)

        self._current_stream_iterator = iter(event_stream)

        self._logger.debug(f"Started streaming with {model} in {region}")

    def _prepare_streaming_args(
        self, model: str, access_info: ModelAccessInfo, partial_content: str
    ) -> Dict[str, Any]:
        """
        Prepare streaming operation arguments with recovery context.

        Args:
            model: Model name
            access_info: Access information for the model
            partial_content: Partial content for recovery

        Returns:
            Prepared operation arguments
        """
        # Prepare operation arguments using retry manager's logic
        current_args = self._operation_args.copy()

        # Set model ID based on access method
        if access_info.access_method.value in ["direct", "both"]:
            current_args["model_id"] = access_info.model_id
        elif access_info.access_method.value == "cris_only":
            current_args["model_id"] = access_info.inference_profile_id

        # Add recovery context if we have partial content
        if partial_content:
            # Build recovery context by modifying the last user message
            original_messages = current_args.get("messages", [])
            if original_messages:
                # Add context about partial response to the last user message
                recovery_messages = original_messages.copy()
                last_message = recovery_messages[-1]
                if last_message.get("role") == "user":
                    # Add a note about continuing from where we left off
                    last_content = last_message.get("content", [])
                    if last_content and isinstance(last_content, list):
                        # Add recovery context to the message
                        recovery_text = f" [Continuing response that was interrupted. Partial content received: {len(partial_content)} characters]"
                        # Find the last text block and append the recovery context
                        for block in reversed(last_content):
                            if isinstance(block, dict) and "text" in block:
                                block["text"] += recovery_text
                                break

                current_args["messages"] = recovery_messages

        return current_args

    def _track_content_from_event(self, event: Dict[str, Any]) -> None:
        """
        Track content from streaming events for recovery context.

        Args:
            event: Streaming event to analyze
        """
        # Import here to avoid circular imports
        from .streaming_constants import StreamingEventTypes

        # Check if this is a content delta event
        for event_type in StreamingEventTypes:
            if event_type.value in event:
                if event_type == StreamingEventTypes.CONTENT_BLOCK_DELTA:
                    delta_data = event[event_type.value]
                    if StreamingConstants.FIELD_DELTA in delta_data:
                        delta = delta_data[StreamingConstants.FIELD_DELTA]
                        if StreamingConstants.FIELD_TEXT in delta:
                            content = delta[StreamingConstants.FIELD_TEXT]
                            self._partial_content += content

                            # Track timing
                            current_time = datetime.now()
                            if not self._first_content_time:
                                self._first_content_time = current_time
                            self._last_content_time = current_time
                break

    def _handle_mid_stream_error(self, error: Exception) -> None:
        """
        Handle a mid-stream error by recording it for tracking.

        Args:
            error: Exception that occurred during streaming
        """
        mid_stream_exception = MidStreamException(
            error=error,
            position=len(self._partial_content),
            model=self._current_model or "unknown",
            region=self._current_region or "unknown",
            recovered=False,  # Will be updated if recovery succeeds
        )

        self._mid_stream_exceptions.append(mid_stream_exception)

        self._logger.warning(
            StreamingLogMessages.STREAM_INTERRUPTED.format(
                model=self._current_model or "unknown",
                region=self._current_region or "unknown",
                error=str(error),
            )
        )

    def _should_retry_with_next_target(self, error: Exception) -> bool:
        """
        Determine if we should retry with the next target for this error.

        Args:
            error: The error to evaluate

        Returns:
            True if we should try the next target
        """
        # Use retry manager's logic for determining retryable errors
        return bool(
            self._retry_manager.is_streaming_retryable_error(
                error=error, attempt_count=self._current_target_index + 1
            )
        )

    def _switch_to_next_target(self) -> bool:
        """
        Switch to the next retry target.

        Returns:
            True if successfully switched, False if no more targets
        """
        # Mark the current exception as recovered if we're switching
        if self._mid_stream_exceptions:
            self._mid_stream_exceptions[-1].recovered = True

        # Reset current stream state
        self._current_stream_iterator = None
        self._current_target_index += 1

        # Check if we have more targets
        if self._current_target_index < len(self._retry_targets):
            next_model, next_region, _ = self._retry_targets[self._current_target_index]

            self._logger.info(
                StreamingLogMessages.STREAM_RETRY_ATTEMPT.format(
                    attempt=self._current_target_index + 1,
                    max_attempts=len(self._retry_targets),
                    model=next_model,
                )
            )

            if self._partial_content:
                self._logger.debug(
                    StreamingLogMessages.STREAM_RECOVERY_CONTEXT.format(
                        partial_length=len(self._partial_content)
                    )
                )

            return True

        return False

    @property
    def mid_stream_exceptions(self) -> List[MidStreamException]:
        """Get list of mid-stream exceptions that occurred."""
        return self._mid_stream_exceptions.copy()

    @property
    def partial_content(self) -> str:
        """Get partial content accumulated so far."""
        return self._partial_content

    @property
    def current_model(self) -> Optional[str]:
        """Get currently active model."""
        return self._current_model

    @property
    def current_region(self) -> Optional[str]:
        """Get currently active region."""
        return self._current_region

    @property
    def target_switches(self) -> int:
        """Get number of target switches that occurred."""
        return len([exc for exc in self._mid_stream_exceptions if exc.recovered])

    def get_timing_metrics(self) -> Dict[str, Optional[float]]:
        """
        Get timing metrics for the streaming session.

        Returns:
            Dictionary with timing information
        """
        metrics: Dict[str, Optional[float]] = {
            "total_duration_ms": None,
            "time_to_first_content_ms": None,
            "time_to_last_content_ms": None,
            "content_generation_duration_ms": None,
        }

        current_time = datetime.now()

        # Total duration
        metrics["total_duration_ms"] = (current_time - self._start_time).total_seconds() * 1000

        # Time to first content
        if self._first_content_time:
            metrics["time_to_first_content_ms"] = (
                self._first_content_time - self._start_time
            ).total_seconds() * 1000

        # Time to last content
        if self._last_content_time:
            metrics["time_to_last_content_ms"] = (
                self._last_content_time - self._start_time
            ).total_seconds() * 1000

        # Content generation duration
        if self._first_content_time and self._last_content_time:
            metrics["content_generation_duration_ms"] = (
                self._last_content_time - self._first_content_time
            ).total_seconds() * 1000

        return metrics

    def __repr__(self) -> str:
        """Return string representation of the iterator."""
        return (
            f"RetryingStreamIterator(targets={len(self._retry_targets)}, "
            f"current={self._current_target_index}, "
            f"exceptions={len(self._mid_stream_exceptions)}, "
            f"content_length={len(self._partial_content)})"
        )
