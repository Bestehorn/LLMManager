"""
Data structures for LLM Manager system.
Contains typed data classes for configuration, requests, and responses.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from .llm_manager_constants import (
    ConverseAPIFields,
    LLMManagerConfig,
)
from .llm_manager_constants import ResponseValidationConfig as ValidationConstants


class AuthenticationType(Enum):
    """Enumeration of authentication types supported by LLM Manager."""

    PROFILE = LLMManagerConfig.AUTH_TYPE_PROFILE
    CREDENTIALS = LLMManagerConfig.AUTH_TYPE_CREDENTIALS
    IAM_ROLE = LLMManagerConfig.AUTH_TYPE_IAM_ROLE
    AUTO = LLMManagerConfig.AUTH_TYPE_AUTO


class RetryStrategy(Enum):
    """Enumeration of retry strategies."""

    REGION_FIRST = LLMManagerConfig.RETRY_STRATEGY_REGION_FIRST
    MODEL_FIRST = LLMManagerConfig.RETRY_STRATEGY_MODEL_FIRST


@dataclass(frozen=True)
class AuthConfig:
    """
    Configuration for AWS authentication.

    Attributes:
        auth_type: Type of authentication to use
        profile_name: AWS CLI profile name (for PROFILE auth_type)
        access_key_id: AWS access key ID (for CREDENTIALS auth_type)
        secret_access_key: AWS secret access key (for CREDENTIALS auth_type)
        session_token: AWS session token (optional, for temporary credentials)
        region: Default AWS region for authentication
    """

    auth_type: AuthenticationType
    profile_name: Optional[str] = None
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    session_token: Optional[str] = None
    region: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate authentication configuration."""
        if self.auth_type == AuthenticationType.PROFILE and not self.profile_name:
            raise ValueError("profile_name is required for PROFILE authentication")

        if self.auth_type == AuthenticationType.CREDENTIALS:
            if not self.access_key_id or not self.secret_access_key:
                raise ValueError(
                    "access_key_id and secret_access_key are required for CREDENTIALS authentication"
                )


@dataclass(frozen=True)
class RetryConfig:
    """
    Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        backoff_multiplier: Multiplier for exponential backoff
        max_retry_delay: Maximum delay between retries
        retry_strategy: Strategy for selecting retry targets
        enable_feature_fallback: Whether to disable features and retry on compatibility errors
        retryable_errors: Additional error types to consider retryable
    """

    max_retries: int = LLMManagerConfig.DEFAULT_MAX_RETRIES
    retry_delay: float = LLMManagerConfig.DEFAULT_RETRY_DELAY
    backoff_multiplier: float = LLMManagerConfig.DEFAULT_BACKOFF_MULTIPLIER
    max_retry_delay: float = LLMManagerConfig.DEFAULT_MAX_RETRY_DELAY
    retry_strategy: RetryStrategy = RetryStrategy.REGION_FIRST
    enable_feature_fallback: bool = True
    retryable_errors: tuple = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate retry configuration."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")
        if self.backoff_multiplier <= 0:
            raise ValueError("backoff_multiplier must be positive")
        if self.max_retry_delay <= 0:
            raise ValueError("max_retry_delay must be positive")


