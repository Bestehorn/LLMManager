"""
BedrockResponse class for LLM Manager system.
Provides comprehensive response handling with convenience methods.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .llm_manager_constants import ConverseAPIFields
from .llm_manager_structures import RequestAttempt, ValidationAttempt


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

    def get_attempt_count(self) -> int:
        """
        Get the total number of attempts made.

        Returns:
            Number of attempts made
        """
        return len(self.attempts)

    def get_successful_attempt(self) -> Optional[RequestAttempt]:
        """
        Get the successful attempt details.

        Returns:
            RequestAttempt that succeeded, None if no success
        """
        successful_attempts = [a for a in self.attempts if a.success]
        return successful_attempts[0] if successful_attempts else None

    def get_cached_tokens_info(self) -> Optional[Dict[str, int]]:
        """
        Get prompt caching information if available.

        Returns:
            Dictionary with cache hit/write information, None if not available
        """
        usage = self.get_usage()
        if not usage:
            return None

        cache_read = usage.get("cache_read_tokens", 0)
        cache_write = usage.get("cache_write_tokens", 0)

        if cache_read > 0 or cache_write > 0:
            return {
                "cache_read_tokens": cache_read,
                "cache_write_tokens": cache_write,
                "cache_hit": cache_read > 0,
                "cache_write": cache_write > 0,
            }

        return None

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
            from .llm_manager_structures import ValidationResult

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

    def __repr__(self) -> str:
        """Return string representation of the BedrockResponse."""
        status = "SUCCESS" if self.success else "FAILED"
        return (
            f"BedrockResponse(status={status}, model={self.model_used}, "
            f"region={self.region_used}, attempts={len(self.attempts)})"
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

    def add_content_part(self, content: str) -> None:
        """
        Add a content part to the streaming response.

        Args:
            content: Content part to add
        """
        self.content_parts.append(content)
        self.stream_position += len(content)

    def add_stream_error(self, error: Exception) -> None:
        """
        Add an error encountered during streaming.

        Args:
            error: Error to add
        """
        self.stream_errors.append(error)

    def get_stream_errors(self) -> List[Exception]:
        """
        Get all errors encountered during streaming.

        Returns:
            List of streaming errors
        """
        return self.stream_errors.copy()

    def __repr__(self) -> str:
        """Return string representation of the StreamingResponse."""
        status = "SUCCESS" if self.success else "FAILED"
        return (
            f"StreamingResponse(status={status}, parts={len(self.content_parts)}, "
            f"position={self.stream_position}, errors={len(self.stream_errors)})"
        )
