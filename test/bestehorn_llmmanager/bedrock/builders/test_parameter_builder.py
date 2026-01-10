"""
Tests for ParameterBuilder class.
"""

import copy

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.builders.parameter_builder import (
    ParameterBuilder,
    ParameterFields,
)
from bestehorn_llmmanager.bedrock.models.model_specific_structures import (
    ModelSpecificConfig,
)


# Hypothesis strategies for generating test data
def nested_dict_strategy(max_depth: int = 3) -> st.SearchStrategy:
    """
    Generate nested dictionaries with various data types.

    Args:
        max_depth: Maximum nesting depth

    Returns:
        Hypothesis strategy for nested dictionaries
    """
    simple_values = st.one_of(
        st.text(),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.booleans(),
        st.none(),
    )

    def extend_dict(children: st.SearchStrategy) -> st.SearchStrategy:
        return st.one_of(
            st.lists(children, max_size=5),
            st.dictionaries(st.text(min_size=1, max_size=20), children, max_size=5),
        )

    return st.recursive(
        simple_values,
        extend_dict,
        max_leaves=10,
    )


additional_fields_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=50),
    values=nested_dict_strategy(max_depth=3),
    max_size=10,
)

model_name_strategy = st.sampled_from(
    [
        "Claude 3 Haiku",
        "Claude 3 Sonnet",
        "Claude 3.5 Sonnet v2",
        "Claude Sonnet 4",
        "Claude 3 Opus",
        "Titan Text Express",
        "Llama 3.1 70B",
        "us.anthropic.claude-sonnet-4-20250514-v1:0",
    ]
)


