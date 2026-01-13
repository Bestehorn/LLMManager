"""
Unit tests for ProfileRequirementDetector.

This module contains unit tests for the ProfileRequirementDetector class,
verifying error pattern matching, model ID extraction, and edge case handling.

**Feature: inference-profile-support**
"""

from bestehorn_llmmanager.bedrock.retry.profile_requirement_detector import (
    ProfileRequirementDetector,
)


class TestProfileRequirementDetection:
    """Test profile requirement error detection."""

    def test_detects_on_demand_throughput_pattern(self) -> None:
        """Test detection of 'on-demand throughput' pattern."""
        error = Exception(
            "Invocation of model ID anthropic.claude-sonnet-4-20250514-v1:0 "
            "with on-demand throughput isn't supported"
        )

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is True

    def test_detects_retry_with_profile_pattern(self) -> None:
        """Test detection of 'retry with profile' pattern."""
        error = Exception(
            "ValidationException: Retry your request with the ID or ARN of an inference profile"
        )

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is True

    def test_detects_inference_profile_contains_pattern(self) -> None:
        """Test detection of 'inference profile contains' pattern."""
        error = Exception("Model requires an inference profile that contains this model")

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is True

    def test_detects_model_id_not_supported_pattern(self) -> None:
        """Test detection of 'model ID not supported' pattern."""
        error = Exception("model ID anthropic.claude-sonnet-4-20250514-v1:0 isn't supported")

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is True

    def test_detects_case_insensitive(self) -> None:
        """Test that detection is case-insensitive."""
        error = Exception("INVOCATION OF MODEL ID WITH ON-DEMAND THROUGHPUT ISN'T SUPPORTED")

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is True

    def test_rejects_throttling_error(self) -> None:
        """Test that throttling errors are not detected as profile requirement."""
        error = Exception("ThrottlingException: Rate exceeded")

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is False

    def test_rejects_access_denied_error(self) -> None:
        """Test that access denied errors are not detected as profile requirement."""
        error = Exception("AccessDeniedException: User not authorized")

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is False

    def test_rejects_resource_not_found_error(self) -> None:
        """Test that resource not found errors are not detected as profile requirement."""
        error = Exception("ResourceNotFoundException: Model not found")

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is False

    def test_rejects_generic_validation_error(self) -> None:
        """Test that generic validation errors are not detected as profile requirement."""
        error = Exception("ValidationException: Invalid parameter value")

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is False

    def test_handles_none_error(self) -> None:
        """Test that None error is handled gracefully."""
        result = ProfileRequirementDetector.is_profile_requirement_error(error=None)

        assert result is False

    def test_handles_empty_error_message(self) -> None:
        """Test that empty error message is handled gracefully."""
        error = Exception("")

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is False

    def test_handles_whitespace_only_error_message(self) -> None:
        """Test that whitespace-only error message is handled gracefully."""
        error = Exception("   \t\n   ")

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is False


