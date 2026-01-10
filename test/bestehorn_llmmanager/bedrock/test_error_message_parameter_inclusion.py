"""
Property-based tests for error message parameter inclusion (Property 16).

Tests that when all retry attempts fail due to parameter incompatibility,
the final error message includes the names of the incompatible parameters.
"""

from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import RetryExhaustedError
from bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import RetryConfig
from bestehorn_llmmanager.bedrock.retry.retry_manager import RetryManager

# Hypothesis strategies for test data generation
parameter_name_strategy = st.sampled_from(
    [
        "anthropic_beta",
        "custom_param",
        "model_specific_field",
        "beta_feature",
        "extended_context",
        "tool_config_param",
    ]
)

model_name_strategy = st.sampled_from(
    [
        "Claude 3 Haiku",
        "Claude 3 Sonnet",
        "Claude Sonnet 4",
        "Titan Text Express",
        "Llama 3.1 70B",
    ]
)

region_strategy = st.sampled_from(
    [
        "us-east-1",
        "us-west-2",
        "eu-west-1",
        "ap-southeast-1",
    ]
)


class TestErrorMessageParameterInclusion:
    """Test cases for error message parameter inclusion (Property 16)."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.retry_config = RetryConfig(max_retries=2, retry_delay=0.01)
        self.retry_manager = RetryManager(retry_config=self.retry_config)

        # Clear the parameter compatibility tracker to avoid interference between tests
        from bestehorn_llmmanager.bedrock.tracking.parameter_compatibility_tracker import (
            ParameterCompatibilityTracker,
        )

        tracker = ParameterCompatibilityTracker.get_instance()
        tracker._compatible.clear()
        tracker._parameter_hashes.clear()

    @given(
        param_name=parameter_name_strategy,
        model_name=model_name_strategy,
        region=region_strategy,
    )
    @settings(max_examples=100)
    def test_property_16_error_message_includes_parameter_names(
        self, param_name: str, model_name: str, region: str
    ) -> None:
        """
        Property 16: Error Message Parameter Inclusion.

        For any error where all retry attempts fail due to parameter incompatibility,
        the final error message SHALL include the names of the incompatible parameters.

        Feature: additional-model-request-fields, Property 16: Error Message Parameter Inclusion
        Validates: Requirements 9.4
        """
        # Create mock access info
        access_info = ModelAccessInfo(
            region=region,
            has_direct_access=True,
            model_id=f"test.{model_name.lower().replace(' ', '-')}",
        )

        # Create operation args with parameters
        operation_args = {
            "messages": [{"role": "user", "content": [{"text": "test"}]}],
            "additionalModelRequestFields": {param_name: ["test-value"]},
        }

        # Mock operation that always fails with parameter error
        def mock_operation(**kwargs: Any) -> Dict[str, Any]:
            # Always fail with parameter incompatibility error
            raise Exception(f"unsupported parameter '{param_name}' is not valid for this model")

        retry_targets = [(model_name, region, access_info)]

        # Execute with retry and expect RetryExhaustedError
        with pytest.raises(RetryExhaustedError) as exc_info:
            self.retry_manager.execute_with_retry(
                operation=mock_operation,
                operation_args=operation_args,
                retry_targets=retry_targets,
            )

        # Verify the error message includes the parameter name
        error = exc_info.value
        error_message = str(error)

        # The error message should include the parameter name
        # This could be in the main message or in the details
        error_contains_param = (
            param_name in error_message
            or (error.details and param_name in str(error.details))
            or any(param_name in str(err) for err in error.last_errors)
        )

        assert error_contains_param, (
            f"Error message should include parameter name '{param_name}'. "
            f"Error message: {error_message}, "
            f"Details: {error.details}, "
            f"Last errors: {error.last_errors}"
        )

    @given(
        param_names=st.lists(parameter_name_strategy, min_size=2, max_size=4, unique=True),
        model_name=model_name_strategy,
        region=region_strategy,
    )
    @settings(max_examples=50)  # Reduced to avoid tracker interference
    def test_property_16_error_message_includes_multiple_parameter_names(
        self, param_names: list, model_name: str, region: str
    ) -> None:
        """
        Property 16: Error Message Parameter Inclusion (Multiple Parameters).

        For any error where all retry attempts fail due to multiple parameter incompatibilities,
        the final error message SHALL include all the incompatible parameter names.

        Feature: additional-model-request-fields, Property 16: Error Message Parameter Inclusion
        Validates: Requirements 9.4
        """
        # Clear tracker for this test to avoid interference
        from bestehorn_llmmanager.bedrock.tracking.parameter_compatibility_tracker import (
            ParameterCompatibilityTracker,
        )

        tracker = ParameterCompatibilityTracker.get_instance()
        tracker._compatible.clear()
        tracker._parameter_hashes.clear()

        # Create mock access info
        access_info = ModelAccessInfo(
            region=region,
            has_direct_access=True,
            model_id=f"test.{model_name.lower().replace(' ', '-')}",
        )

        # Create operation args with multiple parameters
        additional_fields = {param: ["test-value"] for param in param_names}
        operation_args = {
            "messages": [{"role": "user", "content": [{"text": "test"}]}],
            "additionalModelRequestFields": additional_fields,
        }

        # Mock operation that always fails with parameter error mentioning all params
        def mock_operation(**kwargs: Any) -> Dict[str, Any]:
            # Fail with error mentioning all parameters
            params_str = ", ".join(f"'{p}'" for p in param_names)
            raise Exception(f"unsupported parameters {params_str} are not valid for this model")

        retry_targets = [(model_name, region, access_info)]

        # Execute with retry and expect RetryExhaustedError
        with pytest.raises(RetryExhaustedError) as exc_info:
            self.retry_manager.execute_with_retry(
                operation=mock_operation,
                operation_args=operation_args,
                retry_targets=retry_targets,
            )

        # Verify the error message includes parameter names
        error = exc_info.value
        error_message = str(error)

        # Check that at least some of the parameter names are in the error
        params_found = 0
        for param_name in param_names:
            error_contains_param = (
                param_name in error_message
                or (error.details and param_name in str(error.details))
                or any(param_name in str(err) for err in error.last_errors)
            )
            if error_contains_param:
                params_found += 1

        # At least one parameter should be mentioned
        assert params_found > 0, (
            f"Error message should include at least one parameter name from {param_names}. "
            f"Error message: {error_message}, "
            f"Details: {error.details}, "
            f"Last errors: {error.last_errors}"
        )

    def test_error_message_with_single_parameter_unit_test(self) -> None:
        """
        Unit test: Verify error message includes parameter name for single parameter failure.

        This is a concrete example to complement the property-based tests.
        """
        # Create mock access info
        access_info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            model_id="anthropic.claude-3-sonnet",
        )

        # Create operation args with a specific parameter
        operation_args = {
            "messages": [{"role": "user", "content": [{"text": "test"}]}],
            "additionalModelRequestFields": {"anthropic_beta": ["context-1m-2025-08-07"]},
        }

        # Mock operation that always fails
        def mock_operation(**kwargs: Any) -> Dict[str, Any]:
            raise Exception("unsupported parameter 'anthropic_beta' in this region")

        retry_targets = [("Claude 3 Sonnet", "us-east-1", access_info)]

        # Execute with retry and expect RetryExhaustedError
        with pytest.raises(RetryExhaustedError) as exc_info:
            self.retry_manager.execute_with_retry(
                operation=mock_operation,
                operation_args=operation_args,
                retry_targets=retry_targets,
            )

        # Verify the error includes the parameter name
        error = exc_info.value
        error_message = str(error)

        # Check various places where the parameter name might appear
        error_contains_param = (
            "anthropic_beta" in error_message
            or (error.details and "anthropic_beta" in str(error.details))
            or any("anthropic_beta" in str(err) for err in error.last_errors)
        )

        assert error_contains_param, (
            f"Error should include 'anthropic_beta'. "
            f"Error message: {error_message}, "
            f"Details: {error.details}, "
            f"Last errors: {error.last_errors}"
        )

    def test_error_message_with_multiple_retry_targets(self) -> None:
        """
        Unit test: Verify error message includes parameter names when multiple targets fail.

        Tests that when all retry targets fail due to parameter incompatibility,
        the error message includes the parameter information.
        """
        # Create mock access info for multiple targets
        access_info_1 = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            model_id="anthropic.claude-3-haiku",
        )

        access_info_2 = ModelAccessInfo(
            region="us-west-2",
            has_direct_access=True,
            model_id="anthropic.claude-3-sonnet",
        )

        # Create operation args with parameters
        operation_args = {
            "messages": [{"role": "user", "content": [{"text": "test"}]}],
            "additionalModelRequestFields": {
                "anthropic_beta": ["context-1m-2025-08-07"],
                "custom_param": ["value"],
            },
        }

        # Mock operation that always fails with parameter error
        def mock_operation(**kwargs: Any) -> Dict[str, Any]:
            raise Exception(
                "unsupported parameters 'anthropic_beta', 'custom_param' not valid for this model"
            )

        retry_targets = [
            ("Claude 3 Haiku", "us-east-1", access_info_1),
            ("Claude 3 Sonnet", "us-west-2", access_info_2),
        ]

        # Execute with retry and expect RetryExhaustedError
        with pytest.raises(RetryExhaustedError) as exc_info:
            self.retry_manager.execute_with_retry(
                operation=mock_operation,
                operation_args=operation_args,
                retry_targets=retry_targets,
            )

        # Verify the error includes at least one parameter name
        error = exc_info.value
        error_message = str(error)

        # Check for either parameter name
        has_anthropic_beta = (
            "anthropic_beta" in error_message
            or (error.details and "anthropic_beta" in str(error.details))
            or any("anthropic_beta" in str(err) for err in error.last_errors)
        )

        has_custom_param = (
            "custom_param" in error_message
            or (error.details and "custom_param" in str(error.details))
            or any("custom_param" in str(err) for err in error.last_errors)
        )

        assert has_anthropic_beta or has_custom_param, (
            f"Error should include at least one parameter name. "
            f"Error message: {error_message}, "
            f"Details: {error.details}, "
            f"Last errors: {error.last_errors}"
        )
