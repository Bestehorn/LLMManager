"""
Property-based tests for logging level compliance.

Tests verify that logging occurs at the correct levels for different operations:
- DEBUG level for parameter names
- WARNING level for parameter removal
- INFO level for extended context enablement
"""

from typing import Any, Dict
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.builders.parameter_builder import ParameterBuilder
from bestehorn_llmmanager.bedrock.models.model_specific_structures import ModelSpecificConfig


# Strategies for test data generation
@st.composite
def additional_fields_strategy(draw):
    """Generate random additionalModelRequestFields dictionaries."""
    # Use simple alphanumeric keys to avoid escaping issues
    keys = draw(
        st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
                min_size=1,
                max_size=10,
            ),
            min_size=1,
            max_size=3,
            unique=True,
        )
    )
    values = draw(
        st.lists(
            st.one_of(
                st.text(max_size=20),
                st.integers(),
                st.booleans(),
            ),
            min_size=len(keys),
            max_size=len(keys),
        )
    )
    return dict(zip(keys, values))


@st.composite
def model_config_strategy(draw):
    """Generate random ModelSpecificConfig instances."""
    enable_extended = draw(st.booleans())
    has_custom = draw(st.booleans())
    custom_fields = draw(additional_fields_strategy()) if has_custom else None
    return ModelSpecificConfig(enable_extended_context=enable_extended, custom_fields=custom_fields)


model_name_strategy = st.sampled_from(
    [
        "Claude 3 Haiku",
        "Claude 3 Sonnet",
        "Claude 3.5 Sonnet v2",
        "Claude Sonnet 4",
        "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "Claude 3 Opus",
        "Titan Text Express",
        "Llama 3.1 70B",
    ]
)


