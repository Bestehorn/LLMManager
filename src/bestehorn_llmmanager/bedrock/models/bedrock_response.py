"""
BedrockResponse class for LLM Manager system.
Provides comprehensive response handling with convenience methods.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from .citation import Citation
from .content_block_types import ResponseContentType
from .llm_manager_constants import ConverseAPIFields
from .llm_manager_structures import RequestAttempt, ValidationAttempt
from .reasoning_content import ReasoningContent
from .stop_reason import StopReasonCategory, StopReasonClassifier
from .tool_use import ToolUse


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
        access_method_used: Access method that was used (direct/regional_cris/global_cris)
        inference_profile_used: Whether an inference profile was used for the request
        inference_profile_id: The inference profile ID/ARN if profile was used
        attempts: List of all attempts made
        total_duration_ms: Total time taken for all attempts
        api_latency_ms: API latency from successful response
        warnings: List of warning messages encountered
        features_disabled: List of features that were disabled for compatibility
        validation_attempts: List of validation attempts made
        validation_errors: List of validation error details
        parameters_removed: List of parameter names removed due to incompatibility
        original_additional_fields: Original additionalModelRequestFields before removal
        final_additional_fields: Final additionalModelRequestFields actually used
    """

    success: bool
    response_data: Optional[Dict[str, Any]] = None
    model_used: Optional[str] = None
    region_used: Optional[str] = None
    access_method_used: Optional[str] = None
    inference_profile_used: bool = False
    inference_profile_id: Optional[str] = None
    attempts: List[RequestAttempt] = field(default_factory=list)
    total_duration_ms: Optional[float] = None
    api_latency_ms: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    features_disabled: List[str] = field(default_factory=list)
    validation_attempts: List["ValidationAttempt"] = field(default_factory=list)
    validation_errors: List[Dict[str, Any]] = field(default_factory=list)
    parameters_removed: Optional[List[str]] = None
    original_additional_fields: Optional[Dict[str, Any]] = None
    final_additional_fields: Optional[Dict[str, Any]] = None

    def get_content_blocks(self) -> Optional[List[Any]]:
        """
        Get the ordered list of typed content blocks from the response message.

        This is the general response-content accessor: it returns every content block
        from the assistant's message — text, ``toolUse``, ``reasoningContent``,
        ``image``, ``citationsContent``, and any other ``ContentBlock`` union member —
        in the order the model produced them, so callers can handle any modality
        without hand-navigating the raw response dictionary. The type-specific
        accessors (:meth:`get_text_blocks`, :meth:`get_image_blocks`,
        :meth:`get_content_blocks_by_type`) and the text convenience
        :meth:`get_content` are all built on top of this iterator.

        The returned list is a shallow copy, so mutating it does not affect the
        underlying ``response_data``. Individual block dicts are not copied.

        Returns:
            The ordered list of content blocks, or ``None`` if the response was
            unsuccessful, has no response data, or has no content list.

        Reference:
            https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ContentBlock.html
        """
        if not self.success or not self.response_data:
            return None

        try:
            output = self.response_data.get(ConverseAPIFields.OUTPUT, {})
            message = output.get(ConverseAPIFields.MESSAGE, {})
            content_blocks = message.get(ConverseAPIFields.CONTENT, None)
        except (KeyError, TypeError, AttributeError):
            return None

        if not isinstance(content_blocks, list):
            return None

        return list(content_blocks)

    def get_content_blocks_by_type(
        self, content_type: Union[ResponseContentType, str]
    ) -> List[Any]:
        """
        Get all content blocks of a single type, in order.

        Filters the result of :meth:`get_content_blocks` to the blocks whose
        discriminating union key matches ``content_type``.

        Args:
            content_type: The block type to keep, either a :class:`ResponseContentType`
                or its raw string key (e.g. ``"text"``, ``"toolUse"``, ``"image"``).

        Returns:
            The matching blocks in order; an empty list if there are none or if the
            response has no content blocks.
        """
        target = (
            content_type
            if isinstance(content_type, ResponseContentType)
            else ResponseContentType.from_block(block={str(content_type): None})
        )

        blocks = self.get_content_blocks()
        if not blocks:
            return []

        return [
            block
            for block in blocks
            if isinstance(block, dict) and ResponseContentType.from_block(block=block) is target
        ]

    def get_text_blocks(self) -> List[str]:
        """
        Get the text strings from all text content blocks, in order.

        Returns:
            The ordered list of text strings; an empty list if the response has no
            text blocks.
        """
        return [
            block[ConverseAPIFields.TEXT]
            for block in self.get_content_blocks_by_type(content_type=ResponseContentType.TEXT)
        ]

    def get_image_blocks(self) -> List[Dict[str, Any]]:
        """
        Get the image payloads from all image content blocks, in order.

        Each returned item is the value under the block's ``image`` key — an
        ``ImageBlock`` (``{"format": ..., "source": ...}``) — not the wrapping block.

        Returns:
            The ordered list of image payloads; an empty list if the response has no
            image blocks.
        """
        return [
            block[ConverseAPIFields.IMAGE]
            for block in self.get_content_blocks_by_type(content_type=ResponseContentType.IMAGE)
        ]

    def get_tool_uses(self) -> List[ToolUse]:
        """
        Get the tool-use (function-call) requests from the response, in order.

        Parses every ``toolUse`` content block into a typed :class:`ToolUse`
        (id, name, parsed input), so a tool-use turn is reachable without touching the
        raw response dict. Built on :meth:`get_content_blocks_by_type`.

        Returns:
            The ordered list of :class:`ToolUse`; an empty list if the response contains
            no tool-use blocks.
        """
        return [
            ToolUse.from_tool_use_block(tool_use_block=block[ConverseAPIFields.TOOL_USE])
            for block in self.get_content_blocks_by_type(content_type=ResponseContentType.TOOL_USE)
        ]

    def has_tool_use(self) -> bool:
        """
        Check whether the model requested a tool call.

        True if the response contains a ``toolUse`` content block OR its stop reason is
        ``tool_use`` (the model may signal a tool turn via the stop reason even before
        the blocks are inspected).

        Returns:
            True if a tool call was requested, False otherwise.
        """
        if self.get_tool_uses():
            return True
        return self.get_stop_reason() == ConverseAPIFields.STOP_REASON_TOOL_USE

    def get_reasoning(self) -> Optional["ReasoningContent"]:
        """
        Get the reasoning / extended-thinking content from the response, if any.

        Parses the first ``reasoningContent`` block into a typed
        :class:`~bestehorn_llmmanager.bedrock.models.reasoning_content.ReasoningContent`
        (text + signature, or redacted bytes), so the reasoning can be read and echoed
        back into a multi-turn request with its signature preserved. Built on
        :meth:`get_content_blocks_by_type`.

        Returns:
            The :class:`ReasoningContent`, or ``None`` if the response contains no
            reasoning block.
        """
        reasoning_blocks = self.get_content_blocks_by_type(
            content_type=ResponseContentType.REASONING_CONTENT
        )
        if not reasoning_blocks:
            return None
        return ReasoningContent.from_reasoning_block(
            reasoning_block=reasoning_blocks[0][ConverseAPIFields.REASONING_CONTENT]
        )

    def get_citations(self) -> List[Citation]:
        """
        Get the document citations from the response, in order.

        When document citations are enabled (via the document builder's
        ``citations_enabled``), the model returns ``citationsContent`` blocks whose
        ``citations`` arrays reference the source spans. This flattens every
        ``citationsContent`` block's citations into typed :class:`Citation` objects
        (source title / location / referenced spans), built on
        :meth:`get_content_blocks_by_type`.

        Returns:
            The ordered list of :class:`Citation`; an empty list if the response
            contains no citations.
        """
        citations: List[Citation] = []
        for block in self.get_content_blocks_by_type(
            content_type=ResponseContentType.CITATIONS_CONTENT
        ):
            citations_content = block[ConverseAPIFields.CITATIONS_CONTENT]
            for raw_citation in citations_content.get(ConverseAPIFields.CITATIONS, []) or []:
                citations.append(Citation.from_citation(citation=raw_citation))
        return citations

    def get_content(self) -> Optional[str]:
        """
        Extract the main text content from the response.

        Joins every text content block with newlines. Built on
        :meth:`get_text_blocks` (and thus :meth:`get_content_blocks`), so non-text
        modalities are ignored here but reachable through the typed accessors.

        Returns:
            The joined text content from the assistant's response, None if not available
        """
        text_parts = self.get_text_blocks()
        return "\n".join(text_parts) if text_parts else None

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

    def get_input_tokens(self) -> int:
        """
        Get the number of input tokens used in the request.

        Returns:
            Number of input tokens, 0 if not available
        """
        usage = self.get_usage()
        return usage.get("input_tokens", 0) if usage else 0

    def get_output_tokens(self) -> int:
        """
        Get the number of output tokens generated in the response.

        Returns:
            Number of output tokens, 0 if not available
        """
        usage = self.get_usage()
        return usage.get("output_tokens", 0) if usage else 0

    def get_total_tokens(self) -> int:
        """
        Get the total number of tokens (input + output) used.

        Returns:
            Total number of tokens, 0 if not available
        """
        usage = self.get_usage()
        return usage.get("total_tokens", 0) if usage else 0

    def get_cache_read_tokens(self) -> int:
        """
        Get the number of tokens read from prompt cache.

        Returns:
            Number of cache read tokens, 0 if not available
        """
        usage = self.get_usage()
        return usage.get("cache_read_tokens", 0) if usage else 0

    def get_cache_write_tokens(self) -> int:
        """
        Get the number of tokens written to prompt cache.

        Returns:
            Number of cache write tokens, 0 if not available
        """
        usage = self.get_usage()
        return usage.get("cache_write_tokens", 0) if usage else 0

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

    def get_stop_reason_category(self) -> StopReasonCategory:
        """
        Get the canonical retry/failover category of this response's stop reason.

        Classifies the raw ``stopReason`` (see :meth:`get_stop_reason`) into a
        :class:`StopReasonCategory` so callers can branch on intent rather than on raw
        strings — e.g. ``model_context_window_exceeded`` and ``malformed_*`` are
        retryable (the former only against a different model/region), while ``end_turn`` /
        ``tool_use`` / ``stop_sequence`` / ``max_tokens`` are terminal (issue #37). An
        absent or unrecognized reason maps to ``StopReasonCategory.UNKNOWN``.

        Returns:
            The :class:`StopReasonCategory` for this response's stop reason.
        """
        return StopReasonClassifier.categorize(self.get_stop_reason())

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
            Dictionary with cache hit/write information, None if usage unavailable
        """
        usage = self.get_usage()
        if not usage:
            return None

        cache_read = usage.get("cache_read_tokens", 0)
        cache_write = usage.get("cache_write_tokens", 0)

        # Always return cache information, even if 0 (shows caching status)
        return {
            "cache_read_tokens": cache_read,
            "cache_write_tokens": cache_write,
            "cache_hit": cache_read > 0,
            "cache_write": cache_write > 0,
        }

    def get_cache_efficiency(self) -> Optional[Dict[str, Any]]:
        """
        Get cache efficiency metrics.

        Returns:
            Dictionary with cache efficiency metrics, None if not available
        """
        cache_info = self.get_cached_tokens_info()
        if not cache_info:
            return None

        usage = self.get_usage()
        if not usage:
            return None

        # Calculate metrics
        cache_read_tokens = cache_info.get("cache_read_tokens", 0)
        cache_write_tokens = cache_info.get("cache_write_tokens", 0)
        total_input_tokens = usage.get("input_tokens", 0)

        # Avoid division by zero
        if total_input_tokens == 0:
            return None

        # Cache hit ratio
        cache_hit_ratio = cache_read_tokens / total_input_tokens if total_input_tokens > 0 else 0.0

        # Estimate cost savings (example rate: $0.03 per 1K tokens)
        COST_PER_1K_TOKENS = 0.03
        cache_savings_tokens = cache_read_tokens
        cache_savings_cost = (cache_savings_tokens / 1000) * COST_PER_1K_TOKENS

        # Estimate latency reduction (rough estimate: 1ms per 100 cached tokens)
        latency_reduction_ms = int(cache_read_tokens / 100)

        return {
            "cache_hit_ratio": round(cache_hit_ratio, 2),
            "cache_savings_tokens": cache_savings_tokens,
            "cache_savings_cost": f"${cache_savings_cost:.2f}",
            "latency_reduction_ms": latency_reduction_ms,
            "cache_write_tokens": cache_write_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_effectiveness": round(cache_hit_ratio * 100, 1),  # Percentage
        }

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

    def had_parameters_removed(self) -> bool:
        """
        Check if any parameters were removed during retry due to incompatibility.

        Returns:
            True if parameters were removed, False otherwise
        """
        return bool(self.parameters_removed)

    def get_parameter_warnings(self) -> List[str]:
        """
        Get warnings related to parameter compatibility.

        Returns:
            List of warning messages about parameter removal
        """
        parameter_warnings = []

        if self.had_parameters_removed() and self.parameters_removed:
            # Add warnings about removed parameters
            for param_name in self.parameters_removed:
                warning_msg = (
                    f"Parameter '{param_name}' was removed due to incompatibility "
                    f"with model/region combination"
                )
                parameter_warnings.append(warning_msg)

            # Add summary warning if multiple parameters were removed
            if len(self.parameters_removed) > 1:
                summary_msg = (
                    f"Total of {len(self.parameters_removed)} parameters were removed "
                    f"for compatibility"
                )
                parameter_warnings.append(summary_msg)

        return parameter_warnings

    def get_access_method(self) -> Optional[str]:
        """
        Get the access method used for the successful request.

        Returns:
            Access method name (e.g., "direct", "regional_cris", "global_cris"), None if not available
        """
        return self.access_method_used

    def was_profile_used(self) -> bool:
        """
        Check if an inference profile was used for the request.

        Returns:
            True if inference profile was used, False otherwise
        """
        return self.inference_profile_used

    def get_profile_id(self) -> Optional[str]:
        """
        Get the inference profile ID/ARN if profile was used.

        Returns:
            Profile ID/ARN if profile was used, None otherwise
        """
        return self.inference_profile_id if self.inference_profile_used else None

    def get_access_method_info(self) -> Dict[str, Any]:
        """
        Get comprehensive access method information.

        Returns:
            Dictionary with access method details including:
            - access_method: The access method used
            - profile_used: Whether profile was used
            - profile_id: Profile ID if used
            - model_id: Model ID used
            - region: Region used
        """
        return {
            "access_method": self.access_method_used,
            "profile_used": self.inference_profile_used,
            "profile_id": self.inference_profile_id,
            "model_id": self.model_used,
            "region": self.region_used,
        }

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
            "inference_profile_used": self.inference_profile_used,
            "inference_profile_id": self.inference_profile_id,
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
            "parameters_removed": self.parameters_removed,
            "original_additional_fields": self.original_additional_fields,
            "final_additional_fields": self.final_additional_fields,
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
            inference_profile_used=data.get("inference_profile_used", False),
            inference_profile_id=data.get("inference_profile_id"),
            attempts=attempts,
            total_duration_ms=data.get("total_duration_ms"),
            api_latency_ms=data.get("api_latency_ms"),
            warnings=data.get("warnings", []),
            features_disabled=data.get("features_disabled", []),
            validation_attempts=validation_attempts,
            validation_errors=data.get("validation_errors", []),
            parameters_removed=data.get("parameters_removed"),
            original_additional_fields=data.get("original_additional_fields"),
            final_additional_fields=data.get("final_additional_fields"),
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
    Response object for streaming operations with iterator protocol support.

    This class implements the iterator protocol to provide real-time streaming
    where content chunks are yielded as they arrive from the AWS EventStream.
    After iteration completes, all metadata (tokens, metrics, etc.) is available
    just like a regular BedrockResponse.

    Attributes:
        success: Whether the streaming was successful
        content_parts: List of content parts received during streaming
        final_response: Final consolidated response
        stream_errors: List of errors encountered during streaming
        stream_position: Final position in the stream
        model_used: Model ID that was used for streaming
        region_used: AWS region that was used for streaming
        access_method_used: Access method that was used (direct/regional_cris/global_cris)
        inference_profile_used: Whether an inference profile was used for the request
        inference_profile_id: The inference profile ID/ARN if profile was used
        total_duration_ms: Total streaming duration in milliseconds
        api_latency_ms: API latency from streaming metadata
        stop_reason: Reason why streaming stopped
        usage_info: Token usage information from streaming
        metrics_info: Performance metrics from streaming
        trace_info: Trace information from streaming
        additional_model_response_fields: Additional model-specific response fields
        current_message_role: Role of the current message being streamed
        request_attempt: Request attempt information
        warnings: List of warning messages encountered during streaming
        _event_stream: Internal AWS EventStream for lazy processing
        _stream_iterator: Internal iterator for EventStream processing
        _stream_completed: Flag indicating if streaming has completed
        _start_time: When streaming started (for duration calculation)
    """

    success: bool
    content_parts: List[str] = field(default_factory=list)
    final_response: Optional[BedrockResponse] = None
    stream_errors: List[Exception] = field(default_factory=list)
    stream_position: int = 0
    model_used: Optional[str] = None
    region_used: Optional[str] = None
    access_method_used: Optional[str] = None
    inference_profile_used: bool = False
    inference_profile_id: Optional[str] = None
    total_duration_ms: Optional[float] = None
    api_latency_ms: Optional[float] = None
    stop_reason: Optional[str] = None
    usage_info: Optional[Dict[str, Any]] = None
    metrics_info: Optional[Dict[str, Any]] = None
    trace_info: Optional[Dict[str, Any]] = None
    additional_model_response_fields: Optional[Dict[str, Any]] = None
    current_message_role: Optional[str] = None
    request_attempt: Optional[RequestAttempt] = None
    warnings: List[str] = field(default_factory=list)
    # Reasoning / extended-thinking accumulated across reasoningContent deltas (issue #32),
    # so the final signed block can be reconstructed for multi-turn echo-back.
    reasoning_text_parts: List[str] = field(default_factory=list)
    reasoning_signature: Optional[str] = None
    reasoning_redacted_content: Optional[Any] = None
    # Document citations accumulated across citation deltas (issue #40).
    citation_blocks: List[Dict[str, Any]] = field(default_factory=list)

    # Internal fields for iterator protocol
    _event_stream: Optional[Any] = field(default=None, init=False, repr=False)
    _retrying_iterator: Optional[Any] = field(default=None, init=False, repr=False)
    _stream_iterator: Optional[Any] = field(default=None, init=False, repr=False)
    _stream_completed: bool = field(default=False, init=False, repr=False)
    _start_time: Optional[datetime] = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize the streaming response."""
        self._start_time = datetime.now()
        self._first_token_time: Optional[datetime] = None
        self._last_token_time: Optional[datetime] = None

    def _set_event_stream(self, event_stream: Any) -> None:
        """
        Set the AWS EventStream for lazy processing.

        Args:
            event_stream: AWS EventStream from converse_stream API
        """
        self._event_stream = event_stream
        self._stream_iterator = iter(event_stream) if event_stream else None

    def _set_retrying_iterator(self, retrying_iterator: Any) -> None:
        """
        Set the RetryingStreamIterator for advanced retry handling.

        Args:
            retrying_iterator: RetryingStreamIterator instance for mid-stream recovery
        """
        self._retrying_iterator = retrying_iterator
        self._stream_iterator = iter(retrying_iterator)

    def __iter__(self) -> "StreamingResponse":
        """
        Return self as iterator.

        Returns:
            Self for iterator protocol
        """
        return self

    def __next__(self) -> str:
        """
        Get the next content chunk from the stream.

        This method processes EventStream events lazily and yields content
        chunks as they arrive, providing true real-time streaming.

        Returns:
            Content chunk string

        Raises:
            StopIteration: When streaming completes
        """
        if self._stream_completed:
            raise StopIteration

        if not self._stream_iterator:
            self._stream_completed = True
            raise StopIteration

        try:
            # Process events until we get content or stream ends
            while True:
                try:
                    event = next(self._stream_iterator)
                    content_chunk = self._process_streaming_event(event)

                    if content_chunk:
                        # Got content, return it
                        return content_chunk
                    # No content in this event, continue to next event

                except StopIteration:
                    # Stream completed
                    self._finalize_streaming()
                    raise

        except StopIteration:
            # Normal completion - re-raise without treating as error
            self._finalize_streaming()
            raise
        except Exception as error:
            # Handle actual streaming errors (not normal completion)
            self.add_stream_error(error)
            self._stream_completed = True
            # Don't automatically set success=False here - let _finalize_streaming determine final status
            self._finalize_streaming()
            # The error is recorded via add_stream_error; surface end-of-iteration to the
            # caller without chaining the original error onto StopIteration.
            raise StopIteration from None

    def _process_streaming_event(self, event: Dict[str, Any]) -> Optional[str]:
        """
        Process a single streaming event and return content if available.

        Args:
            event: Event from AWS EventStream

        Returns:
            Content chunk if available, None otherwise
        """
        # Import here to avoid circular imports
        from ..streaming.event_handlers import StreamEventHandler

        try:
            # Determine event type
            event_type = self._determine_event_type(event)

            # Get handler and process event
            handler = StreamEventHandler().get_event_handler(event_type)
            processed_event = handler(event[event_type.value])

            # Update response based on event type
            return self._update_from_streaming_event(event_type, processed_event)

        except Exception as error:
            self.add_stream_error(error)
            return None

    def _determine_event_type(self, event: Dict[str, Any]) -> Any:
        """
        Determine the type of streaming event.

        Args:
            event: Event dictionary from EventStream

        Returns:
            StreamingEventTypes enum value
        """
        # Import here to avoid circular imports
        from ..streaming.streaming_constants import StreamingEventTypes

        # Check for each possible event type
        for event_type in StreamingEventTypes:
            if event_type.value in event:
                return event_type

        # Unknown event type
        raise ValueError(f"Unknown streaming event type. Available keys: {list(event.keys())}")

    def _update_from_streaming_event(
        self, event_type: Any, processed_event: Dict[str, Any]
    ) -> Optional[str]:
        """
        Update StreamingResponse from processed event and return content if available.

        Args:
            event_type: Type of the event
            processed_event: Processed event data

        Returns:
            Content chunk if this event contains content, None otherwise
        """
        # Import here to avoid circular imports
        from ..streaming.streaming_constants import StreamingConstants, StreamingEventTypes

        if event_type == StreamingEventTypes.MESSAGE_START:
            # Initialize message tracking
            self.current_message_role = processed_event.get(StreamingConstants.FIELD_ROLE)

        elif event_type == StreamingEventTypes.CONTENT_BLOCK_DELTA:
            # Accumulate reasoning text / signature / redacted bytes so the final signed
            # reasoningContent block can be reconstructed for echo-back (issue #32).
            reasoning_text = processed_event.get("reasoning_text")
            if reasoning_text:
                self.reasoning_text_parts.append(reasoning_text)
            reasoning_signature = processed_event.get("reasoning_signature")
            if reasoning_signature:
                self.reasoning_signature = reasoning_signature
            reasoning_redacted = processed_event.get("reasoning_redacted_content")
            if reasoning_redacted is not None:
                self.reasoning_redacted_content = reasoning_redacted

            # Accumulate document citations so get_citations() can return typed
            # Citation references after streaming (issue #40).
            citation = processed_event.get("citation")
            if citation:
                self.citation_blocks.append(citation)

            # Add content chunk and return it for real-time display
            content = processed_event.get("content", "")
            if content and isinstance(content, str):
                self.add_content_part(content)
                return str(content)  # Return for real-time display

        elif event_type == StreamingEventTypes.MESSAGE_STOP:
            # Store stop reason and additional fields
            self.stop_reason = processed_event.get(StreamingConstants.FIELD_STOP_REASON)
            self.additional_model_response_fields = processed_event.get(
                StreamingConstants.FIELD_ADDITIONAL_MODEL_RESPONSE_FIELDS
            )

        elif event_type == StreamingEventTypes.METADATA:
            # Store metadata information
            self.usage_info = processed_event.get(StreamingConstants.FIELD_USAGE)
            self.metrics_info = processed_event.get(StreamingConstants.FIELD_METRICS)
            self.trace_info = processed_event.get(StreamingConstants.FIELD_TRACE)
            self.api_latency_ms = processed_event.get("latency_ms")

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
            self.add_stream_error(error)

        return None  # No content to return for non-content events

    def _finalize_streaming(self) -> None:
        """Finalize streaming when iteration completes."""
        self._stream_completed = True

        # Calculate total duration
        if self._start_time:
            end_time = datetime.now()
            self.total_duration_ms = (end_time - self._start_time).total_seconds() * 1000

        # Extract information from RetryingStreamIterator if available
        if self._retrying_iterator:
            # Update model/region used from successful stream
            if self._retrying_iterator.current_model:
                self.model_used = self._retrying_iterator.current_model
            if self._retrying_iterator.current_region:
                self.region_used = self._retrying_iterator.current_region

            # Get timing metrics from the iterator
            iterator_metrics = self._retrying_iterator.get_timing_metrics()
            if iterator_metrics.get("total_duration_ms"):
                self.total_duration_ms = iterator_metrics["total_duration_ms"]

        # Determine final success status based on streaming results
        if self.stream_errors:
            # Check if these are unrecovered errors
            unrecovered_errors = [
                error for error in self.stream_errors if not self._is_recovered_error(error)
            ]
            if unrecovered_errors:
                self.success = False
            else:
                # All errors were recovered, mark as successful if we have content
                self.success = bool(self.content_parts or self.stop_reason)
        elif self.content_parts or self.stop_reason:
            # If we have content or a proper stop reason, mark as successful
            self.success = True
        else:
            # No content and no explicit stop reason - this could be a problem
            # But if no errors occurred, we'll consider it successful (empty response)
            self.success = True

    def _is_recovered_error(self, error: Exception) -> bool:
        """
        Check if an error was recovered from during streaming.

        Args:
            error: Error to check

        Returns:
            True if error was recovered from
        """
        if not self._retrying_iterator:
            return False

        # Check if this error appears in the recovered exceptions
        for mid_stream_exc in self._retrying_iterator.mid_stream_exceptions:
            if mid_stream_exc.recovered and mid_stream_exc.error == error:
                return True

        return False

    def get_full_content(self) -> str:
        """
        Get the full content by concatenating all parts.

        If streaming is still in progress, this returns content accumulated so far.
        If streaming is complete, this returns the complete content.

        Returns:
            Complete content string
        """
        return "".join(self.content_parts)

    def get_reasoning(self) -> Optional[ReasoningContent]:
        """
        Get the reasoning / extended-thinking content reconstructed from the stream.

        Joins the ``reasoningContent`` text deltas and pairs them with the verification
        signature (and any redacted bytes) captured during streaming, into a typed
        :class:`~bestehorn_llmmanager.bedrock.models.reasoning_content.ReasoningContent`.
        Its :meth:`ReasoningContent.to_content_block` rebuilds a re-submittable signed
        block for multi-turn echo-back (issue #32).

        Returns:
            The :class:`ReasoningContent`, or ``None`` if the stream carried no reasoning.
        """
        if self.reasoning_text_parts:
            return ReasoningContent(
                text="".join(self.reasoning_text_parts),
                signature=self.reasoning_signature,
                redacted_content=self.reasoning_redacted_content,
            )
        if self.reasoning_redacted_content is not None:
            return ReasoningContent(redacted_content=self.reasoning_redacted_content)
        return None

    def get_citations(self) -> List[Citation]:
        """
        Get the document citations accumulated from the stream, in order.

        Each citation object captured from the ``citation`` deltas is parsed into a typed
        :class:`~bestehorn_llmmanager.bedrock.models.citation.Citation` (issue #40).

        Returns:
            The ordered list of :class:`Citation`; an empty list if the stream carried
            no citations.
        """
        return [Citation.from_citation(citation=block) for block in self.citation_blocks]

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
        current_time = datetime.now()

        # Track first token timing
        if not self._first_token_time:
            self._first_token_time = current_time

        # Always update last token timing
        self._last_token_time = current_time

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

    def get_usage(self) -> Optional[Dict[str, int]]:
        """
        Get token usage information from streaming metadata.

        This follows the same pattern as BedrockResponse.get_usage()

        Returns:
            Dictionary with usage information, None if not available
        """
        if not self.usage_info:
            return None

        try:
            # Usage info from streaming already has normalized field names from event handlers
            return {
                "input_tokens": self.usage_info.get("input_tokens", 0),
                "output_tokens": self.usage_info.get("output_tokens", 0),
                "total_tokens": self.usage_info.get("total_tokens", 0),
                "cache_read_tokens": self.usage_info.get("cache_read_tokens", 0),
                "cache_write_tokens": self.usage_info.get("cache_write_tokens", 0),
            }
        except (KeyError, TypeError, AttributeError):
            return None

    def get_input_tokens(self) -> int:
        """
        Get the number of input tokens used in the request.

        Returns:
            Number of input tokens, 0 if not available
        """
        usage = self.get_usage()
        return usage.get("input_tokens", 0) if usage else 0

    def get_output_tokens(self) -> int:
        """
        Get the number of output tokens generated in the response.

        Returns:
            Number of output tokens, 0 if not available
        """
        usage = self.get_usage()
        return usage.get("output_tokens", 0) if usage else 0

    def get_total_tokens(self) -> int:
        """
        Get the total number of tokens (input + output) used.

        Returns:
            Total number of tokens, 0 if not available
        """
        usage = self.get_usage()
        return usage.get("total_tokens", 0) if usage else 0

    def get_cache_read_tokens(self) -> int:
        """
        Get the number of tokens read from prompt cache.

        Returns:
            Number of cache read tokens, 0 if not available
        """
        usage = self.get_usage()
        return usage.get("cache_read_tokens", 0) if usage else 0

    def get_cache_write_tokens(self) -> int:
        """
        Get the number of tokens written to prompt cache.

        Returns:
            Number of cache write tokens, 0 if not available
        """
        usage = self.get_usage()
        return usage.get("cache_write_tokens", 0) if usage else 0

    def get_metrics(self) -> Optional[Dict[str, Union[float, int]]]:
        """
        Get performance metrics from streaming.

        This follows the same pattern as BedrockResponse.get_metrics()

        Returns:
            Dictionary with metrics information, None if not available
        """
        metrics = {}

        # API latency from streaming metadata
        if self.api_latency_ms is not None:
            metrics["api_latency_ms"] = self.api_latency_ms

        # Total duration from our tracking
        if self.total_duration_ms is not None:
            metrics["total_duration_ms"] = self.total_duration_ms

        # Streaming-specific timing metrics
        if self._start_time and self._first_token_time:
            time_to_first_token = (self._first_token_time - self._start_time).total_seconds() * 1000
            metrics["time_to_first_token_ms"] = time_to_first_token

        if self._start_time and self._last_token_time:
            time_to_last_token = (self._last_token_time - self._start_time).total_seconds() * 1000
            metrics["time_to_last_token_ms"] = time_to_last_token

        if self._first_token_time and self._last_token_time:
            token_generation_time = (
                self._last_token_time - self._first_token_time
            ).total_seconds() * 1000
            metrics["token_generation_duration_ms"] = token_generation_time

        # Streaming-specific metrics
        metrics["content_parts"] = int(len(self.content_parts))
        metrics["stream_position"] = int(self.stream_position)
        metrics["stream_errors"] = int(len(self.stream_errors))

        return metrics if metrics else None

    def is_streaming_complete(self) -> bool:
        """
        Check if streaming has completed.

        Returns:
            True if streaming is complete, False if still in progress
        """
        return self._stream_completed

    def get_mid_stream_exceptions(self) -> List[Dict[str, Any]]:
        """
        Get mid-stream exceptions that occurred during streaming.

        Returns:
            List of dictionaries with exception information
        """
        if not self._retrying_iterator:
            return []

        exceptions = []
        for mid_stream_exc in self._retrying_iterator.mid_stream_exceptions:
            exceptions.append(
                {
                    "error_type": type(mid_stream_exc.error).__name__,
                    "error_message": str(mid_stream_exc.error),
                    "position": mid_stream_exc.position,
                    "model": mid_stream_exc.model,
                    "region": mid_stream_exc.region,
                    "timestamp": mid_stream_exc.timestamp.isoformat(),
                    "recovered": mid_stream_exc.recovered,
                }
            )

        return exceptions

    def get_target_switches(self) -> int:
        """
        Get number of target switches that occurred during streaming.

        Returns:
            Number of model/region switches that occurred
        """
        if not self._retrying_iterator:
            return 0

        return int(self._retrying_iterator.target_switches)

    def get_recovery_info(self) -> Dict[str, Any]:
        """
        Get comprehensive recovery information from streaming.

        Returns:
            Dictionary with recovery statistics and details
        """
        if not self._retrying_iterator:
            return {
                "total_exceptions": 0,
                "recovered_exceptions": 0,
                "target_switches": 0,
                "recovery_enabled": False,
            }

        mid_stream_exceptions = self._retrying_iterator.mid_stream_exceptions
        recovered_count = len([exc for exc in mid_stream_exceptions if exc.recovered])

        return {
            "total_exceptions": len(mid_stream_exceptions),
            "recovered_exceptions": recovered_count,
            "target_switches": self._retrying_iterator.target_switches,
            "recovery_enabled": True,
            "final_model": self._retrying_iterator.current_model,
            "final_region": self._retrying_iterator.current_region,
            "partial_content_preserved": len(self._retrying_iterator.partial_content) > 0,
        }

    def __repr__(self) -> str:
        """Return string representation of the StreamingResponse."""
        if self._stream_completed:
            status = "SUCCESS" if self.success else "FAILED"
        else:
            status = "STREAMING"

        return (
            f"StreamingResponse(status={status}, parts={len(self.content_parts)}, "
            f"position={self.stream_position}, errors={int(len(self.stream_errors))})"
        )
