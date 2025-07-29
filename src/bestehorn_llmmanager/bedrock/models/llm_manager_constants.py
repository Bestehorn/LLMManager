"""
Constants for LLM Manager system.
Contains string constants for JSON field access and configuration values.
"""

import logging
from typing import Final


class ConverseAPIFields:
    """JSON field constants for AWS Bedrock Converse API requests and responses."""

    # Request fields
    MODEL_ID: Final[str] = "modelId"
    MESSAGES: Final[str] = "messages"
    SYSTEM: Final[str] = "system"
    INFERENCE_CONFIG: Final[str] = "inferenceConfig"
    ADDITIONAL_MODEL_REQUEST_FIELDS: Final[str] = "additionalModelRequestFields"
    ADDITIONAL_MODEL_RESPONSE_FIELD_PATHS: Final[str] = "additionalModelResponseFieldPaths"
    GUARDRAIL_CONFIG: Final[str] = "guardrailConfig"
    TOOL_CONFIG: Final[str] = "toolConfig"
    REQUEST_METADATA: Final[str] = "requestMetadata"
    PROMPT_VARIABLES: Final[str] = "promptVariables"

    # Message fields
    ROLE: Final[str] = "role"
    CONTENT: Final[str] = "content"

    # Content block fields
    TEXT: Final[str] = "text"
    IMAGE: Final[str] = "image"
    DOCUMENT: Final[str] = "document"
    VIDEO: Final[str] = "video"
    CACHE_POINT: Final[str] = "cachePoint"
    GUARD_CONTENT: Final[str] = "guardContent"
    REASONING_CONTENT: Final[str] = "reasoningContent"
    TOOL_USE: Final[str] = "toolUse"
    TOOL_RESULT: Final[str] = "toolResult"

    # Image block fields
    FORMAT: Final[str] = "format"
    SOURCE: Final[str] = "source"
    BYTES: Final[str] = "bytes"
    S3_LOCATION: Final[str] = "s3Location"
    URI: Final[str] = "uri"
    BUCKET_OWNER: Final[str] = "bucketOwner"

    # Document block fields
    NAME: Final[str] = "name"

    # Inference configuration fields
    MAX_TOKENS: Final[str] = "maxTokens"
    STOP_SEQUENCES: Final[str] = "stopSequences"
    TEMPERATURE: Final[str] = "temperature"
    TOP_P: Final[str] = "topP"

    # Response fields
    OUTPUT: Final[str] = "output"
    MESSAGE: Final[str] = "message"
    STOP_REASON: Final[str] = "stopReason"
    USAGE: Final[str] = "usage"
    METRICS: Final[str] = "metrics"
    ADDITIONAL_MODEL_RESPONSE_FIELDS: Final[str] = "additionalModelResponseFields"

    # Usage fields
    INPUT_TOKENS: Final[str] = "inputTokens"
    OUTPUT_TOKENS: Final[str] = "outputTokens"
    TOTAL_TOKENS: Final[str] = "totalTokens"
    CACHE_READ_INPUT_TOKENS_COUNT: Final[str] = "cacheReadInputTokens"
    CACHE_WRITE_INPUT_TOKENS_COUNT: Final[str] = "cacheWriteInputTokens"

    # Metrics fields
    LATENCY_MS: Final[str] = "latencyMs"

    # Streaming fields
    STREAM: Final[str] = "stream"
    MESSAGE_START: Final[str] = "messageStart"
    CONTENT_BLOCK_START: Final[str] = "contentBlockStart"
    CONTENT_BLOCK_DELTA: Final[str] = "contentBlockDelta"
    CONTENT_BLOCK_STOP: Final[str] = "contentBlockStop"
    MESSAGE_STOP: Final[str] = "messageStop"
    METADATA: Final[str] = "metadata"
    DELTA: Final[str] = "delta"
    CONTENT_BLOCK_INDEX: Final[str] = "contentBlockIndex"

    # Role values
    ROLE_USER: Final[str] = "user"
    ROLE_ASSISTANT: Final[str] = "assistant"

    # Stop reason values
    STOP_REASON_END_TURN: Final[str] = "end_turn"
    STOP_REASON_MAX_TOKENS: Final[str] = "max_tokens"
    STOP_REASON_STOP_SEQUENCE: Final[str] = "stop_sequence"
    STOP_REASON_TOOL_USE: Final[str] = "tool_use"
    STOP_REASON_CONTENT_FILTERED: Final[str] = "content_filtered"


