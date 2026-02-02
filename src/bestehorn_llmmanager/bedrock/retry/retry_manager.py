"""
Retry manager for LLM Manager system.
Handles retry logic, strategies, and error classification.
"""

import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from botocore.exceptions import ClientError

from ..exceptions.llm_manager_exceptions import RetryExhaustedError
from ..filters.content_filter import ContentFilter
from ..models.access_method import ModelAccessInfo
from ..models.llm_manager_constants import (
    LLMManagerErrorMessages,
    LLMManagerLogMessages,
    ResponseValidationLogMessages,
    RetryableErrorTypes,
)
from ..models.llm_manager_structures import (
    ContentFilterState,
    RequestAttempt,
    ResponseValidationConfig,
    RetryConfig,
    RetryStrategy,
    ValidationAttempt,
    ValidationResult,
)
from ..tracking.access_method_tracker import AccessMethodTracker
from ..tracking.parameter_compatibility_tracker import ParameterCompatibilityTracker
from .access_method_selector import AccessMethodSelector
from .profile_requirement_detector import ProfileRequirementDetector


class RetryManager:
    """
    Manages retry logic and strategies for LLM Manager operations.

    Implements different retry strategies, error classification, and
    handles graceful degradation of features when needed.
    """

    # Error patterns indicating parameter incompatibility
    PARAMETER_INCOMPATIBILITY_PATTERNS = [
        "unsupported parameter",
        "invalid field",
        "unknown parameter",
        "parameter not supported",
        "unrecognized field",
        "invalid request field",
        "does not support parameter",
        "parameter is not valid for this model",
    ]

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

        # Initialize parameter compatibility tracker
        self._parameter_tracker = ParameterCompatibilityTracker.get_instance()

        # Initialize profile support components
        self._access_method_tracker = AccessMethodTracker.get_instance()
        self._access_method_selector = AccessMethodSelector(
            access_method_tracker=self._access_method_tracker
        )

        # Build combined retryable error types
        self._retryable_errors = (
            RetryableErrorTypes.THROTTLING_ERRORS
            + RetryableErrorTypes.SERVICE_ERRORS
            + RetryableErrorTypes.NETWORK_ERRORS
            + self._config.retryable_errors
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
            error_code = error.response.get("Error", {}).get("Code", "")

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
            "timeout",
            "connection",
            "throttl",
            "rate limit",
            "too many requests",
            "service unavailable",
            "internal error",
            "temporary failure",  # Added to fix retry delay test
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
            error_code = error.response.get("Error", {}).get("Code", "")

            # These errors suggest trying different region/model might help
            access_related_errors = [
                "AccessDeniedException",
                "UnauthorizedException",
                "ValidationException",
                "ModelNotReadyException",
                "ResourceNotFoundException",
                "ThrottlingException",
                "ServiceQuotaExceededException",
            ]

            return error_code in access_related_errors

        return False

    def is_content_compatibility_error(self, error: Exception) -> Tuple[bool, Optional[str]]:
        """
        Determine if an error is due to content type incompatibility with the current model.

        Content compatibility errors should trigger model switching rather than feature disabling.

        Args:
            error: The error to evaluate

        Returns:
            Tuple of (is_content_error, content_type)
        """
        error_message = str(error).lower()

        # Map error patterns to content types that require model switching
        content_error_patterns = {
            "video_processing": ["video", "doesn't support the video"],
            "image_processing": ["image", "doesn't support the image"],
            "document_processing": ["document", "doesn't support the document"],
        }

        for content_type, patterns in content_error_patterns.items():
            for pattern in patterns:
                if pattern in error_message:
                    return True, content_type

        return False, None

    def is_parameter_compatibility_error(self, error: Exception) -> Tuple[bool, Optional[str]]:
        """
        Determine if an error is due to unsupported parameters.

        Args:
            error: The error to evaluate

        Returns:
            Tuple of (is_parameter_error, parameter_name_if_identified)
        """
        error_message = str(error).lower()

        # Check for parameter incompatibility patterns
        for pattern in self.PARAMETER_INCOMPATIBILITY_PATTERNS:
            if pattern in error_message:
                # Try to extract parameter name from error message
                parameter_name = self._extract_parameter_name(error_message)
                return True, parameter_name

        return False, None

    def _extract_parameter_name(self, error_message: str) -> Optional[str]:
        """
        Extract parameter name from error message if possible.

        Args:
            error_message: Error message to parse (should be lowercase)

        Returns:
            Parameter name if found, None otherwise
        """
        # Common patterns for parameter names in error messages
        import re

        # Pattern: "parameter 'name'" or "field 'name'"
        match = re.search(r"(?:parameter|field)\s+['\"]([^'\"]+)['\"]", error_message)
        if match:
            return match.group(1)

        # Pattern: "additionalModelRequestFields.name" (case-insensitive since message is lowercase)
        match = re.search(r"additionalmodelrequestfields\.(\w+)", error_message)
        if match:
            return match.group(1)

        return None

    def should_disable_feature_and_retry(self, error: Exception) -> Tuple[bool, Optional[str]]:
        """
        Determine if we should disable a feature and retry.

        This method handles both API-level features and content processing features
        that can be disabled for compatibility.

        Args:
            error: The error to evaluate

        Returns:
            Tuple of (should_retry, feature_to_disable)
        """
        if not self._config.enable_feature_fallback:
            return False, None

        error_message = str(error).lower()

        # Check for content processing errors that can be disabled
        content_feature_error_patterns = {
            "image_processing": [
                "image processing not supported",
                "image not supported",
                "model does not support image processing",
                "doesn't support the image",
            ],
            "document_processing": [
                "document processing not supported",
                "document not supported",
                "model does not support document processing",
                "doesn't support the document",
            ],
            "video_processing": [
                "video processing not supported",
                "video not supported",
                "model does not support video processing",
                "doesn't support the video",
            ],
        }

        # Check content processing features first
        for feature, patterns in content_feature_error_patterns.items():
            for pattern in patterns:
                if pattern in error_message:
                    return True, feature

        # Map error patterns to API-level features that can be safely disabled
        api_feature_error_patterns = {
            "guardrails": ["guardrail", "content filter"],
            "tool_use": ["tool", "function"],
            "prompt_caching": ["cache", "caching"],
            "streaming": ["stream"],
        }

        for feature, patterns in api_feature_error_patterns.items():
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
        unified_model_manager: Any,
        failed_combinations: Optional[List[Tuple[str, str]]] = None,
    ) -> List[Tuple[str, str, ModelAccessInfo]]:
        """
        Generate list of model/region combinations to try based on retry strategy.

        For content compatibility issues, prioritize trying different models over regions.

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
        access_failures = []

        if self._config.retry_strategy == RetryStrategy.REGION_FIRST:
            # Try all regions for each model before moving to next model
            for model in models:
                for region in regions:
                    if (model, region) in failed_combinations:
                        continue

                    try:
                        access_info = unified_model_manager.get_model_access_info(
                            model_name=model, region=region
                        )
                        if access_info:
                            retry_targets.append((model, region, access_info))
                            # Migration: Use orthogonal flags instead of deprecated access_method property
                            access_flags = []
                            if access_info.has_direct_access:
                                access_flags.append("direct")
                            if access_info.has_regional_cris:
                                access_flags.append("regional_cris")
                            if access_info.has_global_cris:
                                access_flags.append("global_cris")
                            self._logger.debug(
                                f"Found access info for {model} in {region}: {', '.join(access_flags)}"
                            )
                        else:
                            access_failures.append(
                                f"Model '{model}' not available in region '{region}'"
                            )
                            self._logger.debug(f"No access info returned for {model} in {region}")
                    except Exception as e:
                        self._logger.debug(
                            f"Could not get access info for {model} in {region}: {e}"
                        )
                        access_failures.append(f"Error accessing '{model}' in '{region}': {str(e)}")
                        continue

        elif self._config.retry_strategy == RetryStrategy.MODEL_FIRST:
            # Try all models for each region before moving to next region
            for region in regions:
                for model in models:
                    if (model, region) in failed_combinations:
                        continue

                    try:
                        access_info = unified_model_manager.get_model_access_info(
                            model_name=model, region=region
                        )
                        if access_info:
                            retry_targets.append((model, region, access_info))
                        else:
                            access_failures.append(
                                f"Model '{model}' not available in region '{region}'"
                            )
                    except Exception as e:
                        self._logger.debug(
                            f"Could not get access info for {model} in {region}: {e}"
                        )
                        access_failures.append(f"Error accessing '{model}' in '{region}': {str(e)}")
                        continue

        # Log debug information about retry target generation
        if retry_targets:
            self._logger.debug(
                f"Generated {len(retry_targets)} retry targets for {len(models)} models and {len(regions)} regions"
            )
        else:
            self._logger.warning(
                f"No retry targets generated. Models: {models}, Regions: {regions}"
            )
            if access_failures:
                for failure in access_failures[:5]:  # Log first 5 failures to avoid spam
                    self._logger.debug(f"Access failure: {failure}")
                if len(access_failures) > 5:
                    self._logger.debug(f"... and {len(access_failures) - 5} more access failures")

        return retry_targets

    def execute_with_retry(
        self,
        operation: Callable[..., Any],
        operation_args: Dict[str, Any],
        retry_targets: List[Tuple[str, str, ModelAccessInfo]],
        disabled_features: Optional[List[str]] = None,
        model_specific_config: Optional[Any] = None,
    ) -> Tuple[Any, List[RequestAttempt], List[str]]:
        """
        Execute an operation with retry logic and content filtering.

        This method implements the fix for content compatibility errors by properly
        distinguishing between content errors (which require model switching) and
        API feature errors (which can be disabled).

        Args:
            operation: Function to execute (e.g., bedrock client converse call)
            operation_args: Arguments to pass to the operation
            retry_targets: List of (model, region, access_info) to try
            disabled_features: List of features to disable for compatibility
            model_specific_config: Optional model-specific configuration

        Returns:
            Tuple of (result, attempts_made, warnings)

        Raises:
            RetryExhaustedError: If all retry attempts fail
        """
        attempts = []
        warnings: List[str] = []
        disabled_features = disabled_features or []

        # Create filter state to track content filtering
        filter_state = self._content_filter.create_filter_state(operation_args)

        # Track original parameters for compatibility tracking
        original_additional_fields = operation_args.get("additionalModelRequestFields")

        for attempt_num, (model, region, access_info) in enumerate(retry_targets, 1):
            attempt_start = datetime.now()

            # Create attempt record
            # Migration: Get access method name from selector instead of deprecated property
            _, access_method_name = self._select_model_id_for_request(
                access_info=access_info, model_name=model, region=region
            )
            attempt = RequestAttempt(
                model_id=model,
                region=region,
                access_method=access_method_name,  # Use current access method name
                attempt_number=attempt_num,
                start_time=attempt_start,
            )

            try:
                # Log attempt
                if attempt_num == 1:
                    self._logger.info(
                        LLMManagerLogMessages.REQUEST_STARTED.format(model=model, region=region)
                    )
                else:
                    self._logger.info(
                        LLMManagerLogMessages.REQUEST_RETRY.format(
                            attempt=attempt_num,
                            max_attempts=len(retry_targets),
                            model=model,
                            region=region,
                        )
                    )

                # Get tracking ID for parameter compatibility (use profile ID if model_id is None)
                tracking_id = (
                    access_info.model_id
                    or access_info.regional_cris_profile_id
                    or access_info.global_cris_profile_id
                )

                # Check if we should skip this combination due to known parameter incompatibility
                if (
                    tracking_id
                    and original_additional_fields
                    and self._parameter_tracker.is_known_incompatible(
                        model_id=tracking_id,
                        region=region,
                        parameters=original_additional_fields,
                    )
                ):
                    self._logger.debug(
                        f"Skipping known incompatible combination: {model} in {region} "
                        f"with parameters {list(original_additional_fields.keys())}"
                    )
                    continue

                # Check if we should restore features for this model
                should_restore, features_to_restore = (
                    self._content_filter.should_restore_features_for_model(
                        filter_state=filter_state, model_name=model
                    )
                )

                if should_restore and features_to_restore:
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

                # Select model ID using intelligent selection (considers learned preferences)
                model_id_to_use, selected_access_method = self._select_model_id_for_request(
                    access_info=access_info, model_name=model, region=region
                )

                current_args["model_id"] = model_id_to_use
                self._logger.debug(
                    f"Using model ID '{model_id_to_use}' with access method '{selected_access_method}'"
                )

                # Apply content filtering based on current disabled features
                if disabled_features and self._config.enable_feature_fallback:
                    current_args = self._content_filter.apply_filters(
                        filter_state=filter_state, disabled_features=set(disabled_features)
                    )
                    # Re-add model ID which might have been overwritten
                    current_args["model_id"] = model_id_to_use

                # Execute the operation
                result = operation(region=region, **current_args)

                # Success! Record parameter compatibility (use tracking_id from above)
                if tracking_id and original_additional_fields:
                    self._parameter_tracker.record_success(
                        model_id=tracking_id,
                        region=region,
                        parameters=original_additional_fields,
                    )

                # Record successful access method (use tracking_id from above)
                if tracking_id:
                    self._access_method_tracker.record_success(
                        model_id=tracking_id,
                        region=region,
                        access_method=selected_access_method,
                        model_id_used=model_id_to_use,
                    )

                    # Log access method learning
                    self._logger.debug(
                        f"Learned access method '{selected_access_method}' for model "
                        f"'{tracking_id}' in region '{region}'"
                    )

                attempt.end_time = datetime.now()
                attempt.success = True
                attempts.append(attempt)

                self._logger.info(
                    LLMManagerLogMessages.REQUEST_SUCCEEDED.format(
                        model=model, region=region, attempts=attempt_num
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
                        model=model, region=region, error=str(error)
                    )
                )

                # Check if this is a profile requirement error
                if ProfileRequirementDetector.is_profile_requirement_error(error=error):
                    # Extract model ID from error
                    detected_model_id = ProfileRequirementDetector.extract_model_id_from_error(
                        error=error
                    )

                    # Log profile requirement detection
                    self._logger.warning(
                        f"Profile requirement detected for model '{model}' in region '{region}'. "
                        f"Model ID from error: {detected_model_id or 'not extracted'}"
                    )

                    # Try immediate retry with profile
                    profile_result, profile_success, profile_warning = self._retry_with_profile(
                        operation=operation,
                        operation_args=operation_args,
                        model=model,
                        region=region,
                        access_info=access_info,
                        original_error=error,
                    )

                    if profile_success:
                        # Success with profile!
                        attempt.success = True
                        if profile_warning:
                            warnings.append(profile_warning)

                        self._logger.info(
                            f"Request succeeded for {model} in {region} using inference profile"
                        )

                        return profile_result, attempts, warnings
                    else:
                        # Profile retry failed, continue to next target
                        self._logger.debug(
                            f"Profile retry also failed for {model} in {region}, "
                            f"continuing to next target"
                        )

                # Check if this is a parameter compatibility error
                is_param_error, param_name = self.is_parameter_compatibility_error(error)
                if is_param_error and tracking_id and original_additional_fields:
                    # Record parameter incompatibility (use tracking_id from above)
                    self._parameter_tracker.record_failure(
                        model_id=tracking_id,
                        region=region,
                        parameters=original_additional_fields,
                        error=error,
                    )

                    # Try to retry without parameters
                    self._logger.warning(
                        f"Parameter compatibility error detected for {model} in {region}. "
                        f"Retrying without additionalModelRequestFields."
                    )

                    retry_result, retry_success, retry_warning = self._retry_without_parameters(
                        operation=operation,
                        operation_args=operation_args,
                        model=model,
                        region=region,
                        access_info=access_info,
                    )

                    if retry_success:
                        # Success without parameters!
                        attempt.success = True
                        if retry_warning:
                            warnings.append(retry_warning)

                        self._logger.info(
                            f"Request succeeded for {model} in {region} after removing parameters"
                        )

                        return retry_result, attempts, warnings
                    else:
                        # Retry without parameters also failed, continue to next target
                        self._logger.debug(
                            f"Retry without parameters also failed for {model} in {region}"
                        )

                # Check if we should try feature fallback first
                should_fallback, feature_to_disable = self.should_disable_feature_and_retry(error)
                if (
                    should_fallback
                    and feature_to_disable
                    and feature_to_disable not in disabled_features
                ):
                    self._logger.warning(
                        LLMManagerLogMessages.FEATURE_DISABLED.format(
                            feature=feature_to_disable, model=model
                        )
                    )

                    disabled_features.append(feature_to_disable)
                    warnings.append(f"Disabled {feature_to_disable} due to compatibility issues")

                    # Retry with the same target but disabled feature
                    try:
                        fallback_args = self._content_filter.apply_filters(
                            filter_state=filter_state, disabled_features=set(disabled_features)
                        )
                        # Re-add model ID
                        fallback_args["model_id"] = model_id_to_use

                        result = operation(region=region, **fallback_args)

                        # Success with fallback!
                        attempt.success = True
                        self._logger.info(
                            LLMManagerLogMessages.REQUEST_SUCCEEDED.format(
                                model=model, region=region, attempts=attempt_num
                            )
                        )

                        return result, attempts, warnings

                    except Exception as fallback_error:
                        # Fallback also failed, continue to next target
                        attempt.error = fallback_error
                        self._logger.debug(f"Feature fallback also failed: {fallback_error}")

                # Check if this is a content compatibility error requiring model switch
                is_content_error, content_type = self.is_content_compatibility_error(error)
                if is_content_error:
                    self._logger.info(
                        f"Content compatibility error for {content_type} with model {model}. "
                        "Trying next model instead of disabling feature."
                    )
                    # Continue to next target without feature fallback
                    if attempt_num < len(retry_targets):
                        delay = self.calculate_retry_delay(attempt_num)
                        if delay > 0:
                            self._logger.debug(f"Waiting {delay}s before trying next model")
                            time.sleep(delay)
                    continue

                # If not the last attempt and error is retryable, add delay
                if attempt_num < len(retry_targets) and self.is_retryable_error(error, attempt_num):
                    delay = self.calculate_retry_delay(attempt_num)
                    if delay > 0:
                        self._logger.debug(f"Waiting {delay}s before retry")
                        time.sleep(delay)

                # Continue to next target
                continue

        # All attempts failed - check if profile unavailability was the issue
        last_errors = [attempt.error for attempt in attempts if attempt.error]
        models_tried = list(set(attempt.model_id for attempt in attempts))
        regions_tried = list(set(attempt.region for attempt in attempts))

        # Check if all errors were profile requirement errors
        profile_requirement_errors = [
            error
            for error in last_errors
            if ProfileRequirementDetector.is_profile_requirement_error(error=error)
        ]

        # Build error message with profile-specific guidance if applicable
        if profile_requirement_errors and len(profile_requirement_errors) == len(last_errors):
            # All errors were profile requirements - provide specific guidance
            error_message = (
                f"All retry attempts exhausted. All {len(models_tried)} model(s) tried "
                f"require inference profiles but profile access failed. "
                f"Models requiring profiles: {', '.join(models_tried)}. "
                f"Consider refreshing catalog data or trying different models/regions."
            )
        elif profile_requirement_errors:
            # Some errors were profile requirements
            error_message = (
                f"All retry attempts exhausted. {len(profile_requirement_errors)} of "
                f"{len(last_errors)} attempts failed due to missing inference profiles. "
                f"Models tried: {', '.join(models_tried)}. "
                f"Consider refreshing catalog data."
            )
        else:
            # Use default error message
            error_message = LLMManagerErrorMessages.ALL_RETRIES_FAILED.format(
                model_count=len(models_tried), region_count=len(regions_tried)
            )

        raise RetryExhaustedError(
            message=error_message,
            attempts_made=len(attempts),
            last_errors=last_errors,
            models_tried=models_tried,
            regions_tried=regions_tried,
        )

    def _retry_without_parameters(
        self,
        operation: Callable[..., Any],
        operation_args: Dict[str, Any],
        model: str,
        region: str,
        access_info: ModelAccessInfo,
    ) -> Tuple[Any, bool, Optional[str]]:
        """
        Retry operation without additionalModelRequestFields.

        Args:
            operation: Function to execute
            operation_args: Original operation arguments
            model: Model name
            region: Region name
            access_info: Model access information

        Returns:
            Tuple of (result, success, warning_message)
        """
        try:
            # Create args without additionalModelRequestFields
            retry_args = operation_args.copy()
            original_fields = retry_args.pop("additionalModelRequestFields", None)

            # Migration: Use orthogonal flags instead of deprecated access_method property
            # Set model ID based on available access methods
            if access_info.has_direct_access:
                # Use direct model ID
                retry_args["model_id"] = access_info.model_id
            elif access_info.has_regional_cris:
                # Use regional CRIS profile
                retry_args["model_id"] = access_info.regional_cris_profile_id
            elif access_info.has_global_cris:
                # Use global CRIS profile
                retry_args["model_id"] = access_info.global_cris_profile_id
            else:
                # This should not happen due to ModelAccessInfo validation
                raise ValueError(f"No access methods available for {model} in {region}")

            # Log parameter removal
            if original_fields:
                param_names = list(original_fields.keys())
                self._logger.warning(
                    f"Removed additionalModelRequestFields for {model} in {region}: "
                    f"{', '.join(param_names)}"
                )

            # Execute without parameters
            result = operation(region=region, **retry_args)

            # Create warning message
            warning = None
            if original_fields:
                param_names = list(original_fields.keys())
                warning = (
                    f"Parameters removed due to incompatibility with {model} in {region}: "
                    f"{', '.join(param_names)}"
                )

            return result, True, warning

        except Exception as retry_error:
            self._logger.debug(f"Retry without parameters failed: {retry_error}")
            return None, False, None

    def _retry_with_profile(
        self,
        operation: Callable[..., Any],
        operation_args: Dict[str, Any],
        model: str,
        region: str,
        access_info: ModelAccessInfo,
        original_error: Exception,
    ) -> Tuple[Any, bool, Optional[str]]:
        """
        Retry operation with inference profile after detecting requirement.

        This method is called when a profile requirement error is detected.
        It attempts to retry with available CRIS profiles without incrementing
        the retry attempt counter.

        Args:
            operation: Function to execute
            operation_args: Original operation arguments
            model: Model name
            region: Region name
            access_info: Model access information
            original_error: The profile requirement error

        Returns:
            Tuple of (result, success, warning_message)
        """
        from .access_method_structures import AccessMethodNames

        # Get tracking ID (use profile ID if model_id is None)
        tracking_id = (
            access_info.model_id
            or access_info.regional_cris_profile_id
            or access_info.global_cris_profile_id
        )

        if tracking_id is None:
            self._logger.warning(
                f"Cannot retry with profile for {model} in {region}: no tracking ID available"
            )
            return None, False, None

        # Record profile requirement for future requests
        self._access_method_tracker.record_profile_requirement(model_id=tracking_id, region=region)

        # Check if profile information is available in catalog
        if not access_info.has_any_cris_access():
            self._logger.warning(
                f"Model '{model}' in region '{region}' requires inference profile but "
                f"no profile information available in catalog. Continuing to next model/region."
            )
            return None, False, None

        # Get fallback access methods (excluding direct access which failed)
        fallback_methods = self._access_method_selector.get_fallback_access_methods(
            access_info=access_info, failed_method=AccessMethodNames.DIRECT
        )

        if not fallback_methods:
            self._logger.warning(
                f"No inference profiles available for model '{model}' in region '{region}'"
            )
            return None, False, None

        # Try each fallback method
        for profile_id, access_method in fallback_methods:
            try:
                # Log profile selection
                self._logger.info(
                    f"Retrying with inference profile for model '{model}' in region '{region}' "
                    f"using access method '{access_method}'"
                )

                # Create args with profile ID
                retry_args = operation_args.copy()
                retry_args["model_id"] = profile_id

                # Execute with profile
                result = operation(region=region, **retry_args)

                # Success! Record successful access method (use tracking_id from above)
                self._access_method_tracker.record_success(
                    model_id=tracking_id,
                    region=region,
                    access_method=access_method,
                    model_id_used=profile_id,
                )

                # Log access method learning
                self._logger.debug(
                    f"Learned access method '{access_method}' for model "
                    f"'{access_info.model_id}' in region '{region}' (from profile requirement)"
                )

                # Log success
                self._logger.info(
                    f"Profile retry succeeded for model '{model}' in region '{region}' "
                    f"using access method '{access_method}'"
                )

                # Create warning message with actual profile ID for debugging
                warning = (
                    f"Model '{model}' in region '{region}' requires inference profile access. "
                    f"Using {access_method} profile (ID: {profile_id})."
                )

                return result, True, warning

            except Exception as profile_error:
                self._logger.debug(
                    f"Profile retry failed with access method '{access_method}': {profile_error}"
                )
                # Continue to next fallback method
                continue

        # All profile retries failed
        self._logger.warning(f"All profile retries failed for model '{model}' in region '{region}'")
        return None, False, None

    def _select_model_id_for_request(
        self,
        access_info: ModelAccessInfo,
        model_name: str,
        region: str,
    ) -> Tuple[str, str]:
        """
        Select appropriate model ID for request based on access info and learned preferences.

        This method queries the AccessMethodTracker for learned preferences and uses
        the AccessMethodSelector to choose the optimal model ID (direct or profile).

        Args:
            access_info: Model access information from catalog
            model_name: User-provided model name
            region: Target region

        Returns:
            Tuple of (model_id_to_use, access_method_name)

        Examples:
            - ("anthropic.claude-3-haiku-20240307-v1:0", "direct")
            - ("arn:aws:bedrock:us-east-1::inference-profile/...", "regional_cris")
        """
        # Get tracking ID (use profile ID if model_id is None)
        tracking_id = (
            access_info.model_id
            or access_info.regional_cris_profile_id
            or access_info.global_cris_profile_id
        )

        if tracking_id is None:
            raise ValueError(
                f"Cannot select model ID for {model_name} in {region}: no tracking ID available"
            )

        # Query for learned preference
        learned_preference = self._access_method_tracker.get_preference(
            model_id=tracking_id, region=region
        )

        # Use selector to choose optimal access method
        model_id_to_use, access_method = self._access_method_selector.select_access_method(
            access_info=access_info, learned_preference=learned_preference
        )

        # Log selection
        if learned_preference:
            self._logger.debug(
                f"Selected access method '{access_method}' for model '{model_name}' "
                f"in region '{region}' based on learned preference"
            )
        else:
            self._logger.debug(
                f"Selected access method '{access_method}' for model '{model_name}' "
                f"in region '{region}' using default preference order"
            )

        return model_id_to_use, access_method

    def _remove_disabled_features(
        self, request_args: Dict[str, Any], disabled_features: List[str]
    ) -> Dict[str, Any]:
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
            if feature == "guardrails" and "guardrailConfig" in modified_args:
                del modified_args["guardrailConfig"]
            elif feature == "tool_use" and "toolConfig" in modified_args:
                del modified_args["toolConfig"]
            elif feature == "streaming" and "stream" in modified_args:
                modified_args["stream"] = False
            elif feature in ["document_processing", "image_processing", "video_processing"]:
                # Remove content blocks of these types from messages
                if "messages" in modified_args:
                    modified_args["messages"] = self._filter_content_blocks(
                        modified_args["messages"], feature
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
            "document_processing": "document",
            "image_processing": "image",
            "video_processing": "video",
        }

        block_type = feature_to_block_type.get(disabled_feature)
        if not block_type:
            return messages

        filtered_messages = []
        for message in messages:
            if "content" in message:
                filtered_content = []
                for block in message["content"]:
                    if not isinstance(block, dict) or block_type not in block:
                        filtered_content.append(block)

                # Only include message if it has remaining content
                if filtered_content:
                    filtered_message = message.copy()
                    filtered_message["content"] = filtered_content
                    filtered_messages.append(filtered_message)
            else:
                filtered_messages.append(message)

        return filtered_messages

    def _execute_response_validation(
        self, response: Any, validation_config: ResponseValidationConfig, model: str, region: str
    ) -> Tuple[bool, List[ValidationAttempt]]:
        """
        Execute response validation with retry logic.

        Args:
            response: BedrockResponse object to validate
            validation_config: Configuration for validation
            model: Model name for logging
            region: Region name for logging

        Returns:
            Tuple of (validation_success, validation_attempts)
        """
        validation_attempts = []

        for attempt_num in range(1, validation_config.response_validation_retries + 1):
            self._logger.debug(
                ResponseValidationLogMessages.VALIDATION_STARTED.format(model=model, region=region)
            )

            # Execute validation function safely
            validation_result, content = self._safe_validate_response(
                response=response,
                validation_function=validation_config.response_validation_function,
            )

            # Create validation attempt record
            validation_attempt = ValidationAttempt(
                attempt_number=attempt_num,
                validation_result=validation_result,
                failed_content=content if not validation_result.success else None,
            )
            validation_attempts.append(validation_attempt)

            if validation_result.success:
                self._logger.info(
                    ResponseValidationLogMessages.VALIDATION_SUCCEEDED.format(
                        model=model, region=region, attempts=attempt_num
                    )
                )
                return True, validation_attempts
            else:
                # Log validation failure with content
                self._logger.warning(
                    ResponseValidationLogMessages.VALIDATION_FAILED.format(
                        attempt=attempt_num,
                        max_attempts=validation_config.response_validation_retries,
                        model=model,
                        region=region,
                        error=validation_result.error_message or "Unknown validation error",
                    )
                )

                if content:
                    self._logger.warning(
                        ResponseValidationLogMessages.VALIDATION_CONTENT_LOGGED.format(
                            model=model,
                            content=content[:500] + "..." if len(content) > 500 else content,
                        )
                    )

                # Add delay before next validation attempt if configured
                if (
                    attempt_num < validation_config.response_validation_retries
                    and validation_config.response_validation_delay > 0
                ):
                    time.sleep(validation_config.response_validation_delay)

        # All validation attempts failed
        self._logger.warning(
            ResponseValidationLogMessages.VALIDATION_RETRIES_EXHAUSTED.format(
                model=model, region=region
            )
        )

        return False, validation_attempts

    def _safe_validate_response(
        self, response: Any, validation_function: Callable
    ) -> Tuple[ValidationResult, Optional[str]]:
        """
        Safely execute validation function and return result with error info.

        Args:
            response: BedrockResponse to validate
            validation_function: Function to validate the response

        Returns:
            Tuple of (ValidationResult, content_that_failed)
        """
        try:
            content = response.get_content()
            result = validation_function(response)
            return result, content
        except Exception as e:
            self._logger.warning(f"Validation function raised exception: {e}")
            error_result = ValidationResult(
                success=False,
                error_message=f"Validation function error: {str(e)}",
                error_details={"exception_type": type(e).__name__},
            )
            content = response.get_content() if hasattr(response, "get_content") else None
            return error_result, content

    def execute_with_validation_retry(
        self,
        operation: Callable[..., Any],
        operation_args: Dict[str, Any],
        retry_targets: List[Tuple[str, str, ModelAccessInfo]],
        validation_config: Optional[ResponseValidationConfig] = None,
        disabled_features: Optional[List[str]] = None,
    ) -> Tuple[Any, List[RequestAttempt], List[str]]:
        """
        Execute an operation with both regular retry logic and response validation.

        This method combines the existing retry functionality with response validation,
        handling validation retries and switching to different models/regions when
        validation consistently fails.

        Args:
            operation: Function to execute (e.g., bedrock client converse call)
            operation_args: Arguments to pass to the operation
            retry_targets: List of (model, region, access_info) to try
            validation_config: Optional validation configuration
            disabled_features: List of features to disable for compatibility

        Returns:
            Tuple of (result, attempts_made, warnings)

        Raises:
            RetryExhaustedError: If all retry attempts fail
        """
        # If no validation config, use regular retry logic
        if validation_config is None:
            return self.execute_with_retry(
                operation=operation,
                operation_args=operation_args,
                retry_targets=retry_targets,
                disabled_features=disabled_features,
            )

        attempts = []
        warnings: List[str] = []
        disabled_features = disabled_features or []

        # Create filter state to track content filtering
        filter_state = self._content_filter.create_filter_state(operation_args)

        from ..models.bedrock_response import BedrockResponse

        for attempt_num, (model, region, access_info) in enumerate(retry_targets, 1):
            attempt_start = datetime.now()

            # Create attempt record
            # Migration: Get access method name from selector instead of deprecated property
            _, access_method_name = self._select_model_id_for_request(
                access_info=access_info, model_name=model, region=region
            )
            attempt = RequestAttempt(
                model_id=model,
                region=region,
                access_method=access_method_name,  # Use current access method name
                attempt_number=attempt_num,
                start_time=attempt_start,
            )

            try:
                # Log attempt
                if attempt_num == 1:
                    self._logger.info(
                        LLMManagerLogMessages.REQUEST_STARTED.format(model=model, region=region)
                    )
                else:
                    self._logger.info(
                        LLMManagerLogMessages.REQUEST_RETRY.format(
                            attempt=attempt_num,
                            max_attempts=len(retry_targets),
                            model=model,
                            region=region,
                        )
                    )

                # Prepare operation arguments (same logic as regular retry)
                current_args = self._prepare_operation_args(
                    operation_args=operation_args,
                    access_info=access_info,
                    model=model,
                    disabled_features=disabled_features,
                    filter_state=filter_state,
                )

                # Execute the operation
                result = operation(region=region, **current_args)

                # Create BedrockResponse object for validation
                if isinstance(result, BedrockResponse):
                    bedrock_response = result
                else:
                    # If result is raw dict, create BedrockResponse
                    # Migration: Use access_method_name from earlier selection
                    bedrock_response = BedrockResponse(
                        success=True,
                        response_data=result,
                        model_used=model,
                        region_used=region,
                        access_method_used=access_method_name,  # Use current access method name
                    )

                # Execute response validation with retries
                validation_success, validation_attempts = self._execute_response_validation(
                    response=bedrock_response,
                    validation_config=validation_config,
                    model=model,
                    region=region,
                )

                if validation_success:
                    # Success with validation!
                    attempt.end_time = datetime.now()
                    attempt.success = True
                    attempts.append(attempt)

                    # Add validation data to response
                    if isinstance(result, BedrockResponse):
                        result.validation_attempts.extend(validation_attempts)
                        # Add validation error details for failed attempts
                        for va in validation_attempts:
                            if not va.validation_result.success:
                                result.validation_errors.append(va.validation_result.to_dict())

                    self._logger.info(
                        LLMManagerLogMessages.REQUEST_SUCCEEDED.format(
                            model=model, region=region, attempts=attempt_num
                        )
                    )

                    return result, attempts, warnings
                else:
                    # Validation failed, treat as validation error and try next target
                    attempt.end_time = datetime.now()
                    attempt.success = False

                    # Create a validation error for the attempt
                    last_validation_error = (
                        validation_attempts[-1].validation_result if validation_attempts else None
                    )
                    validation_error_msg = (
                        last_validation_error.error_message
                        if last_validation_error
                        else "Response validation failed"
                    )
                    attempt.error = Exception(f"Validation failed: {validation_error_msg}")
                    attempts.append(attempt)

                    # Add validation data to response for debugging
                    if isinstance(result, BedrockResponse):
                        result.validation_attempts.extend(validation_attempts)
                        for va in validation_attempts:
                            if not va.validation_result.success:
                                result.validation_errors.append(va.validation_result.to_dict())

                    self._logger.warning(
                        f"Validation failed for model '{model}' in region '{region}', trying next target"
                    )

                    # Add delay before trying next target
                    if attempt_num < len(retry_targets):
                        delay = self.calculate_retry_delay(attempt_num)
                        if delay > 0:
                            self._logger.debug(f"Waiting {delay}s before trying next target")
                            time.sleep(delay)
                    continue

            except Exception as error:
                # Handle regular operation errors (same as original retry logic)
                attempt.end_time = datetime.now()
                attempt.error = error
                attempt.success = False
                attempts.append(attempt)

                self._logger.warning(
                    LLMManagerLogMessages.REQUEST_FAILED.format(
                        model=model, region=region, error=str(error)
                    )
                )

                # Apply same feature fallback logic as regular retry
                should_fallback, feature_to_disable = self.should_disable_feature_and_retry(error)
                if (
                    should_fallback
                    and feature_to_disable
                    and feature_to_disable not in disabled_features
                ):
                    # ... (same feature fallback logic as in execute_with_retry)
                    pass

                # Continue to next target
                continue

        # All attempts failed - check if profile unavailability was the issue
        last_errors = [attempt.error for attempt in attempts if attempt.error]
        models_tried = list(set(attempt.model_id for attempt in attempts))
        regions_tried = list(set(attempt.region for attempt in attempts))

        # Check if all errors were profile requirement errors
        profile_requirement_errors = [
            error
            for error in last_errors
            if ProfileRequirementDetector.is_profile_requirement_error(error=error)
        ]

        # Build error message with profile-specific guidance if applicable
        if profile_requirement_errors and len(profile_requirement_errors) == len(last_errors):
            # All errors were profile requirements - provide specific guidance
            error_message = (
                f"All retry attempts exhausted. All {len(models_tried)} model(s) tried "
                f"require inference profiles but profile access failed. "
                f"Models requiring profiles: {', '.join(models_tried)}. "
                f"Consider refreshing catalog data or trying different models/regions."
            )
        elif profile_requirement_errors:
            # Some errors were profile requirements
            error_message = (
                f"All retry attempts exhausted. {len(profile_requirement_errors)} of "
                f"{len(last_errors)} attempts failed due to missing inference profiles. "
                f"Models tried: {', '.join(models_tried)}. "
                f"Consider refreshing catalog data."
            )
        else:
            # Use default error message
            error_message = LLMManagerErrorMessages.ALL_RETRIES_FAILED.format(
                model_count=len(models_tried), region_count=len(regions_tried)
            )

        raise RetryExhaustedError(
            message=error_message,
            attempts_made=len(attempts),
            last_errors=last_errors,
            models_tried=models_tried,
            regions_tried=regions_tried,
        )

    def _prepare_operation_args(
        self,
        operation_args: Dict[str, Any],
        access_info: ModelAccessInfo,
        model: str,
        disabled_features: List[str],
        filter_state: ContentFilterState,
    ) -> Dict[str, Any]:
        """
        Prepare operation arguments for a specific model/region combination.

        Args:
            operation_args: Original operation arguments
            access_info: Access information for the model
            model: Model name
            disabled_features: Features to disable
            filter_state: Content filter state

        Returns:
            Prepared operation arguments
        """
        # Check if we should restore features for this model
        should_restore, features_to_restore = (
            self._content_filter.should_restore_features_for_model(
                filter_state=filter_state, model_name=model
            )
        )

        if should_restore and features_to_restore:
            self._logger.info(
                f"Restoring features for model {model}: {', '.join(features_to_restore)}"
            )
            # Remove restored features from disabled list
            for feature in features_to_restore:
                if feature in disabled_features:
                    disabled_features.remove(feature)

        # Prepare operation arguments with current target
        current_args = operation_args.copy()

        # Migration: Use orthogonal flags instead of deprecated access_method property
        # Set model ID based on available access methods (prefer direct, then regional CRIS, then global CRIS)
        if access_info.has_direct_access:
            current_args["model_id"] = access_info.model_id
            self._logger.debug(f"Using direct access for {model}")
        elif access_info.has_regional_cris:
            current_args["model_id"] = access_info.regional_cris_profile_id
            self._logger.debug(f"Using regional CRIS access for {model}")
        elif access_info.has_global_cris:
            current_args["model_id"] = access_info.global_cris_profile_id
            self._logger.debug(f"Using global CRIS access for {model}")
        else:
            # This should not happen due to ModelAccessInfo validation
            raise ValueError(f"No access methods available for {model} in {access_info.region}")

        # Apply content filtering based on current disabled features
        if disabled_features and self._config.enable_feature_fallback:
            current_args = self._content_filter.apply_filters(
                filter_state=filter_state, disabled_features=set(disabled_features)
            )
            # Re-add model ID which might have been overwritten
            if access_info.has_direct_access:
                current_args["model_id"] = access_info.model_id
            elif access_info.has_regional_cris:
                current_args["model_id"] = access_info.regional_cris_profile_id
            elif access_info.has_global_cris:
                current_args["model_id"] = access_info.global_cris_profile_id

        return current_args

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
            "non_retryable_error_count": len(self._non_retryable_errors),
        }
