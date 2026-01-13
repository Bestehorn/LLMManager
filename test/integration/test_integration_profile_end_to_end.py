"""
End-to-end integration tests for inference profile support.

These tests validate the complete flow from error detection to profile retry,
access method learning, backward compatibility, and parallel processing.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from bestehorn_llmmanager.bedrock.models.llm_manager_structures import RetryConfig
from bestehorn_llmmanager.bedrock.retry.profile_requirement_detector import (
    ProfileRequirementDetector,
)
from bestehorn_llmmanager.bedrock.tracking.access_method_tracker import (
    AccessMethodTracker,
)
from bestehorn_llmmanager.llm_manager import LLMManager
from bestehorn_llmmanager.parallel_llm_manager import ParallelLLMManager

# Test configuration
TEST_REGIONS = ["us-east-1", "us-west-2"]
TEST_MODELS = ["Claude 3 Haiku"]


@pytest.fixture(autouse=True)
def reset_access_method_tracker():
    """Reset AccessMethodTracker singleton before each test."""
    # Clear the singleton instance
    AccessMethodTracker._instance = None
    yield
    # Clean up after test
    AccessMethodTracker._instance = None


@pytest.fixture
def sample_messages():
    """Create sample messages for testing."""
    return [{"role": "user", "content": [{"text": "Hello, this is a test message."}]}]


@pytest.mark.integration
@pytest.mark.aws_integration
class TestProfileEndToEndFlow:
    """Test complete end-to-end flow of profile support."""

    def test_complete_flow_error_detection_to_profile_retry(self, sample_messages):
        """
        Test complete flow from profile requirement detection to successful retry.

        This test validates:
        - Profile requirement error detection
        - Automatic profile selection
        - Immediate retry with profile
        - Success recording

        Validates: Requirements 1.1, 2.1, 4.1, 5.1
        """
        # Create LLMManager with test configuration
        manager = LLMManager(
            models=TEST_MODELS,
            regions=TEST_REGIONS,
            retry_config=RetryConfig(max_retries=3),
            log_level=logging.DEBUG,
        )

        # Mock the bedrock client to simulate profile requirement error then success
        call_count = [0]

        def mock_converse(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: profile requirement error
                error = Exception(
                    "Invocation of model ID anthropic.claude-3-haiku-20240307-v1:0 "
                    "with on-demand throughput isn't supported. Retry your request with "
                    "the ID or ARN of an inference profile that contains this model."
                )
                error.response = {"Error": {"Code": "ValidationException", "Message": str(error)}}
                raise error
            else:
                # Second call: success with profile
                return {
                    "output": {"message": {"role": "assistant", "content": [{"text": "Success"}]}},
                    "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
                    "stopReason": "end_turn",
                    "ResponseMetadata": {"HTTPStatusCode": 200},
                }

        with patch.object(manager._bedrock_client, "converse", side_effect=mock_converse):
            # Execute request
            response = manager.converse(messages=sample_messages)

            # Verify success
            assert response.success, "Request should succeed after profile retry"
            assert response.get_content() == "Success", "Should get expected content"

            # Verify profile was used
            warnings = response.get_warnings()
            assert any(
                "profile" in w.lower() for w in warnings
            ), "Should have warning about profile usage"

    def test_access_method_learning_across_multiple_requests(self, sample_messages):
        """
        Test that access method preferences are learned and applied across requests.

        This test validates:
        - First request learns profile requirement
        - Second request uses learned preference immediately
        - No unnecessary retries on second request

        Validates: Requirements 5.1, 5.2, 5.3, 5.4
        """
        # Create LLMManager
        manager = LLMManager(
            models=TEST_MODELS,
            regions=TEST_REGIONS,
            retry_config=RetryConfig(max_retries=3),
            log_level=logging.DEBUG,
        )

        # Track calls
        call_count = [0]
        model_ids_used = []

        def mock_converse(**kwargs):
            call_count[0] += 1
            model_id = kwargs.get("modelId", "")
            model_ids_used.append(model_id)

            # First request: direct fails, profile succeeds
            if call_count[0] == 1:
                error = Exception(
                    "Invocation of model ID anthropic.claude-3-haiku-20240307-v1:0 "
                    "with on-demand throughput isn't supported."
                )
                error.response = {"Error": {"Code": "ValidationException", "Message": str(error)}}
                raise error
            else:
                # All other calls succeed
                return {
                    "output": {"message": {"role": "assistant", "content": [{"text": "Success"}]}},
                    "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
                    "stopReason": "end_turn",
                    "ResponseMetadata": {"HTTPStatusCode": 200},
                }

        with patch.object(manager._bedrock_client, "converse", side_effect=mock_converse):
            # First request - learns profile requirement
            response1 = manager.converse(messages=sample_messages)
            assert response1.success, "First request should succeed"

            # Second request - should use learned preference
            response2 = manager.converse(messages=sample_messages)
            assert response2.success, "Second request should succeed"

            # Verify learning occurred
            # First request: direct (failed) + profile (succeeded) = 2 calls
            # Second request: profile (succeeded) = 1 call
            # Total: 3 calls
            assert call_count[0] == 3, f"Expected 3 calls, got {call_count[0]}"

            # Verify second request used profile directly
            assert len(model_ids_used) == 3, "Should have 3 model IDs recorded"
            # Third call (second request) should use profile ARN
            assert model_ids_used[2].startswith(
                "arn:"
            ), "Second request should use profile ARN directly"

    def test_backward_compatibility_with_existing_code(self, sample_messages):
        """
        Test that existing code using direct access continues to work unchanged.

        This test validates:
        - Direct access models work without changes
        - No profile detection overhead for direct access
        - Response structure unchanged

        Validates: Requirements 6.1, 6.2, 6.3
        """
        # Create LLMManager
        manager = LLMManager(
            models=TEST_MODELS,
            regions=TEST_REGIONS,
            log_level=logging.DEBUG,
        )

        # Mock successful direct access
        def mock_converse(**kwargs):
            return {
                "output": {
                    "message": {"role": "assistant", "content": [{"text": "Direct success"}]}
                },
                "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
                "stopReason": "end_turn",
                "ResponseMetadata": {"HTTPStatusCode": 200},
            }

        with patch.object(manager._bedrock_client, "converse", side_effect=mock_converse):
            # Execute request
            response = manager.converse(messages=sample_messages)

            # Verify success with direct access
            assert response.success, "Request should succeed"
            assert response.get_content() == "Direct success", "Should get expected content"

            # Verify no profile-related warnings
            warnings = response.get_warnings()
            assert not any(
                "profile" in w.lower() for w in warnings
            ), "Should not have profile warnings for direct access"

            # Verify access method
            assert response.access_method_used == "direct", "Should use direct access"
            assert not response.inference_profile_used, "Should not use profile"
            assert response.inference_profile_id is None, "Should not have profile ID"


class TestParallelProcessingWithProfiles:
    """Test parallel processing with profile support."""

    def test_parallel_processing_with_profiles(self, sample_messages):
        """
        Test that profile support works correctly in parallel processing.

        This test validates:
        - Profile detection works in parallel requests
        - Each request gets independent access method selection
        - Profile retry works for individual requests
        - Statistics aggregation works correctly

        Validates: Requirements 10.1, 10.2, 10.3
        """
        from bestehorn_llmmanager.bedrock.models.parallel_structures import (
            BedrockConverseRequest,
        )

        # Create ParallelLLMManager
        manager = ParallelLLMManager(
            models=TEST_MODELS,
            regions=TEST_REGIONS,
            log_level=logging.DEBUG,
        )

        # Create multiple requests
        requests = [
            BedrockConverseRequest(messages=sample_messages),
            BedrockConverseRequest(messages=sample_messages),
            BedrockConverseRequest(messages=sample_messages),
        ]

        # Mock responses with mixed access methods
        call_count = [0]

        def mock_converse(**kwargs):
            call_count[0] += 1
            # First request: profile requirement then success
            # Other requests: direct success
            if call_count[0] == 1:
                error = Exception(
                    "Invocation of model ID anthropic.claude-3-haiku-20240307-v1:0 "
                    "with on-demand throughput isn't supported."
                )
                error.response = {"Error": {"Code": "ValidationException", "Message": str(error)}}
                raise error
            else:
                return {
                    "output": {"message": {"role": "assistant", "content": [{"text": "Success"}]}},
                    "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
                    "stopReason": "end_turn",
                    "ResponseMetadata": {"HTTPStatusCode": 200},
                }

        with patch.object(
            manager._llm_manager._bedrock_client, "converse", side_effect=mock_converse
        ):
            # Execute parallel requests
            response = manager.converse_parallel(requests=requests, target_regions_per_request=1)

            # Verify all requests succeeded
            assert response.success, "All requests should succeed"
            assert len(response.request_responses) == 3, "Should have 3 responses"

            # Verify statistics
            stats = response.get_access_method_statistics()
            assert stats["total_requests"] == 3, "Should have 3 total requests"
            assert stats["profile_usage_count"] >= 1, "At least one request should use profile"


class TestProfileDetectorIntegration:
    """Test ProfileRequirementDetector integration."""

    def test_profile_detector_with_real_error_patterns(self):
        """
        Test ProfileRequirementDetector with realistic AWS error messages.

        Validates: Requirements 1.1, 1.2, 1.3
        """
        # Test various error message patterns
        error_patterns = [
            "Invocation of model ID anthropic.claude-sonnet-4-20250514-v1:0 "
            "with on-demand throughput isn't supported. Retry your request with "
            "the ID or ARN of an inference profile that contains this model.",
            "Model ID anthropic.claude-opus-4-20250514-v1:0 with on-demand throughput "
            "isn't supported. Retry your request with the ID or ARN of an inference profile.",
            "Invocation of model ID meta.llama3-3-70b-instruct-v1:0 isn't supported. "
            "Retry your request with an inference profile that contains this model.",
        ]

        for error_msg in error_patterns:
            error = Exception(error_msg)

            # Test detection
            is_profile_error = ProfileRequirementDetector.is_profile_requirement_error(error=error)
            assert is_profile_error, f"Should detect profile requirement in: {error_msg}"

            # Test model ID extraction
            model_id = ProfileRequirementDetector.extract_model_id_from_error(error=error)
            assert model_id is not None, f"Should extract model ID from: {error_msg}"
            assert "." in model_id, f"Model ID should contain provider: {model_id}"

    def test_profile_detector_with_non_profile_errors(self):
        """
        Test that ProfileRequirementDetector correctly identifies non-profile errors.

        Validates: Requirements 1.1, 1.2
        """
        # Test non-profile error patterns
        non_profile_errors = [
            "ThrottlingException: Rate exceeded",
            "AccessDeniedException: You don't have access to the model",
            "ValidationException: Invalid parameter value",
            "ServiceUnavailableException: Service temporarily unavailable",
        ]

        for error_msg in non_profile_errors:
            error = Exception(error_msg)

            # Test detection
            is_profile_error = ProfileRequirementDetector.is_profile_requirement_error(error=error)
            assert not is_profile_error, f"Should not detect profile requirement in: {error_msg}"


class TestAccessMethodTrackerIntegration:
    """Test AccessMethodTracker integration."""

    def test_tracker_persistence_across_manager_instances(self, sample_messages):
        """
        Test that AccessMethodTracker persists preferences across LLMManager instances.

        Validates: Requirements 5.3, 5.4
        """
        # Create first manager and record a preference
        manager1 = LLMManager(
            models=TEST_MODELS,
            regions=TEST_REGIONS,
            log_level=logging.DEBUG,
        )

        # Get tracker and record preference
        tracker = AccessMethodTracker.get_instance()
        tracker.record_profile_requirement(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
        )

        # Create second manager
        manager2 = LLMManager(
            models=TEST_MODELS,
            regions=TEST_REGIONS,
            log_level=logging.DEBUG,
        )

        # Verify second manager has access to same tracker
        tracker2 = manager2._retry_manager._access_method_tracker
        assert tracker2 is tracker, "Should use same tracker instance"

        # Verify preference is available
        preference = tracker2.get_preference(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
        )
        assert preference is not None, "Preference should be available"
        assert not preference.prefer_direct, "Should not prefer direct access"

    def test_tracker_statistics_aggregation(self):
        """
        Test AccessMethodTracker statistics aggregation.

        Validates: Requirements 7.4
        """
        # Get tracker
        tracker = AccessMethodTracker.get_instance()

        # Record various access methods
        tracker.record_success(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            access_method="direct",
            model_id_used="anthropic.claude-3-haiku-20240307-v1:0",
        )

        tracker.record_success(
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-west-2",
            access_method="regional_cris",
            model_id_used="arn:aws:bedrock:us-west-2::inference-profile/test",
        )

        tracker.record_profile_requirement(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
        )

        # Get statistics
        stats = tracker.get_statistics()

        # Verify statistics structure
        assert "total_tracked" in stats, "Should have total_tracked"
        assert "profile_required_count" in stats, "Should have profile_required_count"
        assert "direct_access_count" in stats, "Should have direct_access_count"
        assert "regional_cris_count" in stats, "Should have regional_cris_count"

        # Verify counts
        assert stats["total_tracked"] == 3, "Should track 3 combinations"
        assert stats["profile_required_count"] == 1, "Should have 1 profile-required"
        assert stats["direct_access_count"] == 1, "Should have 1 direct access"
        assert stats["regional_cris_count"] == 1, "Should have 1 regional CRIS"


class TestGracefulDegradation:
    """Test graceful degradation when profiles are unavailable."""

    def test_missing_profile_fallback_to_other_models(self, sample_messages):
        """
        Test that system falls back to other models when profile is unavailable.

        Validates: Requirements 9.1, 9.2
        """
        # Create LLMManager with multiple models
        manager = LLMManager(
            models=["Claude Sonnet 4.5", "Claude 3 Haiku"],
            regions=TEST_REGIONS,
            log_level=logging.DEBUG,
        )

        # Mock first model fails with profile requirement, second succeeds
        call_count = [0]

        def mock_converse(**kwargs):
            call_count[0] += 1
            model_id = kwargs.get("modelId", "")

            if "sonnet-4" in model_id.lower():
                # First model: profile requirement
                error = Exception(
                    f"Invocation of model ID {model_id} with on-demand throughput isn't supported."
                )
                error.response = {"Error": {"Code": "ValidationException", "Message": str(error)}}
                raise error
            else:
                # Second model: success
                return {
                    "output": {
                        "message": {"role": "assistant", "content": [{"text": "Fallback success"}]}
                    },
                    "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
                    "stopReason": "end_turn",
                    "ResponseMetadata": {"HTTPStatusCode": 200},
                }

        with patch.object(manager._bedrock_client, "converse", side_effect=mock_converse):
            # Execute request
            response = manager.converse(messages=sample_messages)

            # Verify success with fallback model
            assert response.success, "Should succeed with fallback model"
            assert response.get_content() == "Fallback success", "Should get fallback content"
            assert "haiku" in response.model_used.lower(), "Should use Haiku model"


class TestResponseMetadata:
    """Test response metadata for profile usage."""

    def test_response_includes_access_method_metadata(self, sample_messages):
        """
        Test that BedrockResponse includes access method metadata.

        Validates: Requirements 8.1, 8.2, 8.3, 8.5
        """
        # Create LLMManager
        manager = LLMManager(
            models=TEST_MODELS,
            regions=TEST_REGIONS,
            log_level=logging.DEBUG,
        )

        # Mock successful response
        def mock_converse(**kwargs):
            return {
                "output": {"message": {"role": "assistant", "content": [{"text": "Success"}]}},
                "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
                "stopReason": "end_turn",
                "ResponseMetadata": {"HTTPStatusCode": 200},
            }

        with patch.object(manager._bedrock_client, "converse", side_effect=mock_converse):
            # Execute request
            response = manager.converse(messages=sample_messages)

            # Verify access method metadata
            assert hasattr(response, "access_method_used"), "Should have access_method_used"
            assert hasattr(response, "inference_profile_used"), "Should have inference_profile_used"
            assert hasattr(response, "inference_profile_id"), "Should have inference_profile_id"

            # Verify values for direct access
            assert response.access_method_used in [
                "direct",
                "regional_cris",
                "global_cris",
            ], "Should have valid access method"
            assert isinstance(
                response.inference_profile_used, bool
            ), "inference_profile_used should be boolean"
