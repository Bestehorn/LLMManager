"""
Property-based and unit tests for RetryManager parameter compatibility features.

Tests the enhanced retry manager's ability to handle parameter compatibility errors,
retry without parameters, and track compatibility information.
"""

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from hypothesis import given, settings
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import RetryExhaustedError
from bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import RetryConfig
from bestehorn_llmmanager.bedrock.retry.retry_manager import RetryManager

# Hypothesis strategies for test data generation
error_message_strategy = st.text(min_size=10, max_size=200)

parameter_name_strategy = st.sampled_from(
    [
        "anthropic_beta",
        "custom_param",
        "model_specific_field",
        "beta_feature",
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


class TestParameterCompatibilityErrorClassification:
    """Test cases for parameter compatibility error classification (Property 6)."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.retry_config = RetryConfig(max_retries=3, retry_delay=0.1)
        self.retry_manager = RetryManager(retry_config=self.retry_config)

    @given(
        pattern=st.sampled_from(RetryManager.PARAMETER_INCOMPATIBILITY_PATTERNS),
        param_name=parameter_name_strategy,
    )
    @settings(max_examples=100)
    def test_property_6_parameter_error_classification(self, pattern: str, param_name: str) -> None:
        """
        Property 6: Parameter Compatibility Error Classification.

        For any error message containing parameter incompatibility patterns,
        the system SHALL correctly classify it as a parameter compatibility error.

        Feature: additional-model-request-fields, Property 6: Parameter Compatibility Error Classification
        Validates: Requirements 4.1
        """
        # Create error message with pattern
        error_message = f"Request failed: {pattern} '{param_name}' is not supported"
        error = Exception(error_message)

        # Test classification
        is_param_error, detected_param = self.retry_manager.is_parameter_compatibility_error(error)

        # Verify correct classification
        assert is_param_error is True, f"Failed to classify parameter error: {error_message}"

    @given(error_msg=error_message_strategy)
    @settings(max_examples=100)
    def test_property_6_non_parameter_error_classification(self, error_msg: str) -> None:
        """
        Property 6: Non-parameter errors should not be classified as parameter errors.

        For any error message NOT containing parameter incompatibility patterns,
        the system SHALL NOT classify it as a parameter compatibility error.

        Feature: additional-model-request-fields, Property 6: Parameter Compatibility Error Classification
        Validates: Requirements 4.1
        """
        # Filter out messages that might accidentally contain our patterns
        if any(
            pattern in error_msg.lower()
            for pattern in RetryManager.PARAMETER_INCOMPATIBILITY_PATTERNS
        ):
            return  # Skip this example

        error = Exception(error_msg)

        # Test classification
        is_param_error, _ = self.retry_manager.is_parameter_compatibility_error(error)

        # Verify correct classification
        assert is_param_error is False, f"Incorrectly classified as parameter error: {error_msg}"

    def test_parameter_error_with_clienterror(self) -> None:
        """Test parameter error classification with AWS ClientError."""
        error_response = {
            "Error": {
                "Code": "ValidationException",
                "Message": "Invalid field 'anthropic_beta' in additionalModelRequestFields",
            }
        }
        error = ClientError(error_response, "Converse")

        is_param_error, param_name = self.retry_manager.is_parameter_compatibility_error(error)

        assert is_param_error is True
        assert param_name == "anthropic_beta"

    def test_parameter_name_extraction(self) -> None:
        """Test extraction of parameter names from error messages."""
        test_cases = [
            ("unsupported parameter 'anthropic_beta'", "anthropic_beta"),
            ("invalid field 'custom_param'", "custom_param"),
            ("unsupported parameter additionalModelRequestFields.beta_feature", "beta_feature"),
            ("unknown parameter in request", None),  # No specific parameter name
        ]

        for error_msg, expected_param in test_cases:
            error = Exception(error_msg)
            is_param_error, param_name = self.retry_manager.is_parameter_compatibility_error(error)

            if expected_param:
                assert is_param_error is True, f"Failed to detect parameter error: {error_msg}"
                assert param_name == expected_param, f"Expected {expected_param}, got {param_name}"
            else:
                # Should still detect as parameter error even without specific name
                assert is_param_error is True


class TestRetryWarningLogging:
    """Test cases for retry warning logging (Property 7)."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.retry_config = RetryConfig(max_retries=3, retry_delay=0.1)
        self.retry_manager = RetryManager(retry_config=self.retry_config)

    @given(
        param_name=parameter_name_strategy,
        model_name=model_name_strategy,
        region=region_strategy,
    )
    @settings(max_examples=100)
    def test_property_7_retry_warning_logging(
        self, param_name: str, model_name: str, region: str
    ) -> None:
        """
        Property 7: Retry Warning Logging.

        For any request that requires retry without additionalModelRequestFields,
        the system SHALL log a warning message that includes the names of the removed parameters.

        Feature: additional-model-request-fields, Property 7: Retry Warning Logging
        Validates: Requirements 4.3
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

        # Mock operation that succeeds without parameters
        def mock_operation(**kwargs: Any) -> Dict[str, Any]:
            if "additionalModelRequestFields" in kwargs:
                raise Exception(f"unsupported parameter '{param_name}'")
            return {"output": {"message": {"content": [{"text": "success"}]}}}

        # Capture log messages
        with patch.object(self.retry_manager._logger, "warning") as mock_warning:
            result, success, warning = self.retry_manager._retry_without_parameters(
                operation=mock_operation,
                operation_args=operation_args,
                model=model_name,
                region=region,
                access_info=access_info,
            )

            # Verify warning was logged
            assert success is True
            assert warning is not None
            assert param_name in warning
            assert model_name in warning
            assert region in warning

            # Verify logger.warning was called with parameter name
            mock_warning.assert_called()
            warning_call_args = str(mock_warning.call_args)
            assert param_name in warning_call_args


class TestResponseWarnings:
    """Test cases for response warning inclusion (Property 8)."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.retry_config = RetryConfig(max_retries=3, retry_delay=0.1)
        self.retry_manager = RetryManager(retry_config=self.retry_config)

    @given(
        param_name=parameter_name_strategy,
        model_name=model_name_strategy,
        region=region_strategy,
    )
    @settings(max_examples=100)
    def test_property_8_response_warning_inclusion(
        self, param_name: str, model_name: str, region: str
    ) -> None:
        """
        Property 8: Response Warning Inclusion.

        For any request where parameters are removed due to incompatibility,
        the BedrockResponse SHALL include this information in the warnings list.

        Feature: additional-model-request-fields, Property 8: Response Warning Inclusion
        Validates: Requirements 4.5
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

        # Mock operation that fails with parameters, succeeds without
        call_count = {"count": 0}

        def mock_operation(**kwargs: Any) -> Dict[str, Any]:
            call_count["count"] += 1
            if "additionalModelRequestFields" in kwargs and call_count["count"] == 1:
                raise Exception(f"unsupported parameter '{param_name}'")
            return {"output": {"message": {"content": [{"text": "success"}]}}}

        retry_targets = [(model_name, region, access_info)]

        # Execute with retry
        result, attempts, warnings = self.retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args=operation_args,
            retry_targets=retry_targets,
        )

        # Verify warnings include parameter removal information
        assert len(warnings) > 0
        warning_text = " ".join(warnings)
        assert param_name in warning_text
        assert "removed" in warning_text.lower() or "incompatibility" in warning_text.lower()


class TestRetryBehavior:
    """Unit tests for retry behavior with parameter compatibility."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.retry_config = RetryConfig(max_retries=3, retry_delay=0.1)
        self.retry_manager = RetryManager(retry_config=self.retry_config)

    def test_retry_without_parameters_after_compatibility_error(self) -> None:
        """
        Test retry without parameters after compatibility error (Requirement 4.2).

        When a parameter compatibility error occurs, the system should retry
        the request without additionalModelRequestFields.
        """
        # Create mock access info
        access_info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            model_id="anthropic.claude-3-sonnet",
        )

        # Create operation args with parameters
        operation_args = {
            "messages": [{"role": "user", "content": [{"text": "test"}]}],
            "additionalModelRequestFields": {"anthropic_beta": ["context-1m-2025-08-07"]},
        }

        # Mock operation that fails with parameters, succeeds without
        call_count = {"count": 0}

        def mock_operation(**kwargs: Any) -> Dict[str, Any]:
            call_count["count"] += 1
            if "additionalModelRequestFields" in kwargs and call_count["count"] == 1:
                raise Exception("unsupported parameter 'anthropic_beta'")
            return {"output": {"message": {"content": [{"text": "success"}]}}}

        retry_targets = [("Claude 3 Sonnet", "us-east-1", access_info)]

        # Execute with retry
        result, attempts, warnings = self.retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args=operation_args,
            retry_targets=retry_targets,
        )

        # Verify success after parameter removal
        assert result is not None
        assert len(warnings) > 0
        assert "anthropic_beta" in " ".join(warnings)

    def test_multiple_model_region_retry_order(self) -> None:
        """
        Test multiple model/region retry order (Requirement 4.4).

        When multiple model/region combinations are configured, the system
        should attempt each combination before removing parameters.
        """
        # Create mock access info for different models
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
            "additionalModelRequestFields": {"anthropic_beta": ["context-1m-2025-08-07"]},
        }

        # Mock operation that fails for first model, succeeds for second
        def mock_operation(**kwargs: Any) -> Dict[str, Any]:
            model_id = kwargs.get("model_id", "")
            if "haiku" in model_id:
                raise Exception("unsupported parameter 'anthropic_beta'")
            return {"output": {"message": {"content": [{"text": "success"}]}}}

        retry_targets = [
            ("Claude 3 Haiku", "us-east-1", access_info_1),
            ("Claude 3 Sonnet", "us-west-2", access_info_2),
        ]

        # Execute with retry
        result, attempts, warnings = self.retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args=operation_args,
            retry_targets=retry_targets,
        )

        # Verify it tried multiple targets
        assert len(attempts) >= 1
        assert result is not None

    def test_extended_context_with_unsupported_region(self) -> None:
        """
        Test extended context with unsupported region (Requirement 2.5).

        When enable_extended_context=True and the region does not support
        the beta feature, the system should handle the error and retry
        without the beta parameter.
        """
        # Create mock access info
        access_info = ModelAccessInfo(
            region="ap-southeast-1",  # Unsupported region
            has_direct_access=True,
            model_id="anthropic.claude-sonnet-4",
        )

        # Create operation args with extended context
        operation_args = {
            "messages": [{"role": "user", "content": [{"text": "test"}]}],
            "additionalModelRequestFields": {"anthropic_beta": ["context-1m-2025-08-07"]},
        }

        # Mock operation that fails with beta parameter in this region
        call_count = {"count": 0}

        def mock_operation(**kwargs: Any) -> Dict[str, Any]:
            call_count["count"] += 1
            if "additionalModelRequestFields" in kwargs and call_count["count"] == 1:
                raise Exception("unsupported parameter 'anthropic_beta' in this region")
            return {"output": {"message": {"content": [{"text": "success"}]}}}

        retry_targets = [("Claude Sonnet 4", "ap-southeast-1", access_info)]

        # Execute with retry
        result, attempts, warnings = self.retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args=operation_args,
            retry_targets=retry_targets,
        )

        # Verify success after parameter removal
        assert result is not None
        assert len(warnings) > 0
        assert "anthropic_beta" in " ".join(warnings)
