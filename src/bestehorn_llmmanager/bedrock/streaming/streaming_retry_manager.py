"""
Streaming retry manager for LLM Manager system.
Extends RetryManager with streaming-specific retry logic and recovery patterns.
"""

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..exceptions.llm_manager_exceptions import RetryExhaustedError
from ..models.access_method import ModelAccessInfo
from ..models.bedrock_response import StreamingResponse
from ..models.llm_manager_structures import RequestAttempt
from ..retry.retry_manager import RetryManager
from .stream_processor import StreamProcessor
from .streaming_constants import (
    StreamingConstants,
    StreamingErrorMessages,
    StreamingEventTypes,
    StreamingLogMessages,
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
        original_error: Optional[Exception] = None
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
        Execute streaming operation with recovery logic.
        
        This method implements intelligent stream restart with context preservation
        when streams are interrupted mid-generation.
        
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
        attempts = []
        warnings: List[str] = []
        disabled_features = disabled_features or []
        partial_content = ""
        
        # Create filter state to track content filtering
        filter_state = self._content_filter.create_filter_state(operation_args)
        
        for attempt_num, (model, region, access_info) in enumerate(retry_targets, 1):
            attempt_start = datetime.now()
            
            # Create attempt record
            attempt = RequestAttempt(
                model_id=model,
                region=region,
                access_method=access_info.access_method.value,
                attempt_number=attempt_num,
                start_time=attempt_start,
            )
            
            try:
                # Log attempt
                if attempt_num == 1:
                    self._logger.info(
                        StreamingLogMessages.STREAM_STARTED.format(model=model, region=region)
                    )
                else:
                    self._logger.info(
                        StreamingLogMessages.STREAM_RETRY_ATTEMPT.format(
                            attempt=attempt_num,
                            max_attempts=len(retry_targets),
                            model=model
                        )
                    )
                
                # Prepare operation arguments with recovery context if needed
                current_args = self._prepare_streaming_args(
                    operation_args=operation_args,
                    access_info=access_info,
                    model=model,
                    disabled_features=disabled_features,
                    filter_state=filter_state,
                    partial_content=partial_content
                )
                
                # Execute streaming operation
                streaming_response = self._execute_streaming_operation(
                    operation=operation,
                    operation_args=current_args,
                    model=model,
                    region=region,
                    access_info=access_info,
                    attempt=attempt
                )
                
                # Success!
                attempt.end_time = datetime.now()
                attempt.success = True
                attempts.append(attempt)
                
                self._logger.info(
                    StreamingLogMessages.STREAM_COMPLETED.format(
                        model=model, region=region
                    )
                )
                
                return streaming_response, attempts, warnings
                
            except StreamInterruptedException as stream_error:
                # Handle stream interruption
                attempt.end_time = datetime.now()
                attempt.error = stream_error
                attempt.success = False
                attempts.append(attempt)
                
                # Preserve partial content for next attempt
                partial_content = stream_error.partial_content
                
                self._logger.warning(
                    StreamingLogMessages.STREAM_INTERRUPTED.format(
                        model=model,
                        region=region,
                        error=str(stream_error)
                    )
                )
                
                # Continue to next target with preserved content
                continue
                
            except Exception as error:
                # Handle regular operation errors (same as parent class)
                attempt.end_time = datetime.now()
                attempt.error = error
                attempt.success = False
                attempts.append(attempt)
                
                self._logger.warning(
                    f"Streaming request failed for model '{model}' in region '{region}': {error}"
                )
                
                # Check for feature fallback opportunities
                should_fallback, feature_to_disable = self.should_disable_feature_and_retry(error)
                if (
                    should_fallback
                    and feature_to_disable
                    and feature_to_disable not in disabled_features
                ):
                    disabled_features.append(feature_to_disable)
                    warnings.append(f"Disabled {feature_to_disable} for streaming compatibility")
                    
                    # Retry with same target but disabled feature
                    try:
                        fallback_args = self._prepare_streaming_args(
                            operation_args=operation_args,
                            access_info=access_info,
                            model=model,
                            disabled_features=disabled_features,
                            filter_state=filter_state,
                            partial_content=partial_content
                        )
                        
                        fallback_response = self._execute_streaming_operation(
                            operation=operation,
                            operation_args=fallback_args,
                            model=model,
                            region=region,
                            access_info=access_info,
                            attempt=attempt
                        )
                        
                        # Success with fallback!
                        attempt.success = True
                        return fallback_response, attempts, warnings
                        
                    except Exception as fallback_error:
                        # Fallback also failed, continue to next target
                        attempt.error = fallback_error
                        self._logger.debug(f"Streaming feature fallback also failed: {fallback_error}")
                
                # Continue to next target
                continue
        
        # All attempts failed
        last_errors = [attempt.error for attempt in attempts if attempt.error]
        models_tried = list(set(attempt.model_id for attempt in attempts))
        regions_tried = list(set(attempt.region for attempt in attempts))
        
        raise RetryExhaustedError(
            message=StreamingErrorMessages.STREAM_RETRY_EXHAUSTED.format(
                models=models_tried
            ),
            attempts_made=len(attempts),
            last_errors=last_errors,
            models_tried=models_tried,
            regions_tried=regions_tried,
        )

    def _execute_streaming_operation(
        self,
        operation: Callable[..., Any],
        operation_args: Dict[str, Any],
        model: str,
        region: str,
        access_info: ModelAccessInfo,
        attempt: RequestAttempt
    ) -> StreamingResponse:
        """
        Execute a single streaming operation with interruption detection.
        
        Args:
            operation: The streaming operation to execute
            operation_args: Arguments for the operation
            model: Model being used
            region: Region being used
            access_info: Access information
            attempt: Request attempt tracking
            
        Returns:
            StreamingResponse with processed streaming data
            
        Raises:
            StreamInterruptedException: If stream is interrupted
            Exception: For other errors
        """
        try:
            # Execute the streaming operation (returns AWS EventStream)
            aws_response = operation(region=region, **operation_args)
            
            # Extract EventStream from response
            event_stream = aws_response.get(StreamingConstants.FIELD_STREAM)
            if not event_stream:
                raise ValueError(StreamingErrorMessages.NO_STREAM_DATA)
            
            # Create StreamingResponse and process events
            streaming_response = StreamingResponse(success=False)
            
            # Process the stream with interruption detection
            try:
                processed_response = self._stream_processor.process_event_stream(
                    event_stream=event_stream,
                    response=streaming_response,
                    model_used=model,
                    region_used=region,
                    access_method_used=access_info.access_method.value,
                    attempt=attempt
                )
                
                return processed_response
                
            except Exception as stream_error:
                # Check if this is a recoverable stream interruption
                if self._is_stream_interruption(error=stream_error):
                    partial_content = self._stream_processor.extract_partial_content(
                        response=streaming_response
                    )
                    
                    raise StreamInterruptedException(
                        message=StreamingErrorMessages.STREAM_INTERRUPTED_ERROR,
                        partial_content=partial_content,
                        interruption_point=streaming_response.stream_position,
                        original_error=stream_error
                    )
                else:
                    # Not a recoverable interruption, re-raise
                    raise
                    
        except StreamInterruptedException:
            # Re-raise stream interruptions
            raise
        except Exception as error:
            # Handle other errors
            self._logger.error(f"Streaming operation failed: {error}")
            raise

    def _prepare_streaming_args(
        self,
        operation_args: Dict[str, Any],
        access_info: ModelAccessInfo,
        model: str,
        disabled_features: List[str],
        filter_state: Any,
        partial_content: str = ""
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
            filter_state=filter_state
        )
        
        # Add recovery context if we have partial content
        if partial_content:
            original_messages = current_args.get("messages", [])
            recovery_messages = self._stream_processor.build_recovery_context(
                original_messages=original_messages,
                partial_content=partial_content,
                failure_context="Stream was interrupted"
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
            "read timeout"
        ]
        
        for pattern in interruption_patterns:
            if pattern in error_message:
                return True
                
        # Check for specific AWS streaming errors
        if hasattr(error, 'response'):
            error_response = getattr(error, 'response', None)
            if error_response:
                error_code = error_response.get("Error", {}).get("Code", "")
                streaming_error_codes = [
                    "ModelStreamErrorException",
                    "ThrottlingException", 
                    "ServiceUnavailableException",
                    "InternalServerException"
                ]
                if error_code in streaming_error_codes:
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
