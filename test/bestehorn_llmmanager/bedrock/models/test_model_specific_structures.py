"""
Tests for model-specific configuration structures.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.models.model_specific_structures import (
    ModelSpecificConfig,
    ModelSpecificFields,
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


custom_fields_strategy = st.one_of(
    st.none(),
    st.dictionaries(
        keys=st.text(min_size=1, max_size=50),
        values=nested_dict_strategy(max_depth=3),
        max_size=10,
    ),
)


model_specific_config_strategy = st.builds(
    ModelSpecificConfig,
    enable_extended_context=st.booleans(),
    custom_fields=custom_fields_strategy,
)


class TestModelSpecificConfig:
    """Test ModelSpecificConfig functionality."""

    def test_init_defaults(self):
        """Test initialization with default values."""
        config = ModelSpecificConfig()

        assert config.enable_extended_context is False
        assert config.custom_fields is None

    def test_init_with_values(self):
        """Test initialization with explicit values."""
        custom = {"anthropic_beta": ["context-1m-2025-08-07"]}
        config = ModelSpecificConfig(
            enable_extended_context=True,
            custom_fields=custom,
        )

        assert config.enable_extended_context is True
        assert config.custom_fields == custom

    def test_post_init_invalid_enable_extended_context_type(self):
        """Test validation of enable_extended_context type."""
        with pytest.raises(TypeError, match="enable_extended_context must be a boolean"):
            ModelSpecificConfig(enable_extended_context="true")  # type: ignore

    def test_post_init_invalid_custom_fields_type(self):
        """Test validation of custom_fields type."""
        with pytest.raises(TypeError, match="custom_fields must be a dictionary or None"):
            ModelSpecificConfig(custom_fields="not a dict")  # type: ignore

    def test_to_dict_defaults(self):
        """Test to_dict with default values."""
        config = ModelSpecificConfig()
        result = config.to_dict()

        assert result[ModelSpecificFields.ENABLE_EXTENDED_CONTEXT] is False
        assert result[ModelSpecificFields.CUSTOM_FIELDS] is None

    def test_to_dict_with_values(self):
        """Test to_dict with explicit values."""
        custom = {"anthropic_beta": ["context-1m-2025-08-07"]}
        config = ModelSpecificConfig(
            enable_extended_context=True,
            custom_fields=custom,
        )
        result = config.to_dict()

        assert result[ModelSpecificFields.ENABLE_EXTENDED_CONTEXT] is True
        assert result[ModelSpecificFields.CUSTOM_FIELDS] == custom

    def test_from_dict_defaults(self):
        """Test from_dict with minimal data."""
        data = {}
        config = ModelSpecificConfig.from_dict(data)

        assert config.enable_extended_context is False
        assert config.custom_fields is None

    def test_from_dict_with_values(self):
        """Test from_dict with explicit values."""
        custom = {"anthropic_beta": ["context-1m-2025-08-07"]}
        data = {
            ModelSpecificFields.ENABLE_EXTENDED_CONTEXT: True,
            ModelSpecificFields.CUSTOM_FIELDS: custom,
        }
        config = ModelSpecificConfig.from_dict(data)

        assert config.enable_extended_context is True
        assert config.custom_fields == custom

    def test_from_dict_invalid_data_type(self):
        """Test from_dict with invalid data type."""
        with pytest.raises(ValueError, match="Data must be a dictionary"):
            ModelSpecificConfig.from_dict("not a dict")  # type: ignore

    def test_from_dict_invalid_enable_extended_context_type(self):
        """Test from_dict with invalid enable_extended_context type."""
        data = {ModelSpecificFields.ENABLE_EXTENDED_CONTEXT: "true"}
        with pytest.raises(TypeError, match="enable_extended_context must be a boolean"):
            ModelSpecificConfig.from_dict(data)

    def test_from_dict_invalid_custom_fields_type(self):
        """Test from_dict with invalid custom_fields type."""
        data = {ModelSpecificFields.CUSTOM_FIELDS: "not a dict"}
        with pytest.raises(TypeError, match="custom_fields must be a dictionary or None"):
            ModelSpecificConfig.from_dict(data)

    # Property-Based Tests

    @settings(max_examples=100)
    @given(config=model_specific_config_strategy)
    def test_property_serialization_round_trip(self, config: ModelSpecificConfig):
        """
        Property 5: Configuration Serialization Round-Trip

        Feature: additional-model-request-fields, Property 5: For any valid
        ModelSpecificConfig instance, serializing to dictionary and then
        deserializing SHALL produce an equivalent configuration object.

        Validates: Requirements 3.5

        Test that to_dict() → from_dict() produces equivalent object.
        """
        # Serialize to dictionary
        serialized = config.to_dict()

        # Deserialize back to object
        deserialized = ModelSpecificConfig.from_dict(serialized)

        # Verify equivalence
        assert deserialized.enable_extended_context == config.enable_extended_context
        assert deserialized.custom_fields == config.custom_fields

    @settings(max_examples=100)
    @given(
        enable_extended_context=st.booleans(),
        custom_fields=custom_fields_strategy,
    )
    def test_property_serialization_preserves_values(
        self,
        enable_extended_context: bool,
        custom_fields: dict,
    ):
        """
        Test that serialization preserves all field values.

        Validates: Requirements 3.5
        """
        config = ModelSpecificConfig(
            enable_extended_context=enable_extended_context,
            custom_fields=custom_fields,
        )

        serialized = config.to_dict()
        deserialized = ModelSpecificConfig.from_dict(serialized)

        # Verify all fields are preserved
        assert deserialized.enable_extended_context == enable_extended_context
        assert deserialized.custom_fields == custom_fields

    @settings(max_examples=100)
    @given(
        custom_fields=st.dictionaries(
            keys=st.text(min_size=1, max_size=50),
            values=st.recursive(
                st.one_of(
                    st.text(),
                    st.integers(),
                    st.floats(allow_nan=False, allow_infinity=False),
                    st.booleans(),
                ),
                lambda children: st.one_of(
                    st.lists(children, max_size=5),
                    st.dictionaries(st.text(min_size=1, max_size=20), children, max_size=5),
                ),
                max_leaves=10,
            ),
            max_size=10,
        )
    )
    def test_property_nested_structure_preservation(self, custom_fields: dict):
        """
        Test that nested structures in custom_fields are preserved.

        Validates: Requirements 3.5
        """
        config = ModelSpecificConfig(
            enable_extended_context=True,
            custom_fields=custom_fields,
        )

        serialized = config.to_dict()
        deserialized = ModelSpecificConfig.from_dict(serialized)

        # Verify nested structure is preserved
        assert deserialized.custom_fields == custom_fields
