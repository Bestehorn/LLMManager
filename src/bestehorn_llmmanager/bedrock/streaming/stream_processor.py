"""
Stream processor for AWS Bedrock Converse Stream API.
Handles EventStream processing and integration with StreamingResponse.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional

from ..models.bedrock_response import StreamingResponse
from ..models.llm_manager_structures import RequestAttempt
from .event_handlers import StreamEventHandler
from .streaming_constants import (
    StreamingConstants,
    StreamingErrorMessages,
    StreamingEventTypes,
    StreamingLogMessages,
)


class StreamProcessor:
    """
    Processes AWS Bedrock EventStream and converts to StreamingResponse.

    Provides real-time event processing with proper error handling,
    content accumulation, and integration with existing response patterns.
    """

    def __init__(self) -> None:
        """Initialize the stream processor."""
        self._logger = logging.getLogger(__name__)
        self._event_handler = StreamEventHandler()

    def process_event_stream(
        self,
        event_stream: Any,
        response: StreamingResponse,
        model_used: Optional[str] = None,
        region_used: Optional[str] = None,
        access_method_used: Optional[str] = None,
        attempt: Optional[RequestAttempt] = None,
    ) -> StreamingResponse:
        """
        Process AWS EventStream and populate StreamingResponse.

        Args:
            event_stream: AWS EventStream from converse_stream API
            response: StreamingResponse to populate
            model_used: Model ID that was used
            region_used: Region that was used
            access_method_used: Access method that was used
            attempt: RequestAttempt information

        Returns:
            Populated StreamingResponse with streaming data

        Raises:
            Exception: If stream processing fails
        """
        start_time = datetime.now()

        try:
            # Initialize response metadata
            self._initialize_response_metadata(
                response=response,
                model_used=model_used,
                region_used=region_used,
                access_method_used=access_method_used,
                attempt=attempt,
            )

            # Process all events in the stream
            for event in event_stream:
                self._process_single_event(event=event, response=response)

            # Finalize response
            self._finalize_response(response=response, start_time=start_time)

            self._logger.info(
                StreamingLogMessages.STREAM_COMPLETED.format(
                    model=model_used or "unknown", region=region_used or "unknown"
                )
            )

            return response

        except Exception as error:
            self._handle_stream_error(
                error=error, response=response, model_used=model_used, region_used=region_used
            )
            raise

    def create_streaming_iterator(
        self,
        event_stream: Any,
        response: StreamingResponse,
        model_used: Optional[str] = None,
        region_used: Optional[str] = None,
    ) -> Iterator[str]:
        """
        Create an iterator that yields content chunks in real-time.

        Args:
            event_stream: AWS EventStream from converse_stream API
            response: StreamingResponse to populate as we iterate
            model_used: Model ID that was used
            region_used: Region that was used

        Yields:
            Content chunks as they arrive from the stream

        Raises:
            Exception: If stream processing fails
        """
        self._logger.info(
            StreamingLogMessages.STREAM_STARTED.format(
                model=model_used or "unknown", region=region_used or "unknown"
            )
        )

        try:
            for event in event_stream:
                processed_event = self._process_single_event(event=event, response=response)

                # Yield content if available
                content = processed_event.get("content", "")
                if content:
                    self._logger.debug(
                        StreamingLogMessages.STREAM_CONTENT_CHUNK.format(chunk_size=len(content))
                    )
                    yield content

        except Exception as error:
            self._handle_stream_error(
                error=error, response=response, model_used=model_used, region_used=region_used
            )
            raise

    def _process_single_event(
        self, event: Dict[str, Any], response: StreamingResponse
    ) -> Dict[str, Any]:
        """
        Process a single event from the stream.

        Args:
            event: Individual event from EventStream
            response: StreamingResponse to update

        Returns:
            Processed event data

        Raises:
            ValueError: If event format is invalid
        """
        if not isinstance(event, dict):
            raise ValueError(StreamingErrorMessages.INVALID_STREAM_EVENT.format(event=event))

        # Determine event type
        event_type = self._determine_event_type(event=event)

        self._logger.debug(StreamingLogMessages.STREAM_EVENT_RECEIVED.format(event_type=event_type))

        # Get appropriate handler and process event
        handler = self._event_handler.get_event_handler(event_type=event_type)
        processed_event: Dict[str, Any] = handler(event[event_type.value])

        # Update response based on event type
        self._update_response_from_event(
            event_type=event_type, processed_event=processed_event, response=response
        )

        return processed_event

    def _determine_event_type(self, event: Dict[str, Any]) -> StreamingEventTypes:
        """
        Determine the type of streaming event.

        Args:
            event: Event dictionary from EventStream

        Returns:
            StreamingEventTypes enum value

        Raises:
            ValueError: If event type cannot be determined
        """
        # Check for each possible event type
        for event_type in StreamingEventTypes:
            if event_type.value in event:
                return event_type

        # No recognized event type found
        available_keys = list(event.keys())
        raise ValueError(
            f"Unknown event type. Available keys: {available_keys}. "
            f"Expected one of: {[e.value for e in StreamingEventTypes]}"
        )

    def _update_response_from_event(
        self,
        event_type: StreamingEventTypes,
        processed_event: Dict[str, Any],
        response: StreamingResponse,
    ) -> None:
        """
        Update StreamingResponse based on processed event.

        Args:
            event_type: Type of the event
            processed_event: Processed event data
            response: StreamingResponse to update
        """
        if event_type == StreamingEventTypes.MESSAGE_START:
            # Initialize message tracking
            response.current_message_role = processed_event.get(StreamingConstants.FIELD_ROLE)

        elif event_type == StreamingEventTypes.CONTENT_BLOCK_DELTA:
            # Add content chunk
            content = processed_event.get("content", "")
            if content:
                response.add_content_part(content=content)

        elif event_type == StreamingEventTypes.MESSAGE_STOP:
            # Store stop reason and additional fields
            response.stop_reason = processed_event.get(StreamingConstants.FIELD_STOP_REASON)
            response.additional_model_response_fields = processed_event.get(
                StreamingConstants.FIELD_ADDITIONAL_MODEL_RESPONSE_FIELDS
            )

        elif event_type == StreamingEventTypes.METADATA:
            # Store metadata information
            response.usage_info = processed_event.get(StreamingConstants.FIELD_USAGE)
            response.metrics_info = processed_event.get(StreamingConstants.FIELD_METRICS)
            response.trace_info = processed_event.get(StreamingConstants.FIELD_TRACE)
            response.api_latency_ms = processed_event.get("latency_ms")

        elif event_type in [
            StreamingEventTypes.INTERNAL_SERVER_EXCEPTION,
            StreamingEventTypes.MODEL_STREAM_ERROR_EXCEPTION,
            StreamingEventTypes.VALIDATION_EXCEPTION,
            StreamingEventTypes.THROTTLING_EXCEPTION,
            StreamingEventTypes.SERVICE_UNAVAILABLE_EXCEPTION,
        ]:
            # Handle error events
            error_message = processed_event.get(StreamingConstants.FIELD_MESSAGE, "Unknown error")
            error = Exception(f"{event_type.value}: {error_message}")
            response.add_stream_error(error=error)

    def _initialize_response_metadata(
        self,
        response: StreamingResponse,
        model_used: Optional[str],
        region_used: Optional[str],
        access_method_used: Optional[str],
        attempt: Optional[RequestAttempt],
    ) -> None:
        """
        Initialize response metadata.

        Args:
            response: StreamingResponse to initialize
            model_used: Model ID that was used
            region_used: Region that was used
            access_method_used: Access method that was used
            attempt: RequestAttempt information
        """
        response.model_used = model_used
        response.region_used = region_used
        response.access_method_used = access_method_used

        if attempt:
            response.request_attempt = attempt

    def _finalize_response(self, response: StreamingResponse, start_time: datetime) -> None:
        """
        Finalize response with calculated metrics.

        Args:
            response: StreamingResponse to finalize
            start_time: When processing started
        """
        # Calculate total duration
        end_time = datetime.now()
        total_duration_ms = (end_time - start_time).total_seconds() * 1000
        response.total_duration_ms = total_duration_ms

        # Mark as successful if no errors
        if not response.get_stream_errors():
            response.success = True

    def _handle_stream_error(
        self,
        error: Exception,
        response: StreamingResponse,
        model_used: Optional[str],
        region_used: Optional[str],
    ) -> None:
        """
        Handle stream processing error.

        Args:
            error: The error that occurred
            response: StreamingResponse to update
            model_used: Model ID that was used
            region_used: Region that was used
        """
        self._logger.error(
            StreamingLogMessages.STREAM_ERROR.format(
                model=model_used or "unknown", region=region_used or "unknown", error=str(error)
            )
        )

        # Add error to response
        response.add_stream_error(error=error)
        response.success = False

    def extract_partial_content(self, response: StreamingResponse) -> str:
        """
        Extract partial content from a StreamingResponse for recovery.

        Args:
            response: StreamingResponse with partial content

        Returns:
            Accumulated partial content
        """
        return response.get_full_content()

    def build_recovery_context(
        self,
        original_messages: List[Dict[str, Any]],
        partial_content: str,
        failure_context: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Build recovery context for stream restart.

        Args:
            original_messages: Original conversation messages
            partial_content: Partial content received before failure
            failure_context: Optional context about the failure

        Returns:
            Enhanced messages for stream restart
        """
        if not partial_content:
            return original_messages

        recovery_messages = original_messages.copy()

        # Add assistant message with partial content
        assistant_message = {"role": "assistant", "content": [{"text": partial_content}]}
        recovery_messages.append(assistant_message)

        # Add user message requesting continuation
        continuation_text = "Please continue from where you left off."
        if failure_context:
            continuation_text += f" (Context: {failure_context})"

        continuation_message = {"role": "user", "content": [{"text": continuation_text}]}
        recovery_messages.append(continuation_message)

        self._logger.debug(
            StreamingLogMessages.STREAM_RECOVERY_CONTEXT.format(partial_length=len(partial_content))
        )

        return recovery_messages
