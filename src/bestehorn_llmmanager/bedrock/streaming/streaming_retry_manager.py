"""
Streaming retry manager for LLM Manager system.
Extends RetryManager with streaming-specific retry logic and recovery patterns.
"""

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..exceptions.llm_manager_exceptions import RetryExhaustedError
from ..models.access_method import ModelAccessInfo
from ..models.bedrock_response import StreamingResponse
from ..models.llm_manager_structures import RequestAttempt
from ..retry.retry_manager import RetryManager
from .retrying_stream_iterator import RetryingStreamIterator
from .stream_processor import StreamProcessor
from .streaming_constants import (
    StreamingConstants,
    StreamingErrorMessages,
)


class StreamInterruptedException(Exception):
    """
    Exception raised when a stream is interrupted and needs recovery.

    Attributes:
        partial_content: Content received before interruption
        interruption_point: Position where stream was interrupted
        original_error: The original error that caused interruption
    """

    def __init__(
        self,
        message: str,
        partial_content: str = "",
        interruption_point: int = 0,
        original_error: Optional[Exception] = None,
    ) -> None:
        """
        Initialize stream interruption exception.

        Args:
            message: Error message
            partial_content: Content received before interruption
            interruption_point: Position where stream was interrupted
            original_error: The original error that caused interruption
        """
        super().__init__(message)
        self.partial_content = partial_content
        self.interruption_point = interruption_point
        self.original_error = original_error