class TestParameterBuilder:
    """Test ParameterBuilder functionality."""

    def test_build_additional_fields_none_inputs(self):
        """Test None and empty additionalModelRequestFields (Requirement 1.3)."""
        builder = ParameterBuilder()

        # Test with all None
        result = builder.build_additional_fields(
            model_name="Claude 3 Haiku",
            model_specific_config=None,
            additional_model_request_fields=None,
        )
        assert result is None

        # Test with empty dict
        result = builder.build_additional_fields(
            model_name="Claude 3 Haiku",
            model_specific_config=None,
            additional_model_request_fields={},
        )
        assert result == {}

    def test_enable_extended_context_with_claude_sonnet_4(self):
        """Test enable_extended_context with Claude Sonnet 4 (Requirement 2.1)."""
        builder = ParameterBuilder()
        config = ModelSpecificConfig(enable_extended_context=True)

        result = builder.build_additional_fields(
            model_name="Claude Sonnet 4",
            model_specific_config=config,
        )

        assert result is not None
        assert ParameterFields.ANTHROPIC_BETA in result
        assert (
            ParameterBuilder.EXTENDED_CONTEXT_BETA_HEADER in result[ParameterFields.ANTHROPIC_BETA]
        )

    def test_enable_extended_context_with_incompatible_model(self):
        """Test enable_extended_context with incompatible models (Requirement 2.2)."""
        builder = ParameterBuilder()
        config = ModelSpecificConfig(enable_extended_context=True)

        result = builder.build_additional_fields(
            model_name="Claude 3 Haiku",
            model_specific_config=config,
        )

        # Should not add extended context for incompatible model
        assert result is None or ParameterFields.ANTHROPIC_BETA not in result

    def test_enable_extended_context_false_default(self):
        """Test enable_extended_context=False default (Requirement 2.3)."""
        builder = ParameterBuilder()
        config = ModelSpecificConfig(enable_extended_context=False)

        result = builder.build_additional_fields(
            model_name="Claude Sonnet 4",
            model_specific_config=config,
        )

        # Should not add extended context when disabled
        assert result is None or ParameterFields.ANTHROPIC_BETA not in result

    def test_merge_anthropic_beta_no_duplicates(self):
        """Test that merging anthropic_beta doesn't create duplicates."""
        builder = ParameterBuilder()

        existing = {
            ParameterFields.ANTHROPIC_BETA: [
                "context-1m-2025-08-07",
                "other-beta-feature",
            ]
        }

        result = builder._merge_anthropic_beta(
            existing_fields=existing,
            new_beta_values=["context-1m-2025-08-07", "new-feature"],
        )

        # Should not duplicate context-1m header
        beta_array = result[ParameterFields.ANTHROPIC_BETA]
        assert beta_array.count("context-1m-2025-08-07") == 1
        assert "other-beta-feature" in beta_array
        assert "new-feature" in beta_array

    def test_merge_anthropic_beta_empty_existing(self):
        """Test merging when existing fields have no anthropic_beta."""
        builder = ParameterBuilder()

        existing = {"other_field": "value"}

        result = builder._merge_anthropic_beta(
            existing_fields=existing,
            new_beta_values=["context-1m-2025-08-07"],
        )

        assert ParameterFields.ANTHROPIC_BETA in result
        assert result[ParameterFields.ANTHROPIC_BETA] == ["context-1m-2025-08-07"]
        assert result["other_field"] == "value"

    def test_merge_anthropic_beta_non_list_existing(self):
        """Test merging when existing anthropic_beta is not a list."""
        builder = ParameterBuilder()

        existing = {ParameterFields.ANTHROPIC_BETA: "not-a-list"}

        result = builder._merge_anthropic_beta(
            existing_fields=existing,
            new_beta_values=["context-1m-2025-08-07"],
        )

        # Should replace non-list with proper list
        assert isinstance(result[ParameterFields.ANTHROPIC_BETA], list)
        assert "context-1m-2025-08-07" in result[ParameterFields.ANTHROPIC_BETA]

    def test_is_extended_context_compatible(self):
        """Test model compatibility checking."""
        builder = ParameterBuilder()

        # Compatible models
        assert builder._is_extended_context_compatible(model_name="Claude Sonnet 4")
        assert builder._is_extended_context_compatible(
            model_name="us.anthropic.claude-sonnet-4-20250514-v1:0"
        )
        assert builder._is_extended_context_compatible(model_name="Claude 3.5 Sonnet v2")

        # Incompatible models
        assert not builder._is_extended_context_compatible(model_name="Claude 3 Haiku")
        assert not builder._is_extended_context_compatible(model_name="Titan Text Express")

    def test_priority_order_direct_fields_only(self):
        """Test that direct fields are used when no config provided."""
        builder = ParameterBuilder()

        direct_fields = {"custom_param": "value"}

        result = builder.build_additional_fields(
            model_name="Claude 3 Haiku",
            additional_model_request_fields=direct_fields,
        )

        assert result == direct_fields

    def test_priority_order_config_custom_fields(self):
        """Test that config custom_fields merge with direct fields."""
        builder = ParameterBuilder()

        direct_fields = {"param1": "value1"}
        config = ModelSpecificConfig(
            custom_fields={"param2": "value2"},
        )

        result = builder.build_additional_fields(
            model_name="Claude 3 Haiku",
            model_specific_config=config,
            additional_model_request_fields=direct_fields,
        )

        assert result["param1"] == "value1"
        assert result["param2"] == "value2"

    def test_priority_order_config_overrides_direct(self):
        """Test that config custom_fields override direct fields."""
        builder = ParameterBuilder()

        direct_fields = {"param": "original"}
        config = ModelSpecificConfig(
            custom_fields={"param": "override"},
        )

        result = builder.build_additional_fields(
            model_name="Claude 3 Haiku",
            model_specific_config=config,
            additional_model_request_fields=direct_fields,
        )

        assert result["param"] == "override"

    # Property-Based Tests

    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow],
    )
    @given(
        additional_fields=additional_fields_strategy,
        model_name=model_name_strategy,
    )
    def test_property_parameter_pass_through_preservation(
        self,
        additional_fields: dict,
        model_name: str,
    ):
        """
        Property 1: Parameter Pass-Through Preservation

        Feature: additional-model-request-fields, Property 1: For any valid
        additionalModelRequestFields dictionary (including nested structures
        and multiple key-value pairs), when passed to the ParameterBuilder,
        the complete structure SHALL be preserved and passed without modification.

        Validates: Requirements 1.1, 1.2, 1.5
        """
        builder = ParameterBuilder()

        # Build with only additional_fields (no config)
        result = builder.build_additional_fields(
            model_name=model_name,
            additional_model_request_fields=additional_fields,
        )

        # Verify complete structure preservation
        assert result == additional_fields

        # Verify it's a deep copy (not the same object)
        if additional_fields:
            assert result is not additional_fields

    @settings(max_examples=100)
    @given(
        additional_fields=additional_fields_strategy,
        model_name=model_name_strategy,
    )
    def test_property_parameter_coexistence(
        self,
        additional_fields: dict,
        model_name: str,
    ):
        """
        Property 2: Parameter Coexistence

        Feature: additional-model-request-fields, Property 2: For any valid
        inferenceConfig and additionalModelRequestFields, when both are provided,
        both parameters SHALL be included without interference.

        Note: This test verifies that ParameterBuilder doesn't interfere with
        additionalModelRequestFields. The actual coexistence with inferenceConfig
        is tested at the LLMManager level.

        Validates: Requirements 1.4
        """
        builder = ParameterBuilder()

        # Build with additional_fields
        result = builder.build_additional_fields(
            model_name=model_name,
            additional_model_request_fields=additional_fields,
        )

        # Verify additionalModelRequestFields are preserved
        assert result == additional_fields

    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(
        existing_beta=st.lists(st.text(min_size=1, max_size=50), max_size=10),
        new_beta=st.lists(st.text(min_size=1, max_size=50), max_size=10),
        model_name=st.sampled_from(
            ["Claude Sonnet 4", "us.anthropic.claude-sonnet-4-20250514-v1:0"]
        ),
    )
    def test_property_extended_context_beta_merging(
        self,
        existing_beta: list,
        new_beta: list,
        model_name: str,
    ):
        """
        Property 3: Extended Context Beta Merging

        Feature: additional-model-request-fields, Property 3: For any existing
        additionalModelRequestFields containing an anthropic_beta array, when
        enable_extended_context=True is set, the system SHALL merge the beta
        arrays without creating duplicates of the context-1m-2025-08-07 value.

        Validates: Requirements 2.4
        """
        builder = ParameterBuilder()

        # Create existing fields with anthropic_beta
        existing_fields = {
            ParameterFields.ANTHROPIC_BETA: existing_beta.copy(),
            "other_field": "value",
        }

        # Add extended context header to new_beta to test deduplication
        new_beta_with_context = new_beta.copy()
        if ParameterBuilder.EXTENDED_CONTEXT_BETA_HEADER not in new_beta_with_context:
            new_beta_with_context.append(ParameterBuilder.EXTENDED_CONTEXT_BETA_HEADER)

        # Create config with extended context and custom beta values
        config = ModelSpecificConfig(
            enable_extended_context=True,
            custom_fields={ParameterFields.ANTHROPIC_BETA: new_beta.copy()},
        )

        result = builder.build_additional_fields(
            model_name=model_name,
            model_specific_config=config,
            additional_model_request_fields=existing_fields,
        )

        # Verify no duplicates
        beta_array = result[ParameterFields.ANTHROPIC_BETA]
        assert len(beta_array) == len(set(beta_array)), "Beta array contains duplicates"

        # Verify extended context header is present
        assert ParameterBuilder.EXTENDED_CONTEXT_BETA_HEADER in beta_array

        # Verify all original values are preserved
        for value in existing_beta:
            if value:  # Skip empty strings
                assert value in beta_array

    @settings(max_examples=100)
    @given(
        additional_fields=additional_fields_strategy,
    )
    def test_property_nested_structure_preservation(
        self,
        additional_fields: dict,
    ):
        """
        Test that nested structures are preserved through ParameterBuilder.

        Validates: Requirements 1.2
        """
        builder = ParameterBuilder()

        # Make a deep copy to compare later
        original = copy.deepcopy(additional_fields)

        result = builder.build_additional_fields(
            model_name="Claude 3 Haiku",
            additional_model_request_fields=additional_fields,
        )

        # Verify nested structure is preserved
        assert result == original

    @settings(max_examples=100)
    @given(
        custom_fields=additional_fields_strategy,
        enable_extended_context=st.booleans(),
        model_name=model_name_strategy,
    )
    def test_property_model_specific_config_extraction(
        self,
        custom_fields: dict,
        enable_extended_context: bool,
        model_name: str,
    ):
        """
        Property 4: ModelSpecificConfig Extraction

        Feature: additional-model-request-fields, Property 4: For any
        ModelSpecificConfig instance provided, the ParameterBuilder SHALL
        correctly extract and apply the additionalModelRequestFields, including
        both enable_extended_context transformations and custom_fields.

        Validates: Requirements 3.2, 3.4
        """
        builder = ParameterBuilder()

        config = ModelSpecificConfig(
            enable_extended_context=enable_extended_context,
            custom_fields=custom_fields,
        )

        result = builder.build_additional_fields(
            model_name=model_name,
            model_specific_config=config,
        )

        # Verify custom_fields are applied
        if custom_fields:
            for key, value in custom_fields.items():
                # Skip anthropic_beta if extended context is enabled and model is compatible
                if (
                    key == ParameterFields.ANTHROPIC_BETA
                    and enable_extended_context
                    and builder._is_extended_context_compatible(model_name=model_name)
                ):
                    # Beta array will be merged, so just check it exists
                    assert key in result
                else:
                    assert result[key] == value

        # Verify enable_extended_context is applied for compatible models
        if enable_extended_context and builder._is_extended_context_compatible(
            model_name=model_name
        ):
            assert ParameterFields.ANTHROPIC_BETA in result
            assert (
                ParameterBuilder.EXTENDED_CONTEXT_BETA_HEADER
                in result[ParameterFields.ANTHROPIC_BETA]
            )
