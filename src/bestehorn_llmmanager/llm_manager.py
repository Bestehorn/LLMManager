"""
LLMManager - Main class for managing AWS Bedrock Converse API interactions.

Provides a unified interface for interacting with multiple LLMs across regions
with automatic retry logic, authentication handling, and comprehensive response management.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

from .bedrock.auth.auth_manager import AuthManager
from .bedrock.builders.parameter_builder import ParameterBuilder
from .bedrock.cache import CachePointManager
from .bedrock.catalog import BedrockModelCatalog
from .bedrock.exceptions.llm_manager_exceptions import (
    AuthenticationError,
    ConfigurationError,
    LLMManagerError,
    RequestValidationError,
    RetryExhaustedError,
)
from .bedrock.models.bedrock_response import BedrockResponse, StreamingResponse
from .bedrock.models.cache_structures import CacheConfig
from .bedrock.models.catalog_structures import CacheMode
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
from .bedrock.models.model_specific_structures import ModelSpecificConfig
from .bedrock.models.parallel_structures import BedrockConverseRequest
from .bedrock.retry.retry_manager import RetryManager
from .bedrock.streaming.streaming_retry_manager import StreamingRetryManager
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
        cache_config: Optional[CacheConfig] = None,
        unified_model_manager: Optional[UnifiedModelManager] = None,
        catalog_cache_mode: Optional[CacheMode] = None,
        catalog_cache_directory: Optional[Path] = None,
        force_download: bool = False,
        strict_cache_mode: bool = False,
        ignore_cache_age: bool = False,
        default_inference_config: Optional[Dict[str, Any]] = None,
        model_specific_config: Optional[ModelSpecificConfig] = None,
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
            cache_config: Cache configuration for prompt caching. If None, caching is disabled
            unified_model_manager: DEPRECATED - Pre-configured UnifiedModelManager for backward
                                  compatibility. If None, uses new BedrockModelCatalog.
            catalog_cache_mode: Cache mode for model catalog (FILE, MEMORY, NONE).
                               If None, defaults to FILE. Ignored if unified_model_manager provided.
            catalog_cache_directory: Directory for catalog cache file.
                                    If None, uses platform-specific default.
                                    Ignored if unified_model_manager provided.
            force_download: DEPRECATED - Use catalog_cache_mode=CacheMode.NONE with force_refresh
                           instead. If True, force download fresh model data during initialization.
                           Note: This parameter is ignored if unified_model_manager is provided.
            strict_cache_mode: DEPRECATED - Applies only to legacy UnifiedModelManager.
                              If True, fail when expired model profile cache cannot be refreshed.
            ignore_cache_age: DEPRECATED - Applies only to legacy UnifiedModelManager.
                             If True, bypass model profile cache age validation entirely.
            default_inference_config: Default inference parameters to apply
            model_specific_config: Default configuration for model-specific parameters
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
        self._default_model_specific_config = model_specific_config

        # Initialize components
        self._auth_manager = AuthManager(auth_config=auth_config)
        self._retry_manager = RetryManager(retry_config=retry_config or RetryConfig())
        self._streaming_retry_manager = StreamingRetryManager(
            retry_config=retry_config or RetryConfig()
        )
        self._parameter_builder = ParameterBuilder()

        # Initialize cache manager if caching is enabled
        self._cache_config = cache_config or CacheConfig(enabled=False)
        self._cache_point_manager = None
        if self._cache_config.enabled:
            self._cache_point_manager = CachePointManager(self._cache_config)
            self._logger.info(f"Caching enabled with strategy: {self._cache_config.strategy.value}")

        # Initialize model catalog (new system or legacy for backward compatibility)
        if unified_model_manager:
            # Legacy path: use provided UnifiedModelManager
            self._logger.warning(
                "Using deprecated UnifiedModelManager. Please migrate to BedrockModelCatalog. "
                "The unified_model_manager parameter will be removed in a future version. "
                "See migration guide for details."
            )
            self._unified_model_manager = unified_model_manager
            self._catalog = None  # Not using new catalog

            # Handle force_download conflict
            if force_download:
                self._logger.warning(
                    "Both 'unified_model_manager' and 'force_download=True' were provided. "
                    "The 'force_download' parameter will be ignored since a pre-configured "
                    "UnifiedModelManager was supplied."
                )

            # Initialize model data with legacy manager
            self._initialize_model_data_legacy(force_download=False)
        else:
            # New path: use BedrockModelCatalog
            self._unified_model_manager = None  # type: ignore  # Not using legacy manager

            # Determine catalog cache mode
            effective_cache_mode = catalog_cache_mode or CacheMode.FILE

            # Handle deprecated parameters
            if force_download:
                self._logger.warning(
                    "The 'force_download' parameter is deprecated. "
                    "Using force_refresh=True with BedrockModelCatalog instead."
                )

            if strict_cache_mode or ignore_cache_age:
                self._logger.warning(
                    "The 'strict_cache_mode' and 'ignore_cache_age' parameters are deprecated "
                    "and only apply to the legacy UnifiedModelManager. "
                    "They are ignored when using BedrockModelCatalog."
                )

            # Initialize BedrockModelCatalog
            self._catalog = BedrockModelCatalog(
                auth_manager=self._auth_manager,
                cache_mode=effective_cache_mode,
                cache_directory=catalog_cache_directory,
                force_refresh=force_download,  # Map force_download to force_refresh
                timeout=timeout,
            )

            # Ensure catalog is available (will trigger initialization strategy)
            try:
                self._catalog.ensure_catalog_available()
                self._logger.info("Model catalog initialized successfully")
            except Exception as e:
                raise ConfigurationError(f"Failed to initialize model catalog: {str(e)}") from e

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

    def _initialize_model_data_legacy(self, force_download: bool = False) -> None:
        """
        Initialize model data for the legacy UnifiedModelManager.

        DEPRECATED: This method is only used for backward compatibility with
        the legacy UnifiedModelManager. New code should use BedrockModelCatalog.

        This method attempts to load cached model data first (unless force_download is True),
        and if unavailable, refreshes the data by downloading from AWS documentation. Model
        data is required for LLMManager to operate properly.

        Args:
            force_download: If True, skip cache and force download fresh data

        Raises:
            ConfigurationError: If model data cannot be loaded or refreshed
        """
        try:
            if not force_download:
                # Try to load cached data first
                cached_catalog = self._load_cached_model_data()
                if cached_catalog is not None:
                    self._logger.info("Successfully loaded cached model data")
                    return
            else:
                self._logger.info("Force download requested - skipping cache check")

            # No cached data available or force_download=True, refresh from AWS
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

        Uses the catalog's name resolution system to provide helpful error messages
        with suggestions when model names cannot be resolved.

        Raises:
            ConfigurationError: If no valid model/region combinations are found
        """
        available_combinations = 0
        validation_errors = []

        for model in self._models:
            model_found_in_any_region = False
            for region in self._regions:
                try:
                    # Use appropriate method based on which system is active
                    if self._catalog:
                        # New catalog system - uses name resolution internally
                        access_info = self._catalog.get_model_info(model_name=model, region=region)
                    else:
                        # Legacy UnifiedModelManager
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
                # Build detailed error message with suggestions
                error_msg = self._build_model_not_found_error(model_name=model)
                validation_errors.append(error_msg)

        if available_combinations == 0:
            # Build comprehensive error message
            error_message = self._build_no_combinations_error(validation_errors=validation_errors)
            self._logger.error(error_message)
            raise ConfigurationError(error_message)

    def _build_model_not_found_error(self, model_name: str) -> str:
        """
        Build a detailed error message for a model that wasn't found.

        Args:
            model_name: The model name that wasn't found

        Returns:
            Detailed error message with suggestions
        """
        error_parts = [f"Model '{model_name}' not found in any specified region."]

        # Try to get suggestions from name resolver
        if self._catalog:
            try:
                resolver = self._catalog._get_name_resolver()
                suggestions = resolver.get_suggestions(user_name=model_name, max_suggestions=3)

                if suggestions:
                    error_parts.append(f"Did you mean: {', '.join(suggestions)}?")
                else:
                    # No suggestions available - provide general guidance
                    error_parts.append(
                        "Check the model name spelling or use catalog.list_models() "
                        "to see available models."
                    )
            except Exception as e:
                self._logger.debug(f"Could not get suggestions for {model_name}: {e}")
                error_parts.append("Check the model name and region availability.")

        return " ".join(error_parts)

    def _build_no_combinations_error(self, validation_errors: List[str]) -> str:
        """
        Build a comprehensive error message when no valid combinations are found.

        Args:
            validation_errors: List of validation error messages for each model

        Returns:
            Comprehensive error message with all details
        """
        error_details = []
        error_details.append("No valid model/region combinations found during initialization.")
        error_details.append(f"Models specified: {self._models}")
        error_details.append(f"Regions specified: {self._regions}")
        error_details.extend(validation_errors)

        # Add catalog status information
        try:
            if self._catalog:
                # New catalog system
                if not self._catalog.is_catalog_loaded:
                    error_details.append(
                        "No model data available. Try refreshing model data or "
                        "ensure internet connectivity."
                    )
                else:
                    # Show sample of available models
                    available_models = [m.model_name for m in self._catalog.list_models()[:10]]
                    error_details.append(f"Available models (sample): {available_models}")
            else:
                # Legacy system
                if not self._unified_model_manager._cached_catalog:
                    error_details.append(
                        "No model data available. Try refreshing model data or "
                        "ensure internet connectivity."
                    )
                else:
                    available_models = self._unified_model_manager.get_model_names()[:10]
                    error_details.append(f"Available models (sample): {available_models}")
        except Exception:
            error_details.append("Could not retrieve available model information.")

        return " ".join(error_details)

    def converse(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[List[Dict[str, str]]] = None,
        inference_config: Optional[Dict[str, Any]] = None,
        additional_model_request_fields: Optional[Dict[str, Any]] = None,
        model_specific_config: Optional[ModelSpecificConfig] = None,
        enable_extended_context: bool = False,
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
            additional_model_request_fields: Model-specific request parameters (legacy)
            model_specific_config: Configuration for model-specific parameters (overrides default)
            enable_extended_context: Convenience flag to enable extended context window
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

        # Determine effective model_specific_config
        # Priority: per-request config > enable_extended_context flag > default config
        effective_model_specific_config = self._resolve_model_specific_config(
            model_specific_config=model_specific_config,
            enable_extended_context=enable_extended_context,
        )

        # Build request arguments
        request_args = self._build_converse_request(
            messages=messages,
            system=system,
            inference_config=inference_config,
            additional_model_request_fields=additional_model_request_fields,
            model_specific_config=effective_model_specific_config,
            additional_model_response_field_paths=additional_model_response_field_paths,
            guardrail_config=guardrail_config,
            tool_config=tool_config,
            request_metadata=request_metadata,
            prompt_variables=prompt_variables,
        )

        # Generate retry targets
        # Pass the appropriate manager based on which system is active
        manager_for_retry = self._catalog if self._catalog else self._unified_model_manager
        retry_targets = self._retry_manager.generate_retry_targets(
            models=self._models,
            regions=self._regions,
            unified_model_manager=manager_for_retry,
        )

        if not retry_targets:
            # Build error message with suggestions
            error_parts = ["No valid model/region combinations available."]

            # Try to get suggestions for each model
            if self._catalog:
                try:
                    resolver = self._catalog._get_name_resolver()
                    for model in self._models:
                        suggestions = resolver.get_suggestions(user_name=model, max_suggestions=3)
                        if suggestions:
                            error_parts.append(
                                f"Model '{model}' not found. Did you mean: {', '.join(suggestions)}?"
                            )
                        else:
                            error_parts.append(f"Model '{model}' not found.")
                except Exception as e:
                    self._logger.debug(f"Could not get suggestions: {e}")
                    error_parts.append("Check model names and region availability.")
            else:
                error_parts.append("Check model names and region availability.")

            raise ConfigurationError(" ".join(error_parts))

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

            # Determine if profile was used and extract profile ID
            inference_profile_used = False
            inference_profile_id = None
            if successful_attempt:
                # Check if access method indicates profile usage
                access_method = successful_attempt.access_method
                if access_method in ["regional_cris", "global_cris"]:
                    inference_profile_used = True
                    inference_profile_id = (
                        successful_attempt.model_id
                    )  # model_id contains profile ARN

            # Create response object
            response = BedrockResponse(
                success=True,
                response_data=result,
                model_used=successful_attempt.model_id if successful_attempt else None,
                region_used=successful_attempt.region if successful_attempt else None,
                access_method_used=successful_attempt.access_method if successful_attempt else None,
                inference_profile_used=inference_profile_used,
                inference_profile_id=inference_profile_id,
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
        model_specific_config: Optional[ModelSpecificConfig] = None,
        enable_extended_context: bool = False,
        additional_model_response_field_paths: Optional[List[str]] = None,
        guardrail_config: Optional[Dict[str, Any]] = None,
        tool_config: Optional[Dict[str, Any]] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
        prompt_variables: Optional[Dict[str, Any]] = None,
    ) -> StreamingResponse:
        """
        Send a streaming conversation request to available models with retry logic and recovery.

        This method uses the AWS Bedrock converse_stream API to provide real-time streaming
        responses with intelligent retry logic, stream interruption recovery, and comprehensive
        error handling.

        Args:
            messages: List of message objects for the conversation
            system: List of system message objects
            inference_config: Inference configuration parameters
            additional_model_request_fields: Model-specific request parameters (legacy)
            model_specific_config: Configuration for model-specific parameters (overrides default)
            enable_extended_context: Convenience flag to enable extended context window
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
        request_start = datetime.now()

        # Validate request
        self._validate_converse_request(messages=messages)

        # Determine effective model_specific_config
        # Priority: per-request config > enable_extended_context flag > default config
        effective_model_specific_config = self._resolve_model_specific_config(
            model_specific_config=model_specific_config,
            enable_extended_context=enable_extended_context,
        )

        # Build request arguments (same as regular converse but we'll handle streaming)
        request_args = self._build_converse_request(
            messages=messages,
            system=system,
            inference_config=inference_config,
            additional_model_request_fields=additional_model_request_fields,
            model_specific_config=effective_model_specific_config,
            additional_model_response_field_paths=additional_model_response_field_paths,
            guardrail_config=guardrail_config,
            tool_config=tool_config,
            request_metadata=request_metadata,
            prompt_variables=prompt_variables,
        )

        # Generate retry targets using the regular retry manager
        # Pass the appropriate manager based on which system is active
        manager_for_retry = self._catalog if self._catalog else self._unified_model_manager
        retry_targets = self._retry_manager.generate_retry_targets(
            models=self._models,
            regions=self._regions,
            unified_model_manager=manager_for_retry,
        )

        if not retry_targets:
            # Build error message with suggestions
            error_parts = ["No valid model/region combinations available for streaming."]

            # Try to get suggestions for each model
            if self._catalog:
                try:
                    resolver = self._catalog._get_name_resolver()
                    for model in self._models:
                        suggestions = resolver.get_suggestions(user_name=model, max_suggestions=3)
                        if suggestions:
                            error_parts.append(
                                f"Model '{model}' not found. Did you mean: {', '.join(suggestions)}?"
                            )
                        else:
                            error_parts.append(f"Model '{model}' not found.")
                except Exception as e:
                    self._logger.debug(f"Could not get suggestions: {e}")
                    error_parts.append("Check model names and region availability.")
            else:
                error_parts.append("Check model names and region availability.")

            raise ConfigurationError(" ".join(error_parts))

        try:
            # Execute with streaming retry logic and recovery
            streaming_response, attempts, warnings = (
                self._streaming_retry_manager.execute_streaming_with_recovery(
                    operation=self._execute_converse_stream,
                    operation_args=request_args,
                    retry_targets=retry_targets,
                )
            )

            # Add attempt information and warnings
            streaming_response.warnings = warnings

            return streaming_response

        except RetryExhaustedError as e:
            # Create failed streaming response
            total_duration = (datetime.now() - request_start).total_seconds() * 1000

            streaming_response = StreamingResponse(
                success=False, stream_errors=[e], total_duration_ms=total_duration
            )

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

    def _resolve_model_specific_config(
        self,
        model_specific_config: Optional[ModelSpecificConfig],
        enable_extended_context: bool,
    ) -> Optional[ModelSpecificConfig]:
        """
        Resolve the effective model_specific_config from multiple sources.

        Priority order:
        1. Per-request model_specific_config (if provided)
        2. Create config from enable_extended_context flag (if True)
        3. Default model_specific_config from __init__ (if set)
        4. None (no model-specific configuration)

        Args:
            model_specific_config: Per-request configuration
            enable_extended_context: Convenience flag for extended context

        Returns:
            Effective ModelSpecificConfig or None
        """
        # If per-request config provided, use it (highest priority)
        if model_specific_config is not None:
            return model_specific_config

        # If enable_extended_context flag is True, create config from it
        if enable_extended_context:
            return ModelSpecificConfig(enable_extended_context=True)

        # Fall back to default config from __init__
        return self._default_model_specific_config

    def _build_converse_request(
        self,
        messages: List[Dict[str, Any]],
        system: Optional[List[Dict[str, str]]] = None,
        inference_config: Optional[Dict[str, Any]] = None,
        additional_model_request_fields: Optional[Dict[str, Any]] = None,
        model_specific_config: Optional[ModelSpecificConfig] = None,
        additional_model_response_field_paths: Optional[List[str]] = None,
        guardrail_config: Optional[Dict[str, Any]] = None,
        tool_config: Optional[Dict[str, Any]] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
        prompt_variables: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build the request arguments for the Converse API.

        Args:
            messages: List of message objects
            system: System message objects
            inference_config: Inference configuration
            additional_model_request_fields: Direct model-specific fields (legacy)
            model_specific_config: Structured model-specific configuration
            additional_model_response_field_paths: Additional response fields
            guardrail_config: Guardrail configuration
            tool_config: Tool configuration
            request_metadata: Request metadata
            prompt_variables: Prompt variables

        Returns:
            Dictionary of request arguments for the Converse API
        """
        # Apply cache point injection if caching is enabled
        processed_messages = messages
        if self._cache_point_manager and self._cache_config.enabled:
            # Note: Model and region will be determined during retry execution
            # For now, we inject cache points without model/region validation
            processed_messages = self._cache_point_manager.inject_cache_points(messages)

            # Validate cache configuration
            validation_warnings = self._cache_point_manager.validate_cache_configuration(
                {ConverseAPIFields.MESSAGES: processed_messages}
            )
            for warning in validation_warnings:
                self._logger.warning(f"Cache configuration warning: {warning}")

        # Explicitly type the request args dictionary to avoid type inference issues
        request_args: Dict[str, Any] = {ConverseAPIFields.MESSAGES: processed_messages}

        # Add optional fields
        if system:
            request_args[ConverseAPIFields.SYSTEM] = system

        # Merge default and provided inference config
        effective_inference_config = self._default_inference_config.copy()
        if inference_config:
            effective_inference_config.update(inference_config)

        if effective_inference_config:
            request_args[ConverseAPIFields.INFERENCE_CONFIG] = effective_inference_config

        # Build additionalModelRequestFields using ParameterBuilder
        # Use the first model as a reference for model-specific parameter building
        # The retry manager will rebuild if needed for different models
        reference_model = self._models[0] if self._models else ""

        built_additional_fields = None
        if model_specific_config is not None or additional_model_request_fields is not None:
            built_additional_fields = self._parameter_builder.build_additional_fields(
                model_name=reference_model,
                model_specific_config=model_specific_config,
                additional_model_request_fields=additional_model_request_fields,
            )

        if built_additional_fields:
            request_args[ConverseAPIFields.ADDITIONAL_MODEL_REQUEST_FIELDS] = (
                built_additional_fields
            )

        # Store model_specific_config for retry manager to rebuild parameters per model
        if model_specific_config is not None:
            request_args["_model_specific_config"] = model_specific_config

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
            # Use appropriate method based on which system is active
            if self._catalog:
                # New catalog system
                access_info = self._catalog.get_model_info(model_name=model_name, region=region)
            else:
                # Legacy UnifiedModelManager
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
                    # Use appropriate method based on which system is active
                    if self._catalog:
                        # New catalog system
                        access_info = self._catalog.get_model_info(model_name=model, region=region)
                    else:
                        # Legacy UnifiedModelManager
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
            # Use appropriate method based on which system is active
            if self._catalog:
                # New catalog system
                self._catalog.refresh_catalog()
                self._logger.info("Model catalog refreshed successfully")
            else:
                # Legacy UnifiedModelManager
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
