"""
Constants for streaming functionality in LLM Manager system.
Defines field names, event types, and configuration values for AWS Bedrock streaming.
"""

from enum import Enum

from ..models.stop_reason import StopReasonEnum


class StreamingEventTypes(str, Enum):
    """Enumeration of AWS Bedrock Converse Stream event types."""

    MESSAGE_START = "messageStart"
    CONTENT_BLOCK_START = "contentBlockStart"
    CONTENT_BLOCK_DELTA = "contentBlockDelta"
    CONTENT_BLOCK_STOP = "contentBlockStop"
    MESSAGE_STOP = "messageStop"
    METADATA = "metadata"
    INTERNAL_SERVER_EXCEPTION = "internalServerException"
    MODEL_STREAM_ERROR_EXCEPTION = "modelStreamErrorException"
    VALIDATION_EXCEPTION = "validationException"
    THROTTLING_EXCEPTION = "throttlingException"
    SERVICE_UNAVAILABLE_EXCEPTION = "serviceUnavailableException"


class StreamingConstants:
    """Constants for streaming field names and configuration."""

    # Event Stream Fields
    FIELD_STREAM = "stream"
    FIELD_ROLE = "role"
    FIELD_START = "start"
    FIELD_DELTA = "delta"
    FIELD_CONTENT_BLOCK_INDEX = "contentBlockIndex"
    FIELD_STOP_REASON = "stopReason"
    FIELD_ADDITIONAL_MODEL_RESPONSE_FIELDS = "additionalModelResponseFields"

    # Content Block Fields
    FIELD_TEXT = "text"
    FIELD_TOOL_USE = "toolUse"
    FIELD_TOOL_USE_ID = "toolUseId"
    FIELD_NAME = "name"
    FIELD_INPUT = "input"
    FIELD_REASONING_CONTENT = "reasoningContent"
    FIELD_CITATION = "citation"
    FIELD_TITLE = "title"
    FIELD_SOURCE_CONTENT = "sourceContent"
    FIELD_LOCATION = "location"
    FIELD_REDACTED_CONTENT = "redactedContent"
    FIELD_SIGNATURE = "signature"

    # Metadata Fields
    FIELD_USAGE = "usage"
    FIELD_INPUT_TOKENS = "inputTokens"
    FIELD_OUTPUT_TOKENS = "outputTokens"
    FIELD_TOTAL_TOKENS = "totalTokens"
    FIELD_CACHE_READ_INPUT_TOKENS = "cacheReadInputTokens"
    FIELD_CACHE_WRITE_INPUT_TOKENS = "cacheWriteInputTokens"
    FIELD_METRICS = "metrics"
    FIELD_LATENCY_MS = "latencyMs"
    FIELD_TRACE = "trace"
    FIELD_PERFORMANCE_CONFIG = "performanceConfig"

    # Error Fields
    FIELD_MESSAGE = "message"
    FIELD_ORIGINAL_STATUS_CODE = "originalStatusCode"
    FIELD_ORIGINAL_MESSAGE = "originalMessage"

    # Stop Reasons — the complete Bedrock Converse stopReason set (issue #37), derived
    # from the canonical StopReasonEnum so streaming and core (ConverseAPIFields) stay in
    # lockstep.
    STOP_REASON_END_TURN = StopReasonEnum.END_TURN.value
    STOP_REASON_TOOL_USE = StopReasonEnum.TOOL_USE.value
    STOP_REASON_MAX_TOKENS = StopReasonEnum.MAX_TOKENS.value
    STOP_REASON_STOP_SEQUENCE = StopReasonEnum.STOP_SEQUENCE.value
    STOP_REASON_GUARDRAIL_INTERVENED = StopReasonEnum.GUARDRAIL_INTERVENED.value
    STOP_REASON_CONTENT_FILTERED = StopReasonEnum.CONTENT_FILTERED.value
    STOP_REASON_MALFORMED_MODEL_OUTPUT = StopReasonEnum.MALFORMED_MODEL_OUTPUT.value
    STOP_REASON_MALFORMED_TOOL_USE = StopReasonEnum.MALFORMED_TOOL_USE.value
    STOP_REASON_MODEL_CONTEXT_WINDOW_EXCEEDED = StopReasonEnum.MODEL_CONTEXT_WINDOW_EXCEEDED.value

    # Configuration
    DEFAULT_STREAM_TIMEOUT = 300  # seconds
    DEFAULT_RETRY_ON_STREAM_ERROR = True
    DEFAULT_PRESERVE_PARTIAL_CONTENT = True
    MAX_STREAM_INTERRUPTION_RETRIES = 3
    STREAM_CHUNK_BUFFER_SIZE = 1024


class StreamingLogMessages:
    """Log message templates for streaming operations."""

    STREAM_STARTED = "Started streaming request for model '{model}' in region '{region}'"
    STREAM_EVENT_RECEIVED = "Received streaming event: {event_type}"
    STREAM_CONTENT_CHUNK = "Received content chunk: {chunk_size} characters"
    STREAM_COMPLETED = "Streaming completed successfully for model '{model}' in region '{region}'"
    STREAM_INTERRUPTED = "Stream interrupted for model '{model}' in region '{region}': {error}"
    STREAM_RETRY_ATTEMPT = "Attempting stream retry {attempt}/{max_attempts} for model '{model}'"
    STREAM_RECOVERY_CONTEXT = (
        "Building recovery context with {partial_length} characters of partial content"
    )
    STREAM_ERROR = "Stream error in model '{model}', region '{region}': {error}"


class StreamingErrorMessages:
    """Error message templates for streaming operations."""

    STREAM_PROCESSING_FAILED = "Failed to process streaming event: {event_type}"
    INVALID_STREAM_EVENT = "Invalid streaming event format: {event}"
    STREAM_INTERRUPTED_ERROR = "Stream was interrupted unexpectedly"
    NO_STREAM_DATA = "No streaming data received from response"
    STREAM_RETRY_EXHAUSTED = "All streaming retry attempts failed for models: {models}"
    MALFORMED_EVENT_DATA = "Malformed event data in streaming response: {data}"
