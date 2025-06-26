"""
Integration tests for LLMManager functionality with real AWS Bedrock.

These tests validate the main LLMManager class functionality with real AWS calls,
covering areas that have low coverage in unit tests due to mocking.
"""

from typing import Any, Dict, List, Optional, Tuple

import pytest

from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
    ConfigurationError,
    RequestValidationError,
    RetryExhaustedError,
)
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    AuthConfig,
    AuthenticationType,
    ResponseValidationConfig,
    RetryConfig,
)
from bestehorn_llmmanager.bedrock.testing.integration_markers import IntegrationTestMarkers
from bestehorn_llmmanager.bedrock.UnifiedModelManager import (
    UnifiedModelManager,
    UnifiedModelManagerError,
)
from bestehorn_llmmanager.llm_manager import LLMManager

# Constants for preferred test regions (in order of preference)
PREFERRED_TEST_REGIONS = ["us-east-1", "us-west-2"]
FALLBACK_TEST_REGIONS = ["eu-west-1", "ap-southeast-1"]


def _select_preferred_region_from_available(available_regions: List[str]) -> Optional[str]:
    """
    Select the most preferred region from available regions for testing.

    Prioritizes regions that typically have full functionality and account access.

    Args:
        available_regions: List of regions where the model is available

    Returns:
        Preferred region if available, None if no regions available
    """
    if not available_regions:
        return None

    # Try preferred regions first
    for preferred_region in PREFERRED_TEST_REGIONS:
        if preferred_region in available_regions:
            return preferred_region

    # Try fallback regions
    for fallback_region in FALLBACK_TEST_REGIONS:
        if fallback_region in available_regions:
            return fallback_region

    # If no preferred regions available, use first available region
    return available_regions[0]


def _get_provider_models_with_case_handling(
    unified_manager: UnifiedModelManager, provider: str
) -> Dict[str, Any]:
    """
    Get models for a provider with case-insensitive handling.

    Args:
        unified_manager: Initialized UnifiedModelManager instance
        provider: Model provider name

    Returns:
        Dictionary of provider models, empty dict if none found
    """
    # Try exact case first
    provider_models = unified_manager.get_models_by_provider(provider=provider)
    if provider_models:
        return provider_models

    # Try capitalized version if exact case fails
    capitalized_provider = provider.capitalize()
    if capitalized_provider != provider:
        provider_models = unified_manager.get_models_by_provider(provider=capitalized_provider)
        if provider_models:
            return provider_models

    # Try lowercase version if exact case fails
    lowercase_provider = provider.lower()
    if lowercase_provider != provider:
        provider_models = unified_manager.get_models_by_provider(provider=lowercase_provider)
        if provider_models:
            return provider_models

    return {}


def get_available_test_model_and_region(
    provider: str = "Anthropic",
) -> Tuple[Optional[str], Optional[str]]:
    """
    Get an available model and region combination for testing.

    Uses UnifiedModelManager to dynamically discover available models and
    prioritizes regions that typically have full functionality and account access
    (us-east-1, us-west-2) over other regions.

    Args:
        provider: Model provider to search for (default: "Anthropic")

    Returns:
        Tuple of (model_name, region) if available combination found, (None, None) otherwise
    """
    try:
        # Create and initialize UnifiedModelManager
        unified_manager = UnifiedModelManager()
        unified_manager.ensure_data_available()

        # Get models for the specified provider with case handling
        provider_models = _get_provider_models_with_case_handling(
            unified_manager=unified_manager, provider=provider
        )
        if not provider_models:
            return None, None

        # Try each model to find one with available regions in preferred order
        for model_name in sorted(provider_models.keys()):
            available_regions = unified_manager.get_regions_for_model(model_name=model_name)
            if available_regions:
                preferred_region = _select_preferred_region_from_available(
                    available_regions=available_regions
                )
                if preferred_region:
                    return model_name, preferred_region

        return None, None

    except UnifiedModelManagerError:
        # If UnifiedModelManager fails, return None to skip tests
        return None, None
    except Exception:
        # For any other error, return None to skip tests
        return None, None


