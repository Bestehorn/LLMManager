"""
Retry manager for LLM Manager system.
Handles retry logic, strategies, and error classification.
"""

import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from botocore.exceptions import ClientError

from ..exceptions.llm_manager_exceptions import RetryExhaustedError, ModelAccessError
from ..models.llm_manager_structures import RetryConfig, RetryStrategy, RequestAttempt, ContentFilterState
from ..models.llm_manager_constants import (
    RetryableErrorTypes,
    LLMManagerLogMessages,
    LLMManagerErrorMessages
)
from ..models.access_method import ModelAccessMethod, ModelAccessInfo
from ..filters.content_filter import ContentFilter


class RetryManager:
    """
    Manages retry logic and strategies for LLM Manager operations.
    
    Implements different retry strategies, error classification, and
    handles graceful degradation of features when needed.
    """
    
    def __init__(self, retry_config: RetryConfig) -> None:
        """
        Initialize the retry manager.
        
        Args:
            retry_config: Configuration for retry behavior
        """
        self._logger = logging.getLogger(__name__)
        self._config = retry_config
        
        # Initialize content filter for feature restoration
        self._content_filter = ContentFilter()
        
        # Build combined retryable error types
        self._retryable_errors = (
            RetryableErrorTypes.THROTTLING_ERRORS +
            RetryableErrorTypes.SERVICE_ERRORS +
            RetryableErrorTypes.NETWORK_ERRORS +
            self._config.retryable_errors
        )
        
        # Access errors are conditionally retryable (with different region/model)
        self._access_errors = RetryableErrorTypes.ACCESS_ERRORS
        
        # Non-retryable errors
        self._non_retryable_errors = RetryableErrorTypes.NON_RETRYABLE_ERRORS
    
    def is_retryable_error(self, error: Exception, attempt_count: int = 1) -> bool:
        """
        Determine if an error is retryable.
        
        Args:
            error: The error to evaluate
            attempt_count: Current attempt count
            
        Returns:
            True if the error should be retried
        """
        if attempt_count > self._config.max_retries:
            return False
        
        error_name = type(error).__name__
        error_message = str(error)
        
        # Check for AWS ClientError with specific error codes
        if isinstance(error, ClientError):
            error_code = error.response.get('Error', {}).get('Code', '')
            
            # Always retryable errors
            if error_code in self._retryable_errors:
                return True
            
            # Non-retryable errors
            if error_code in self._non_retryable_errors:
                return False
            
            # Access errors are retryable with different region/model
            if error_code in self._access_errors:
                return True
        
        # Check error class names
        if error_name in self._retryable_errors:
            return True
        
        if error_name in self._non_retryable_errors:
            return False
        
        # Check error message for known patterns
        retryable_patterns = [
            'timeout',
            'connection',
            'throttl',
            'rate limit',
            'too many requests',
            'service unavailable',
            'internal error'
        ]
        
        error_message_lower = error_message.lower()
        for pattern in retryable_patterns:
            if pattern in error_message_lower:
                return True
        
        # Default to non-retryable for unknown errors
        return False
    
    def should_retry_with_different_target(self, error: Exception) -> bool:
        """
        Determine if we should try a different region/model for this error.
        
        Args:
            error: The error to evaluate
            
        Returns:
            True if we should try different region/model
        """
        if isinstance(error, ClientError):
            error_code = error.response.get('Error', {}).get('Code', '')
            
            # These errors suggest trying different region/model might help
            access_related_errors = [
                'AccessDeniedException',
                'UnauthorizedException',
                'ValidationException',
                'ModelNotReadyException',
                'ResourceNotFoundException',
                'ThrottlingException',
                'ServiceQuotaExceededException'
            ]
            
            return error_code in access_related_errors
        
        return False
    
    def should_disable_feature_and_retry(self, error: Exception) -> Tuple[bool, Optional[str]]:
        """
        Determine if we should disable a feature and retry.
        
        Args:
            error: The error to evaluate
            
        Returns:
            Tuple of (should_retry, feature_to_disable)
        """
        if not self._config.enable_feature_fallback:
            return False, None
        
        error_message = str(error).lower()
        
        # Map error patterns to features that might need to be disabled
        feature_error_patterns = {
            'guardrails': ['guardrail', 'content filter'],
            'tool_use': ['tool', 'function'],
            'prompt_caching': ['cache', 'caching'],
            'streaming': ['stream'],
            'document_processing': ['document'],
            'image_processing': ['image'],
            'video_processing': ['video']
        }
        
        for feature, patterns in feature_error_patterns.items():
            for pattern in patterns:
                if pattern in error_message:
                    return True, feature
        
        return False, None
    
    def calculate_retry_delay(self, attempt_number: int) -> float:
        """
        Calculate delay before next retry attempt.
        
        Args:
            attempt_number: Current attempt number (1-based)
            
        Returns:
            Delay in seconds
        """
        if attempt_number <= 1:
            return self._config.retry_delay
        
        # Exponential backoff
        delay = self._config.retry_delay * (self._config.backoff_multiplier ** (attempt_number - 1))
        
        # Cap at maximum delay
        return min(delay, self._config.max_retry_delay)
    
    def generate_retry_targets(
        self,
        models: List[str],
        regions: List[str],
        unified_model_manager,
        failed_combinations: Optional[List[Tuple[str, str]]] = None
    ) -> List[Tuple[str, str, ModelAccessInfo]]:
        """
        Generate list of model/region combinations to try based on retry strategy.
        
        Args:
            models: List of model names/IDs
            regions: List of regions
            unified_model_manager: UnifiedModelManager instance for access info
            failed_combinations: Previously failed (model, region) combinations to skip
            
        Returns:
            List of (model, region, access_info) tuples in retry order
        """
        failed_combinations = failed_combinations or []
        retry_targets = []
        
        if self._config.retry_strategy == RetryStrategy.REGION_FIRST:
            # Try all regions for each model before moving to next model
            for model in models:
                for region in regions:
                    if (model, region) in failed_combinations:
                        continue
                    
                    try:
                        access_info = unified_model_manager.get_model_access_info(
                            model_name=model,
                            region=region
                        )
                        if access_info:
                            retry_targets.append((model, region, access_info))
                    except Exception as e:
                        self._logger.debug(f"Could not get access info for {model} in {region}: {e}")
                        continue
        
        elif self._config.retry_strategy == RetryStrategy.MODEL_FIRST:
            # Try all models for each region before moving to next region
            for region in regions:
                for model in models:
                    if (model, region) in failed_combinations:
                        continue
                    
                    try:
                        access_info = unified_model_manager.get_model_access_info(
                            model_name=model,
                            region=region
                        )
                        if access_info:
                            retry_targets.append((model, region, access_info))
                    except Exception as e:
                        self._logger.debug(f"Could not get access info for {model} in {region}: {e}")
                        continue
        
        return retry_targets
    
    def execute_with_retry(
        self,
        operation: Callable[..., Any],
        operation_args: Dict[str, Any],
        retry_targets: List[Tuple[str, str, ModelAccessInfo]],
        disabled_features: Optional[List[str]] = None
    ) -> Tuple[Any, List[RequestAttempt], List[str]]:
        """
        Execute an operation with retry logic and content filtering.
        
        This method implements the fix for the image analysis issue by properly
        managing content filtering and restoration across retry attempts.
        
        Args:
            operation: Function to execute (e.g., bedrock client converse call)
            operation_args: Arguments to pass to the operation
            retry_targets: List of (model, region, access_info) to try
            disabled_features: List of features to disable for compatibility
            
        Returns:
            Tuple of (result, attempts_made, warnings)
            
        Raises:
            RetryExhaustedError: If all retry attempts fail
        """
        attempts = []
        warnings = []
        disabled_features = disabled_features or []
        
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
                start_time=attempt_start
            )
            
            try:
                # Log attempt
                if attempt_num == 1:
                    self._logger.info(
                        LLMManagerLogMessages.REQUEST_STARTED.format(
                            model=model,
                            region=region
                        )
                    )
                else:
                    self._logger.info(
                        LLMManagerLogMessages.REQUEST_RETRY.format(
                            attempt=attempt_num,
                            max_attempts=len(retry_targets),
                            model=model,
                            region=region
                        )
                    )
                
                # Check if we should restore features for this model
                should_restore, features_to_restore = self._content_filter.should_restore_features_for_model(
                    filter_state=filter_state,
                    model_name=model
                )
                
                if should_restore:
                    self._logger.info(
                        f"Restoring features for model {model}: {', '.join(features_to_restore)}"
                    )
                    # Restore features and update warnings
                    for feature in features_to_restore:
                        if feature in disabled_features:
                            disabled_features.remove(feature)
                            warnings.append(f"Restored {feature} for model {model}")
                
                # Prepare operation arguments with current target
                current_args = operation_args.copy()
                
                # Set model ID based on access method
                if access_info.access_method in [ModelAccessMethod.DIRECT, ModelAccessMethod.BOTH]:
                    # Prefer direct access
                    current_args['model_id'] = access_info.model_id
                    if access_info.access_method == ModelAccessMethod.BOTH:
                        self._logger.debug(f"Using direct access for {model}")
                elif access_info.access_method == ModelAccessMethod.CRIS_ONLY:
                    # Use CRIS profile
                    current_args['model_id'] = access_info.inference_profile_id
                    self._logger.debug(f"Using CRIS access for {model}")
                
                # Apply content filtering based on current disabled features
                if disabled_features and self._config.enable_feature_fallback:
                    current_args = self._content_filter.apply_filters(
                        filter_state=filter_state,
                        disabled_features=set(disabled_features)
                    )
                    # Re-add model ID which might have been overwritten
                    if access_info.access_method in [ModelAccessMethod.DIRECT, ModelAccessMethod.BOTH]:
                        current_args['model_id'] = access_info.model_id
                    else:
                        current_args['model_id'] = access_info.inference_profile_id
                
                # Execute the operation
                result = operation(**current_args)
                
                # Success!
                attempt.end_time = datetime.now()
                attempt.success = True
                attempts.append(attempt)
                
                self._logger.info(
                    LLMManagerLogMessages.REQUEST_SUCCEEDED.format(
                        model=model,
                        region=region,
                        attempts=attempt_num
                    )
                )
                
                return result, attempts, warnings
                
            except Exception as error:
                attempt.end_time = datetime.now()
                attempt.error = error
                attempt.success = False
                attempts.append(attempt)
                
                self._logger.warning(
                    LLMManagerLogMessages.REQUEST_FAILED.format(
                        model=model,
                        region=region,
                        error=str(error)
                    )
                )
                
                # Check if we should try feature fallback
                should_fallback, feature_to_disable = self.should_disable_feature_and_retry(error)
                if should_fallback and feature_to_disable and feature_to_disable not in disabled_features:
                    self._logger.warning(
                        LLMManagerLogMessages.FEATURE_DISABLED.format(
                            feature=feature_to_disable,
                            model=model
                        )
                    )
                    
                    disabled_features.append(feature_to_disable)
                    warnings.append(f"Disabled {feature_to_disable} due to compatibility issues")
                    
                    # Retry with the same target but disabled feature
                    try:
                        fallback_args = self._content_filter.apply_filters(
                            filter_state=filter_state,
                            disabled_features=set(disabled_features)
                        )
                        # Re-add model ID
                        if access_info.access_method in [ModelAccessMethod.DIRECT, ModelAccessMethod.BOTH]:
                            fallback_args['model_id'] = access_info.model_id
                        else:
                            fallback_args['model_id'] = access_info.inference_profile_id
                        
                        result = operation(**fallback_args)
                        
                        # Success with fallback!
                        attempt.success = True
                        self._logger.info(
                            LLMManagerLogMessages.REQUEST_SUCCEEDED.format(
                                model=model,
                                region=region,
                                attempts=attempt_num
                            )
                        )
                        
                        return result, attempts, warnings
                        
                    except Exception as fallback_error:
                        # Fallback also failed, continue to next target
                        attempt.error = fallback_error
                        self._logger.debug(f"Feature fallback also failed: {fallback_error}")
                
                # If not the last attempt and error is retryable, add delay
                if attempt_num < len(retry_targets) and self.is_retryable_error(error, attempt_num):
                    delay = self.calculate_retry_delay(attempt_num)
                    if delay > 0:
                        self._logger.debug(f"Waiting {delay}s before retry")
                        time.sleep(delay)
                
                # Continue to next target
                continue
        
        # All attempts failed
        last_errors = [attempt.error for attempt in attempts if attempt.error]
        models_tried = list(set(attempt.model_id for attempt in attempts))
        regions_tried = list(set(attempt.region for attempt in attempts))
        
        raise RetryExhaustedError(
            message=LLMManagerErrorMessages.ALL_RETRIES_FAILED.format(
                model_count=len(models_tried),
                region_count=len(regions_tried)
            ),
            attempts_made=len(attempts),
            last_errors=last_errors,
            models_tried=models_tried,
            regions_tried=regions_tried
        )
    
    def _remove_disabled_features(self, request_args: Dict[str, Any], disabled_features: List[str]) -> Dict[str, Any]:
        """
        Remove disabled features from request arguments.
        
        Args:
            request_args: Original request arguments
            disabled_features: List of features to disable
            
        Returns:
            Modified request arguments with disabled features removed
        """
        modified_args = request_args.copy()
        
        for feature in disabled_features:
            if feature == 'guardrails' and 'guardrailConfig' in modified_args:
                del modified_args['guardrailConfig']
            elif feature == 'tool_use' and 'toolConfig' in modified_args:
                del modified_args['toolConfig']
            elif feature == 'streaming' and 'stream' in modified_args:
                modified_args['stream'] = False
            elif feature in ['document_processing', 'image_processing', 'video_processing']:
                # Remove content blocks of these types from messages
                if 'messages' in modified_args:
                    modified_args['messages'] = self._filter_content_blocks(
                        modified_args['messages'], 
                        feature
                    )
        
        return modified_args
    
    def _filter_content_blocks(self, messages: List[Dict], disabled_feature: str) -> List[Dict]:
        """
        Filter out content blocks for disabled features.
        
        Args:
            messages: List of message dictionaries
            disabled_feature: Feature to filter out
            
        Returns:
            Filtered messages
        """
        feature_to_block_type = {
            'document_processing': 'document',
            'image_processing': 'image',
            'video_processing': 'video'
        }
        
        block_type = feature_to_block_type.get(disabled_feature)
        if not block_type:
            return messages
        
        filtered_messages = []
        for message in messages:
            if 'content' in message:
                filtered_content = []
                for block in message['content']:
                    if not isinstance(block, dict) or block_type not in block:
                        filtered_content.append(block)
                
                # Only include message if it has remaining content
                if filtered_content:
                    filtered_message = message.copy()
                    filtered_message['content'] = filtered_content
                    filtered_messages.append(filtered_message)
            else:
                filtered_messages.append(message)
        
        return filtered_messages
    
    def get_retry_stats(self) -> Dict[str, Any]:
        """
        Get statistics about retry configuration.
        
        Returns:
            Dictionary with retry statistics
        """
        return {
            "max_retries": self._config.max_retries,
            "retry_strategy": self._config.retry_strategy.value,
            "enable_feature_fallback": self._config.enable_feature_fallback,
            "retryable_error_count": len(self._retryable_errors),
            "access_error_count": len(self._access_errors),
            "non_retryable_error_count": len(self._non_retryable_errors)
        }