class StreamingRetryManager(RetryManager):
    """
    Extends RetryManager with streaming-specific retry logic.

    Provides stream interruption detection, recovery context building,
    and intelligent retry with partial content preservation.
    """

    def __init__(self, retry_config: Any) -> None:
        """
        Initialize the streaming retry manager.

        Args:
            retry_config: Configuration for retry behavior
        """
        super().__init__(retry_config=retry_config)
        self._stream_processor = StreamProcessor()

    def execute_streaming_with_recovery(
        self,
        operation: Callable[..., Any],
        operation_args: Dict[str, Any],
        retry_targets: List[Tuple[str, str, ModelAccessInfo]],
        disabled_features: Optional[List[str]] = None,
    ) -> Tuple[StreamingResponse, List[RequestAttempt], List[str]]:
        """
        Execute streaming operation with recovery logic using RetryingStreamIterator.

        This method creates a RetryingStreamIterator that provides seamless
        mid-stream error recovery with automatic target switching and partial
        content preservation.

        Args:
            operation: Function to execute (bedrock client converse_stream call)
            operation_args: Arguments to pass to the operation
            retry_targets: List of (model, region, access_info) to try
            disabled_features: List of features to disable for compatibility

        Returns:
            Tuple of (StreamingResponse, attempts_made, warnings)

        Raises:
            RetryExhaustedError: If all retry attempts fail
        """
        warnings: List[str] = []
        disabled_features = disabled_features or []

        if not retry_targets:
            raise RetryExhaustedError(
                message="No retry targets available for streaming",
                attempts_made=0,
                last_errors=[],
                models_tried=[],
                regions_tried=[],
            )

        try:
            # Create RetryingStreamIterator for mid-stream error recovery
            retrying_iterator = RetryingStreamIterator(
                retry_manager=self,
                retry_targets=retry_targets,
                operation=operation,
                operation_args=operation_args,
                disabled_features=disabled_features,
            )

            # Create StreamingResponse with the retrying iterator
            streaming_response = StreamingResponse(True)

            # Set up the retrying iterator for the streaming response
            streaming_response._set_retrying_iterator(retrying_iterator)

            # Create minimal attempt record for successful setup
            setup_attempt = RequestAttempt(
                model_id="multiple",  # Will be updated when iterator starts
                region="multiple",  # Will be updated when iterator starts
                access_method="mixed",  # Will be updated when iterator starts
                attempt_number=1,
                start_time=datetime.now(),
                end_time=datetime.now(),
                success=True,
            )

            self._logger.info("Streaming with recovery initialized successfully")

            return streaming_response, [setup_attempt], warnings

        except Exception as error:
            # Handle initialization errors
            self._logger.error(f"Failed to initialize streaming with recovery: {error}")

            # Create failed attempt
            RequestAttempt(
                model_id="initialization",
                region="initialization",
                access_method="initialization",
                attempt_number=1,
                start_time=datetime.now(),
                end_time=datetime.now(),
                success=False,
                error=error,
            )

            raise RetryExhaustedError(
                message=f"Failed to initialize streaming with recovery: {str(error)}",
                attempts_made=1,
                last_errors=[error],
                models_tried=[],
                regions_tried=[],
            )

    def _execute_streaming_operation(
        self,
        operation: Callable[..., Any],
        operation_args: Dict[str, Any],
        model: str,
        region: str,
        access_info: ModelAccessInfo,
        attempt: RequestAttempt,
    ) -> StreamingResponse:
        """
        Execute a single streaming operation and set up EventStream for lazy processing.

        Args:
            operation: The streaming operation to execute
            operation_args: Arguments for the operation
            model: Model being used
            region: Region being used
            access_info: Access information
            attempt: Request attempt tracking

        Returns:
            StreamingResponse with EventStream set up for iterator protocol

        Raises:
            StreamInterruptedException: If stream setup fails
            Exception: For other errors
        """
        try:
            # Execute the streaming operation (returns AWS EventStream)
            aws_response = operation(region=region, **operation_args)

            # Extract EventStream from response
            event_stream = aws_response.get(StreamingConstants.FIELD_STREAM)
            if not event_stream:
                raise ValueError(StreamingErrorMessages.NO_STREAM_DATA)

            # Create StreamingResponse with metadata - initialize as successful, will be set to false only on actual errors
            streaming_response = StreamingResponse(True)
            streaming_response.model_used = model
            streaming_response.region_used = region
            streaming_response.access_method_used = access_info.access_method.value
            streaming_response.request_attempt = attempt

            # Set up the EventStream for lazy processing through iterator protocol
            streaming_response._set_event_stream(event_stream)

            return streaming_response

        except Exception as error:
            # Handle setup errors
            self._logger.error(f"Streaming operation setup failed: {error}")
            raise

    def _prepare_streaming_args(
        self,
        operation_args: Dict[str, Any],
        access_info: ModelAccessInfo,
        model: str,
        disabled_features: List[str],
        filter_state: Any,
        partial_content: str = "",
    ) -> Dict[str, Any]:
        """
        Prepare streaming operation arguments with recovery context.

        Args:
            operation_args: Original operation arguments
            access_info: Access information for the model
            model: Model name
            disabled_features: Features to disable
            filter_state: Content filter state
            partial_content: Partial content for recovery

        Returns:
            Prepared operation arguments
        """
        # Use parent class preparation logic
        current_args = self._prepare_operation_args(
            operation_args=operation_args,
            access_info=access_info,
            model=model,
            disabled_features=disabled_features,
            filter_state=filter_state,
        )

        # Add recovery context if we have partial content
        if partial_content:
            original_messages = current_args.get("messages", [])
            recovery_messages = self._stream_processor.build_recovery_context(
                original_messages=original_messages,
                partial_content=partial_content,
                failure_context="Stream was interrupted",
            )
            current_args["messages"] = recovery_messages

        return current_args

    def _is_stream_interruption(self, error: Exception) -> bool:
        """
        Determine if an error represents a recoverable stream interruption.

        Args:
            error: The error to evaluate

        Returns:
            True if this is a recoverable stream interruption
        """
        error_message = str(error).lower()

        # Stream interruption patterns
        interruption_patterns = [
            "connection",
            "timeout",
            "interrupted",
            "broken pipe",
            "connection reset",
            "network",
            "stream",
            "socket",
            "eof",
            "read timeout",
        ]

        for pattern in interruption_patterns:
            if pattern in error_message:
                return True

        # Check for AWS throttling and other retryable exceptions in error message
        aws_retryable_patterns = [
            "throttlingexception",
            "throttled",
            "too many requests",
            "service unavailable",
            "internal server error",
            "modelstreamerrorexception",
            "validationexception",
        ]

        for pattern in aws_retryable_patterns:
            if pattern in error_message:
                return True

        # Check for specific AWS streaming errors in exception structure
        if hasattr(error, "response"):
            error_response = getattr(error, "response", None)
            if error_response:
                error_code = error_response.get("Error", {}).get("Code", "")
                streaming_error_codes = [
                    "ModelStreamErrorException",
                    "ThrottlingException",
                    "ServiceUnavailableException",
                    "InternalServerException",
                    "ValidationException",
                ]
                if error_code in streaming_error_codes:
                    return True

        # Check for boto3 exception types
        if hasattr(error, "__class__"):
            error_class_name = error.__class__.__name__.lower()
            if any(
                exc_type in error_class_name
                for exc_type in ["throttling", "serviceexception", "clienterror", "botocore"]
            ):
                return True

        return False

    def is_streaming_retryable_error(self, error: Exception, attempt_count: int = 1) -> bool:
        """
        Determine if a streaming error is retryable.

        Extends parent class retry logic with streaming-specific patterns.

        Args:
            error: The error to evaluate
            attempt_count: Current attempt count

        Returns:
            True if the error should be retried for streaming
        """
        # Use parent class logic first
        parent_retryable = self.is_retryable_error(error=error, attempt_count=attempt_count)
        if parent_retryable:
            return True

        # Additional streaming-specific retryable errors
        if isinstance(error, StreamInterruptedException):
            return True

        return self._is_stream_interruption(error=error)
