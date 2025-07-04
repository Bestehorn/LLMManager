"""
LLMManager - Main class for managing AWS Bedrock Converse API interactions.

Provides a unified interface for interacting with multiple LLMs across regions
with automatic retry logic, authentication handling, and comprehensive response management.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union, cast

from .bedrock.auth.auth_manager import AuthManager
from .bedrock.exceptions.llm_manager_exceptions import (
    AuthenticationError,
    ConfigurationError,
    LLMManagerError,
    RequestValidationError,
    RetryExhaustedError,
)
from .bedrock.models.bedrock_response import BedrockResponse, StreamingResponse
from .bedrock.models.llm_manager_constants import (
    ContentLimits,
    ConverseAPIFields,
    LLMManagerConfig,
    LLMManagerErrorMessages,
    LLMManagerLogMessages,
)
from .bedrock.models.llm_manager_structures import (
    AuthConfig,
    ResponseValidationConfig,
    RetryConfig,
)
from .bedrock.models.parallel_structures import BedrockConverseRequest
from .bedrock.retry.retry_manager import RetryManager
from .bedrock.UnifiedModelManager import UnifiedModelManager


class LLMManager:
    """
    Main class for managing AWS Bedrock LLM interactions.

    Provides a unified interface for:
    - Multiple models and regions with automatic failover
    - Authentication handling (profiles, credentials, IAM roles)
    - Retry logic with graceful degradation
    - Comprehensive response handling
    - Support for all Converse API features

    Example:
        Basic usage:
        >>> manager = LLMManager(
        ...     models=["Claude 3 Haiku", "Claude 3 Sonnet"],
        ...     regions=["us-east-1", "us-west-2"]
        ... )
        >>> response = manager.converse(
        ...     messages=[{"role": "user", "content": [{"text": "Hello!"}]}]
        ... )
        >>> print(response.get_content())

        With authentication:
        >>> auth_config = AuthConfig(
        ...     auth_type=AuthenticationType.PROFILE,
        ...     profile_name="my-profile"
        ... )
        >>> manager = LLMManager(
        ...     models=["Claude 3 Haiku"],
        ...     regions=["us-east-1"],
        ...     auth_config=auth_config
        ... )
    """

    def __init__(
        self,
        models: List[str],
        regions: List[str],
        auth_config: Optional[AuthConfig] = None,
        retry_config: Optional[RetryConfig] = None,
        unified_model_manager: Optional[UnifiedModelManager] = None,
        default_inference_config: Optional[Dict[str, Any]] = None,
        timeout: int = LLMManagerConfig.DEFAULT_TIMEOUT,
        log_level: Union[int, str] = LLMManagerConfig.DEFAULT_LOG_LEVEL,
    ) -> None:
        """
        Initialize the LLM Manager.

        Args:
            models: List of model names/IDs to use for requests
            regions: List of AWS regions to try
            auth_config: Authentication configuration. If None, uses auto-detection
            retry_config: Retry behavior configuration. If None, uses defaults
            unified_model_manager: Pre-configured UnifiedModelManager. If None, creates new one
            default_inference_config: Default inference parameters to apply
            timeout: Request timeout in seconds
            log_level: Logging level (e.g., logging.WARNING, "INFO", 20). Defaults to logging.WARNING

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Configure logging for the entire bestehorn_llmmanager package
        self._configure_logging(log_level=log_level)

        self._logger = logging.getLogger(__name__)

        # Validate inputs
        self._validate_initialization_params(models=models, regions=regions)

        # Store configuration
        self._models = models.copy()
        self._regions = regions.copy()
        self._timeout = timeout
        self._default_inference_config = default_inference_config or {}

        # Initialize components
        self._auth_manager = AuthManager(auth_config=auth_config)
        self._retry_manager = RetryManager(retry_config=retry_config or RetryConfig())

        # Initialize or use provided UnifiedModelManager
        if unified_model_manager:
            self._unified_model_manager = unified_model_manager
        else:
            self._unified_model_manager = UnifiedModelManager()

        # Initialize model data with proper cache management
        self._initialize_model_data()

        # Validate model/region combinations
        self._validate_model_region_combinations()

        self._logger.info(
            LLMManagerLogMessages.MANAGER_INITIALIZED.format(
                model_count=len(self._models), region_count=len(self._regions)
            )
        )

    def _configure_logging(self, log_level: Union[int, str]) -> None:
        """
        Configure logging level for the bestehorn_llmmanager package.

        Args:
            log_level: Logging level (int, string, or logging constant)
        """
        # Get the root logger for the bestehorn_llmmanager package
        package_logger = logging.getLogger("bestehorn_llmmanager")

        # Set the logging level using the built-in setLevel method
        # This method accepts int, str, or logging constants
        package_logger.setLevel(log_level)

        # Also configure the root logger of the current module's package
        # This ensures all sub-modules inherit the logging level
        root_parts = __name__.split(".")
        if len(root_parts) > 1:
            root_logger = logging.getLogger(root_parts[0])
            root_logger.setLevel(log_level)

    def _validate_initialization_params(self, models: List[str], regions: List[str]) -> None:
        """Validate initialization parameters."""
        if not models:
            raise ConfigurationError(LLMManagerErrorMessages.NO_MODELS_SPECIFIED)

        if not regions:
            raise ConfigurationError(LLMManagerErrorMessages.NO_REGIONS_SPECIFIED)

        # Validate model names are strings
        for model in models:
            if not isinstance(model, str) or not model.strip():
                raise ConfigurationError(f"Invalid model name: {model}")

        # Validate region names are strings
        for region in regions:
            if not isinstance(region, str) or not region.strip():
                raise ConfigurationError(f"Invalid region name: {region}")

    def _initialize_model_data(self) -> None:
        """
        Initialize model data for the UnifiedModelManager.

        This method attempts to load cached model data first, and if unavailable,
        refreshes the data by downloading from AWS documentation. Model data is
        required for LLMManager to operate properly.

        Raises:
            ConfigurationError: If model data cannot be loaded or refreshed
        """
        try:
            # Try to load cached data first
            cached_catalog = self._load_cached_model_data()
            if cached_catalog is not None:
                self._logger.info("Successfully loaded cached model data")
                return

            # No cached data available, refresh from AWS
            self._refresh_model_data_from_aws()
            self._logger.info("Successfully refreshed model data from AWS documentation")

        except Exception as e:
            self._raise_model_data_initialization_error(error=e)

    def _load_cached_model_data(self) -> Optional[Any]:
        """
        Attempt to load cached model data.

        Returns:
            Cached model catalog if available, None otherwise
        """
        try:
            return self._unified_model_manager.load_cached_data()
        except Exception as e:
            self._logger.debug(f"Could not load cached model data: {e}")
            return None

    def _refresh_model_data_from_aws(self) -> None:
        """
        Refresh model data by downloading from AWS documentation.

        Raises:
            Exception: If model data refresh fails
        """
        self._logger.info("No cached model data found, refreshing from AWS documentation...")
        self._unified_model_manager.refresh_unified_data()

    def _raise_model_data_initialization_error(self, error: Exception) -> None:
        """
        Raise a comprehensive ConfigurationError for model data initialization failure.

        Args:
            error: The underlying error that caused the failure

        Raises:
            ConfigurationError: Always raises with detailed error message
        """
        error_message = self._build_model_data_error_message(error=error)
        self._logger.error(f"LLMManager initialization failed: {error_message}")
        raise ConfigurationError(error_message) from error

    def _build_model_data_error_message(self, error: Exception) -> str:
        """
        Build a comprehensive error message for model data initialization failure.

        Args:
            error: The underlying error that caused the failure

        Returns:
            Detailed error message with troubleshooting guidance
        """
        base_message = (
            "LLMManager initialization failed: Could not load or refresh model data. "
            "Model data is required for LLMManager to operate properly."
        )

        error_details = str(error)

        # Provide specific guidance based on error type
        if "network" in error_details.lower() or "connection" in error_details.lower():
            troubleshooting = (
                "This appears to be a network connectivity issue. "
                "Ensure you have internet access and can reach AWS documentation URLs. "
                "If behind a corporate firewall, contact your network administrator."
            )
        elif "timeout" in error_details.lower():
            troubleshooting = (
                "This appears to be a network timeout issue. "
                "Try again with a stable internet connection or increase the download timeout."
            )
        elif "permission" in error_details.lower() or "access" in error_details.lower():
            troubleshooting = (
                "This appears to be a file system permissions issue. "
                "Ensure the application has write access to the cache directory."
            )
        else:
            troubleshooting = (
                "Try running in an environment with internet access to download model data, "
                "or provide a pre-configured UnifiedModelManager with cached data."
            )

        return f"{base_message} {troubleshooting} Original error: {error_details}"

    def _validate_model_region_combinations(self) -> None:
        """
        Validate that at least one model/region combination is available.

        Raises:
            ConfigurationError: If no valid model/region combinations are found
        """
        available_combinations = 0
        validation_errors = []

        for model in self._models:
            model_found_in_any_region = False
            for region in self._regions:
                try:
                    access_info = self._unified_model_manager.get_model_access_info(
                        model_name=model, region=region
                    )
                    if access_info:
                        available_combinations += 1
                        model_found_in_any_region = True
                except Exception as e:
                    self._logger.debug(f"Could not validate {model} in {region}: {e}")
                    continue

            if not model_found_in_any_region:
                validation_errors.append(f"Model '{model}' not found in any specified region")

        if available_combinations == 0:
            error_details = []
            error_details.append(f"Models specified: {self._models}")
            error_details.append(f"Regions specified: {self._regions}")
            error_details.extend(validation_errors)

            # Check if this is due to missing model data
            try:
                if not self._unified_model_manager._cached_catalog:
                    error_details.append(
                        "No model data available. Try refreshing model data or ensure internet connectivity."
                    )
                else:
                    available_models = self._unified_model_manager.get_model_names()[
                        :10
                    ]  # Show first 10
                    error_details.append(f"Available models (sample): {available_models}")
            except Exception:
                error_details.append("Could not retrieve available model information.")

            error_message = (
                "No valid model/region combinations found during initialization. "
                "Please check model names and region availability. " + " ".join(error_details)
            )

            self._logger.error(error_message)
            raise ConfigurationError(error_message)

    def converse(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[List[Dict[str, str]]] = None,
        inference_config: Optional[Dict[str, Any]] = None,
        additional_model_request_fields: Optional[Dict[str, Any]] = None,
        additional_model_response_field_paths: Optional[List[str]] = None,
        guardrail_config: Optional[Dict[str, Any]] = None,
        tool_config: Optional[Dict[str, Any]] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
        prompt_variables: Optional[Dict[str, Any]] = None,
        response_validation_config: Optional[ResponseValidationConfig] = None,
    ) -> BedrockResponse:
        """
        Send a conversation request to available models with retry logic.

        Args:
            messages: List of message objects for the conversation
            system: List of system message objects
            inference_config: Inference configuration parameters
            additional_model_request_fields: Model-specific request parameters
            additional_model_response_field_paths: Additional response fields to return
            guardrail_config: Guardrail configuration
            tool_config: Tool use configuration
            request_metadata: Metadata for the request
            prompt_variables: Variables for prompt templates
            response_validation_config: Configuration for response validation and retry

        Returns:
            BedrockResponse with the conversation result

        Raises:
            RequestValidationError: If request validation fails
            RetryExhaustedError: If all retry attempts fail
            AuthenticationError: If authentication fails
        """
        request_start = datetime.now()

        # Validate request
        self._validate_converse_request(messages=messages)

        # Build request arguments
        request_args = self._build_converse_request(
            messages=messages,
            system=system,
            inference_config=inference_config,
            additional_model_request_fields=additional_model_request_fields,
            additional_model_response_field_paths=additional_model_response_field_paths,
            guardrail_config=guardrail_config,
            tool_config=tool_config,
            request_metadata=request_metadata,
            prompt_variables=prompt_variables,
        )

        # Generate retry targets
        retry_targets = self._retry_manager.generate_retry_targets(
            models=self._models,
            regions=self._regions,
            unified_model_manager=self._unified_model_manager,
        )

        if not retry_targets:
            raise ConfigurationError(
                "No valid model/region combinations available. "
                "Check model names and region availability."
            )

        try:
            # Execute with retry logic (with optional response validation)
            if response_validation_config:
                result, attempts, warnings = self._retry_manager.execute_with_validation_retry(
                    operation=self._execute_converse,
                    operation_args=request_args,
                    retry_targets=retry_targets,
                    validation_config=response_validation_config,
                )
            else:
                result, attempts, warnings = self._retry_manager.execute_with_retry(
                    operation=self._execute_converse,
                    operation_args=request_args,
                    retry_targets=retry_targets,
                )

            # Calculate total duration
            total_duration = (datetime.now() - request_start).total_seconds() * 1000

            # Extract API latency from response
            api_latency = None
            if ConverseAPIFields.METRICS in result:
                api_latency = result[ConverseAPIFields.METRICS].get(ConverseAPIFields.LATENCY_MS)

            # Get successful attempt info
            successful_attempt = next((a for a in attempts if a.success), None)

            # Create response object
            response = BedrockResponse(
                success=True,
                response_data=result,
                model_used=successful_attempt.model_id if successful_attempt else None,
                region_used=successful_attempt.region if successful_attempt else None,
                access_method_used=successful_attempt.access_method if successful_attempt else None,
                attempts=attempts,
                total_duration_ms=total_duration,
                api_latency_ms=api_latency,
                warnings=warnings,
                features_disabled=[],  # Will be populated by retry manager if needed
            )

            return response

        except RetryExhaustedError as e:
            # Create failed response
            total_duration = (datetime.now() - request_start).total_seconds() * 1000

            response = BedrockResponse(
                success=False,
                attempts=[],  # Will be populated by retry manager with RequestAttempt objects
                total_duration_ms=total_duration,
                warnings=[],
            )

            raise e

    def converse_stream(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[List[Dict[str, str]]] = None,
        inference_config: Optional[Dict[str, Any]] = None,
        additional_model_request_fields: Optional[Dict[str, Any]] = None,
        additional_model_response_field_paths: Optional[List[str]] = None,
        guardrail_config: Optional[Dict[str, Any]] = None,
        tool_config: Optional[Dict[str, Any]] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
        prompt_variables: Optional[Dict[str, Any]] = None,
    ) -> StreamingResponse:
        """
        Send a streaming conversation request to available models.

        Args:
            messages: List of message objects for the conversation
            system: List of system message objects
            inference_config: Inference configuration parameters
            additional_model_request_fields: Model-specific request parameters
            additional_model_response_field_paths: Additional response fields to return
            guardrail_config: Guardrail configuration
            tool_config: Tool use configuration
            request_metadata: Metadata for the request
            prompt_variables: Variables for prompt templates

        Returns:
            StreamingResponse with the streaming conversation result

        Raises:
            RequestValidationError: If request validation fails
            RetryExhaustedError: If all retry attempts fail
            AuthenticationError: If authentication fails
        """
        # Comment this back in when Streaming Response format is implemented. Avoid flake8 errors
        # request_start = datetime.now()

        # Validate request
        self._validate_converse_request(messages=messages)

        # Build request arguments (same as regular converse but we'll handle streaming)
        request_args = self._build_converse_request(
            messages=messages,
            system=system,
            inference_config=inference_config,
            additional_model_request_fields=additional_model_request_fields,
            additional_model_response_field_paths=additional_model_response_field_paths,
            guardrail_config=guardrail_config,
            tool_config=tool_config,
            request_metadata=request_metadata,
            prompt_variables=prompt_variables,
        )

        # Generate retry targets
        retry_targets = self._retry_manager.generate_retry_targets(
            models=self._models,
            regions=self._regions,
            unified_model_manager=self._unified_model_manager,
        )

        if not retry_targets:
            raise ConfigurationError(
                "No valid model/region combinations available for streaming. "
                "Check model names and region availability."
            )

        try:
            # Execute with retry logic (streaming version)
            result, attempts, warnings = self._retry_manager.execute_with_retry(
                operation=self._execute_converse_stream,
                operation_args=request_args,
                retry_targets=retry_targets,
            )

            # Process streaming result
            streaming_response = StreamingResponse(success=True)

            # Extract content from streaming result
            # This would need to be implemented based on the actual streaming response format
            # For now, create a placeholder implementation

            return streaming_response

        except RetryExhaustedError as e:
            streaming_response = StreamingResponse(success=False, stream_errors=[e])
            raise e

    def _validate_converse_request(self, messages: List[Dict[str, Any]]) -> None:
        """
        Validate a converse request.

        Args:
            messages: Messages to validate

        Raises:
            RequestValidationError: If validation fails
        """
        if not messages:
            raise RequestValidationError(LLMManagerErrorMessages.EMPTY_MESSAGES)

        validation_errors = []

        for i, message in enumerate(messages):
            if not isinstance(message, dict):
                validation_errors.append(f"Message {i} must be a dictionary")
                continue

            # Check required fields
            if ConverseAPIFields.ROLE not in message:
                validation_errors.append(f"Message {i} missing required 'role' field")
            elif message[ConverseAPIFields.ROLE] not in [
                ConverseAPIFields.ROLE_USER,
                ConverseAPIFields.ROLE_ASSISTANT,
            ]:
                validation_errors.append(
                    f"Message {i} has invalid role: {message[ConverseAPIFields.ROLE]}"
                )

            if ConverseAPIFields.CONTENT not in message:
                validation_errors.append(f"Message {i} missing required 'content' field")
            elif not isinstance(message[ConverseAPIFields.CONTENT], list):
                validation_errors.append(f"Message {i} content must be a list")
            else:
                # Validate content blocks
                self._validate_content_blocks(
                    message[ConverseAPIFields.CONTENT], i, validation_errors
                )

        if validation_errors:
            raise RequestValidationError(
                message="Request validation failed", validation_errors=validation_errors
            )
        # Implicit return here - defensive code for robustness

    def _validate_content_blocks(
        self, content_blocks: List[Dict], message_index: int, errors: List[str]
    ) -> None:
        """Validate content blocks within a message."""
        image_count = 0
        document_count = 0
        video_count = 0

        for j, block in enumerate(content_blocks):
            if not isinstance(block, dict):
                errors.append(f"Message {message_index}, block {j} must be a dictionary")
                continue

            # Count content types
            if ConverseAPIFields.IMAGE in block:
                image_count += 1
            elif ConverseAPIFields.DOCUMENT in block:
                document_count += 1
            elif ConverseAPIFields.VIDEO in block:
                video_count += 1

        # Check limits
        if image_count > ContentLimits.MAX_IMAGES_PER_REQUEST:
            errors.append(
                f"Message {message_index} exceeds image limit: {image_count} > {ContentLimits.MAX_IMAGES_PER_REQUEST}"
            )

        if document_count > ContentLimits.MAX_DOCUMENTS_PER_REQUEST:
            errors.append(
                f"Message {message_index} exceeds document limit: {document_count} > {ContentLimits.MAX_DOCUMENTS_PER_REQUEST}"
            )

        if video_count > ContentLimits.MAX_VIDEOS_PER_REQUEST:
            errors.append(
                f"Message {message_index} exceeds video limit: {video_count} > {ContentLimits.MAX_VIDEOS_PER_REQUEST}"
            )
        # Implicit return here - defensive code for robustness

    def _build_converse_request(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[List[Dict[str, str]]] = None,
        inference_config: Optional[Dict[str, Any]] = None,
        additional_model_request_fields: Optional[Dict[str, Any]] = None,
        additional_model_response_field_paths: Optional[List[str]] = None,
        guardrail_config: Optional[Dict[str, Any]] = None,
        tool_config: Optional[Dict[str, Any]] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
        prompt_variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build the request arguments for the Converse API."""
        # Explicitly type the request args dictionary to avoid type inference issues
        request_args: Dict[str, Any] = {ConverseAPIFields.MESSAGES: messages}

        # Add optional fields
        if system:
            request_args[ConverseAPIFields.SYSTEM] = system

        # Merge default and provided inference config
        effective_inference_config = self._default_inference_config.copy()
        if inference_config:
            effective_inference_config.update(inference_config)

        if effective_inference_config:
            request_args[ConverseAPIFields.INFERENCE_CONFIG] = effective_inference_config

        if additional_model_request_fields:
            request_args[ConverseAPIFields.ADDITIONAL_MODEL_REQUEST_FIELDS] = (
                additional_model_request_fields
            )

        if additional_model_response_field_paths:
            request_args[ConverseAPIFields.ADDITIONAL_MODEL_RESPONSE_FIELD_PATHS] = (
                additional_model_response_field_paths
            )

        if guardrail_config:
            request_args[ConverseAPIFields.GUARDRAIL_CONFIG] = guardrail_config

        if tool_config:
            request_args[ConverseAPIFields.TOOL_CONFIG] = tool_config

        if request_metadata:
            request_args[ConverseAPIFields.REQUEST_METADATA] = request_metadata

        if prompt_variables:
            request_args[ConverseAPIFields.PROMPT_VARIABLES] = prompt_variables

        return request_args

    def _execute_converse(self, region: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute a single converse request.

        This method is called by the RetryManager with prepared arguments including
        the model_id. The region should be provided by the RetryManager.

        Args:
            region: AWS region to use for the request
            **kwargs: Prepared arguments for the Bedrock converse API call

        Returns:
            Dictionary containing the Bedrock API response

        Raises:
            AuthenticationError: If authentication fails
        """
        # Determine region - prefer provided region, fallback to first available
        target_region = region
        if not target_region:
            # Fallback: try to find a working region
            for test_region in self._regions:
                try:
                    # Try to get a client to see if the region is configured
                    self._auth_manager.get_bedrock_client(region=test_region)
                    target_region = test_region
                    break
                except Exception:
                    continue  # Try the next region
            else:
                # This block executes if the loop completes without a break
                raise AuthenticationError("Could not authenticate to any specified region")

        # At this point, target_region is guaranteed to be a non-empty string.
        client = self._auth_manager.get_bedrock_client(region=target_region)

        # Map model_id to modelId for AWS API compatibility
        converse_args = kwargs.copy()
        if "model_id" in converse_args:
            converse_args["modelId"] = converse_args.pop("model_id")

        # Execute the converse call with all prepared arguments
        response = client.converse(**converse_args)

        return cast(Dict[str, Any], response)

    def _execute_converse_stream(
        self, region: Optional[str] = None, **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Execute a single streaming converse request.

        This method is called by the RetryManager with prepared arguments including
        the model_id. The region should be provided by the RetryManager.

        Args:
            region: AWS region to use for the request
            **kwargs: Prepared arguments for the Bedrock converse_stream API call

        Returns:
            Dictionary containing the Bedrock API streaming response

        Raises:
            AuthenticationError: If authentication fails
        """
        # Determine region - prefer provided region, fallback to first available
        target_region = region
        if not target_region:
            # Fallback: try to find a working region
            for test_region in self._regions:
                try:
                    # Try to get a client to see if the region is configured
                    self._auth_manager.get_bedrock_client(region=test_region)
                    target_region = test_region
                    break
                except Exception:
                    continue  # Try the next region
            else:
                # This block executes if the loop completes without a break
                raise AuthenticationError("Could not authenticate to any specified region")

        # At this point, target_region is guaranteed to be a non-empty string.
        client = self._auth_manager.get_bedrock_client(region=target_region)

        # Map model_id to modelId for AWS API compatibility
        converse_stream_args = kwargs.copy()
        if "model_id" in converse_stream_args:
            converse_stream_args["modelId"] = converse_stream_args.pop("model_id")

        # Execute the streaming converse call with all prepared arguments
        response = client.converse_stream(**converse_stream_args)

        return cast(Dict[str, Any], response)

    def get_available_models(self) -> List[str]:
        """
        Get list of currently configured models.

        Returns:
            List of model names
        """
        return self._models.copy()

    def get_available_regions(self) -> List[str]:
        """
        Get list of currently configured regions.

        Returns:
            List of region names
        """
        return self._regions.copy()

    def get_model_access_info(self, model_name: str, region: str) -> Optional[Dict[str, Any]]:
        """
        Get access information for a specific model in a region.

        Args:
            model_name: Name of the model
            region: AWS region

        Returns:
            Dictionary with access information, None if not available
        """
        try:
            access_info = self._unified_model_manager.get_model_access_info(
                model_name=model_name, region=region
            )
            if access_info:
                return {
                    "access_method": access_info.access_method.value,
                    "model_id": access_info.model_id,
                    "inference_profile_id": access_info.inference_profile_id,
                    "region": access_info.region,
                }
        except Exception as e:
            self._logger.debug(f"Could not get access info for {model_name} in {region}: {e}")

        return None

    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate the current configuration and return status information.

        Returns:
            Dictionary with validation results
        """
        validation_result: Dict[str, Union[bool, List[str], int, str]] = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "model_region_combinations": 0,
            "auth_status": "unknown",
        }

        # Check authentication
        try:
            auth_info = self._auth_manager.get_auth_info()
            validation_result["auth_status"] = auth_info["auth_type"]
        except Exception as e:
            validation_result["valid"] = False
            # Type assertion to help mypy
            cast(List[str], validation_result["errors"]).append(f"Authentication error: {str(e)}")

        # Check model/region combinations
        for model in self._models:
            for region in self._regions:
                try:
                    access_info = self._unified_model_manager.get_model_access_info(
                        model_name=model, region=region
                    )
                    if access_info:
                        # Type assertion to help mypy
                        validation_result["model_region_combinations"] = (
                            cast(int, validation_result["model_region_combinations"]) + 1
                        )
                except Exception as e:
                    # Type assertion to help mypy
                    cast(List[str], validation_result["warnings"]).append(
                        f"Could not validate {model} in {region}: {str(e)}"
                    )

        if validation_result["model_region_combinations"] == 0:
            validation_result["valid"] = False
            # Type assertion to help mypy
            cast(List[str], validation_result["errors"]).append(
                "No valid model/region combinations found"
            )

        return validation_result

    def refresh_model_data(self) -> None:
        """
        Refresh the unified model data.

        Raises:
            LLMManagerError: If refresh fails
        """
        try:
            self._unified_model_manager.refresh_unified_data()
            self._logger.info("Model data refreshed successfully")
        except Exception as e:
            raise LLMManagerError(f"Failed to refresh model data: {str(e)}") from e

    def get_retry_stats(self) -> Dict[str, Any]:
        """
        Get retry configuration statistics.

        Returns:
            Dictionary with retry statistics
        """
        return self._retry_manager.get_retry_stats()

    def converse_with_request(
        self,
        request: BedrockConverseRequest,
        response_validation_config: Optional[ResponseValidationConfig] = None,
    ) -> BedrockResponse:
        """
        Send a conversation request using BedrockConverseRequest object.

        This method provides compatibility with the new parallel processing
        request structure while using the existing retry and error handling logic.

        Args:
            request: BedrockConverseRequest containing all parameters
            response_validation_config: Optional validation configuration

        Returns:
            BedrockResponse with the conversation result

        Raises:
            RequestValidationError: If request validation fails
            RetryExhaustedError: If all retry attempts fail
            AuthenticationError: If authentication fails
        """
        # Convert BedrockConverseRequest to existing converse() parameters
        converse_args = request.to_converse_args()

        return self.converse(response_validation_config=response_validation_config, **converse_args)

    def __repr__(self) -> str:
        """Return string representation of the LLMManager."""
        return (
            f"LLMManager(models={len(self._models)}, regions={len(self._regions)}, "
            f"auth={self._auth_manager.get_auth_info()['auth_type']})"
        )
