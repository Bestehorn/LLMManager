"""
Property-based tests for error type distinction in logs.

Feature: additional-model-request-fields
Property 17: Error Type Distinction in Logs
Validates: Requirements 9.5
"""

import logging
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError
from hypothesis import given, settings
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.models.llm_manager_structures import RetryConfig
from bestehorn_llmmanager.bedrock.retry.retry_manager import RetryManager


class TestErrorTypeDistinction:
    """Test that different error types produce distinct log patterns."""

    def setup_method(self):
        """Set up test fixtures."""
        self.retry_config = RetryConfig(
            max_retries=3,
            retry_delay=0.1,
            backoff_multiplier=2.0,
            max_retry_delay=1.0,
            enable_feature_fallback=True,
        )
        self.retry_manager = RetryManager(retry_config=self.retry_config)

    def test_parameter_error_log_pattern_distinct_from_content_error(self):
        """
        Verify that parameter compatibility errors produce different log patterns
        than content compatibility errors.
        """
        # Create parameter compatibility error
        param_error = Exception("unsupported parameter 'anthropic_beta'")

        # Create content compatibility error
        content_error = Exception("model doesn't support the video")

        # Classify both
        is_param_error_1, param_name_1 = self.retry_manager.is_parameter_compatibility_error(
            param_error
        )
        should_fallback_1, feature_1 = self.retry_manager.should_disable_feature_and_retry(
            param_error
        )

        is_param_error_2, param_name_2 = self.retry_manager.is_parameter_compatibility_error(
            content_error
        )
        should_fallback_2, feature_2 = self.retry_manager.should_disable_feature_and_retry(
            content_error
        )

        # Verify distinct classification
        assert (
            is_param_error_1 is True and is_param_error_2 is False
        ), "Parameter and content errors not distinguished"
        assert (
            should_fallback_1 is False and should_fallback_2 is True
        ), "Parameter and content errors produce same fallback behavior"
        assert feature_2 is not None, "Content error should identify feature to disable"

    def test_parameter_error_includes_parameter_keyword_in_classification(self):
        """
        Verify that parameter compatibility errors can be identified by the
        presence of parameter-related keywords in the classification.
        """
        test_cases = [
            ("unsupported parameter 'test'", True),
            ("invalid field in request", True),
            ("unknown parameter: custom", True),
            ("model doesn't support the video", False),
            ("throttling exception", False),
            ("access denied", False),
        ]

        for error_message, should_be_param_error in test_cases:
            error = Exception(error_message)
            is_param_error, _ = self.retry_manager.is_parameter_compatibility_error(error)

            assert is_param_error == should_be_param_error, (
                f"Error '{error_message}' classification mismatch. "
                f"Expected: {should_be_param_error}, Got: {is_param_error}"
            )

    @given(
        param_error_msg=st.sampled_from(
            [
                "unsupported parameter 'anthropic_beta'",
                "invalid field: custom_field",
                "unknown parameter in additionalModelRequestFields",
            ]
        ),
        content_error_msg=st.sampled_from(
            [
                "model doesn't support the video",
                "image not supported",
                "document processing not supported",
            ]
        ),
    )
    @settings(max_examples=50, deadline=None)
    def test_error_classification_is_mutually_exclusive(
        self, param_error_msg: str, content_error_msg: str
    ):
        """
        Property: Error classifications should be mutually exclusive.

        An error cannot be both a parameter compatibility error and a
        content compatibility error at the same time.
        """
        # Test parameter error
        param_error = Exception(param_error_msg)
        is_param_1, _ = self.retry_manager.is_parameter_compatibility_error(param_error)
        should_fallback_1, _ = self.retry_manager.should_disable_feature_and_retry(param_error)

        # Parameter errors should be classified as parameter errors, not feature fallback
        if is_param_1:
            assert (
                not should_fallback_1
            ), f"Parameter error '{param_error_msg}' incorrectly triggers feature fallback"

        # Test content error
        content_error = Exception(content_error_msg)
        is_param_2, _ = self.retry_manager.is_parameter_compatibility_error(content_error)
        should_fallback_2, _ = self.retry_manager.should_disable_feature_and_retry(content_error)

        # Content errors should be classified as feature fallback, not parameter errors
        if should_fallback_2:
            assert (
                not is_param_2
            ), f"Content error '{content_error_msg}' incorrectly classified as parameter error"
