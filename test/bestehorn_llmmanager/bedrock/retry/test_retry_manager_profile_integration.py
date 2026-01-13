"""
Unit tests for RetryManager profile integration.

Tests specific scenarios for profile requirement detection, retry logic,
access method selection, and preference learning.
"""

import pytest

from src.bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo
from src.bestehorn_llmmanager.bedrock.models.llm_manager_structures import RetryConfig
from src.bestehorn_llmmanager.bedrock.retry.retry_manager import RetryManager


@pytest.fixture(autouse=True)
def clear_tracker():
    """Clear the access method tracker before each test."""
    from src.bestehorn_llmmanager.bedrock.tracking.access_method_tracker import AccessMethodTracker

    tracker = AccessMethodTracker.get_instance()
    # Clear the preferences dictionary
    tracker._preferences.clear()
    yield
    # Clear again after test
    tracker._preferences.clear()


class TestProfileRequirementDetection:
    """Test profile requirement detection in retry flow."""

    def test_profile_requirement_detected_and_retried(self):
        """
        Test that profile requirement errors are detected and trigger immediate retry.

        Requirements: 1.1, 1.2, 4.1
        """
        # Create retry manager
        retry_config = RetryConfig(max_retries=3)
        retry_manager = RetryManager(retry_config=retry_config)

        # Create access info with both direct and profile access
        access_info = ModelAccessInfo(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            has_direct_access=True,
            has_regional_cris=True,
            regional_cris_profile_id="arn:aws:bedrock:us-east-1::inference-profile/test-profile",
        )

        # Track calls
        call_count = [0]

        def mock_operation(region, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call fails with profile requirement error
                raise Exception(
                    "Invocation of model ID anthropic.claude-3-haiku-20240307-v1:0 "
                    "with on-demand throughput isn't supported"
                )
            else:
                # Profile retry succeeds
                return {"success": True, "model_id": kwargs.get("model_id")}

        # Execute with retry
        retry_targets = [("Claude 3 Haiku", access_info.region, access_info)]
        result, attempts, warnings = retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args={},
            retry_targets=retry_targets,
        )

        # Assertions
        assert result is not None, "Should succeed with profile retry"
        assert result["success"], "Result should indicate success"
        assert len(attempts) == 1, "Should only record one attempt (profile retry doesn't count)"
        assert attempts[0].success, "Attempt should be marked as successful"
        assert len(warnings) > 0, "Should have warning about profile usage"
        assert any("profile" in w.lower() for w in warnings), "Warning should mention profile"

    def test_profile_requirement_without_profile_available(self):
        """
        Test behavior when profile is required but not available.

        Requirements: 2.4, 9.1, 9.2
        """
        # Create retry manager
        retry_config = RetryConfig(max_retries=3)
        retry_manager = RetryManager(retry_config=retry_config)

        # Create access info with only direct access (no profile)
        access_info = ModelAccessInfo(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            has_direct_access=True,
        )

        def mock_operation(region, **kwargs):
            # Always fails with profile requirement error
            raise Exception(
                "Invocation of model ID anthropic.claude-3-haiku-20240307-v1:0 "
                "with on-demand throughput isn't supported"
            )

        # Execute with retry - should fail since no profile available
        retry_targets = [("Claude 3 Haiku", access_info.region, access_info)]

        with pytest.raises(Exception):
            retry_manager.execute_with_retry(
                operation=mock_operation,
                operation_args={},
                retry_targets=retry_targets,
            )


