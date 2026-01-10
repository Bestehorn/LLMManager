"""
Property-based tests for input validation in RequestValidator.

Feature: additional-model-request-fields
Property 15: Input Validation
Validates: Requirements 9.1, 9.2
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from src.bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
    RequestValidationError,
)
from src.bestehorn_llmmanager.bedrock.models.model_specific_structures import (
    ModelSpecificConfig,
)
from src.bestehorn_llmmanager.bedrock.validators.request_validator import RequestValidator

# Strategy for generating invalid types (non-dict, non-None)
invalid_dict_types = st.one_of(
    st.integers(),
    st.floats(),
    st.text(),
    st.booleans(),
    st.lists(st.integers()),
    st.tuples(st.integers(), st.text()),
)

# Strategy for generating invalid types (non-bool)
invalid_bool_types = st.one_of(
    st.integers(),
    st.floats(),
    st.text(),
    st.none(),
    st.dictionaries(st.text(), st.integers()),
    st.lists(st.integers()),
)

# Strategy for generating invalid types (non-ModelSpecificConfig, non-None)
invalid_model_config_types = st.one_of(
    st.integers(),
    st.floats(),
    st.text(),
    st.booleans(),
    st.dictionaries(st.text(), st.integers()),
    st.lists(st.integers()),
)


class TestInputValidationProperties:
    """Property-based tests for input validation."""

    @given(invalid_value=invalid_dict_types)
    def test_property_15_additional_model_request_fields_type_validation(
        self, invalid_value: any
    ) -> None:
        """
        Property 15: Input Validation - additionalModelRequestFields type.

        For any invalid input where additionalModelRequestFields is not a dictionary,
        the system SHALL raise a RequestValidationError with a descriptive message.

        Feature: additional-model-request-fields, Property 15: Input Validation
        Validates: Requirements 9.1
        """
        validator = RequestValidator()

        # Verify RequestValidationError is raised
        with pytest.raises(RequestValidationError) as exc_info:
            validator.validate_additional_model_request_fields(
                additional_model_request_fields=invalid_value
            )

        # Verify error message is descriptive
        error = exc_info.value
        assert "additionalModelRequestFields" in error.message
        assert "dictionary" in error.message.lower()
        assert type(invalid_value).__name__ in error.message

        # Verify invalid_fields is populated
        assert "additionalModelRequestFields" in error.invalid_fields

    def test_property_15_additional_model_request_fields_none_is_valid(self) -> None:
        """
        Property 15: Input Validation - None is valid for additionalModelRequestFields.

        When additionalModelRequestFields is None, no error should be raised.

        Feature: additional-model-request-fields, Property 15: Input Validation
        Validates: Requirements 9.1
        """
        validator = RequestValidator()

        # Should not raise any exception
        validator.validate_additional_model_request_fields(additional_model_request_fields=None)

    def test_property_15_additional_model_request_fields_dict_is_valid(self) -> None:
        """
        Property 15: Input Validation - Dictionary is valid for additionalModelRequestFields.

        When additionalModelRequestFields is a dictionary, no error should be raised.

        Feature: additional-model-request-fields, Property 15: Input Validation
        Validates: Requirements 9.1
        """
        validator = RequestValidator()

        # Should not raise any exception
        validator.validate_additional_model_request_fields(
            additional_model_request_fields={"key": "value"}
        )

    @given(invalid_value=invalid_bool_types)
    def test_property_15_enable_extended_context_type_validation(self, invalid_value: any) -> None:
        """
        Property 15: Input Validation - enable_extended_context type.

        For any invalid input where enable_extended_context is not a boolean,
        the system SHALL raise a RequestValidationError with a descriptive message.

        Feature: additional-model-request-fields, Property 15: Input Validation
        Validates: Requirements 9.2
        """
        validator = RequestValidator()

        # Verify RequestValidationError is raised
        with pytest.raises(RequestValidationError) as exc_info:
            validator.validate_enable_extended_context(enable_extended_context=invalid_value)

        # Verify error message is descriptive
        error = exc_info.value
        assert "enable_extended_context" in error.message
        assert "boolean" in error.message.lower()
        assert type(invalid_value).__name__ in error.message

        # Verify invalid_fields is populated
        assert "enable_extended_context" in error.invalid_fields

    def test_property_15_enable_extended_context_bool_is_valid(self) -> None:
        """
        Property 15: Input Validation - Boolean is valid for enable_extended_context.

        When enable_extended_context is a boolean, no error should be raised.

        Feature: additional-model-request-fields, Property 15: Input Validation
        Validates: Requirements 9.2
        """
        validator = RequestValidator()

        # Should not raise any exception for True
        validator.validate_enable_extended_context(enable_extended_context=True)

        # Should not raise any exception for False
        validator.validate_enable_extended_context(enable_extended_context=False)

    @given(invalid_value=invalid_model_config_types)
    def test_property_15_model_specific_config_type_validation(self, invalid_value: any) -> None:
        """
        Property 15: Input Validation - model_specific_config type.

        For any invalid input where model_specific_config is not a ModelSpecificConfig instance,
        the system SHALL raise a RequestValidationError with a descriptive message.

        Feature: additional-model-request-fields, Property 15: Input Validation
        Validates: Requirements 9.1, 9.2
        """
        validator = RequestValidator()

        # Verify RequestValidationError is raised
        with pytest.raises(RequestValidationError) as exc_info:
            validator.validate_model_specific_config(model_specific_config=invalid_value)

        # Verify error message is descriptive
        error = exc_info.value
        assert "model_specific_config" in error.message
        assert "ModelSpecificConfig" in error.message
        assert type(invalid_value).__name__ in error.message

        # Verify invalid_fields is populated
        assert "model_specific_config" in error.invalid_fields

    def test_property_15_model_specific_config_none_is_valid(self) -> None:
        """
        Property 15: Input Validation - None is valid for model_specific_config.

        When model_specific_config is None, no error should be raised.

        Feature: additional-model-request-fields, Property 15: Input Validation
        Validates: Requirements 9.1, 9.2
        """
        validator = RequestValidator()

        # Should not raise any exception
        validator.validate_model_specific_config(model_specific_config=None)

    def test_property_15_model_specific_config_instance_is_valid(self) -> None:
        """
        Property 15: Input Validation - ModelSpecificConfig instance is valid.

        When model_specific_config is a ModelSpecificConfig instance, no error should be raised.

        Feature: additional-model-request-fields, Property 15: Input Validation
        Validates: Requirements 9.1, 9.2
        """
        validator = RequestValidator()

        config = ModelSpecificConfig(enable_extended_context=True, custom_fields={"key": "value"})

        # Should not raise any exception
        validator.validate_model_specific_config(model_specific_config=config)

    def test_property_15_model_specific_config_validates_internal_structure(self) -> None:
        """
        Property 15: Input Validation - ModelSpecificConfig validates its own structure.

        When creating a ModelSpecificConfig with invalid internal fields,
        TypeError should be raised by ModelSpecificConfig.__post_init__.

        Feature: additional-model-request-fields, Property 15: Input Validation
        Validates: Requirements 9.1, 9.2
        """
        # Invalid enable_extended_context type
        with pytest.raises(TypeError) as exc_info:
            ModelSpecificConfig(enable_extended_context="not a bool")  # type: ignore

        assert "enable_extended_context" in str(exc_info.value)
        assert "boolean" in str(exc_info.value).lower()

        # Invalid custom_fields type
        with pytest.raises(TypeError) as exc_info:
            ModelSpecificConfig(custom_fields="not a dict")  # type: ignore

        assert "custom_fields" in str(exc_info.value)
        assert "dictionary" in str(exc_info.value).lower()