class LLMManagerConfig:
    """Configuration constants for LLM Manager."""

    # Default values
    DEFAULT_MAX_RETRIES: Final[int] = 3
    DEFAULT_RETRY_DELAY: Final[float] = 1.0
    DEFAULT_BACKOFF_MULTIPLIER: Final[float] = 2.0
    DEFAULT_MAX_RETRY_DELAY: Final[float] = 60.0
    DEFAULT_TIMEOUT: Final[int] = 300
    DEFAULT_MAX_TOKENS: Final[int] = 4096
    DEFAULT_LOG_LEVEL: Final[int] = logging.WARNING

    # Retry strategy
    RETRY_STRATEGY_REGION_FIRST: Final[str] = "region_first"
    RETRY_STRATEGY_MODEL_FIRST: Final[str] = "model_first"

    # Authentication types
    AUTH_TYPE_PROFILE: Final[str] = "profile"
    AUTH_TYPE_CREDENTIALS: Final[str] = "credentials"
    AUTH_TYPE_IAM_ROLE: Final[str] = "iam_role"
    AUTH_TYPE_AUTO: Final[str] = "auto"


class LLMManagerLogMessages:
    """Logging message constants for LLM Manager."""

    # Initialization messages
    MANAGER_INITIALIZED: Final[str] = (
        "LLMManager initialized with {model_count} models and {region_count} regions"
    )
    AUTH_CONFIGURED: Final[str] = "Authentication configured using {auth_type}"
    UNIFIED_MODEL_MANAGER_LOADED: Final[str] = (
        "UnifiedModelManager loaded with {model_count} models"
    )

    # Request processing messages
    REQUEST_STARTED: Final[str] = (
        "Starting converse request with model '{model}' in region '{region}'"
    )
    REQUEST_RETRY: Final[str] = (
        "Retrying request (attempt {attempt}/{max_attempts}) with model '{model}' in region '{region}'"
    )
    REQUEST_FALLBACK: Final[str] = (
        "Falling back from {from_method} to {to_method} for model '{model}' in region '{region}'"
    )
    FEATURE_DISABLED: Final[str] = (
        "Disabled feature '{feature}' for model '{model}' due to incompatibility"
    )
    REQUEST_SUCCEEDED: Final[str] = (
        "Request succeeded with model '{model}' in region '{region}' after {attempts} attempts"
    )
    REQUEST_FAILED: Final[str] = "Request failed with model '{model}' in region '{region}': {error}"

    # Retry strategy messages
    TRYING_NEXT_REGION: Final[str] = "Trying next region '{region}' for model '{model}'"
    TRYING_NEXT_MODEL: Final[str] = "Trying next model '{model}' after exhausting regions"
    ALL_ATTEMPTS_EXHAUSTED: Final[str] = (
        "All retry attempts exhausted. Final attempt with model '{model}' in region '{region}'"
    )

    # Performance messages
    REQUEST_TIMING: Final[str] = (
        "Request completed in {duration_ms}ms (API latency: {api_latency_ms}ms)"
    )
    CACHE_HIT: Final[str] = "Cache hit: {cache_read_tokens} tokens read from cache"
    CACHE_WRITE: Final[str] = "Cache write: {cache_write_tokens} tokens written to cache"


class LLMManagerErrorMessages:
    """Error message constants for LLM Manager."""

    # Configuration errors
    NO_MODELS_SPECIFIED: Final[str] = "No models specified for LLM Manager"
    NO_REGIONS_SPECIFIED: Final[str] = "No regions specified for LLM Manager"
    INVALID_AUTH_CONFIG: Final[str] = "Invalid authentication configuration: {details}"
    MODEL_NOT_AVAILABLE: Final[str] = "Model '{model}' is not available in any specified region"
    REGION_NOT_SUPPORTED: Final[str] = "Region '{region}' is not supported by any specified model"

    # Request errors
    EMPTY_MESSAGES: Final[str] = "Messages cannot be empty"
    INVALID_MESSAGE_ROLE: Final[str] = "Invalid message role: {role}. Must be 'user' or 'assistant'"
    INVALID_CONTENT_TYPE: Final[str] = "Invalid content type: {content_type}"
    CONTENT_SIZE_EXCEEDED: Final[str] = (
        "Content size exceeds limit: {size} bytes (max: {max_size} bytes)"
    )

    # Authentication errors
    CREDENTIALS_NOT_FOUND: Final[str] = (
        "AWS credentials not found. Configure credentials using AWS CLI, environment variables, or IAM roles"
    )
    INVALID_PROFILE: Final[str] = "AWS profile '{profile}' not found"
    PERMISSION_DENIED: Final[str] = (
        "Permission denied for bedrock:InvokeModel operation in region '{region}'"
    )

    # Retry errors
    ALL_RETRIES_FAILED: Final[str] = (
        "All retry attempts failed across {model_count} models and {region_count} regions"
    )
    THROTTLING_EXCEEDED: Final[str] = "Request throttling exceeded maximum retry attempts"
    MODEL_ACCESS_DENIED: Final[str] = "Access denied for model '{model}' in region '{region}'"

    # Streaming errors
    STREAMING_CONNECTION_LOST: Final[str] = "Streaming connection lost during response"
    STREAMING_PARSE_ERROR: Final[str] = "Failed to parse streaming response: {error}"