def get_multiple_test_regions(model_name: str, max_regions: int = 3) -> List[str]:
    """
    Get multiple regions where a model is available for testing.

    Args:
        model_name: Name of the model to check
        max_regions: Maximum number of regions to return

    Returns:
        List of regions where the model is available (up to max_regions)
    """
    try:
        unified_manager = UnifiedModelManager()
        unified_manager.ensure_data_available()

        available_regions = unified_manager.get_regions_for_model(model_name=model_name)
        return available_regions[:max_regions]

    except Exception:
        return []


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.aws_fast
class TestLLMManagerBasicFunctionality:
    """Integration tests for basic LLMManager functionality."""

    def test_llm_manager_initialization_with_real_models(self):
        """
        Test LLMManager initialization with real model data using dynamic discovery.
        """
        # Get available test models using dynamic discovery
        anthropic_model, anthropic_region = get_available_test_model_and_region(
            provider="Anthropic"
        )
        amazon_model, amazon_region = get_available_test_model_and_region(provider="Amazon")

        models = []
        regions = []

        if anthropic_model and anthropic_region:
            models.append(anthropic_model)
            if anthropic_region not in regions:
                regions.append(anthropic_region)

        if amazon_model and amazon_region:
            models.append(amazon_model)
            if amazon_region not in regions:
                regions.append(amazon_region)

        if not models:
            pytest.skip("No test models available for testing")

        # Initialize with dynamically discovered models and regions
        try:
            manager = LLMManager(models=models, regions=regions, timeout=30)

            # Verify manager is properly initialized
            assert len(manager.get_available_models()) == len(models)
            assert len(manager.get_available_regions()) >= 1

            # Validate configuration
            validation_result = manager.validate_configuration()
            assert "valid" in validation_result
            assert "auth_status" in validation_result
            assert validation_result["auth_status"] != "unknown"

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to model data issues: {str(e)}")

    def test_llm_manager_converse_with_real_model(
        self, sample_test_messages, simple_inference_config
    ):
        """
        Test LLMManager converse method with real AWS model using dynamic discovery.

        Args:
            sample_test_messages: Sample messages for testing
            simple_inference_config: Simple inference configuration
        """
        # Use dynamic model/region discovery
        model_name, region = get_available_test_model_and_region(provider="Anthropic")
        if not model_name or not region:
            pytest.skip("No available Anthropic model/region combination found for testing")

        # Initialize manager with dynamically discovered model/region
        try:
            manager = LLMManager(
                models=[model_name],
                regions=[region],
                default_inference_config=simple_inference_config,
            )

            # Make real converse call
            response = manager.converse(messages=sample_test_messages)

            # Verify response structure
            assert response.success is True
            assert response.model_used is not None
            assert response.region_used is not None
            assert response.total_duration_ms is not None and response.total_duration_ms > 0

            # Verify content
            content = response.get_content()
            assert content is not None
            assert len(content) > 0
            assert isinstance(content, str)

            # Verify usage information
            usage = response.get_usage()
            assert usage is not None
            assert usage.get("input_tokens", 0) > 0
            assert usage.get("output_tokens", 0) > 0

            # Verify attempt information
            assert len(response.attempts) >= 1
            successful_attempt = next((a for a in response.attempts if a.success), None)
            assert successful_attempt is not None
            assert successful_attempt.model_id == model_name

        except ConfigurationError as e:
            pytest.skip(
                f'Could not initialize LLMManager (Model: "{model_name}"; Region: "{region}") due to model data issues: {str(e)}'
            )

    def test_llm_manager_converse_with_system_message(self, sample_test_messages):
        """
        Test LLMManager converse with system message.

        Args:
            sample_test_messages: Sample messages for testing
        """
        # Use dynamic model/region discovery
        model_name, region = get_available_test_model_and_region(provider="Anthropic")
        if not model_name or not region:
            pytest.skip("No available Anthropic model/region combination found for testing")

        try:
            manager = LLMManager(models=[model_name], regions=[region])

            system_messages = [
                {"text": "You are a helpful assistant. Please respond briefly and clearly."}
            ]

            response = manager.converse(
                messages=sample_test_messages,
                system=system_messages,
                inference_config={"maxTokens": 50},
            )

            assert response.success is True
            assert response.get_content() is not None

        except ConfigurationError as e:
            pytest.skip(
                f'Could not initialize LLMManager (Model: "{model_name}"; Region: "{region}") due to model data issues: {str(e)}'
            )

    def test_llm_manager_converse_with_multiple_regions(self, sample_test_messages):
        """
        Test LLMManager with multiple regions for failover using dynamic discovery.

        Args:
            sample_test_messages: Sample messages for testing
        """
        # Use dynamic model/region discovery
        model_name, primary_region = get_available_test_model_and_region(provider="Anthropic")
        if not model_name or not primary_region:
            pytest.skip("No available Anthropic model/region combination found for testing")

        # Get multiple regions for the model, prioritizing preferred regions
        all_regions = get_multiple_test_regions(model_name=model_name, max_regions=3)
        if not all_regions:
            pytest.skip(f"No regions available for model {model_name}")

        # Ensure we have multiple regions for failover testing
        test_regions = []
        for preferred_region in PREFERRED_TEST_REGIONS:
            if preferred_region in all_regions and preferred_region not in test_regions:
                test_regions.append(preferred_region)

        # Add any remaining regions up to max
        for region in all_regions:
            if region not in test_regions and len(test_regions) < 3:
                test_regions.append(region)

        if len(test_regions) < 2:
            test_regions = [primary_region]  # Fallback to single region

        try:
            manager = LLMManager(models=[model_name], regions=test_regions)

            response = manager.converse(
                messages=sample_test_messages, inference_config={"maxTokens": 30}
            )

            assert response.success is True
            assert response.region_used in test_regions

            # Verify that the manager tried regions in order if needed
            # (This would be more apparent in failure scenarios)
            assert len(response.attempts) >= 1

        except ConfigurationError as e:
            pytest.skip(
                f'Could not initialize LLMManager (Model: "{model_name}"; Regions: {test_regions}) due to model data issues: {str(e)}'
            )
        except RetryExhaustedError as e:
            # Check if it's an access issue - this is expected if the AWS account doesn't have access in all regions
            error_str = str(e)
            if (
                "AccessDeniedException" in error_str
                or "You don't have access to the model" in error_str
            ):
                pytest.skip(
                    f"AWS account doesn't have access to {model_name} in selected regions {test_regions}. This is expected for some accounts."
                )
            else:
                # Re-raise if it's a different kind of retry exhaustion
                raise

    def test_llm_manager_with_retry_config(self, sample_test_messages):
        """
        Test LLMManager with custom retry configuration.

        Args:
            sample_test_messages: Sample messages for testing
        """
        # Use dynamic model/region discovery instead of integration_config
        model_name, region = get_available_test_model_and_region(provider="Anthropic")
        if not model_name or not region:
            pytest.skip("No available Anthropic model/region combination found for testing")

        # Configure custom retry behavior
        retry_config = RetryConfig(
            max_retries=2, retry_delay=1.0, max_retry_delay=5.0, backoff_multiplier=2.0
        )

        try:
            # Initialize LLMManager with retry config using dynamically discovered model/region
            manager = LLMManager(models=[model_name], regions=[region], retry_config=retry_config)

            # Test converse functionality with retry config
            response = manager.converse(
                messages=sample_test_messages, inference_config={"maxTokens": 30}
            )

            assert response.success is True

            # Verify retry configuration was applied
            retry_stats = manager.get_retry_stats()
            assert isinstance(retry_stats, dict)
            assert "max_retries" in retry_stats
            assert retry_stats["max_retries"] == 2

        except ConfigurationError as e:
            # Skip if LLMManager cannot be initialized due to model data issues
            pytest.skip(
                f'Could not initialize LLMManager (Model: "{model_name}"; Region: "{region}") due to model data issues: {str(e)}'
            )


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.aws_fast
class TestLLMManagerErrorHandling:
    """Integration tests for LLMManager error handling with real AWS."""

    def test_llm_manager_with_invalid_model_name(self, integration_config, sample_test_messages):
        """
        Test LLMManager behavior with invalid model name.

        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
        """
        # With fail-fast initialization, LLMManager should raise ConfigurationError
        # during initialization when no valid model/region combinations are available
        with pytest.raises(ConfigurationError) as exc_info:
            manager = LLMManager(
                models=["NonExistentModel"], regions=[integration_config.get_primary_test_region()]
            )

        # Verify the error message contains expected information
        error_message = str(exc_info.value)
        assert "NonExistentModel" in error_message
        assert "not found" in error_message
        assert "Models specified: ['NonExistentModel']" in error_message

    def test_llm_manager_request_validation(self, integration_config):
        """
        Test LLMManager request validation.

        Args:
            integration_config: Integration test configuration
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        try:
            manager = LLMManager(
                models=[anthropic_model],  # Use actual model ID
                regions=[integration_config.get_primary_test_region()],
            )
        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to model data issues: {str(e)}")

        # Test empty messages - should raise RequestValidationError
        with pytest.raises(RequestValidationError) as exc_info:
            manager.converse(messages=[])

        # Verify the error message
        assert "Messages cannot be empty" in str(exc_info.value)

        # Test malformed messages - should raise RequestValidationError
        with pytest.raises(RequestValidationError):
            manager.converse(messages=[{"invalid": "structure"}])

        # Test missing required fields - should raise RequestValidationError
        with pytest.raises(RequestValidationError):
            manager.converse(messages=[{"role": "user"}])  # Missing content

    def test_llm_manager_with_invalid_region(self, integration_config, sample_test_messages):
        """
        Test LLMManager with invalid AWS region.

        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        # With fail-fast initialization, this should raise ConfigurationError during initialization
        with pytest.raises(ConfigurationError) as exc_info:
            manager = LLMManager(
                models=[anthropic_model], regions=["invalid-region-name"]  # Use actual model ID
            )

        # Verify the error message contains expected information
        error_message = str(exc_info.value)
        assert "invalid-region-name" in error_message
        assert "not found" in error_message
        assert "Regions specified: ['invalid-region-name']" in error_message


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.aws_fast
class TestLLMManagerAdvancedFeatures:
    """Integration tests for advanced LLMManager features."""

    def test_llm_manager_converse_stream(self, integration_config, sample_test_messages):
        """
        Test LLMManager streaming converse functionality.

        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        try:
            manager = LLMManager(
                models=[anthropic_model],  # Use actual model ID
                regions=[integration_config.get_primary_test_region()],
            )

            # Test streaming converse
            streaming_response = manager.converse_stream(
                messages=sample_test_messages, inference_config={"maxTokens": 50}
            )

            assert streaming_response.success is True
            # Additional streaming-specific assertions would depend on
            # the actual implementation of StreamingResponse

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to model data issues: {str(e)}")

    def test_llm_manager_model_access_info(self, integration_config):
        """
        Test LLMManager model access information retrieval.

        Args:
            integration_config: Integration test configuration
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        try:
            manager = LLMManager(
                models=[anthropic_model],  # Use actual model ID
                regions=[integration_config.get_primary_test_region()],
            )

            # Test model access info - use the actual model ID
            access_info = manager.get_model_access_info(
                model_name=anthropic_model, region=integration_config.get_primary_test_region()
            )

            if access_info:  # May be None if model data not available
                assert "access_method" in access_info
                assert "model_id" in access_info
                assert "region" in access_info
                assert access_info["region"] == integration_config.get_primary_test_region()

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to model data issues: {str(e)}")

    def test_llm_manager_refresh_model_data(self, integration_config):
        """
        Test LLMManager model data refresh functionality.

        Args:
            integration_config: Integration test configuration
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        try:
            manager = LLMManager(
                models=[anthropic_model],  # Use actual model ID
                regions=[integration_config.get_primary_test_region()],
            )

            # Test model data refresh
            # This should not raise an exception
            manager.refresh_model_data()

            # After refresh, validation should be better
            validation_result = manager.validate_configuration()
            assert "valid" in validation_result
            assert "auth_status" in validation_result

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to model data issues: {str(e)}")


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestLLMManagerResponseValidation:
    """Integration tests for LLMManager response validation features."""

    def test_llm_manager_basic_response_handling(self, integration_config, sample_test_messages):
        """
        Test basic LLMManager response handling and content extraction.

        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        try:
            manager = LLMManager(
                models=[anthropic_model],  # Use actual model ID
                regions=[integration_config.get_primary_test_region()],
            )

            response = manager.converse(
                messages=sample_test_messages, inference_config={"maxTokens": 100}
            )

            assert response.success is True
            content = response.get_content()
            assert content is not None
            assert len(content) > 0  # Should have some content

            # Test additional response methods
            usage = response.get_usage()
            assert usage is not None
            assert usage.get("input_tokens", 0) > 0

            metrics = response.get_metrics()
            assert metrics is not None
            assert "total_duration_ms" in metrics

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to model data issues: {str(e)}")