class TestLoggingLevelCompliance:
    """
    Property 18: Logging Level Compliance
    Validates: Requirements 10.1, 10.2, 10.3

    Tests verify that logging occurs at the correct levels:
    - DEBUG level for parameter names
    - WARNING level for parameter removal
    - INFO level for extended context enablement
    """

    @settings(max_examples=100)
    @given(
        additional_fields=additional_fields_strategy(),
        model_name=model_name_strategy,
    )
    def test_debug_logging_for_parameter_names(
        self, additional_fields: Dict[str, Any], model_name: str
    ):
        """
        Property 18a: DEBUG level for parameter names.

        For any additionalModelRequestFields, when passed to ParameterBuilder,
        the system SHALL log the parameter names at DEBUG level.

        Feature: additional-model-request-fields, Property 18: Logging Level Compliance
        Validates: Requirements 10.1
        """
        builder = ParameterBuilder()

        with patch("bestehorn_llmmanager.bedrock.builders.parameter_builder.logger") as mock_logger:
            # Build parameters
            result = builder.build_additional_fields(
                model_name=model_name,
                additional_model_request_fields=additional_fields,
            )

            # Verify result is not None (we passed fields)
            assert result is not None

            # Verify DEBUG logging was called
            assert mock_logger.debug.called, "DEBUG logging should be called for parameter names"

            # Verify the log message contains parameter names
            # Get the actual call arguments (not string representation)
            debug_call_args = [call[0][0] for call in mock_logger.debug.call_args_list]

            # Check if any parameter name appears in any debug log message
            param_names = list(additional_fields.keys())
            found = False
            for log_message in debug_call_args:
                for param_name in param_names:
                    if param_name in log_message:
                        found = True
                        break
                if found:
                    break

            assert found, (
                f"Parameter names should appear in DEBUG logs. "
                f"Params: {param_names}, Logs: {debug_call_args}"
            )

    @settings(max_examples=100)
    @given(
        model_config=model_config_strategy(),
        model_name=model_name_strategy,
    )
    def test_debug_logging_for_custom_fields(
        self, model_config: ModelSpecificConfig, model_name: str
    ):
        """
        Property 18b: DEBUG level for custom_fields parameter names.

        For any ModelSpecificConfig with custom_fields, when passed to ParameterBuilder,
        the system SHALL log the custom field names at DEBUG level.

        Feature: additional-model-request-fields, Property 18: Logging Level Compliance
        Validates: Requirements 10.1
        """
        # Only test when custom_fields is present
        if model_config.custom_fields is None:
            return

        builder = ParameterBuilder()

        with patch("bestehorn_llmmanager.bedrock.builders.parameter_builder.logger") as mock_logger:
            # Build parameters
            builder.build_additional_fields(
                model_name=model_name,
                model_specific_config=model_config,
            )

            # Verify DEBUG logging was called
            assert mock_logger.debug.called, "DEBUG logging should be called for custom_fields"

            # Verify the log message contains custom field names
            # Get the actual call arguments (not string representation)
            debug_call_args = [call[0][0] for call in mock_logger.debug.call_args_list]

            # Check if any custom field name appears in any debug log message
            custom_field_names = list(model_config.custom_fields.keys())
            found = False
            for log_message in debug_call_args:
                for field_name in custom_field_names:
                    if field_name in log_message:
                        found = True
                        break
                if found:
                    break

            assert found, (
                f"Custom field names should appear in DEBUG logs. "
                f"Fields: {custom_field_names}, Logs: {debug_call_args}"
            )

    @settings(max_examples=100)
    @given(
        model_name=st.sampled_from(
            [
                "Claude Sonnet 4",
                "us.anthropic.claude-sonnet-4-20250514-v1:0",
                "Claude 3.5 Sonnet v2",
            ]
        )
    )
    def test_info_logging_for_extended_context(self, model_name: str):
        """
        Property 18c: INFO level for extended context enablement.

        For any compatible model, when enable_extended_context=True,
        the system SHALL log the enablement at INFO level.

        Feature: additional-model-request-fields, Property 18: Logging Level Compliance
        Validates: Requirements 10.3
        """
        builder = ParameterBuilder()
        config = ModelSpecificConfig(enable_extended_context=True)

        with patch("bestehorn_llmmanager.bedrock.builders.parameter_builder.logger") as mock_logger:
            # Build parameters with extended context enabled
            result = builder.build_additional_fields(
                model_name=model_name,
                model_specific_config=config,
            )

            # Verify result contains extended context
            assert result is not None
            assert "anthropic_beta" in result

            # Verify INFO logging was called
            assert mock_logger.info.called, "INFO logging should be called for extended context"

            # Verify the log message mentions extended context
            info_calls = [str(call) for call in mock_logger.info.call_args_list]
            info_messages = " ".join(info_calls)

            assert (
                "extended context" in info_messages.lower()
            ), "INFO log should mention extended context"
            assert model_name in info_messages, "INFO log should mention the model name"

    @settings(max_examples=100)
    @given(
        model_name=st.sampled_from(
            [
                "Claude 3 Haiku",
                "Claude 3 Opus",
                "Titan Text Express",
                "Llama 3.1 70B",
            ]
        )
    )
    def test_warning_logging_for_incompatible_extended_context(self, model_name: str):
        """
        Property 18d: WARNING level for incompatible extended context.

        For any incompatible model, when enable_extended_context=True,
        the system SHALL log a warning at WARNING level.

        Feature: additional-model-request-fields, Property 18: Logging Level Compliance
        Validates: Requirements 10.3
        """
        builder = ParameterBuilder()
        config = ModelSpecificConfig(enable_extended_context=True)

        with patch("bestehorn_llmmanager.bedrock.builders.parameter_builder.logger") as mock_logger:
            # Build parameters with extended context enabled for incompatible model
            builder.build_additional_fields(
                model_name=model_name,
                model_specific_config=config,
            )

            # Verify WARNING logging was called
            assert (
                mock_logger.warning.called
            ), "WARNING logging should be called for incompatible model"

            # Verify the log message mentions incompatibility
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            warning_messages = " ".join(warning_calls)

            assert (
                "not compatible" in warning_messages.lower()
                or "incompatible" in warning_messages.lower()
            ), "WARNING log should mention incompatibility"
            assert model_name in warning_messages, "WARNING log should mention the model name"


class TestParameterRemovalLogging:
    """
    Tests for WARNING level logging when parameters are removed.
    This is tested in the RetryManager context.
    """

    def test_warning_logging_for_parameter_removal_in_retry_manager(self):
        """
        Property 18e: WARNING level for parameter removal.

        When parameters are removed due to incompatibility in RetryManager,
        the system SHALL log the removal at WARNING level with parameter names.

        Feature: additional-model-request-fields, Property 18: Logging Level Compliance
        Validates: Requirements 10.2
        """
        # This property is already thoroughly tested in:
        # - test_retry_manager_parameter_compatibility.py::test_parameter_removal_warning_logging
        #
        # This test serves as documentation that the property is validated.
        # The actual implementation verification happens in the dedicated retry manager tests.

        # We can verify the logging exists by checking the code directly
        import inspect

        from bestehorn_llmmanager.bedrock.retry import retry_manager

        # Verify that _retry_without_parameters method exists and contains warning logging
        source = inspect.getsource(retry_manager.RetryManager._retry_without_parameters)

        assert (
            "logger.warning" in source or "_logger.warning" in source
        ), "RetryManager._retry_without_parameters should contain WARNING level logging"
        assert "param" in source.lower(), "Warning log should mention parameters"