@dataclass
class RequestAttempt:
    """
    Information about a single request attempt.

    Attributes:
        model_id: Model ID used for the attempt
        region: AWS region used for the attempt
        access_method: Access method used (direct/cris)
        attempt_number: Sequential attempt number
        start_time: When the attempt started
        end_time: When the attempt completed (None if still in progress)
        error: Error encountered during attempt (None if successful)
        success: Whether the attempt was successful
    """

    model_id: str
    region: str
    access_method: str
    attempt_number: int
    start_time: datetime
    end_time: Optional[datetime] = None
    error: Optional[Exception] = None
    success: bool = False

    @property
    def duration_ms(self) -> Optional[float]:
        """Get the duration of the attempt in milliseconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return None


@dataclass
class BedrockResponse:
    """
    Comprehensive response object from LLM Manager operations.

    Contains the response data, execution metadata, performance metrics,
    and error information from Bedrock Converse API calls.

    Attributes:
        success: Whether the request was successful
        response_data: Raw response data from Bedrock API
        model_used: Model ID that was successfully used
        region_used: AWS region that was successfully used
        access_method_used: Access method that was used (direct/cris)
        attempts: List of all attempts made
        total_duration_ms: Total time taken for all attempts
        api_latency_ms: API latency from successful response
        warnings: List of warning messages encountered
        features_disabled: List of features that were disabled for compatibility
        validation_attempts: List of validation attempts made
        validation_errors: List of validation error details
    """

    success: bool
    response_data: Optional[Dict[str, Any]] = None
    model_used: Optional[str] = None
    region_used: Optional[str] = None
    access_method_used: Optional[str] = None
    attempts: List[RequestAttempt] = field(default_factory=list)
    total_duration_ms: Optional[float] = None
    api_latency_ms: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    features_disabled: List[str] = field(default_factory=list)
    validation_attempts: List["ValidationAttempt"] = field(default_factory=list)
    validation_errors: List[Dict[str, Any]] = field(default_factory=list)

    def get_content(self) -> Optional[str]:
        """
        Extract the main text content from the response.

        Returns:
            The text content from the assistant's response, None if not available
        """
        if not self.success or not self.response_data:
            return None

        try:
            output = self.response_data.get(ConverseAPIFields.OUTPUT, {})
            message = output.get(ConverseAPIFields.MESSAGE, {})
            content_blocks = message.get(ConverseAPIFields.CONTENT, [])

            # Extract text from all content blocks
            text_parts = []
            for block in content_blocks:
                if isinstance(block, dict) and ConverseAPIFields.TEXT in block:
                    text_parts.append(block[ConverseAPIFields.TEXT])

            return "\n".join(text_parts) if text_parts else None

        except (KeyError, TypeError, AttributeError):
            return None

    def get_usage(self) -> Optional[Dict[str, int]]:
        """
        Get token usage information from the response.

        Returns:
            Dictionary with usage information, None if not available
        """
        if not self.success or not self.response_data:
            return None

        try:
            usage = self.response_data.get(ConverseAPIFields.USAGE, {})
            return {
                "input_tokens": usage.get(ConverseAPIFields.INPUT_TOKENS, 0),
                "output_tokens": usage.get(ConverseAPIFields.OUTPUT_TOKENS, 0),
                "total_tokens": usage.get(ConverseAPIFields.TOTAL_TOKENS, 0),
                "cache_read_tokens": usage.get(ConverseAPIFields.CACHE_READ_INPUT_TOKENS_COUNT, 0),
                "cache_write_tokens": usage.get(
                    ConverseAPIFields.CACHE_WRITE_INPUT_TOKENS_COUNT, 0
                ),
            }
        except (KeyError, TypeError, AttributeError):
            return None

    def get_metrics(self) -> Optional[Dict[str, Union[float, int]]]:
        """
        Get performance metrics from the response.

        Returns:
            Dictionary with metrics information, None if not available
        """
        if not self.success or not self.response_data:
            return None

        metrics = {}

        # API latency from response
        try:
            response_metrics = self.response_data.get(ConverseAPIFields.METRICS, {})
            if ConverseAPIFields.LATENCY_MS in response_metrics:
                metrics["api_latency_ms"] = response_metrics[ConverseAPIFields.LATENCY_MS]
        except (KeyError, TypeError, AttributeError):
            pass

        # Total duration from our tracking
        if self.total_duration_ms is not None:
            metrics["total_duration_ms"] = self.total_duration_ms

        # Attempt count
        metrics["attempts_made"] = len(self.attempts)

        # Successful attempt number
        successful_attempts = [a for a in self.attempts if a.success]
        if successful_attempts:
            metrics["successful_attempt_number"] = successful_attempts[0].attempt_number

        return metrics if metrics else None

    def get_stop_reason(self) -> Optional[str]:
        """
        Get the reason why the model stopped generating content.

        Returns:
            Stop reason string, None if not available
        """
        if not self.success or not self.response_data:
            return None

        try:
            return self.response_data.get(ConverseAPIFields.STOP_REASON)
        except (KeyError, TypeError, AttributeError):
            return None

    def get_additional_model_response_fields(self) -> Optional[Dict[str, Any]]:
        """
        Get additional model-specific response fields.

        Returns:
            Dictionary with additional fields, None if not available
        """
        if not self.success or not self.response_data:
            return None

        try:
            return self.response_data.get(ConverseAPIFields.ADDITIONAL_MODEL_RESPONSE_FIELDS)
        except (KeyError, TypeError, AttributeError):
            return None

    def was_successful(self) -> bool:
        """
        Check if the request was successful.

        Returns:
            True if successful, False otherwise
        """
        return self.success

    def get_warnings(self) -> List[str]:
        """
        Get all warnings encountered during the request.

        Returns:
            List of warning messages
        """
        return self.warnings.copy()

    def get_disabled_features(self) -> List[str]:
        """
        Get list of features that were disabled for compatibility.

        Returns:
            List of disabled feature names
        """
        return self.features_disabled.copy()

    def get_last_error(self) -> Optional[Exception]:
        """
        Get the last error encountered.

        Returns:
            The last error from failed attempts, None if no errors or successful
        """
        failed_attempts = [a for a in self.attempts if not a.success and a.error]
        if failed_attempts:
            return failed_attempts[-1].error
        return None

    def get_all_errors(self) -> List[Exception]:
        """
        Get all errors encountered during all attempts.

        Returns:
            List of all errors from failed attempts
        """
        return [a.error for a in self.attempts if a.error is not None]

    def had_validation_failures(self) -> bool:
        """
        Check if any validation failures occurred during the request.

        Returns:
            True if validation failed at least once, False otherwise
        """
        return len(self.validation_attempts) > 0

    def get_validation_attempt_count(self) -> int:
        """
        Get the number of validation attempts made.

        Returns:
            Number of validation attempts
        """
        return len(self.validation_attempts)

    def get_validation_errors(self) -> List[Dict[str, Any]]:
        """
        Get all validation error details.

        Returns:
            List of validation error details
        """
        return self.validation_errors.copy()

    def get_last_validation_error(self) -> Optional[Dict[str, Any]]:
        """
        Get the last validation error details.

        Returns:
            Last validation error details, None if no validation errors
        """
        if self.validation_errors:
            return self.validation_errors[-1]
        return None

    def get_validation_metrics(self) -> Dict[str, Any]:
        """
        Get validation-specific metrics.

        Returns:
            Dictionary with validation metrics
        """
        metrics = {
            "validation_attempts": len(self.validation_attempts),
            "validation_errors": len(self.validation_errors),
            "had_validation_failures": self.had_validation_failures(),
        }

        # Add successful validation attempt number if any
        successful_validations = [
            va for va in self.validation_attempts if va.validation_result.success
        ]
        if successful_validations:
            metrics["successful_validation_attempt"] = successful_validations[0].attempt_number

        return metrics

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the response to a dictionary suitable for JSON serialization.

        Returns:
            Dictionary representation of the response
        """
        return {
            "success": self.success,
            "response_data": self.response_data,
            "model_used": self.model_used,
            "region_used": self.region_used,
            "access_method_used": self.access_method_used,
            "total_duration_ms": self.total_duration_ms,
            "api_latency_ms": self.api_latency_ms,
            "warnings": self.warnings,
            "features_disabled": self.features_disabled,
            "attempts": [
                {
                    "model_id": attempt.model_id,
                    "region": attempt.region,
                    "access_method": attempt.access_method,
                    "attempt_number": attempt.attempt_number,
                    "start_time": attempt.start_time.isoformat(),
                    "end_time": attempt.end_time.isoformat() if attempt.end_time else None,
                    "duration_ms": attempt.duration_ms,
                    "success": attempt.success,
                    "error": str(attempt.error) if attempt.error else None,
                }
                for attempt in self.attempts
            ],
            "validation_attempts": [
                {
                    "attempt_number": va.attempt_number,
                    "validation_result": va.validation_result.to_dict(),
                    "failed_content": va.failed_content,
                }
                for va in self.validation_attempts
            ],
            "validation_errors": self.validation_errors,
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        """
        Convert the response to JSON string.

        Args:
            indent: Number of spaces for indentation (None for compact JSON)

        Returns:
            JSON string representation of the response
        """
        return json.dumps(obj=self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BedrockResponse":
        """
        Create BedrockResponse from dictionary data.

        Args:
            data: Dictionary containing response data

        Returns:
            BedrockResponse instance
        """
        attempts = []
        for attempt_data in data.get("attempts", []):
            attempt = RequestAttempt(
                model_id=attempt_data["model_id"],
                region=attempt_data["region"],
                access_method=attempt_data["access_method"],
                attempt_number=attempt_data["attempt_number"],
                start_time=datetime.fromisoformat(attempt_data["start_time"]),
                end_time=(
                    datetime.fromisoformat(attempt_data["end_time"])
                    if attempt_data["end_time"]
                    else None
                ),
                success=attempt_data["success"],
                error=Exception(attempt_data["error"]) if attempt_data["error"] else None,
            )
            attempts.append(attempt)

        # Reconstruct validation attempts
        validation_attempts = []
        for va_data in data.get("validation_attempts", []):
            validation_result = ValidationResult.from_dict(va_data["validation_result"])
            validation_attempt = ValidationAttempt(
                attempt_number=va_data["attempt_number"],
                validation_result=validation_result,
                failed_content=va_data.get("failed_content"),
            )
            validation_attempts.append(validation_attempt)

        return cls(
            success=data["success"],
            response_data=data.get("response_data"),
            model_used=data.get("model_used"),
            region_used=data.get("region_used"),
            access_method_used=data.get("access_method_used"),
            attempts=attempts,
            total_duration_ms=data.get("total_duration_ms"),
            api_latency_ms=data.get("api_latency_ms"),
            warnings=data.get("warnings", []),
            features_disabled=data.get("features_disabled", []),
            validation_attempts=validation_attempts,
            validation_errors=data.get("validation_errors", []),
        )


@dataclass
class StreamingResponse:
    """
    Response object for streaming operations.

    Attributes:
        success: Whether the streaming was successful
        content_parts: List of content parts received during streaming
        final_response: Final consolidated response
        stream_errors: List of errors encountered during streaming
        stream_position: Final position in the stream
    """

    success: bool
    content_parts: List[str] = field(default_factory=list)
    final_response: Optional[BedrockResponse] = None
    stream_errors: List[Exception] = field(default_factory=list)
    stream_position: int = 0

    def get_full_content(self) -> str:
        """
        Get the full content by concatenating all parts.

        Returns:
            Complete content string
        """
        return "".join(self.content_parts)

    def get_content_parts(self) -> List[str]:
        """
        Get individual content parts as received during streaming.

        Returns:
            List of content parts
        """
        return self.content_parts.copy()


@dataclass
class FilteredContent:
    """
    Information about content that was filtered from a request.

    Attributes:
        message_index: Index of the message containing the filtered content
        block_index: Index of the content block within the message
        content_block: The actual content block that was filtered
    """

    message_index: int
    block_index: int
    content_block: Dict[str, Any]


@dataclass
class ContentFilterState:
    """
    State tracking for content filtering and restoration.

    Attributes:
        original_request: The original unmodified request arguments
        disabled_features: Set of features that have been disabled
        filtered_content: Dictionary mapping feature names to filtered content
    """

    original_request: Dict[str, Any]
    disabled_features: set = field(default_factory=set)
    filtered_content: Dict[str, List[FilteredContent]] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """
    Result of response validation containing success status and error details.

    Attributes:
        success: Whether validation passed
        error_message: Error message if validation failed
        error_details: Additional error details if available
    """

    success: bool
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary."""
        result: Dict[str, Any] = {ValidationConstants.VALIDATION_SUCCESS: self.success}
        if self.error_message is not None:
            result[ValidationConstants.VALIDATION_ERROR_MESSAGE] = self.error_message
        if self.error_details is not None:
            result[ValidationConstants.VALIDATION_ERROR_DETAILS] = self.error_details
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationResult":
        """Create ValidationResult from dictionary."""
        return cls(
            success=data[ValidationConstants.VALIDATION_SUCCESS],
            error_message=data.get(ValidationConstants.VALIDATION_ERROR_MESSAGE),
            error_details=data.get(ValidationConstants.VALIDATION_ERROR_DETAILS),
        )


# Type alias for response validation functions
ResponseValidationFunction = Callable[["BedrockResponse"], ValidationResult]


@dataclass(frozen=True)
class ResponseValidationConfig:
    """
    Configuration for response validation.

    Attributes:
        response_validation_function: Function that validates BedrockResponse and returns ValidationResult
        response_validation_retries: Number of validation retries (default: 3)
        response_validation_delay: Delay between validation retries in seconds (default: 0.0)
    """

    response_validation_function: ResponseValidationFunction
    response_validation_retries: int = ValidationConstants.DEFAULT_VALIDATION_RETRIES
    response_validation_delay: float = ValidationConstants.DEFAULT_VALIDATION_DELAY

    def __post_init__(self) -> None:
        """Validate response validation configuration."""
        if self.response_validation_retries < 0:
            raise ValueError("response_validation_retries must be non-negative")
        if self.response_validation_delay < 0:
            raise ValueError("response_validation_delay must be non-negative")


@dataclass
class ValidationAttempt:
    """
    Information about a single validation attempt.

    Attributes:
        attempt_number: Sequential validation attempt number
        validation_result: Result of the validation attempt
        failed_content: Content that failed validation (for logging)
    """

    attempt_number: int
    validation_result: ValidationResult
    failed_content: Optional[str] = None
