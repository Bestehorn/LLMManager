"""
Integration tests for notebook token display functionality.

These tests validate that the ExtendedContext_Demo.ipynb notebook correctly
displays token usage information using the new accessor methods.
"""

from typing import Any, Dict, List, Optional, Tuple

import pytest

from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
    ConfigurationError,
)
from bestehorn_llmmanager.llm_manager import LLMManager

# Constants for preferred test regions (in order of preference)
PREFERRED_TEST_REGIONS = ["us-east-1", "us-west-2"]
FALLBACK_TEST_REGIONS = ["eu-west-1", "ap-southeast-1"]


def _select_preferred_region_from_available(available_regions: List[str]) -> Optional[str]:
    """
    Select the most preferred region from available regions for testing.

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


def _get_provider_models_with_case_handling(unified_manager, provider: str) -> Dict[str, Any]:
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
    prioritizes regions that typically have full functionality and account access.

    Args:
        provider: Model provider to search for (default: "Anthropic")

    Returns:
        Tuple of (model_name, region) if available combination found, (None, None) otherwise
    """
    try:
        from bestehorn_llmmanager.bedrock.UnifiedModelManager import (
            UnifiedModelManager,
            UnifiedModelManagerError,
        )

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

    except Exception:
        # If UnifiedModelManager fails, return None to skip tests
        return None, None


