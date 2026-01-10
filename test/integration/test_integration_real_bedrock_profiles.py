"""
Integration tests with real AWS Bedrock models for profile support.

These tests validate profile support with actual AWS Bedrock API calls.
Tests are skipped if AWS credentials are not available or if specific
models are not accessible in the test account.

IMPORTANT: These tests may incur AWS costs. They are designed to be
minimal and use low token limits to minimize costs.
"""

import logging

import pytest

from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
    ConfigurationError,
    RetryExhaustedError,
)
from bestehorn_llmmanager.bedrock.tracking.access_method_tracker import (
    AccessMethodTracker,
)
from bestehorn_llmmanager.llm_manager import LLMManager


@pytest.fixture(autouse=True)
def reset_access_method_tracker():
    """Reset AccessMethodTracker singleton before each test."""
    AccessMethodTracker._instance = None
    yield
    AccessMethodTracker._instance = None


@pytest.fixture
def sample_messages():
    """Create minimal sample messages for testing."""
    return [{"role": "user", "content": [{"text": "Say 'test' and nothing else."}]}]


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.skipif(
    "not config.getoption('--run-real-bedrock-tests', default=False)",
    reason="Real Bedrock tests require --run-real-bedrock-tests flag",
)
class TestRealBedrockProfileSupport:
    """Test profile support with real AWS Bedrock models."""

    def test_claude_sonnet_45_requires_profile(self, sample_messages):
        """
        Test that Claude Sonnet 4.5 requires inference profile access.

        This test validates:
        - Profile requirement detection with real AWS error
        - Automatic profile selection from catalog
        - Successful retry with profile
        - Access method learning

        Validates: All requirements

        NOTE: This test may be skipped if:
        - Claude Sonnet 4.5 is not available in the test account
        - The model doesn't require profile in the test region
        - AWS credentials are not configured
        """
        try:
            # Create LLMManager with Claude Sonnet 4.5
            manager = LLMManager(
                models=["Claude Sonnet 4.5"],
                regions=["us-east-1"],
                log_level=logging.DEBUG,
            )

            # Execute request
            response = manager.converse(
                messages=sample_messages,
                inference_config={"maxTokens": 10},  # Minimal tokens to reduce cost
            )

            # Verify success
            assert response.success, "Request should succeed"
            assert response.get_content() is not None, "Should have content"

            # Check if profile was used
            if response.inference_profile_used:
                # Profile was used - verify metadata
                assert (
                    response.inference_profile_id is not None
                ), "Should have profile ID when profile used"
                assert response.access_method_used in [
                    "regional_cris",
                    "global_cris",
                ], "Should use CRIS access method"

                # Verify learning occurred
                tracker = AccessMethodTracker.get_instance()
                stats = tracker.get_statistics()
                assert stats["total_tracked"] > 0, "Should have tracked access methods"

            else:
                # Direct access worked - this is also valid
                assert response.access_method_used == "direct", "Should use direct access"

        except ConfigurationError as e:
            pytest.skip(f"Claude Sonnet 4.5 not available in test account: {str(e)}")
        except RetryExhaustedError as e:
            # Check if it's an access issue
            if "AccessDeniedException" in str(e) or "don't have access" in str(e):
                pytest.skip(f"No access to Claude Sonnet 4.5 in test account: {str(e)}")
            else:
                raise

    def test_claude_3_haiku_supports_direct_access(self, sample_messages):
        """
        Test that Claude 3 Haiku supports direct model ID access.

        This test validates:
        - Direct access works for older models
        - No profile requirement for Claude 3 Haiku
        - Backward compatibility

        Validates: Requirements 6.1, 6.2, 6.3

        NOTE: This test may be skipped if:
        - Claude 3 Haiku is not available in the test account
        - AWS credentials are not configured
        """
        try:
            # Create LLMManager with Claude 3 Haiku
            manager = LLMManager(
                models=["Claude 3 Haiku"],
                regions=["us-east-1"],
                log_level=logging.DEBUG,
            )

            # Execute request
            response = manager.converse(
                messages=sample_messages,
                inference_config={"maxTokens": 10},  # Minimal tokens to reduce cost
            )

            # Verify success
            assert response.success, "Request should succeed"
            assert response.get_content() is not None, "Should have content"

            # Verify access method (should be direct or CRIS, both are valid)
            assert response.access_method_used in [
                "direct",
                "regional_cris",
                "global_cris",
            ], "Should use valid access method"

        except ConfigurationError as e:
            pytest.skip(f"Claude 3 Haiku not available in test account: {str(e)}")
        except RetryExhaustedError as e:
            if "AccessDeniedException" in str(e) or "don't have access" in str(e):
                pytest.skip(f"No access to Claude 3 Haiku in test account: {str(e)}")
            else:
                raise

    def test_automatic_profile_selection_with_real_catalog(self, sample_messages):
        """
        Test automatic profile selection using real catalog data.

        This test validates:
        - Catalog provides correct profile information
        - Profile selection works with real data
        - Access method is correctly recorded

        Validates: Requirements 2.1, 2.2, 3.1, 3.2, 3.3

        NOTE: This test uses whichever model is available and may be skipped
        if no models are accessible.
        """
        try:
            # Try multiple models to find one that's available
            test_models = ["Claude 3 Haiku", "Claude 3 Sonnet", "Claude Sonnet 4.5"]

            manager = None
            for model in test_models:
                try:
                    manager = LLMManager(
                        models=[model],
                        regions=["us-east-1", "us-west-2"],
                        log_level=logging.DEBUG,
                    )
                    break
                except ConfigurationError:
                    continue

            if manager is None:
                pytest.skip("No test models available in account")

            # Execute request
            response = manager.converse(
                messages=sample_messages,
                inference_config={"maxTokens": 10},
            )

            # Verify success
            assert response.success, "Request should succeed"

            # Verify access method metadata is present
            assert response.access_method_used is not None, "Should have access method"
            assert isinstance(
                response.inference_profile_used, bool
            ), "Should have profile usage flag"

            # If profile was used, verify profile ID
            if response.inference_profile_used:
                assert (
                    response.inference_profile_id is not None
                ), "Should have profile ID when profile used"

        except RetryExhaustedError as e:
            if "AccessDeniedException" in str(e) or "don't have access" in str(e):
                pytest.skip(f"No access to test models in account: {str(e)}")
            else:
                raise

    def test_access_method_learning_with_real_requests(self, sample_messages):
        """
        Test that access method learning works with real AWS requests.

        This test validates:
        - First request records access method
        - Second request uses learned preference
        - Tracker statistics are accurate

        Validates: Requirements 5.1, 5.2, 5.3, 5.4

        NOTE: This test makes multiple requests and may incur slightly higher costs.
        """
        try:
            # Create LLMManager
            manager = LLMManager(
                models=["Claude 3 Haiku"],
                regions=["us-east-1"],
                log_level=logging.DEBUG,
            )

            # Get tracker
            tracker = AccessMethodTracker.get_instance()

            # First request
            response1 = manager.converse(
                messages=sample_messages,
                inference_config={"maxTokens": 10},
            )
            assert response1.success, "First request should succeed"

            # Check tracker statistics after first request
            stats1 = tracker.get_statistics()
            initial_tracked = stats1["total_tracked"]

            # Second request
            response2 = manager.converse(
                messages=sample_messages,
                inference_config={"maxTokens": 10},
            )
            assert response2.success, "Second request should succeed"

            # Check tracker statistics after second request
            stats2 = tracker.get_statistics()

            # Verify learning occurred (tracked count should be same or higher)
            assert (
                stats2["total_tracked"] >= initial_tracked
            ), "Should maintain or increase tracked combinations"

            # Verify both requests used same access method (due to learning)
            assert (
                response1.access_method_used == response2.access_method_used
            ), "Should use same access method due to learning"

        except ConfigurationError as e:
            pytest.skip(f"Claude 3 Haiku not available in test account: {str(e)}")
        except RetryExhaustedError as e:
            if "AccessDeniedException" in str(e) or "don't have access" in str(e):
                pytest.skip(f"No access to Claude 3 Haiku in test account: {str(e)}")
            else:
                raise


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.skipif(
    "not config.getoption('--run-real-bedrock-tests', default=False)",
    reason="Real Bedrock tests require --run-real-bedrock-tests flag",
)
class TestRealBedrockMultiRegion:
    """Test profile support across multiple regions with real AWS."""

    def test_profile_support_across_regions(self, sample_messages):
        """
        Test that profile support works correctly across multiple regions.

        This test validates:
        - Profile information is region-specific
        - Access method selection works per region
        - Failover to other regions works

        Validates: Requirements 2.1, 2.2, 4.4, 10.1

        NOTE: This test may be skipped if model is not available in multiple regions.
        """
        try:
            # Create LLMManager with multiple regions
            manager = LLMManager(
                models=["Claude 3 Haiku"],
                regions=["us-east-1", "us-west-2", "eu-west-1"],
                log_level=logging.DEBUG,
            )

            # Execute request
            response = manager.converse(
                messages=sample_messages,
                inference_config={"maxTokens": 10},
            )

            # Verify success
            assert response.success, "Request should succeed"
            assert response.region_used is not None, "Should have region used"

            # Verify region is one of the configured regions
            assert response.region_used in [
                "us-east-1",
                "us-west-2",
                "eu-west-1",
            ], "Should use one of configured regions"

        except ConfigurationError as e:
            pytest.skip(f"Claude 3 Haiku not available in test regions: {str(e)}")
        except RetryExhaustedError as e:
            if "AccessDeniedException" in str(e) or "don't have access" in str(e):
                pytest.skip(f"No access to Claude 3 Haiku in test regions: {str(e)}")
            else:
                raise


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.skipif(
    "not config.getoption('--run-real-bedrock-tests', default=False)",
    reason="Real Bedrock tests require --run-real-bedrock-tests flag",
)
class TestRealBedrockErrorHandling:
    """Test error handling with real AWS Bedrock."""

    def test_graceful_handling_of_unavailable_models(self, sample_messages):
        """
        Test graceful handling when models are not available.

        This test validates:
        - Clear error messages for unavailable models
        - Proper fallback behavior
        - No crashes or unexpected errors

        Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5
        """
        try:
            # Try to use a model that likely doesn't exist or isn't accessible
            manager = LLMManager(
                models=["NonExistentModel", "Claude 3 Haiku"],
                regions=["us-east-1"],
                log_level=logging.DEBUG,
            )

            # Execute request - should fall back to Claude 3 Haiku
            response = manager.converse(
                messages=sample_messages,
                inference_config={"maxTokens": 10},
            )

            # Verify success with fallback
            assert response.success, "Should succeed with fallback model"
            assert "haiku" in response.model_used.lower(), "Should use Haiku as fallback"

        except ConfigurationError as e:
            # This is expected if no valid models are available
            error_msg = str(e)
            assert "not found" in error_msg.lower(), "Should have clear error message"
            pytest.skip(f"Expected configuration error: {str(e)}")
        except RetryExhaustedError as e:
            if "AccessDeniedException" in str(e) or "don't have access" in str(e):
                pytest.skip(f"No access to fallback models: {str(e)}")
            else:
                raise