class TestAccessMethodSelection:
    """Test intelligent model ID selection."""

    def test_direct_access_used_by_default(self):
        """
        Test that direct access is used by default when available.

        Requirements: 6.1, 6.2
        """
        # Create retry manager
        retry_config = RetryConfig(max_retries=3)
        retry_manager = RetryManager(retry_config=retry_config)

        # Create access info with both direct and profile access
        access_info = ModelAccessInfo(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            has_direct_access=True,
            has_regional_cris=True,
            regional_cris_profile_id="arn:aws:bedrock:us-east-1::inference-profile/test-profile",
        )

        # Track which model ID was used
        used_model_ids = []

        def mock_operation(region, **kwargs):
            used_model_ids.append(kwargs.get("model_id"))
            return {"success": True}

        # Execute with retry
        retry_targets = [("Claude 3 Haiku", access_info.region, access_info)]
        result, attempts, warnings = retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args={},
            retry_targets=retry_targets,
        )

        # Assertions
        assert len(used_model_ids) == 1, "Should make one call"
        assert used_model_ids[0] == access_info.model_id, "Should use direct model ID"
        assert not used_model_ids[0].startswith("arn:"), "Should not use profile ARN"

    def test_learned_preference_applied(self):
        """
        Test that learned preferences are applied to subsequent requests.

        Requirements: 5.1, 5.2, 5.4
        """
        # Create retry manager
        retry_config = RetryConfig(max_retries=3)
        retry_manager = RetryManager(retry_config=retry_config)

        # Create access info with both direct and profile access
        access_info = ModelAccessInfo(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            has_direct_access=True,
            has_regional_cris=True,
            regional_cris_profile_id="arn:aws:bedrock:us-east-1::inference-profile/test-profile",
        )

        # Record a profile requirement (simulating learned preference)
        retry_manager._access_method_tracker.record_profile_requirement(
            model_id=access_info.model_id,
            region=access_info.region,
        )

        # Track which model ID was used
        used_model_ids = []

        def mock_operation(region, **kwargs):
            used_model_ids.append(kwargs.get("model_id"))
            return {"success": True}

        # Execute with retry
        retry_targets = [("Claude 3 Haiku", access_info.region, access_info)]
        result, attempts, warnings = retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args={},
            retry_targets=retry_targets,
        )

        # Assertions
        assert len(used_model_ids) == 1, "Should make one call"
        # Should use profile instead of direct due to learned preference
        assert (
            used_model_ids[0] == access_info.regional_cris_profile_id
        ), "Should use regional CRIS profile due to learned preference"


class TestPreferenceLearning:
    """Test access method preference learning."""

    def test_successful_request_records_preference(self):
        """
        Test that successful requests record access method preferences.

        Requirements: 5.1, 5.2
        """
        # Create retry manager
        retry_config = RetryConfig(max_retries=3)
        retry_manager = RetryManager(retry_config=retry_config)

        # Create access info
        access_info = ModelAccessInfo(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            has_direct_access=True,
        )

        def mock_operation(region, **kwargs):
            return {"success": True}

        # Execute with retry
        retry_targets = [("Claude 3 Haiku", access_info.region, access_info)]
        result, attempts, warnings = retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args={},
            retry_targets=retry_targets,
        )

        # Check that preference was recorded
        preference = retry_manager._access_method_tracker.get_preference(
            model_id=access_info.model_id,
            region=access_info.region,
        )

        assert preference is not None, "Preference should be recorded"
        assert preference.prefer_direct, "Should prefer direct access"
        assert not preference.learned_from_error, "Should not be learned from error"

    def test_profile_requirement_records_preference(self):
        """
        Test that profile requirement errors record preferences.

        Requirements: 5.1, 5.2
        """
        # Create retry manager
        retry_config = RetryConfig(max_retries=3)
        retry_manager = RetryManager(retry_config=retry_config)

        # Create access info with profile
        access_info = ModelAccessInfo(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            has_direct_access=True,
            has_regional_cris=True,
            regional_cris_profile_id="arn:aws:bedrock:us-east-1::inference-profile/test-profile",
        )

        # Track calls
        call_count = [0]

        def mock_operation(region, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call fails with profile requirement
                raise Exception(
                    "Invocation of model ID anthropic.claude-3-haiku-20240307-v1:0 "
                    "with on-demand throughput isn't supported"
                )
            else:
                # Profile retry succeeds
                return {"success": True}

        # Execute with retry
        retry_targets = [("Claude 3 Haiku", access_info.region, access_info)]
        result, attempts, warnings = retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args={},
            retry_targets=retry_targets,
        )

        # Check that preference was recorded
        preference = retry_manager._access_method_tracker.get_preference(
            model_id=access_info.model_id,
            region=access_info.region,
        )

        assert preference is not None, "Preference should be recorded"
        assert not preference.prefer_direct, "Should not prefer direct access"
        assert preference.prefer_regional_cris, "Should prefer regional CRIS"
        # Note: learned_from_error is False because record_success() was called
        # after the profile retry succeeded. The profile requirement was recorded
        # during the retry, but the final success overwrites it with learned_from_error=False