class TestModelIdExtraction:
    """Test model ID extraction from error messages."""

    def test_extracts_model_id_from_invocation_pattern(self) -> None:
        """Test extraction from 'Invocation of model ID' pattern."""
        error = Exception(
            "Invocation of model ID anthropic.claude-sonnet-4-20250514-v1:0 "
            "with on-demand throughput isn't supported"
        )

        model_id = ProfileRequirementDetector.extract_model_id_from_error(error=error)

        assert model_id == "anthropic.claude-sonnet-4-20250514-v1:0"

    def test_extracts_model_id_from_not_supported_pattern(self) -> None:
        """Test extraction from 'model ID not supported' pattern."""
        error = Exception("model ID anthropic.claude-3-haiku-20240307-v1:0 isn't supported")

        model_id = ProfileRequirementDetector.extract_model_id_from_error(error=error)

        assert model_id == "anthropic.claude-3-haiku-20240307-v1:0"

    def test_extracts_model_id_case_insensitive(self) -> None:
        """Test that extraction is case-insensitive."""
        error = Exception(
            "INVOCATION OF MODEL ID ANTHROPIC.CLAUDE-SONNET-4-20250514-V1:0 "
            "WITH ON-DEMAND THROUGHPUT ISN'T SUPPORTED"
        )

        model_id = ProfileRequirementDetector.extract_model_id_from_error(error=error)

        assert model_id == "ANTHROPIC.CLAUDE-SONNET-4-20250514-V1:0"

    def test_extracts_titan_model_id(self) -> None:
        """Test extraction of Titan model ID."""
        error = Exception(
            "Invocation of model ID amazon.titan-text-express-v1 "
            "with on-demand throughput isn't supported"
        )

        model_id = ProfileRequirementDetector.extract_model_id_from_error(error=error)

        assert model_id == "amazon.titan-text-express-v1"

    def test_extracts_llama_model_id(self) -> None:
        """Test extraction of Llama model ID."""
        error = Exception("model ID meta.llama3-70b-instruct-v1:0 isn't supported")

        model_id = ProfileRequirementDetector.extract_model_id_from_error(error=error)

        assert model_id == "meta.llama3-70b-instruct-v1:0"

    def test_extracts_cohere_model_id(self) -> None:
        """Test extraction of Cohere model ID."""
        error = Exception(
            "Invocation of model ID cohere.command-r-plus-v1:0 "
            "with on-demand throughput isn't supported"
        )

        model_id = ProfileRequirementDetector.extract_model_id_from_error(error=error)

        assert model_id == "cohere.command-r-plus-v1:0"

    def test_returns_none_for_error_without_model_id(self) -> None:
        """Test that None is returned when no model ID is present."""
        error = Exception("ValidationException: Invalid parameter value")

        model_id = ProfileRequirementDetector.extract_model_id_from_error(error=error)

        assert model_id is None

    def test_returns_none_for_none_error(self) -> None:
        """Test that None is returned for None error."""
        model_id = ProfileRequirementDetector.extract_model_id_from_error(error=None)

        assert model_id is None

    def test_returns_none_for_empty_error_message(self) -> None:
        """Test that None is returned for empty error message."""
        error = Exception("")

        model_id = ProfileRequirementDetector.extract_model_id_from_error(error=error)

        assert model_id is None

    def test_returns_none_for_whitespace_only_error_message(self) -> None:
        """Test that None is returned for whitespace-only error message."""
        error = Exception("   \t\n   ")

        model_id = ProfileRequirementDetector.extract_model_id_from_error(error=error)

        assert model_id is None

    def test_extracts_first_model_id_when_multiple_present(self) -> None:
        """Test that first model ID is extracted when multiple are present."""
        error = Exception(
            "Invocation of model ID anthropic.claude-sonnet-4-20250514-v1:0 "
            "with on-demand throughput isn't supported. "
            "Try using anthropic.claude-3-haiku-20240307-v1:0 instead."
        )

        model_id = ProfileRequirementDetector.extract_model_id_from_error(error=error)

        # Should extract the first model ID
        assert model_id == "anthropic.claude-sonnet-4-20250514-v1:0"


class TestEdgeCases:
    """Test edge cases and malformed errors."""

    def test_handles_malformed_error_with_partial_pattern(self) -> None:
        """Test handling of malformed error with partial pattern match."""
        error = Exception("with on-demand throughput")

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        # Should still detect because pattern is present
        assert result is True

    def test_handles_error_with_extra_whitespace(self) -> None:
        """Test handling of error with extra whitespace."""
        error = Exception(
            "   Invocation   of   model   ID   anthropic.claude-sonnet-4-20250514-v1:0   "
            "with   on-demand   throughput   isn't   supported   "
        )

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is True

    def test_handles_error_with_newlines(self) -> None:
        """Test handling of error with newlines."""
        error = Exception(
            "Invocation of model ID\nanthropic.claude-sonnet-4-20250514-v1:0\n"
            "with on-demand throughput\nisn't supported"
        )

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is True

    def test_handles_error_with_special_characters(self) -> None:
        """Test handling of error with special characters."""
        error = Exception(
            "ValidationException: Model ID anthropic.claude-sonnet-4-20250514-v1:0 "
            "with on-demand throughput isn't supported! Please retry."
        )

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is True

    def test_handles_very_long_error_message(self) -> None:
        """Test handling of very long error message."""
        long_prefix = "A" * 1000
        error = Exception(
            f"{long_prefix} Invocation of model ID anthropic.claude-sonnet-4-20250514-v1:0 "
            "with on-demand throughput isn't supported"
        )

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is True

    def test_handles_unicode_characters_in_error(self) -> None:
        """Test handling of unicode characters in error message."""
        error = Exception(
            "Invocation of model ID anthropic.claude-sonnet-4-20250514-v1:0 "
            "with on-demand throughput isn't supported 🚫"
        )

        result = ProfileRequirementDetector.is_profile_requirement_error(error=error)

        assert result is True
