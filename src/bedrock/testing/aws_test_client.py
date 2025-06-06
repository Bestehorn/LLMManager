"""
AWS test client for Bedrock integration testing.

This module provides a test-specific client that wraps the existing authentication
and Bedrock functionality with additional features for integration testing,
including cost tracking, request validation, and test data management.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime

from ..auth.auth_manager import AuthManager
from ..models.llm_manager_structures import AuthConfig, AuthenticationType
from ..models.bedrock_response import BedrockResponse
from ..exceptions.llm_manager_exceptions import LLMManagerError
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
    
    def calculate_estimated_cost(self, input_cost_per_1k: float = 0.001, output_cost_per_1k: float = 0.002) -> None:
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
                    "request_count": len(self.requests)
                }
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
            "cost_limit_utilization": self.total_estimated_cost_usd / self.config.cost_limit_usd
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
        """
        self.config = config
        self._logger = logging.getLogger(__name__)
        
        # Initialize authentication manager
        auth_config = self._create_auth_config()
        self._auth_manager = AuthManager(auth_config=auth_config)
        
        # Test session tracking
        self._current_session: Optional[TestSession] = None
        
        # Validate configuration
        if not self.config.enabled:
            raise IntegrationTestError(
                message="Integration tests are not enabled",
                details={"config": self.config.to_dict()}
            )
    
    def _create_auth_config(self) -> AuthConfig:
        """
        Create authentication configuration from integration test config.
        
        Returns:
            Configured AuthConfig instance
        """
        if self.config.aws_profile:
            return AuthConfig(
                auth_type=AuthenticationType.PROFILE,
                profile_name=self.config.aws_profile
            )
        else:
            return AuthConfig(auth_type=AuthenticationType.AUTO)
    
    def start_test_session(self, session_id: str) -> TestSession:
        """
        Start a new test session for tracking requests.
        
        Args:
            session_id: Unique identifier for the test session
            
        Returns:
            Created test session
        """
        self._logger.info(f"Starting integration test session: {session_id}")
        self._current_session = TestSession(
            session_id=session_id,
            config=self.config
        )
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
        
        session = self._current_session
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
                details={"region": region, "enabled_regions": self.config.test_regions}
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
                "auth_method": self.config.aws_profile or "auto"
            }
            
        except Exception as e:
            raise IntegrationTestError(
                message=f"Authentication test failed for region {region}: {str(e)}",
                details={
                    "region": region,
                    "auth_profile": self.config.aws_profile,
                    "original_error": str(e)
                }
            ) from e
    
    def test_bedrock_converse(
        self,
        model_id: str,
        messages: List[Dict[str, Any]],
        region: Optional[str] = None,
        **kwargs
    ) -> BedrockResponse:
        """
        Test Bedrock converse API with request tracking.
        
        Args:
            model_id: Model identifier to test
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
                details={"model_id": model_id, "enabled_models": list(self.config.test_models.values())}
            )
        
        test_region = region or self.config.get_primary_test_region()
        if not self.config.is_region_enabled(test_region):
            raise IntegrationTestError(
                message=f"Region {test_region} is not enabled for testing",
                details={"region": test_region, "enabled_regions": self.config.test_regions}
            )
        
        # Create request metrics
        request_id = f"{model_id}_{test_region}_{int(time.time())}"
        metrics = TestRequestMetrics(
            request_id=request_id,
            model_id=model_id,
            region=test_region
        )
        
        try:
            # Get client and make request
            client = self._auth_manager.get_bedrock_client(region=test_region)
            
            # Prepare request arguments
            request_args = {
                "modelId": model_id,
                "messages": messages,
                **kwargs
            }
            
            # Make the API call
            self._logger.info(f"Making Bedrock converse request: {request_id}")
            response = client.converse(**request_args)
            
            # Process response
            bedrock_response = BedrockResponse(
                success=True,
                response_data=response,
                model_used=model_id,
                region_used=test_region
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
                    "original_error": error_message
                }
            ) from e
    
    def test_bedrock_converse_stream(
        self,
        model_id: str,
        messages: List[Dict[str, Any]],
        region: Optional[str] = None,
        **kwargs
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
                details={"model_id": model_id, "enabled_models": list(self.config.test_models.values())}
            )
        
        test_region = region or self.config.get_primary_test_region()
        if not self.config.is_region_enabled(test_region):
            raise IntegrationTestError(
                message=f"Region {test_region} is not enabled for testing",
                details={"region": test_region, "enabled_regions": self.config.test_regions}
            )
        
        # Create request metrics
        request_id = f"{model_id}_{test_region}_stream_{int(time.time())}"
        metrics = TestRequestMetrics(
            request_id=request_id,
            model_id=model_id,
            region=test_region
        )
        
        try:
            # Get client and make streaming request
            client = self._auth_manager.get_bedrock_client(region=test_region)
            
            # Prepare request arguments
            request_args = {
                "modelId": model_id,
                "messages": messages,
                **kwargs
            }
            
            # Make the streaming API call
            self._logger.info(f"Making Bedrock streaming converse request: {request_id}")
            response = client.converse_stream(**request_args)
            
            # Process streaming response
            bedrock_response = BedrockResponse(
                success=True,
                response_data=response,
                model_used=model_id,
                region_used=test_region
            )
            
            metrics.mark_completed(success=True)
            
            # Add to session if active
            if self._current_session:
                self._current_session.add_request_metrics(metrics)
                self._current_session.check_cost_limit()
            
            self._logger.info(f"Bedrock streaming converse request completed successfully: {request_id}")
            return bedrock_response
            
        except Exception as e:
            error_message = str(e)
            metrics.mark_completed(success=False, error_message=error_message)
            
            if self._current_session:
                self._current_session.add_request_metrics(metrics)
            
            self._logger.error(f"Bedrock streaming converse request failed: {request_id} - {error_message}")
            
            raise IntegrationTestError(
                message=f"Bedrock streaming converse test failed: {error_message}",
                details={
                    "request_id": request_id,
                    "model_id": model_id,
                    "region": test_region,
                    "original_error": error_message
                }
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
        validation_results = {
            "overall_success": True,
            "config_valid": True,
            "auth_results": {},
            "model_availability": {},
            "errors": []
        }
        
        try:
            # Test authentication for each region
            for region in self.config.test_regions:
                try:
                    auth_result = self.test_authentication(region=region)
                    validation_results["auth_results"][region] = auth_result
                except Exception as e:
                    validation_results["overall_success"] = False
                    validation_results["auth_results"][region] = {
                        "success": False,
                        "error": str(e)
                    }
                    validation_results["errors"].append(f"Authentication failed for {region}: {str(e)}")
            
            # TODO: Add model availability checks when we have model listing functionality
            
            return validation_results
            
        except Exception as e:
            raise IntegrationTestError(
                message=f"Test environment validation failed: {str(e)}",
                details={"validation_results": validation_results}
            ) from e
