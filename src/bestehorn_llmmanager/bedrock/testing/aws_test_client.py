"""
AWS test client for Bedrock integration testing.

This module provides a test-specific client that wraps the existing authentication
and Bedrock functionality with additional features for integration testing,
including cost tracking, request validation, and test data management.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..auth.auth_manager import AuthManager
from ..models.bedrock_response import BedrockResponse
from ..models.llm_manager_structures import AuthConfig, AuthenticationType
from ..UnifiedModelManager import UnifiedModelManager
from .integration_config import IntegrationTestConfig, IntegrationTestError


@dataclass
class TestRequestMetrics:
    """
    Metrics for a single test request.

    Tracks performance, cost, and execution details for integration test requests.
    """

    request_id: str
    model_id: str
    region: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    response_metadata: Optional[Dict[str, Any]] = None

    def mark_completed(self, success: bool = True, error_message: Optional[str] = None) -> None:
        """
        Mark the request as completed and calculate duration.

        Args:
            success: Whether the request succeeded
            error_message: Error message if request failed
        """
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.success = success
        self.error_message = error_message

    def calculate_estimated_cost(
        self, input_cost_per_1k: float = 0.001, output_cost_per_1k: float = 0.002
    ) -> None:
        """
        Calculate estimated cost based on token usage.

        Args:
            input_cost_per_1k: Cost per 1000 input tokens
            output_cost_per_1k: Cost per 1000 output tokens
        """
        if self.input_tokens is not None and self.output_tokens is not None:
            input_cost = (self.input_tokens / 1000) * input_cost_per_1k
            output_cost = (self.output_tokens / 1000) * output_cost_per_1k
            self.estimated_cost_usd = input_cost + output_cost


@dataclass
class TestSession:
    """
    Test session for tracking multiple requests and cumulative metrics.

    Provides session-level tracking of costs, performance, and request patterns
    across multiple integration test requests.
    """

    session_id: str
    config: IntegrationTestConfig
    start_time: datetime = field(default_factory=datetime.now)
    requests: List[TestRequestMetrics] = field(default_factory=list)
    total_estimated_cost_usd: float = 0.0

    def add_request_metrics(self, metrics: TestRequestMetrics) -> None:
        """
        Add request metrics to the session.

        Args:
            metrics: Request metrics to add
        """
        self.requests.append(metrics)
        if metrics.estimated_cost_usd is not None:
            self.total_estimated_cost_usd += metrics.estimated_cost_usd

    def check_cost_limit(self) -> None:
        """
        Check if the session has exceeded the configured cost limit.

        Raises:
            IntegrationTestError: If cost limit is exceeded
        """
        if self.total_estimated_cost_usd > self.config.cost_limit_usd:
            raise IntegrationTestError(
                message=f"Test session cost limit exceeded: ${self.total_estimated_cost_usd:.4f} > ${self.config.cost_limit_usd:.4f}",
                details={
                    "session_id": self.session_id,
                    "current_cost": self.total_estimated_cost_usd,
                    "cost_limit": self.config.cost_limit_usd,
                    "request_count": len(self.requests),
                },
            )

    def get_summary(self) -> Dict[str, Any]:
        """
        Get session summary statistics.

        Returns:
            Dictionary with session summary information
        """
        successful_requests = [r for r in self.requests if r.success]
        failed_requests = [r for r in self.requests if not r.success]

        durations = [r.duration_seconds for r in self.requests if r.duration_seconds is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "total_requests": len(self.requests),
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "success_rate": len(successful_requests) / len(self.requests) if self.requests else 0.0,
            "total_estimated_cost_usd": self.total_estimated_cost_usd,
            "average_request_duration": avg_duration,
            "cost_limit_utilization": self.total_estimated_cost_usd / self.config.cost_limit_usd,
        }


class AWSTestClient:
    """
    AWS test client for Bedrock integration testing.

    This client provides a test-specific interface for making Bedrock API calls
    with additional features for integration testing including request tracking,
    cost monitoring, and test data validation.
    """

    def __init__(self, config: IntegrationTestConfig) -> None:
        """
        Initialize the AWS test client.

        Args:
            config: Integration test configuration

        Raises:
            IntegrationTestError: If initialization fails
        """
        self.config = config
        self._logger = logging.getLogger(__name__)

        # Validate configuration first
        if not self.config.enabled:
            raise IntegrationTestError(
                message="Integration tests are not enabled",
                details={"config": self.config.to_dict()},
            )

        # Initialize authentication manager
        auth_config = self._create_auth_config()
        self._auth_manager = AuthManager(auth_config=auth_config)

        # Initialize unified model manager for model resolution
        self._initialize_model_manager()

        # Validate that required test models are available
        self._validate_test_models()

        # Test session tracking
        self._current_session: Optional[TestSession] = None

    def _create_auth_config(self) -> AuthConfig:
        """
        Create authentication configuration from integration test config.

        Returns:
            Configured AuthConfig instance
        """
        if self.config.aws_profile:
            return AuthConfig(
                auth_type=AuthenticationType.PROFILE, profile_name=self.config.aws_profile
            )
        else:
            return AuthConfig(auth_type=AuthenticationType.AUTO)

    def _initialize_model_manager(self) -> None:
        """
        Initialize the UnifiedModelManager with automatic cache management.

        Raises:
            IntegrationTestError: If model data cannot be loaded
        """
        self._logger.info("Initializing UnifiedModelManager for integration tests")

        try:
            self._unified_model_manager = UnifiedModelManager()

            # Use the new automatic cache management
            self._logger.debug("Ensuring model data is available with automatic cache management")
            catalog = self._unified_model_manager.ensure_data_available()

            model_count = catalog.model_count
            self._logger.info(f"Successfully initialized with {model_count} models")

        except Exception as e:
            error_msg = f"Failed to initialize UnifiedModelManager: {str(e)}"
            self._logger.error(error_msg)
            raise IntegrationTestError(message=error_msg, details={"original_error": str(e)}) from e

    def _refresh_model_data_with_retry(self, max_retries: int = 3) -> None:
        """
        Refresh model data with retry logic.

        Args:
            max_retries: Maximum number of retry attempts

        Raises:
            IntegrationTestError: If all retry attempts fail
        """
        last_exception = None

        for attempt in range(max_retries):
            try:
                self._logger.info(
                    f"Attempting to refresh model data (attempt {attempt + 1}/{max_retries})"
                )
                self._unified_model_manager.refresh_unified_data()
                self._logger.info("Successfully refreshed model data")
                return
            except Exception as e:
                last_exception = e
                self._logger.warning(f"Model data refresh attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    self._logger.info("Retrying in 2 seconds...")
                    time.sleep(2)

        # All attempts failed
        error_msg = f"Failed to refresh model data after {max_retries} attempts"
        self._logger.error(error_msg)
        raise IntegrationTestError(
            message=error_msg, details={"last_error": str(last_exception), "attempts": max_retries}
        ) from last_exception

    def _validate_test_models(self) -> None:
        """
        Validate that configured test models are available in the model data.

        This method now uses a more tolerant approach - it will log warnings for
        missing models but only fail if NO test models are available.

        Raises:
            IntegrationTestError: If no test models are available at all
        """
        self._logger.info("Validating test model availability")

        try:
            # Check if model manager has any data
            try:
                available_models = self._unified_model_manager.get_model_names()
                total_models = len(available_models)
                self._logger.info(f"Total models available: {total_models}")

                if total_models == 0:
                    raise IntegrationTestError(
                        message="No model data available from UnifiedModelManager",
                        details={"total_models": total_models},
                    )

            except Exception as model_access_error:
                self._logger.error(f"Cannot access model data: {model_access_error}")
                raise IntegrationTestError(
                    message=f"Failed to access model data from UnifiedModelManager: {str(model_access_error)}",
                    details={"original_error": str(model_access_error)},
                ) from model_access_error

            # Show first few models for debugging
            sample_models = []
            if available_models:
                sample_models = sorted(available_models)[:10]
                self._logger.info(f"Sample available models: {sample_models}")

            # Check each configured test model
            missing_models = []
            found_models = []

            for provider, model_name in self.config.test_models.items():
                self._logger.debug(f"Checking model '{model_name}' for provider '{provider}'")

                try:
                    if self._unified_model_manager.has_model(model_name=model_name):
                        found_models.append(f"{provider}: {model_name}")

                        # Test model access info for primary region
                        primary_region = self.config.get_primary_test_region()
                        access_info = self._unified_model_manager.get_model_access_info(
                            model_name=model_name, region=primary_region
                        )
                        if access_info:
                            self._logger.debug(f"Model '{model_name}' access info: {access_info}")
                        else:
                            self._logger.warning(
                                f"Model '{model_name}' found but no access info for region '{primary_region}'"
                            )
                    else:
                        missing_models.append(f"{provider}: {model_name}")
                        self._logger.warning(f"Model '{model_name}' not found in model data")

                        # Try to find similar model names for debugging
                        similar_models = [
                            m
                            for m in available_models
                            if model_name.lower() in m.lower() or m.lower() in model_name.lower()
                        ]
                        if similar_models:
                            self._logger.info(
                                f"Similar models found for '{model_name}': {similar_models[:3]}"
                            )
                        else:
                            self._logger.warning(f"No similar models found for '{model_name}'")

                except Exception as model_check_error:
                    self._logger.error(f"Error checking model '{model_name}': {model_check_error}")
                    missing_models.append(
                        f"{provider}: {model_name} (error: {str(model_check_error)})"
                    )

            # Log results
            if found_models:
                self._logger.info(f"Found test models: {found_models}")

            if missing_models:
                self._logger.warning(f"Missing test models: {missing_models}")

                # Only fail if NO models were found
                if not found_models:
                    raise IntegrationTestError(
                        message=f"No test models found in model data. Missing: {missing_models}",
                        details={
                            "missing_models": missing_models,
                            "found_models": found_models,
                            "total_available": total_models,
                            "sample_available": sample_models,
                            "configured_models": self.config.test_models,
                        },
                    )
                else:
                    self._logger.info(
                        f"Proceeding with {len(found_models)} available test models (out of {len(self.config.test_models)} configured)"
                    )
            else:
                self._logger.info(f"All {len(found_models)} test models validated successfully")

        except Exception as e:
            if isinstance(e, IntegrationTestError):
                raise
            error_msg = f"Failed to validate test models: {str(e)}"
            self._logger.error(error_msg)
            raise IntegrationTestError(message=error_msg, details={"original_error": str(e)}) from e

    def _resolve_model_id(self, model_name: str, region: str) -> Optional[str]:
        """
        Resolve a model name (friendly name) to the actual model ID for AWS API calls.

        Args:
            model_name: Model name (can be friendly name like "Claude 3 Haiku" or actual model ID)
            region: AWS region

        Returns:
            Actual model ID if found, None if not resolvable
        """
        try:
            # Get model access info from unified model manager
            access_info = self._unified_model_manager.get_model_access_info(
                model_name=model_name, region=region
            )

            if access_info and access_info.model_id:
                self._logger.debug(
                    f"Resolved model '{model_name}' to '{access_info.model_id}' in region '{region}'"
                )
                return access_info.model_id

            # If no access info found, check if model_name is already an actual model ID
            # (fallback for cases where friendly name resolution fails)
            if "." in model_name and any(
                provider in model_name
                for provider in ["anthropic", "amazon", "meta", "cohere", "ai21"]
            ):
                self._logger.debug(f"Model name '{model_name}' appears to be an actual model ID")
                return model_name

            self._logger.debug(f"Could not resolve model name '{model_name}' in region '{region}'")
            return None

        except Exception as e:
            self._logger.error(
                f"Error resolving model name '{model_name}' in region '{region}': {str(e)}"
            )
            return None

    def start_test_session(self, session_id: str) -> TestSession:
        """
        Start a new test session for tracking requests.

        Args:
            session_id: Unique identifier for the test session

        Returns:
            Created test session
        """
        self._logger.info(f"Starting integration test session: {session_id}")
        self._current_session = TestSession(session_id=session_id, config=self.config)
        return self._current_session

    def end_test_session(self) -> Optional[Dict[str, Any]]:
        """
        End the current test session and return summary.

        Returns:
            Session summary if session was active, None otherwise
        """
        if self._current_session is None:
            return None

        summary = self._current_session.get_summary()
        self._logger.info(f"Test session completed: {self._current_session.session_id}")
        self._logger.info(f"Session summary: {summary}")

        self._current_session = None
        return summary

    def test_authentication(self, region: str) -> Dict[str, Any]:
        """
        Test AWS authentication for a specific region.

        Args:
            region: AWS region to test authentication against

        Returns:
            Dictionary with authentication test results

        Raises:
            IntegrationTestError: If authentication fails
        """
        if not self.config.is_region_enabled(region):
            raise IntegrationTestError(
                message=f"Region {region} is not enabled for testing",
                details={"region": region, "enabled_regions": self.config.test_regions},
            )

        try:
            start_time = time.time()
            client = self._auth_manager.get_bedrock_client(region=region)
            duration = time.time() - start_time

            return {
                "success": True,
                "region": region,
                "duration_seconds": duration,
                "client_type": type(client).__name__,
                "auth_method": self.config.aws_profile or "auto",
            }

        except Exception as e:
            raise IntegrationTestError(
                message=f"Authentication test failed for region {region}: {str(e)}",
                details={
                    "region": region,
                    "auth_profile": self.config.aws_profile,
                    "original_error": str(e),
                },
            ) from e

    def test_bedrock_converse(
        self,
        model_id: str,
        messages: List[Dict[str, Any]],
        region: Optional[str] = None,
        **kwargs: Any,
    ) -> BedrockResponse:
        """
        Test Bedrock converse API with request tracking.

        Args:
            model_id: Model identifier to test (can be friendly name or actual model ID)
            messages: Messages for the conversation
            region: AWS region (uses primary test region if not specified)
            **kwargs: Additional arguments for the converse call

        Returns:
            Bedrock response

        Raises:
            IntegrationTestError: If the test request fails
        """
        # Validate inputs
        if not self.config.is_model_enabled(model_id):
            raise IntegrationTestError(
                message=f"Model {model_id} is not enabled for testing",
                details={
                    "model_id": model_id,
                    "enabled_models": list(self.config.test_models.values()),
                },
            )

        test_region = region or self.config.get_primary_test_region()
        if not self.config.is_region_enabled(test_region):
            raise IntegrationTestError(
                message=f"Region {test_region} is not enabled for testing",
                details={"region": test_region, "enabled_regions": self.config.test_regions},
            )

        # Resolve model name to actual model ID
        actual_model_id = self._resolve_model_id(model_id, test_region)
        if not actual_model_id:
            raise IntegrationTestError(
                message=f"Could not resolve model ID for {model_id} in region {test_region}",
                details={"model_name": model_id, "region": test_region},
            )

        # Create request metrics
        request_id = f"{model_id}_{test_region}_{int(time.time())}"
        metrics = TestRequestMetrics(request_id=request_id, model_id=model_id, region=test_region)

        try:
            # Get client and make request
            client = self._auth_manager.get_bedrock_client(region=test_region)

            # Prepare request arguments (use actual model ID for API call)
            request_args = {"modelId": actual_model_id, "messages": messages, **kwargs}

            # Make the API call
            self._logger.info(
                f"Making Bedrock converse request: {request_id} (using model ID: {actual_model_id})"
            )
            response = client.converse(**request_args)

            # Process response
            bedrock_response = BedrockResponse(
                success=True, response_data=response, model_used=model_id, region_used=test_region
            )

            # Update metrics
            if "usage" in response:
                usage = response["usage"]
                metrics.input_tokens = usage.get("inputTokens")
                metrics.output_tokens = usage.get("outputTokens")
                metrics.calculate_estimated_cost()

            metrics.response_metadata = response.get("ResponseMetadata", {})
            metrics.mark_completed(success=True)

            # Add to session if active
            if self._current_session:
                self._current_session.add_request_metrics(metrics)
                self._current_session.check_cost_limit()

            self._logger.info(f"Bedrock converse request completed successfully: {request_id}")
            return bedrock_response

        except Exception as e:
            error_message = str(e)
            metrics.mark_completed(success=False, error_message=error_message)

            if self._current_session:
                self._current_session.add_request_metrics(metrics)

            self._logger.error(f"Bedrock converse request failed: {request_id} - {error_message}")

            raise IntegrationTestError(
                message=f"Bedrock converse test failed: {error_message}",
                details={
                    "request_id": request_id,
                    "model_id": model_id,
                    "region": test_region,
                    "original_error": error_message,
                },
            ) from e

    def test_bedrock_converse_stream(
        self,
        model_id: str,
        messages: List[Dict[str, Any]],
        region: Optional[str] = None,
        **kwargs: Any,
    ) -> BedrockResponse:
        """
        Test Bedrock streaming converse API with request tracking.

        Args:
            model_id: Model identifier to test
            messages: Messages for the conversation
            region: AWS region (uses primary test region if not specified)
            **kwargs: Additional arguments for the converse_stream call

        Returns:
            Bedrock response with streaming data

        Raises:
            IntegrationTestError: If the test request fails
        """
        # Similar validation as regular converse
        if not self.config.is_model_enabled(model_id):
            raise IntegrationTestError(
                message=f"Model {model_id} is not enabled for testing",
                details={
                    "model_id": model_id,
                    "enabled_models": list(self.config.test_models.values()),
                },
            )

        test_region = region or self.config.get_primary_test_region()
        if not self.config.is_region_enabled(test_region):
            raise IntegrationTestError(
                message=f"Region {test_region} is not enabled for testing",
                details={"region": test_region, "enabled_regions": self.config.test_regions},
            )

        # Resolve model name to actual model ID
        actual_model_id = self._resolve_model_id(model_id, test_region)
        if not actual_model_id:
            raise IntegrationTestError(
                message=f"Could not resolve model ID for {model_id} in region {test_region}",
                details={"model_name": model_id, "region": test_region},
            )

        # Create request metrics
        request_id = f"{model_id}_{test_region}_stream_{int(time.time())}"
        metrics = TestRequestMetrics(request_id=request_id, model_id=model_id, region=test_region)

        try:
            # Get client and make streaming request
            client = self._auth_manager.get_bedrock_client(region=test_region)

            # Prepare request arguments (use actual model ID for API call)
            request_args = {"modelId": actual_model_id, "messages": messages, **kwargs}

            # Make the streaming API call
            self._logger.info(f"Making Bedrock streaming converse request: {request_id}")
            response = client.converse_stream(**request_args)

            # Process streaming response
            bedrock_response = BedrockResponse(
                success=True, response_data=response, model_used=model_id, region_used=test_region
            )

            metrics.mark_completed(success=True)

            # Add to session if active
            if self._current_session:
                self._current_session.add_request_metrics(metrics)
                self._current_session.check_cost_limit()

            self._logger.info(
                f"Bedrock streaming converse request completed successfully: {request_id}"
            )
            return bedrock_response

        except Exception as e:
            error_message = str(e)
            metrics.mark_completed(success=False, error_message=error_message)

            if self._current_session:
                self._current_session.add_request_metrics(metrics)

            self._logger.error(
                f"Bedrock streaming converse request failed: {request_id} - {error_message}"
            )

            raise IntegrationTestError(
                message=f"Bedrock streaming converse test failed: {error_message}",
                details={
                    "request_id": request_id,
                    "model_id": model_id,
                    "region": test_region,
                    "original_error": error_message,
                },
            ) from e

    def get_available_test_models(self) -> Dict[str, str]:
        """
        Get available models for testing.

        Returns:
            Dictionary mapping provider names to model IDs
        """
        return self.config.test_models.copy()

    def get_available_test_regions(self) -> List[str]:
        """
        Get available regions for testing.

        Returns:
            List of AWS region identifiers
        """
        return self.config.test_regions.copy()

    def validate_test_environment(self) -> Dict[str, Any]:
        """
        Validate the complete test environment setup.

        Returns:
            Dictionary with validation results

        Raises:
            IntegrationTestError: If validation fails
        """
        validation_results: Dict[str, Any] = {
            "overall_success": True,
            "config_valid": True,
            "auth_results": {},
            "model_availability": {},
            "errors": [],
        }

        try:
            # Test authentication for each region
            for region in self.config.test_regions:
                try:
                    auth_result = self.test_authentication(region=region)
                    validation_results["auth_results"][region] = auth_result
                except Exception as e:
                    validation_results["overall_success"] = False
                    validation_results["auth_results"][region] = {"success": False, "error": str(e)}
                    validation_results["errors"].append(
                        f"Authentication failed for {region}: {str(e)}"
                    )

            # TODO: Add model availability checks when we have model listing functionality

            return validation_results

        except Exception as e:
            raise IntegrationTestError(
                message=f"Test environment validation failed: {str(e)}",
                details={"validation_results": validation_results},
            ) from e