def create_large_text(size_kb: int = 100) -> str:
    """
    Create a large text string for testing extended context.

    Args:
        size_kb: Size of text in kilobytes

    Returns:
        Large text string
    """
    base_text = "This is a sample text for testing extended context windows. "
    repetitions = (size_kb * 1024) // len(base_text)
    return base_text * repetitions


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.aws_fast
class TestNotebookTokenDisplay:
    """Integration tests for notebook token display functionality."""

    def test_notebook_displays_nonzero_token_counts(self) -> None:
        """
        Test that notebook displays non-zero token counts for successful requests.

        This test validates Requirements 1.4 and 1.5:
        - Token usage should be greater than 0 for successful requests
        - Displayed values should match actual API response

        The test simulates the notebook's display_response() function behavior
        by using the new accessor methods and verifying they return non-zero values.
        """
        # Get available test model using dynamic discovery
        model_name, region = get_available_test_model_and_region(provider="Anthropic")
        if not model_name or not region:
            pytest.skip("No available Anthropic model/region combination found for testing")

        # Initialize manager
        try:
            manager = LLMManager(models=[model_name], regions=[region])
        except ConfigurationError as e:
            pytest.skip(
                f'Could not initialize LLMManager (Model: "{model_name}"; Region: "{region}") due to model data issues: {str(e)}'
            )

        # Create a simple message (similar to notebook examples)
        messages = [
            {
                "role": "user",
                "content": [{"text": "Hello! Please respond with a brief greeting."}],
            }
        ]

        # Make request
        response = manager.converse(messages=messages, inference_config={"maxTokens": 100})

        # Verify response is successful
        assert response.success is True, "Response should be successful"

        # Test accessor methods (as used in notebook's display_response function)
        input_tokens = response.get_input_tokens()
        output_tokens = response.get_output_tokens()
        total_tokens = response.get_total_tokens()

        # Verify non-zero token counts (Requirement 1.4)
        assert input_tokens > 0, "Input tokens should be greater than 0 for successful request"
        assert output_tokens > 0, "Output tokens should be greater than 0 for successful request"
        assert total_tokens > 0, "Total tokens should be greater than 0 for successful request"

        # Verify displayed values match actual API response (Requirement 1.5)
        usage = response.get_usage()
        assert usage is not None, "Usage data should be available"
        assert (
            input_tokens == usage.get("input_tokens", 0)
        ), "Accessor method should match usage dictionary"
        assert (
            output_tokens == usage.get("output_tokens", 0)
        ), "Accessor method should match usage dictionary"
        assert (
            total_tokens == usage.get("total_tokens", 0)
        ), "Accessor method should match usage dictionary"

        # Verify token arithmetic
        assert (
            total_tokens == input_tokens + output_tokens
        ), "Total tokens should equal input + output"

    def test_notebook_example1_large_text_shows_token_usage(self) -> None:
        """
        Test Example 1 with large text input shows token usage > 0.

        This test validates Requirement 1.4 specifically for the notebook's
        Example 1 scenario where a large text is processed.

        The test simulates the notebook's Example 1 by:
        1. Creating a large text (50KB as in the notebook)
        2. Sending it to the model
        3. Verifying token usage is displayed correctly
        """
        # Get available test model using dynamic discovery
        model_name, region = get_available_test_model_and_region(provider="Anthropic")
        if not model_name or not region:
            pytest.skip("No available Anthropic model/region combination found for testing")

        # Initialize manager (similar to notebook Example 1)
        try:
            manager = LLMManager(models=[model_name], regions=[region])
        except ConfigurationError as e:
            pytest.skip(
                f'Could not initialize LLMManager (Model: "{model_name}"; Region: "{region}") due to model data issues: {str(e)}'
            )

        # Create large text (same as notebook Example 1)
        large_text = create_large_text(size_kb=50)  # ~12,500 tokens
        estimated_tokens = len(large_text) // 4

        # Create message (similar to notebook Example 1)
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "text": f"Please summarize the following text in 2-3 sentences:\n\n{large_text}"
                    }
                ],
            }
        ]

        # Make request (similar to notebook Example 1)
        response = manager.converse(
            messages=messages, inference_config={"maxTokens": 512, "temperature": 0.3}
        )

        # Verify response is successful
        assert response.success is True, "Response should be successful"

        # Test accessor methods (as used in notebook's display_response function)
        input_tokens = response.get_input_tokens()
        output_tokens = response.get_output_tokens()
        total_tokens = response.get_total_tokens()

        # Verify non-zero token counts for large text (Requirement 1.4)
        assert (
            input_tokens > 0
        ), "Input tokens should be greater than 0 for large text request"
        assert (
            output_tokens > 0
        ), "Output tokens should be greater than 0 for large text request"
        assert (
            total_tokens > 0
        ), "Total tokens should be greater than 0 for large text request"

        # Verify input tokens are substantial (should be close to estimated)
        # Allow for some variance due to tokenization differences
        assert (
            input_tokens > estimated_tokens * 0.5
        ), f"Input tokens ({input_tokens}) should be substantial for large text (estimated: {estimated_tokens})"

        # Verify the display condition from notebook works correctly
        # The notebook checks: if total_tokens > 0
        assert total_tokens > 0, "Notebook display condition should be satisfied"

        # Verify displayed values match actual API response (Requirement 1.5)
        usage = response.get_usage()
        assert usage is not None, "Usage data should be available"
        assert (
            input_tokens == usage.get("input_tokens", 0)
        ), "Accessor method should match usage dictionary"
        assert (
            output_tokens == usage.get("output_tokens", 0)
        ), "Accessor method should match usage dictionary"
        assert (
            total_tokens == usage.get("total_tokens", 0)
        ), "Accessor method should match usage dictionary"

    def test_notebook_example3_token_tracking(self) -> None:
        """
        Test Example 3 token usage tracking with accessor methods.

        This test validates that the notebook's Example 3 correctly tracks
        token usage across multiple requests using the new accessor methods.

        The test simulates Example 3 by:
        1. Creating texts of different sizes
        2. Processing each text
        3. Collecting token usage statistics
        4. Verifying all values are non-zero and consistent
        """
        # Get available test model using dynamic discovery
        model_name, region = get_available_test_model_and_region(provider="Anthropic")
        if not model_name or not region:
            pytest.skip("No available Anthropic model/region combination found for testing")

        # Initialize manager
        try:
            manager = LLMManager(models=[model_name], regions=[region])
        except ConfigurationError as e:
            pytest.skip(
                f'Could not initialize LLMManager (Model: "{model_name}"; Region: "{region}") due to model data issues: {str(e)}'
            )

        # Test with a single size (to keep test fast)
        size_kb = 10
        label = "Small"

        text = create_large_text(size_kb=size_kb)
        estimated_tokens = len(text) // 4

        messages = [
            {
                "role": "user",
                "content": [{"text": f"Provide a one-sentence summary of this text:\n\n{text}"}],
            }
        ]

        # Make request
        response = manager.converse(messages=messages, inference_config={"maxTokens": 100})

        # Verify response is successful
        assert response.success is True, "Response should be successful"

        # Collect results using accessor methods (as in notebook Example 3)
        result = {
            "label": label,
            "estimated": estimated_tokens,
            "actual_input": response.get_input_tokens(),
            "output": response.get_output_tokens(),
            "total": response.get_total_tokens(),
        }

        # Verify all token counts are non-zero
        assert result["actual_input"] > 0, "Actual input tokens should be greater than 0"
        assert result["output"] > 0, "Output tokens should be greater than 0"
        assert result["total"] > 0, "Total tokens should be greater than 0"

        # Verify token arithmetic
        assert (
            result["total"] == result["actual_input"] + result["output"]
        ), "Total should equal input + output"

        # Verify actual input is reasonable compared to estimate
        assert (
            result["actual_input"] > estimated_tokens * 0.5
        ), f"Actual input ({result['actual_input']}) should be close to estimate ({estimated_tokens})"

        # Verify displayed values match actual API response (Requirement 1.5)
        usage = response.get_usage()
        assert usage is not None, "Usage data should be available"
        assert (
            result["actual_input"] == usage.get("input_tokens", 0)
        ), "Accessor method should match usage dictionary"
        assert (
            result["output"] == usage.get("output_tokens", 0)
        ), "Accessor method should match usage dictionary"
        assert (
            result["total"] == usage.get("total_tokens", 0)
        ), "Accessor method should match usage dictionary"
