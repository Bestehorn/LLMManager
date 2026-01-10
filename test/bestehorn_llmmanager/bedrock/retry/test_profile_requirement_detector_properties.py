"""
Property-based tests for profile requirement detection.

This module contains property-based tests using Hypothesis to verify
universal properties of profile requirement detection.

**Feature: inference-profile-support**

Properties tested:
1. Profile Requirement Detection Accuracy
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.retry.profile_requirement_detector import (
    ProfileRequirementDetector,
)

# ============================================================================
# Hypothesis Strategies
# ============================================================================


@st.composite
def profile_requirement_error_strategy(draw: st.DrawFn) -> Exception:
    """
    Generate error messages that indicate profile requirement.

    Generates ValidationException-like errors with various profile requirement
    patterns embedded in the message.
    """
    # Profile requirement patterns
    patterns = [
        "with on-demand throughput isn't supported",
        "retry your request with the id or arn of an inference profile",
        "inference profile that contains this model",
        "model id anthropic.claude-sonnet-4-20250514-v1:0 isn't supported",
    ]

    # Model IDs to use in messages
    model_ids = [
        "anthropic.claude-sonnet-4-20250514-v1:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
        "amazon.titan-text-express-v1",
        "meta.llama3-70b-instruct-v1:0",
    ]

    # Select pattern and model ID
    pattern = draw(st.sampled_from(patterns))
    model_id = draw(st.sampled_from(model_ids))

    # Build error message with various formats
    message_templates = [
        f"Invocation of model ID {model_id} {pattern}. Retry your request.",
        f"ValidationException: Model {model_id} {pattern}",
        f"Error: {pattern} for model {model_id}",
        f"{pattern.upper()} - Model: {model_id}",
    ]

    message = draw(st.sampled_from(message_templates))

    # Add random prefix/suffix
    prefix = draw(st.sampled_from(["", "AWS Error: ", "Bedrock: ", "API Error: "]))
    suffix = draw(st.sampled_from(["", " Please try again.", " Contact support.", ""]))

    full_message = prefix + message + suffix

    return Exception(full_message)


@st.composite
def non_profile_error_strategy(draw: st.DrawFn) -> Exception:
    """
    Generate error messages that do NOT indicate profile requirement.

    Generates various error types that should not be detected as
    profile requirement errors.
    """
    # Non-profile error messages
    error_messages = [
        "ThrottlingException: Rate exceeded",
        "AccessDeniedException: User not authorized",
        "ResourceNotFoundException: Model not found",
        "ServiceUnavailableException: Service temporarily unavailable",
        "ValidationException: Invalid parameter value",
        "InternalServerError: An internal error occurred",
        "TimeoutException: Request timed out",
        "NetworkError: Connection failed",
        "Invalid request format",
        "Model is currently unavailable",
    ]

    message = draw(st.sampled_from(error_messages))

    # Add random prefix/suffix
    prefix = draw(st.sampled_from(["", "AWS Error: ", "Bedrock: ", "API Error: "]))
    suffix = draw(st.sampled_from(["", " Please try again.", " Contact support.", ""]))

    full_message = prefix + message + suffix

    return Exception(full_message)


@st.composite
def model_id_in_error_strategy(draw: st.DrawFn) -> tuple:
    """
    Generate error messages with extractable model IDs.

    Returns tuple of (error, expected_model_id).
    """
    # Model IDs
    model_ids = [
        "anthropic.claude-sonnet-4-20250514-v1:0",
        "anthropic.claude-3-haiku-20240307-v1:0",
        "amazon.titan-text-express-v1",
        "meta.llama3-70b-instruct-v1:0",
        "cohere.command-r-plus-v1:0",
    ]

    model_id = draw(st.sampled_from(model_ids))

    # Message templates that include model ID
    templates = [
        f"Invocation of model ID {model_id} with on-demand throughput isn't supported",
        f"model ID {model_id} isn't supported",
        f"ValidationException: Model {model_id} requires inference profile",
        f"Error accessing model {model_id} - profile required",
    ]

    message = draw(st.sampled_from(templates))

    return (Exception(message), model_id)


# ============================================================================
# Property 1: Profile Requirement Detection Accuracy
# **Feature: inference-profile-support, Property 1: Profile Requirement Detection Accuracy**
# **Validates: Requirements 1.1, 1.2**
# ============================================================================


class TestProperty1ProfileRequirementDetectionAccuracy:
    """
    Property 1: Profile Requirement Detection Accuracy.

    For any ValidationException containing profile requirement patterns,
    the detector must correctly identify it as a profile requirement error.
    """

    @given(error=profile_requirement_error_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_1_detects_profile_requirement_errors(self, error: Exception) -> None:
        """
        Property: For any error with profile requirement patterns, detection returns True.

        This property verifies that all errors containing profile requirement
        patterns are correctly identified.
        """
        # Property: Should detect profile requirement
        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is True, (
            f"Failed to detect profile requirement in error: '{str(error)}'. "
            f"Expected True, got {result}"
        )

    @given(error=non_profile_error_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_1_rejects_non_profile_errors(self, error: Exception) -> None:
        """
        Property: For any error without profile requirement patterns, detection returns False.

        This property verifies that errors not related to profile requirements
        are correctly rejected.
        """
        # Property: Should NOT detect profile requirement
        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is False, (
            f"Incorrectly detected profile requirement in error: '{str(error)}'. "
            f"Expected False, got {result}"
        )

    @given(
        error=st.one_of(
            st.just(None),
            st.just(Exception("")),
            st.just(Exception("   ")),
            st.just(Exception("\t\n")),
        )
    )
    @settings(max_examples=20, deadline=None)
    def test_property_1_handles_empty_errors(self, error: Exception) -> None:
        """
        Property: For any empty/None error, detection returns False.

        This property verifies that edge cases like None and empty errors
        are handled correctly.
        """
        # Property: Should NOT detect profile requirement for empty errors
        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is False, (
            f"Incorrectly detected profile requirement in empty error. "
            f"Expected False, got {result}"
        )

    @given(error_and_model_id=model_id_in_error_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_1_extracts_model_id_correctly(self, error_and_model_id: tuple) -> None:
        """
        Property: For any error with a model ID, extraction returns the correct model ID.

        This property verifies that model IDs are correctly extracted from
        error messages.
        """
        error, expected_model_id = error_and_model_id

        # Property: Should extract the correct model ID
        extracted_model_id = ProfileRequirementDetector.extract_model_id_from_error(error=error)

        assert extracted_model_id is not None, (
            f"Failed to extract model ID from error: '{str(error)}'. "
            f"Expected '{expected_model_id}', got None"
        )

        assert extracted_model_id == expected_model_id, (
            f"Extracted incorrect model ID from error: '{str(error)}'. "
            f"Expected '{expected_model_id}', got '{extracted_model_id}'"
        )

    @given(
        error=st.one_of(
            st.just(None),
            st.just(Exception("")),
            st.just(Exception("Error without model ID")),
            st.just(Exception("Generic error message")),
        )
    )
    @settings(max_examples=20, deadline=None)
    def test_property_1_extraction_returns_none_for_no_model_id(self, error: Exception) -> None:
        """
        Property: For any error without a model ID, extraction returns None.

        This property verifies that extraction correctly returns None when
        no model ID is present in the error message.
        """
        # Property: Should return None when no model ID present
        extracted_model_id = ProfileRequirementDetector.extract_model_id_from_error(error=error)

        assert extracted_model_id is None, (
            f"Incorrectly extracted model ID from error without model ID: '{str(error)}'. "
            f"Expected None, got '{extracted_model_id}'"
        )

    @given(
        error_message=st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd", "Pd", "Pc", "Zs"),
                whitelist_characters="-_. ",
            ),
            min_size=10,
            max_size=200,
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_1_detection_handles_arbitrary_text(self, error_message: str) -> None:
        """
        Property: For any arbitrary text, detection does not crash.

        This property verifies that the detector handles arbitrary text
        without crashing, even if it doesn't match expected patterns.
        """
        error = Exception(error_message)

        # Property: Should not crash on arbitrary text
        try:
            result = ProfileRequirementDetector.is_profile_requirement_error(error=error)
            # Result should be boolean
            assert isinstance(result, bool), f"Expected bool, got {type(result)}"
        except Exception as e:
            raise AssertionError(
                f"Detector crashed on arbitrary text: '{error_message}'. Error: {e}"
            )