class TestBackwardCompatibility:
    """Test backward compatibility with direct access."""

    def test_direct_access_models_work_unchanged(self):
        """
        Test that models with direct access continue to work without changes.

        Requirements: 6.1, 6.2, 6.3
        """
        # Create retry manager
        retry_config = RetryConfig(max_retries=3)
        retry_manager = RetryManager(retry_config=retry_config)

        # Create access info with only direct access (no profiles)
        access_info = ModelAccessInfo(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            has_direct_access=True,
        )

        def mock_operation(region, **kwargs):
            return {"success": True, "model_id": kwargs.get("model_id")}

        # Execute with retry
        retry_targets = [("Claude 3 Haiku", access_info.region, access_info)]
        result, attempts, warnings = retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args={},
            retry_targets=retry_targets,
        )

        # Assertions
        assert result["success"], "Should succeed"
        assert result["model_id"] == access_info.model_id, "Should use direct model ID"
        assert len(attempts) == 1, "Should make one attempt"
        assert attempts[0].success, "Attempt should succeed"
        assert len(warnings) == 0, "Should have no warnings"


class TestGracefulDegradation:
    """Test graceful degradation when profiles are unavailable."""

    def test_profile_required_but_unavailable_continues_to_next_model(self):
        """
        Test that when profile is required but unavailable, system continues to next model.

        Requirements: 9.1, 9.2
        """
        # Create retry manager
        retry_config = RetryConfig(max_retries=3)
        retry_manager = RetryManager(retry_config=retry_config)

        # First model: requires profile but none available
        access_info_1 = ModelAccessInfo(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
            has_direct_access=True,  # Has direct but will fail with profile requirement
        )

        # Second model: has direct access and works
        access_info_2 = ModelAccessInfo(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-east-1",
            has_direct_access=True,
        )

        call_count = [0]

        def mock_operation(region, **kwargs):
            call_count[0] += 1
            model_id = kwargs.get("model_id")

            if model_id == access_info_1.model_id:
                # First model fails with profile requirement
                raise Exception(
                    f"Invocation of model ID {model_id} with on-demand throughput isn't supported. "
                    "Retry your request with the ID or ARN of an inference profile."
                )
            else:
                # Second model succeeds
                return {"success": True, "model_id": model_id}

        # Execute with retry
        retry_targets = [
            ("Claude Sonnet 4.5", access_info_1.region, access_info_1),
            ("Claude 3 Haiku", access_info_2.region, access_info_2),
        ]
        result, attempts, warnings = retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args={},
            retry_targets=retry_targets,
        )

        # Assertions
        assert result is not None, "Should succeed with second model"
        assert result["success"], "Result should indicate success"
        assert result["model_id"] == access_info_2.model_id, "Should use second model"
        assert len(attempts) == 2, "Should have two attempts"
        assert not attempts[0].success, "First attempt should fail"
        assert attempts[1].success, "Second attempt should succeed"

    def test_all_models_require_profiles_error_message(self):
        """
        Test clear error message when all models require profiles but none available.

        Requirements: 9.3, 9.4, 9.5
        """
        from src.bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
            RetryExhaustedError,
        )

        # Create retry manager
        retry_config = RetryConfig(max_retries=3)
        retry_manager = RetryManager(retry_config=retry_config)

        # All models require profiles but none have them
        access_info_1 = ModelAccessInfo(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
            has_direct_access=True,
        )

        access_info_2 = ModelAccessInfo(
            model_id="anthropic.claude-opus-4-20250514-v1:0",
            region="us-west-2",
            has_direct_access=True,
        )

        def mock_operation(region, **kwargs):
            # All models fail with profile requirement
            model_id = kwargs.get("model_id")
            raise Exception(
                f"Invocation of model ID {model_id} with on-demand throughput isn't supported. "
                "Retry your request with the ID or ARN of an inference profile."
            )

        # Execute with retry - should raise RetryExhaustedError
        retry_targets = [
            ("Claude Sonnet 4.5", access_info_1.region, access_info_1),
            ("Claude Opus 4", access_info_2.region, access_info_2),
        ]

        with pytest.raises(RetryExhaustedError) as exc_info:
            retry_manager.execute_with_retry(
                operation=mock_operation,
                operation_args={},
                retry_targets=retry_targets,
            )

        # Check error message content
        error_message = str(exc_info.value)
        assert "inference profiles" in error_message.lower(), "Should mention inference profiles"
        assert (
            "refresh" in error_message.lower() or "catalog" in error_message.lower()
        ), "Should suggest refreshing catalog"
        assert (
            "Claude Sonnet 4.5" in error_message or "claude-sonnet-4" in error_message.lower()
        ), "Should list models that require profiles"

    def test_partial_profile_failures_error_message(self):
        """
        Test error message when some (but not all) errors are profile-related.

        Requirements: 9.3, 9.4
        """
        from src.bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
            RetryExhaustedError,
        )

        # Create retry manager
        retry_config = RetryConfig(max_retries=3)
        retry_manager = RetryManager(retry_config=retry_config)

        # First model: profile requirement
        access_info_1 = ModelAccessInfo(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
            has_direct_access=True,
        )

        # Second model: different error (throttling)
        access_info_2 = ModelAccessInfo(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            region="us-west-2",
            has_direct_access=True,
        )

        call_count = [0]

        def mock_operation(region, **kwargs):
            call_count[0] += 1
            model_id = kwargs.get("model_id")

            if model_id == access_info_1.model_id:
                # Profile requirement error
                raise Exception(
                    f"Invocation of model ID {model_id} with on-demand throughput isn't supported."
                )
            else:
                # Throttling error
                raise Exception("ThrottlingException: Rate exceeded")

        # Execute with retry - should raise RetryExhaustedError
        retry_targets = [
            ("Claude Sonnet 4.5", access_info_1.region, access_info_1),
            ("Claude 3 Haiku", access_info_2.region, access_info_2),
        ]

        with pytest.raises(RetryExhaustedError) as exc_info:
            retry_manager.execute_with_retry(
                operation=mock_operation,
                operation_args={},
                retry_targets=retry_targets,
            )

        # Check error message content
        error_message = str(exc_info.value)
        assert "inference profiles" in error_message.lower(), "Should mention inference profiles"
        assert (
            "1 of 2" in error_message or "some" in error_message.lower()
        ), "Should indicate partial profile failures"

    def test_profile_unavailable_logs_warning(self, caplog):
        """
        Test that warning is logged when profile required but unavailable.

        Requirements: 9.1, 9.2
        """
        import logging

        # Create retry manager
        retry_config = RetryConfig(max_retries=3)
        retry_manager = RetryManager(retry_config=retry_config)

        # Model requires profile but none available
        access_info = ModelAccessInfo(
            model_id="anthropic.claude-sonnet-4-20250514-v1:0",
            region="us-east-1",
            has_direct_access=True,  # No CRIS access
        )

        def mock_operation(region, **kwargs):
            # Fails with profile requirement
            raise Exception(
                "Invocation of model ID anthropic.claude-sonnet-4-20250514-v1:0 "
                "with on-demand throughput isn't supported."
            )

        # Execute with retry - will fail
        retry_targets = [("Claude Sonnet 4.5", access_info.region, access_info)]

        with caplog.at_level(logging.WARNING):
            try:
                retry_manager.execute_with_retry(
                    operation=mock_operation,
                    operation_args={},
                    retry_targets=retry_targets,
                )
            except Exception:
                pass  # Expected to fail

        # Check that warning was logged
        warning_messages = [
            record.message for record in caplog.records if record.levelname == "WARNING"
        ]
        assert any(
            "profile" in msg.lower()
            and ("unavailable" in msg.lower() or "no profile information" in msg.lower())
            for msg in warning_messages
        ), "Should log warning about profile unavailability"