class RetryableErrorTypes:
    """Constants for retryable error classification."""

    # Throttling errors (always retryable)
    THROTTLING_ERRORS: Final[tuple] = (
        "ThrottlingException",
        "RequestThrottledException",
        "ServiceQuotaExceededException",
        "TooManyRequestsException",
    )

    # Service errors (retryable)
    SERVICE_ERRORS: Final[tuple] = (
        "InternalServerError",
        "ServiceUnavailableException",
        "InternalFailure",
        "ServiceException",
    )

    # Network errors (retryable)
    NETWORK_ERRORS: Final[tuple] = (
        "ConnectionError",
        "TimeoutError",
        "EndpointConnectionError",
        "ConnectTimeoutError",
        "ReadTimeoutError",
    )

    # Access errors (may be retryable with different region/model)
    ACCESS_ERRORS: Final[tuple] = (
        "AccessDeniedException",
        "UnauthorizedException",
        "ValidationException",
    )

    # Non-retryable errors
    NON_RETRYABLE_ERRORS: Final[tuple] = (
        "InvalidRequestException",
        "ModelNotReadyException",
        "ModelTimeoutException",
        "ResourceNotFoundException",
    )


class ContentLimits:
    """Content size and count limits for different content types."""

    # Image limits
    MAX_IMAGES_PER_REQUEST: Final[int] = 20
    MAX_IMAGE_SIZE_BYTES: Final[int] = 3_750_000  # 3.75 MB
    MAX_IMAGE_DIMENSION_PX: Final[int] = 8000

    # Document limits
    MAX_DOCUMENTS_PER_REQUEST: Final[int] = 5
    MAX_DOCUMENT_SIZE_BYTES: Final[int] = 4_500_000  # 4.5 MB

    # Video limits
    MAX_VIDEOS_PER_REQUEST: Final[int] = 1
    MAX_VIDEO_SIZE_BYTES: Final[int] = 100_000_000  # 100 MB (example limit)

    # Text limits
    MAX_CONTENT_BLOCKS_PER_MESSAGE: Final[int] = 100
    MAX_MESSAGES_PER_REQUEST: Final[int] = 1000

    # Token limits (model-dependent, these are conservative defaults)
    DEFAULT_MAX_INPUT_TOKENS: Final[int] = 200_000
    DEFAULT_MAX_OUTPUT_TOKENS: Final[int] = 4_096


class ResponseValidationConfig:
    """Configuration constants for response validation."""

    # Default values
    DEFAULT_VALIDATION_RETRIES: Final[int] = 3
    DEFAULT_VALIDATION_DELAY: Final[float] = 0.0

    # Validation result field constants
    VALIDATION_SUCCESS: Final[str] = "success"
    VALIDATION_ERROR_MESSAGE: Final[str] = "error_message"
    VALIDATION_ERROR_DETAILS: Final[str] = "error_details"


class ResponseValidationLogMessages:
    """Logging message constants for response validation."""

    # Validation messages
    VALIDATION_STARTED: Final[str] = (
        "Starting response validation for model '{model}' in region '{region}'"
    )
    VALIDATION_FAILED: Final[str] = (
        "Response validation failed (attempt {attempt}/{max_attempts}) for model '{model}' in region '{region}': {error}"
    )
    VALIDATION_SUCCEEDED: Final[str] = (
        "Response validation succeeded for model '{model}' in region '{region}' after {attempts} attempts"
    )
    VALIDATION_RETRIES_EXHAUSTED: Final[str] = (
        "Response validation retries exhausted for model '{model}' in region '{region}', trying next target"
    )
    VALIDATION_FUNCTION_ERROR: Final[str] = (
        "Validation function raised exception for model '{model}' in region '{region}': {error}"
    )
    VALIDATION_CONTENT_LOGGED: Final[str] = (
        "Failed validation content for model '{model}': {content}"
    )


class FeatureAvailability:
    """Feature availability constants for different models and regions."""

    # Features that may not be available in all regions/models
    OPTIONAL_FEATURES: Final[tuple] = (
        "guardrails",
        "tool_use",
        "prompt_caching",
        "streaming",
        "document_processing",
        "image_processing",
        "video_processing",
    )

    # Model families with specific capabilities (patterns for matching model names)
    TEXT_ONLY_MODELS: Final[tuple] = ("ai21", "cohere", "jamba", "jurassic")

    MULTIMODAL_MODELS: Final[tuple] = ("claude", "nova", "anthropic.claude", "amazon.nova")

    TOOL_USE_SUPPORTED_MODELS: Final[tuple] = ("claude", "nova", "anthropic.claude", "amazon.nova")
