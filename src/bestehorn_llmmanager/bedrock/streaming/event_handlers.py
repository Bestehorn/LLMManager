"""
Event handlers for AWS Bedrock streaming events.
Provides modular handlers for different streaming event types.
"""

import logging
from typing import Any, Dict

from .streaming_constants import StreamingConstants, StreamingErrorMessages, StreamingEventTypes


class StreamEventHandler:
    """
    Handles individual streaming events from AWS Bedrock Converse Stream API.

    Provides modular event processing with proper error handling and logging.
    """

    def __init__(self) -> None:
        """Initialize the stream event handler."""
        self._logger = logging.getLogger(__name__)

    def handle_message_start(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle messageStart event.

        Args:
            event: The messageStart event data

        Returns:
            Processed event data

        Raises:
            ValueError: If event format is invalid
        """
        if not isinstance(event, dict):
            raise ValueError(StreamingErrorMessages.INVALID_STREAM_EVENT.format(event=event))

        role = event.get(StreamingConstants.FIELD_ROLE)
        if not role:
            raise ValueError(StreamingErrorMessages.MALFORMED_EVENT_DATA.format(data=event))

        self._logger.debug(f"Message started with role: {role}")

        return {
            StreamingConstants.FIELD_ROLE: role,
            "event_type": StreamingEventTypes.MESSAGE_START,
        }

    def handle_content_block_start(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle contentBlockStart event.

        Args:
            event: The contentBlockStart event data

        Returns:
            Processed event data

        Raises:
            ValueError: If event format is invalid
        """
        if not isinstance(event, dict):
            raise ValueError(StreamingErrorMessages.INVALID_STREAM_EVENT.format(event=event))

        start_data = event.get(StreamingConstants.FIELD_START, {})
        content_block_index = event.get(StreamingConstants.FIELD_CONTENT_BLOCK_INDEX, 0)

        # Handle tool use start
        tool_use = start_data.get(StreamingConstants.FIELD_TOOL_USE)
        if tool_use:
            tool_use_id = tool_use.get(StreamingConstants.FIELD_TOOL_USE_ID)
            tool_name = tool_use.get(StreamingConstants.FIELD_NAME)
            self._logger.debug(f"Tool use started: {tool_name} (ID: {tool_use_id})")

        return {
            StreamingConstants.FIELD_START: start_data,
            StreamingConstants.FIELD_CONTENT_BLOCK_INDEX: content_block_index,
            "event_type": StreamingEventTypes.CONTENT_BLOCK_START,
        }

    def handle_content_block_delta(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle contentBlockDelta event.

        Args:
            event: The contentBlockDelta event data

        Returns:
            Processed event data with extracted content

        Raises:
            ValueError: If event format is invalid
        """
        if not isinstance(event, dict):
            raise ValueError(StreamingErrorMessages.INVALID_STREAM_EVENT.format(event=event))

        delta = event.get(StreamingConstants.FIELD_DELTA, {})
        content_block_index = event.get(StreamingConstants.FIELD_CONTENT_BLOCK_INDEX, 0)

        processed_delta = self._process_delta_content(delta=delta)

        return {
            StreamingConstants.FIELD_DELTA: processed_delta,
            StreamingConstants.FIELD_CONTENT_BLOCK_INDEX: content_block_index,
            "event_type": StreamingEventTypes.CONTENT_BLOCK_DELTA,
            "content": processed_delta.get("content", ""),
        }

    def handle_content_block_stop(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle contentBlockStop event.

        Args:
            event: The contentBlockStop event data

        Returns:
            Processed event data

        Raises:
            ValueError: If event format is invalid
        """
        if not isinstance(event, dict):
            raise ValueError(StreamingErrorMessages.INVALID_STREAM_EVENT.format(event=event))

        content_block_index = event.get(StreamingConstants.FIELD_CONTENT_BLOCK_INDEX, 0)

        self._logger.debug(f"Content block {content_block_index} completed")

        return {
            StreamingConstants.FIELD_CONTENT_BLOCK_INDEX: content_block_index,
            "event_type": StreamingEventTypes.CONTENT_BLOCK_STOP,
        }

    def handle_message_stop(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle messageStop event.

        Args:
            event: The messageStop event data

        Returns:
            Processed event data

        Raises:
            ValueError: If event format is invalid
        """
        if not isinstance(event, dict):
            raise ValueError(StreamingErrorMessages.INVALID_STREAM_EVENT.format(event=event))

        stop_reason = event.get(StreamingConstants.FIELD_STOP_REASON)
        additional_fields = event.get(StreamingConstants.FIELD_ADDITIONAL_MODEL_RESPONSE_FIELDS)

        self._logger.debug(f"Message stopped with reason: {stop_reason}")

        return {
            StreamingConstants.FIELD_STOP_REASON: stop_reason,
            StreamingConstants.FIELD_ADDITIONAL_MODEL_RESPONSE_FIELDS: additional_fields,
            "event_type": StreamingEventTypes.MESSAGE_STOP,
        }

    def handle_metadata(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle metadata event.

        Args:
            event: The metadata event data

        Returns:
            Processed metadata

        Raises:
            ValueError: If event format is invalid
        """
        if not isinstance(event, dict):
            raise ValueError(StreamingErrorMessages.INVALID_STREAM_EVENT.format(event=event))

        usage = event.get(StreamingConstants.FIELD_USAGE, {})
        metrics = event.get(StreamingConstants.FIELD_METRICS, {})
        trace = event.get(StreamingConstants.FIELD_TRACE, {})
        performance_config = event.get(StreamingConstants.FIELD_PERFORMANCE_CONFIG, {})

        # Extract token usage
        token_usage = self._extract_token_usage(usage=usage)

        # Extract performance metrics
        latency_ms = metrics.get(StreamingConstants.FIELD_LATENCY_MS)

        self._logger.debug(
            f"Received metadata: {token_usage.get('total_tokens', 0)} tokens, "
            f"{latency_ms} ms latency"
        )

        return {
            StreamingConstants.FIELD_USAGE: token_usage,
            StreamingConstants.FIELD_METRICS: metrics,
            StreamingConstants.FIELD_TRACE: trace,
            StreamingConstants.FIELD_PERFORMANCE_CONFIG: performance_config,
            "event_type": StreamingEventTypes.METADATA,
            "latency_ms": latency_ms,
        }

    def handle_error_event(
        self, event: Dict[str, Any], event_type: StreamingEventTypes
    ) -> Dict[str, Any]:
        """
        Handle error events (exceptions).

        Args:
            event: The error event data
            event_type: The type of error event

        Returns:
            Processed error data

        Raises:
            ValueError: If event format is invalid
        """
        if not isinstance(event, dict):
            raise ValueError(StreamingErrorMessages.INVALID_STREAM_EVENT.format(event=event))

        message = event.get(StreamingConstants.FIELD_MESSAGE, "Unknown error")

        error_data = {
            StreamingConstants.FIELD_MESSAGE: message,
            "event_type": event_type,
            "is_error": True,
        }

        # Add specific error fields based on event type
        if event_type == StreamingEventTypes.MODEL_STREAM_ERROR_EXCEPTION:
            error_data[StreamingConstants.FIELD_ORIGINAL_STATUS_CODE] = event.get(
                StreamingConstants.FIELD_ORIGINAL_STATUS_CODE
            )
            error_data[StreamingConstants.FIELD_ORIGINAL_MESSAGE] = event.get(
                StreamingConstants.FIELD_ORIGINAL_MESSAGE
            )

        self._logger.error(f"Streaming error ({event_type}): {message}")

        return error_data

    def _process_delta_content(self, delta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process delta content from contentBlockDelta event.

        Args:
            delta: The delta content data

        Returns:
            Processed delta with extracted content
        """
        processed_delta = delta.copy()
        content_parts = []

        # Extract text content
        text_content = delta.get(StreamingConstants.FIELD_TEXT)
        if text_content:
            content_parts.append(text_content)

        # Extract tool use input
        tool_use = delta.get(StreamingConstants.FIELD_TOOL_USE, {})
        if tool_use and StreamingConstants.FIELD_INPUT in tool_use:
            tool_input = tool_use[StreamingConstants.FIELD_INPUT]
            processed_delta["tool_input"] = tool_input

        # Extract reasoning content
        reasoning = delta.get(StreamingConstants.FIELD_REASONING_CONTENT)
        if reasoning:
            reasoning_text = reasoning.get(StreamingConstants.FIELD_TEXT)
            if reasoning_text:
                content_parts.append(reasoning_text)
                processed_delta["reasoning_text"] = reasoning_text

        # Extract citation content
        citation = delta.get(StreamingConstants.FIELD_CITATION)
        if citation:
            citation_title = citation.get(StreamingConstants.FIELD_TITLE)
            if citation_title:
                processed_delta["citation_title"] = citation_title

        # Combine all content parts
        combined_content = "".join(content_parts)
        processed_delta["content"] = combined_content

        return processed_delta

    def _extract_token_usage(self, usage: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and normalize token usage information.

        Args:
            usage: Raw usage data from metadata

        Returns:
            Normalized token usage data
        """
        return {
            "input_tokens": usage.get(StreamingConstants.FIELD_INPUT_TOKENS, 0),
            "output_tokens": usage.get(StreamingConstants.FIELD_OUTPUT_TOKENS, 0),
            "total_tokens": usage.get(StreamingConstants.FIELD_TOTAL_TOKENS, 0),
            "cache_read_tokens": usage.get(StreamingConstants.FIELD_CACHE_READ_INPUT_TOKENS, 0),
            "cache_write_tokens": usage.get(StreamingConstants.FIELD_CACHE_WRITE_INPUT_TOKENS, 0),
        }

    def get_event_handler(self, event_type: StreamingEventTypes) -> Any:
        """
        Get the appropriate handler method for an event type.

        Args:
            event_type: The streaming event type

        Returns:
            Handler method for the event type

        Raises:
            ValueError: If event type is not supported
        """
        handler_map = {
            StreamingEventTypes.MESSAGE_START: self.handle_message_start,
            StreamingEventTypes.CONTENT_BLOCK_START: self.handle_content_block_start,
            StreamingEventTypes.CONTENT_BLOCK_DELTA: self.handle_content_block_delta,
            StreamingEventTypes.CONTENT_BLOCK_STOP: self.handle_content_block_stop,
            StreamingEventTypes.MESSAGE_STOP: self.handle_message_stop,
            StreamingEventTypes.METADATA: self.handle_metadata,
            StreamingEventTypes.INTERNAL_SERVER_EXCEPTION: lambda e: self.handle_error_event(
                e, StreamingEventTypes.INTERNAL_SERVER_EXCEPTION
            ),
            StreamingEventTypes.MODEL_STREAM_ERROR_EXCEPTION: lambda e: self.handle_error_event(
                e, StreamingEventTypes.MODEL_STREAM_ERROR_EXCEPTION
            ),
            StreamingEventTypes.VALIDATION_EXCEPTION: lambda e: self.handle_error_event(
                e, StreamingEventTypes.VALIDATION_EXCEPTION
            ),
            StreamingEventTypes.THROTTLING_EXCEPTION: lambda e: self.handle_error_event(
                e, StreamingEventTypes.THROTTLING_EXCEPTION
            ),
            StreamingEventTypes.SERVICE_UNAVAILABLE_EXCEPTION: lambda e: self.handle_error_event(
                e, StreamingEventTypes.SERVICE_UNAVAILABLE_EXCEPTION
            ),
        }

        if event_type not in handler_map:
            raise ValueError(f"Unsupported event type: {event_type}")

        return handler_map[event_type]
