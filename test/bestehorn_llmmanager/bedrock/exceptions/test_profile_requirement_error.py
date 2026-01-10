"""
Unit tests for ProfileRequirementError exception.

Tests the ProfileRequirementError exception class and its attributes.
"""

import pytest

from src.bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
    ExceptionDetailFields,
    ModelAccessError,
    ProfileRequirementError,
)


class TestProfileRequirementError:
    """Test suite for ProfileRequirementError exception."""

    def test_initialization_with_all_parameters(self) -> None:
        """Test ProfileRequirementError initialization with all parameters."""
        original_error = ValueError("Original validation error")
        model_id = "anthropic.claude-sonnet-4-20250514-v1:0"
        region = "us-east-1"
        custom_message = "Custom error message"

        error = ProfileRequirementError(
            model_id=model_id,
            region=region,
            original_error=original_error,
            message=custom_message,
        )

        assert error.model_id == model_id
        assert error.region == region
        assert error.original_error == original_error
        assert error.message == custom_message
        assert custom_message in str(error)

    def test_initialization_with_default_message(self) -> None:
        """Test ProfileRequirementError initialization with default message."""
        original_error = ValueError("Original validation error")
        model_id = "anthropic.claude-sonnet-4-20250514-v1:0"
        region = "us-west-2"

        error = ProfileRequirementError(
            model_id=model_id, region=region, original_error=original_error
        )

        expected_message = f"Model {model_id} requires inference profile in {region}"
        assert error.message == expected_message
        assert model_id in str(error)
        assert region in str(error)

    def test_inherits_from_model_access_error(self) -> None:
        """Test that ProfileRequirementError inherits from ModelAccessError."""
        original_error = ValueError("Original validation error")
        error = ProfileRequirementError(
            model_id="test-model", region="us-east-1", original_error=original_error
        )

        assert isinstance(error, ModelAccessError)
        assert isinstance(error, Exception)

    def test_original_error_attribute(self) -> None:
        """Test that original_error attribute is accessible."""
        original_error = ValueError("AWS ValidationException")
        error = ProfileRequirementError(
            model_id="test-model", region="us-east-1", original_error=original_error
        )

        assert error.original_error is original_error
        assert str(error.original_error) == "AWS ValidationException"

    def test_details_include_model_and_region(self) -> None:
        """Test that details dictionary includes model_id and region."""
        original_error = ValueError("Original error")
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        region = "eu-west-1"

        error = ProfileRequirementError(
            model_id=model_id, region=region, original_error=original_error
        )

        assert error.details is not None
        assert ExceptionDetailFields.MODEL_ID in error.details
        assert ExceptionDetailFields.REGION in error.details
        assert error.details[ExceptionDetailFields.MODEL_ID] == model_id
        assert error.details[ExceptionDetailFields.REGION] == region

    def test_string_representation(self) -> None:
        """Test string representation of ProfileRequirementError."""
        original_error = ValueError("Validation failed")
        model_id = "test-model-id"
        region = "ap-southeast-1"

        error = ProfileRequirementError(
            model_id=model_id, region=region, original_error=original_error
        )

        error_str = str(error)
        assert model_id in error_str
        assert region in error_str
        assert "requires inference profile" in error_str

    def test_repr_representation(self) -> None:
        """Test repr representation of ProfileRequirementError."""
        original_error = ValueError("Validation failed")
        model_id = "test-model"
        region = "us-east-1"

        error = ProfileRequirementError(
            model_id=model_id, region=region, original_error=original_error
        )

        error_repr = repr(error)
        assert "ProfileRequirementError" in error_repr
        assert "message=" in error_repr
        assert "details=" in error_repr

    def test_can_be_raised_and_caught(self) -> None:
        """Test that ProfileRequirementError can be raised and caught."""
        original_error = ValueError("Original error")

        with pytest.raises(ProfileRequirementError) as exc_info:
            raise ProfileRequirementError(
                model_id="test-model", region="us-east-1", original_error=original_error
            )

        assert exc_info.value.model_id == "test-model"
        assert exc_info.value.region == "us-east-1"
        assert exc_info.value.original_error == original_error

    def test_can_be_caught_as_model_access_error(self) -> None:
        """Test that ProfileRequirementError can be caught as ModelAccessError."""
        original_error = ValueError("Original error")

        with pytest.raises(ModelAccessError) as exc_info:
            raise ProfileRequirementError(
                model_id="test-model", region="us-east-1", original_error=original_error
            )

        # Should be caught as ModelAccessError
        assert isinstance(exc_info.value, ProfileRequirementError)

    def test_different_original_error_types(self) -> None:
        """Test ProfileRequirementError with different original error types."""
        # Test with different exception types
        value_error = ValueError("Value error")
        runtime_error = RuntimeError("Runtime error")
        type_error = TypeError("Type error")

        for original_error in [value_error, runtime_error, type_error]:
            error = ProfileRequirementError(
                model_id="test-model", region="us-east-1", original_error=original_error
            )
            assert error.original_error == original_error
            assert isinstance(error.original_error, type(original_error))

    def test_custom_message_overrides_default(self) -> None:
        """Test that custom message overrides the default message."""
        original_error = ValueError("Original error")
        default_error = ProfileRequirementError(
            model_id="test-model", region="us-east-1", original_error=original_error
        )
        custom_error = ProfileRequirementError(
            model_id="test-model",
            region="us-east-1",
            original_error=original_error,
            message="Custom message",
        )

        assert default_error.message != custom_error.message
        assert "Custom message" == custom_error.message
        assert "requires inference profile" in default_error.message

    def test_access_method_not_set_in_details(self) -> None:
        """Test that access_method is not set in details (inherited from ModelAccessError)."""
        original_error = ValueError("Original error")
        error = ProfileRequirementError(
            model_id="test-model", region="us-east-1", original_error=original_error
        )

        # access_method should not be in details since it's not provided
        assert error.access_method is None
