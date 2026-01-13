"""
Property-based tests for LLMManager model-specific configuration.
Tests ModelSpecificConfig extraction and backward compatibility.
"""

from unittest.mock import Mock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.models.model_specific_structures import ModelSpecificConfig
from bestehorn_llmmanager.llm_manager import LLMManager


# Hypothesis strategies for generating test data
@st.composite
def model_specific_config_strategy(draw):
    """Generate random ModelSpecificConfig instances."""
    enable_extended_context = draw(st.booleans())

    # Generate custom_fields or None
    has_custom_fields = draw(st.booleans())
    if has_custom_fields:
        # Generate a dictionary with string keys and various value types
        custom_fields = draw(
            st.dictionaries(
                keys=st.text(
                    min_size=1,
                    max_size=20,
                    alphabet=st.characters(
                        whitelist_categories=("Lu", "Ll"), min_codepoint=65, max_codepoint=122
                    ),
                ),
                values=st.one_of(
                    st.text(min_size=0, max_size=50),
                    st.integers(),
                    st.floats(allow_nan=False, allow_infinity=False),
                    st.booleans(),
                    st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5),
                ),
                min_size=0,
                max_size=5,
            )
        )
    else:
        custom_fields = None

    return ModelSpecificConfig(
        enable_extended_context=enable_extended_context,
        custom_fields=custom_fields,
    )


class TestLLMManagerModelSpecificConfig:
    """Property-based tests for model-specific configuration in LLMManager."""

    @pytest.fixture
    def mock_bedrock_catalog(self):
        """Create a mock BedrockModelCatalog."""
        mock_catalog = Mock()
        mock_catalog.ensure_catalog_available.return_value = Mock()
        mock_catalog.get_model_info.return_value = Mock(
            model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
            has_direct_access=True,
            has_regional_cris=False,
            has_global_cris=False,
            regional_cris_profile_id=None,
            global_cris_profile_id=None,
            access_method=Mock(value="direct"),
        )
        mock_catalog.is_model_available.return_value = True
        mock_catalog.is_catalog_loaded = True
        return mock_catalog

    @pytest.fixture
    def llm_manager(self, mock_bedrock_catalog):
        """Create an LLMManager instance for testing."""
        with patch(
            "bestehorn_llmmanager.llm_manager.BedrockModelCatalog",
            return_value=mock_bedrock_catalog,
        ):
            return LLMManager(
                models=["Claude Sonnet 4"],
                regions=["us-east-1"],
            )

    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(config=model_specific_config_strategy())
    def test_property_4_model_specific_config_extraction(
        self, llm_manager, mock_bedrock_catalog, config
    ):
        """
        Property 4: ModelSpecificConfig Extraction

        For any ModelSpecificConfig instance provided to converse(), the LLMManager
        SHALL correctly extract and apply the additionalModelRequestFields, including
        both enable_extended_context transformations and custom_fields.

        Feature: additional-model-request-fields, Property 4: ModelSpecificConfig Extraction
        Validates: Requirements 3.2, 3.4
        """
        # Build request with the config
        messages = [{"role": "user", "content": [{"text": "test"}]}]

        # Call _build_converse_request to extract and apply the config
        request_args = llm_manager._build_converse_request(
            messages=messages,
            model_specific_config=config,
        )

        # Verify that model_specific_config was stored for retry manager
        assert "_model_specific_config" in request_args
        assert request_args["_model_specific_config"] == config

        # Verify that additionalModelRequestFields was built
        if config.enable_extended_context or config.custom_fields:
            # Should have built some additional fields
            assert "additionalModelRequestFields" in request_args
            built_fields = request_args["additionalModelRequestFields"]

            # If custom_fields were provided, they should be in the built fields
            if config.custom_fields:
                for key, value in config.custom_fields.items():
                    # Handle anthropic_beta specially (it gets merged)
                    if key == "anthropic_beta":
                        assert key in built_fields
                        # Value should be a list containing the original values
                        if isinstance(value, list):
                            for item in value:
                                assert item in built_fields[key]
                    else:
                        assert key in built_fields
                        assert built_fields[key] == value

            # If enable_extended_context is True and model is compatible,
            # should have anthropic_beta with context header
            if config.enable_extended_context:
                # Claude Sonnet 4 is compatible
                assert "anthropic_beta" in built_fields
                assert "context-1m-2025-08-07" in built_fields["anthropic_beta"]
        else:
            # No config, so no additional fields should be built
            # (unless there were legacy additional_model_request_fields)
            pass

    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        enable_extended_context=st.booleans(),
        has_custom_fields=st.booleans(),
    )
    def test_property_4_config_merging(
        self, llm_manager, mock_bedrock_catalog, enable_extended_context, has_custom_fields
    ):
        """
        Test merging of enable_extended_context and custom_fields.

        Validates that both enable_extended_context transformations and custom_fields
        are correctly merged into the final additionalModelRequestFields.
        """
        custom_fields = None
        if has_custom_fields:
            custom_fields = {
                "test_field": "test_value",
                "anthropic_beta": ["some-other-beta"],
            }

        config = ModelSpecificConfig(
            enable_extended_context=enable_extended_context,
            custom_fields=custom_fields,
        )

        messages = [{"role": "user", "content": [{"text": "test"}]}]

        request_args = llm_manager._build_converse_request(
            messages=messages,
            model_specific_config=config,
        )

        if enable_extended_context or has_custom_fields:
            assert "additionalModelRequestFields" in request_args
            built_fields = request_args["additionalModelRequestFields"]

            # Check custom fields are present
            if has_custom_fields:
                assert "test_field" in built_fields
                assert built_fields["test_field"] == "test_value"

            # Check extended context beta header
            if enable_extended_context:
                assert "anthropic_beta" in built_fields
                assert "context-1m-2025-08-07" in built_fields["anthropic_beta"]

            # Check that beta arrays were merged without duplicates
            if has_custom_fields and enable_extended_context:
                beta_array = built_fields["anthropic_beta"]
                assert "some-other-beta" in beta_array
                assert "context-1m-2025-08-07" in beta_array
                # No duplicates
                assert len(beta_array) == len(set(beta_array))

    def test_property_4_config_priority(self, llm_manager, mock_bedrock_catalog):
        """
        Test that per-request config takes priority over default config.

        Validates Requirements 3.2: ModelSpecificConfig extraction from converse()
        """
        # Create a default config
        default_config = ModelSpecificConfig(
            enable_extended_context=False,
            custom_fields={"default_field": "default_value"},
        )

        # Set it as default
        llm_manager._default_model_specific_config = default_config

        # Create a per-request config
        request_config = ModelSpecificConfig(
            enable_extended_context=True,
            custom_fields={"request_field": "request_value"},
        )

        messages = [{"role": "user", "content": [{"text": "test"}]}]

        # Build request with per-request config
        request_args = llm_manager._build_converse_request(
            messages=messages,
            model_specific_config=request_config,
        )

        # Should use request config, not default
        assert request_args["_model_specific_config"] == request_config
        assert "additionalModelRequestFields" in request_args
        built_fields = request_args["additionalModelRequestFields"]

        # Should have request fields, not default fields
        assert "request_field" in built_fields
        assert "default_field" not in built_fields

        # Should have extended context from request config
        assert "anthropic_beta" in built_fields
        assert "context-1m-2025-08-07" in built_fields["anthropic_beta"]


class TestLLMManagerBackwardCompatibility:
    """Property-based tests for backward compatibility of LLMManager."""

    @pytest.fixture
    def mock_bedrock_catalog(self):
        """Create a mock BedrockModelCatalog."""
        mock_catalog = Mock()
        mock_catalog.ensure_catalog_available.return_value = Mock()
        mock_catalog.get_model_info.return_value = Mock(
            model_id="test-model-id",
            has_direct_access=True,
            has_regional_cris=False,
            has_global_cris=False,
            regional_cris_profile_id=None,
            global_cris_profile_id=None,
            access_method=Mock(value="direct"),
        )
        mock_catalog.is_model_available.return_value = True
        mock_catalog.is_catalog_loaded = True
        return mock_catalog

    @pytest.fixture
    def llm_manager(self, mock_bedrock_catalog):
        """Create an LLMManager instance for testing."""
        with patch(
            "bestehorn_llmmanager.llm_manager.BedrockModelCatalog",
            return_value=mock_bedrock_catalog,
        ):
            return LLMManager(
                models=["Claude 3 Haiku"],
                regions=["us-east-1"],
            )

    @settings(
        max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        has_additional_fields=st.booleans(),
        has_system=st.booleans(),
        has_inference_config=st.booleans(),
    )
    def test_property_14_backward_compatibility_preservation(
        self,
        llm_manager,
        mock_bedrock_catalog,
        has_additional_fields,
        has_system,
        has_inference_config,
    ):
        """
        Property 14: Backward Compatibility Preservation

        For any request that does not provide model-specific parameters
        (no additionalModelRequestFields, no ModelSpecificConfig, enable_extended_context=False),
        the system SHALL behave identically to the implementation before this feature was added.

        Feature: additional-model-request-fields, Property 14: Backward Compatibility Preservation
        Validates: Requirements 8.1, 8.2, 8.3, 8.5
        """
        messages = [{"role": "user", "content": [{"text": "test message"}]}]

        # Build request without new parameters
        system = [{"text": "system prompt"}] if has_system else None
        inference_config = {"maxTokens": 100} if has_inference_config else None
        additional_fields = {"test_param": "test_value"} if has_additional_fields else None

        # Call _build_converse_request WITHOUT model_specific_config or enable_extended_context
        request_args = llm_manager._build_converse_request(
            messages=messages,
            system=system,
            inference_config=inference_config,
            additional_model_request_fields=additional_fields,
            # No model_specific_config
            # No enable_extended_context (defaults to False)
        )

        # Verify basic structure is preserved
        assert "messages" in request_args
        assert request_args["messages"] == messages

        # Verify optional fields are handled correctly
        if has_system:
            assert "system" in request_args
            assert request_args["system"] == system
        else:
            assert "system" not in request_args

        if has_inference_config:
            assert "inferenceConfig" in request_args

        # Verify additionalModelRequestFields behavior
        if has_additional_fields:
            # Legacy behavior: pass through as-is
            assert "additionalModelRequestFields" in request_args
            assert request_args["additionalModelRequestFields"] == additional_fields
        else:
            # No additional fields provided, none should be added
            # (unless model_specific_config was provided, which it wasn't)
            pass

        # Verify no model_specific_config was stored (backward compatibility)
        if not has_additional_fields:
            # If no additional fields, _model_specific_config should not be present
            assert "_model_specific_config" not in request_args

    def test_property_14_existing_additional_fields_usage(self, llm_manager, mock_bedrock_catalog):
        """
        Test that existing additionalModelRequestFields usage continues to work.

        Validates Requirement 8.2: Existing code uses the current additionalModelRequestFields
        parameter, THE System SHALL continue to work without modification
        """
        messages = [{"role": "user", "content": [{"text": "test"}]}]

        # Use legacy additionalModelRequestFields parameter
        legacy_fields = {
            "anthropic_beta": ["some-beta-feature"],
            "custom_param": "custom_value",
        }

        request_args = llm_manager._build_converse_request(
            messages=messages,
            additional_model_request_fields=legacy_fields,
        )

        # Should pass through the fields
        assert "additionalModelRequestFields" in request_args
        built_fields = request_args["additionalModelRequestFields"]

        # Fields should be preserved
        assert "anthropic_beta" in built_fields
        assert "some-beta-feature" in built_fields["anthropic_beta"]
        assert "custom_param" in built_fields
        assert built_fields["custom_param"] == "custom_value"

    def test_property_14_plain_dictionary_without_config(self, llm_manager, mock_bedrock_catalog):
        """
        Test that plain dictionary works without ModelSpecificConfig.

        Validates Requirement 8.3: WHEN ModelSpecificConfig is not used,
        THE System SHALL accept additionalModelRequestFields as a plain dictionary
        """
        messages = [{"role": "user", "content": [{"text": "test"}]}]

        # Use plain dictionary (not ModelSpecificConfig)
        plain_dict = {
            "test_field": "test_value",
            "nested": {"key": "value"},
            "array": [1, 2, 3],
        }

        request_args = llm_manager._build_converse_request(
            messages=messages,
            additional_model_request_fields=plain_dict,
        )

        # Should accept and pass through the plain dictionary
        assert "additionalModelRequestFields" in request_args
        built_fields = request_args["additionalModelRequestFields"]

        # All fields should be preserved
        assert "test_field" in built_fields
        assert built_fields["test_field"] == "test_value"
        assert "nested" in built_fields
        assert built_fields["nested"] == {"key": "value"}
        assert "array" in built_fields
        assert built_fields["array"] == [1, 2, 3]

    def test_property_14_enable_extended_context_default_false(
        self, llm_manager, mock_bedrock_catalog
    ):
        """
        Test that enable_extended_context defaults to False.

        Validates Requirement 8.4: WHEN enable_extended_context is not specified,
        THE System SHALL default to False
        """
        messages = [{"role": "user", "content": [{"text": "test"}]}]

        # Call without enable_extended_context parameter
        request_args = llm_manager._build_converse_request(
            messages=messages,
            # enable_extended_context not provided (should default to False)
        )

        # Should not have extended context beta header
        if "additionalModelRequestFields" in request_args:
            built_fields = request_args["additionalModelRequestFields"]
            # If anthropic_beta exists, it should not contain the extended context header
            if "anthropic_beta" in built_fields:
                assert "context-1m-2025-08-07" not in built_fields["anthropic_beta"]

    def test_property_14_no_parameters_no_additional_fields(
        self, llm_manager, mock_bedrock_catalog
    ):
        """
        Test that no parameters results in no additionalModelRequestFields.

        Validates Requirement 8.1: WHEN additionalModelRequestFields is not provided,
        THE System SHALL behave identically to the current implementation
        """
        messages = [{"role": "user", "content": [{"text": "test"}]}]

        # Call with no model-specific parameters at all
        request_args = llm_manager._build_converse_request(
            messages=messages,
            # No additional_model_request_fields
            # No model_specific_config
            # No enable_extended_context
        )

        # Should not have additionalModelRequestFields
        # (or if it does, it should be None/empty)
        if "additionalModelRequestFields" in request_args:
            # If present, should be None or empty
            assert (
                request_args["additionalModelRequestFields"] is None
                or request_args["additionalModelRequestFields"] == {}
            )


class TestLLMManagerIntegration:
    """Unit tests for LLMManager integration with model-specific configuration."""

    @pytest.fixture
    def mock_bedrock_catalog(self):
        """Create a mock BedrockModelCatalog."""
        mock_catalog = Mock()
        mock_catalog.ensure_catalog_available.return_value = Mock()

        # Return different model info based on model name
        def get_model_info_side_effect(model_name, region):
            if "Sonnet 4" in model_name or "sonnet-4" in model_name:
                return Mock(
                    model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
                    has_direct_access=True,
                    has_regional_cris=False,
                    has_global_cris=False,
                    regional_cris_profile_id=None,
                    global_cris_profile_id=None,
                    access_method=Mock(value="direct"),
                )
            else:
                return Mock(
                    model_id="test-model-id",
                    has_direct_access=True,
                    has_regional_cris=False,
                    has_global_cris=False,
                    regional_cris_profile_id=None,
                    global_cris_profile_id=None,
                    access_method=Mock(value="direct"),
                )

        mock_catalog.get_model_info.side_effect = get_model_info_side_effect
        mock_catalog.is_model_available.return_value = True
        mock_catalog.is_catalog_loaded = True
        return mock_catalog

    def test_enable_extended_context_flag_with_compatible_model(self, mock_bedrock_catalog):
        """
        Test enable_extended_context flag with Claude Sonnet 4.

        Validates Requirement 2.1: WHEN a user sets enable_extended_context=True in the request,
        THE LLM_Manager SHALL automatically add {"anthropic_beta": ["context-1m-2025-08-07"]}
        to additionalModelRequestFields for compatible models
        """
        with patch(
            "bestehorn_llmmanager.llm_manager.BedrockModelCatalog",
            return_value=mock_bedrock_catalog,
        ):
            manager = LLMManager(
                models=["Claude Sonnet 4"],
                regions=["us-east-1"],
            )

            messages = [{"role": "user", "content": [{"text": "test"}]}]

            # Build request with enable_extended_context=True
            request_args = manager._build_converse_request(
                messages=messages,
                # Use enable_extended_context flag
            )

            # Resolve the config
            resolved_config = manager._resolve_model_specific_config(
                model_specific_config=None,
                enable_extended_context=True,
            )

            # Build with resolved config
            request_args = manager._build_converse_request(
                messages=messages,
                model_specific_config=resolved_config,
            )

            # Should have additionalModelRequestFields with extended context beta
            assert "additionalModelRequestFields" in request_args
            built_fields = request_args["additionalModelRequestFields"]
            assert "anthropic_beta" in built_fields
            assert "context-1m-2025-08-07" in built_fields["anthropic_beta"]

    def test_enable_extended_context_default_false(self, mock_bedrock_catalog):
        """
        Test that enable_extended_context defaults to False.

        Validates Requirement 8.4: WHEN enable_extended_context is not specified,
        THE System SHALL default to False
        """
        with patch(
            "bestehorn_llmmanager.llm_manager.BedrockModelCatalog",
            return_value=mock_bedrock_catalog,
        ):
            manager = LLMManager(
                models=["Claude Sonnet 4"],
                regions=["us-east-1"],
            )

            messages = [{"role": "user", "content": [{"text": "test"}]}]

            # Build request without enable_extended_context (should default to False)
            request_args = manager._build_converse_request(
                messages=messages,
            )

            # Should not have extended context beta header
            if "additionalModelRequestFields" in request_args:
                built_fields = request_args["additionalModelRequestFields"]
                if "anthropic_beta" in built_fields:
                    assert "context-1m-2025-08-07" not in built_fields["anthropic_beta"]

    def test_existing_additional_model_request_fields(self, mock_bedrock_catalog):
        """
        Test existing additionalModelRequestFields usage.

        Validates Requirement 8.2: WHEN existing code uses the current
        additionalModelRequestFields parameter, THE System SHALL continue to work
        without modification
        """
        with patch(
            "bestehorn_llmmanager.llm_manager.BedrockModelCatalog",
            return_value=mock_bedrock_catalog,
        ):
            manager = LLMManager(
                models=["Claude 3 Haiku"],
                regions=["us-east-1"],
            )

            messages = [{"role": "user", "content": [{"text": "test"}]}]

            # Use existing additionalModelRequestFields parameter
            existing_fields = {
                "custom_param": "custom_value",
                "anthropic_beta": ["existing-beta"],
            }

            request_args = manager._build_converse_request(
                messages=messages,
                additional_model_request_fields=existing_fields,
            )

            # Should preserve the existing fields
            assert "additionalModelRequestFields" in request_args
            built_fields = request_args["additionalModelRequestFields"]
            assert "custom_param" in built_fields
            assert built_fields["custom_param"] == "custom_value"
            assert "anthropic_beta" in built_fields
            assert "existing-beta" in built_fields["anthropic_beta"]

    def test_plain_dictionary_without_model_specific_config(self, mock_bedrock_catalog):
        """
        Test plain dictionary without ModelSpecificConfig.

        Validates Requirement 8.3: WHEN ModelSpecificConfig is not used,
        THE System SHALL accept additionalModelRequestFields as a plain dictionary
        """
        with patch(
            "bestehorn_llmmanager.llm_manager.BedrockModelCatalog",
            return_value=mock_bedrock_catalog,
        ):
            manager = LLMManager(
                models=["Claude 3 Haiku"],
                regions=["us-east-1"],
            )

            messages = [{"role": "user", "content": [{"text": "test"}]}]

            # Use plain dictionary (not ModelSpecificConfig)
            plain_dict = {
                "field1": "value1",
                "field2": {"nested": "value"},
                "field3": [1, 2, 3],
            }

            request_args = manager._build_converse_request(
                messages=messages,
                additional_model_request_fields=plain_dict,
            )

            # Should accept and preserve the plain dictionary
            assert "additionalModelRequestFields" in request_args
            built_fields = request_args["additionalModelRequestFields"]
            assert "field1" in built_fields
            assert built_fields["field1"] == "value1"
            assert "field2" in built_fields
            assert built_fields["field2"] == {"nested": "value"}
            assert "field3" in built_fields
            assert built_fields["field3"] == [1, 2, 3]

    def test_resolve_model_specific_config_priority(self, mock_bedrock_catalog):
        """
        Test that _resolve_model_specific_config follows correct priority order.

        Priority: per-request config > enable_extended_context flag > default config
        """
        with patch(
            "bestehorn_llmmanager.llm_manager.BedrockModelCatalog",
            return_value=mock_bedrock_catalog,
        ):
            # Create manager with default config
            default_config = ModelSpecificConfig(
                enable_extended_context=False,
                custom_fields={"default": "value"},
            )

            manager = LLMManager(
                models=["Claude Sonnet 4"],
                regions=["us-east-1"],
                model_specific_config=default_config,
            )

            # Test 1: Per-request config takes priority
            request_config = ModelSpecificConfig(
                enable_extended_context=True,
                custom_fields={"request": "value"},
            )

            resolved = manager._resolve_model_specific_config(
                model_specific_config=request_config,
                enable_extended_context=False,  # Should be ignored
            )

            assert resolved == request_config

            # Test 2: enable_extended_context flag takes priority over default
            resolved = manager._resolve_model_specific_config(
                model_specific_config=None,
                enable_extended_context=True,
            )

            assert resolved is not None
            assert resolved.enable_extended_context is True

            # Test 3: Default config is used when nothing else provided
            resolved = manager._resolve_model_specific_config(
                model_specific_config=None,
                enable_extended_context=False,
            )

            assert resolved == default_config

    def test_model_specific_config_in_init(self, mock_bedrock_catalog):
        """
        Test that model_specific_config can be set in __init__ as default.
        """
        with patch(
            "bestehorn_llmmanager.llm_manager.BedrockModelCatalog",
            return_value=mock_bedrock_catalog,
        ):
            default_config = ModelSpecificConfig(
                enable_extended_context=True,
                custom_fields={"default_field": "default_value"},
            )

            manager = LLMManager(
                models=["Claude Sonnet 4"],
                regions=["us-east-1"],
                model_specific_config=default_config,
            )

            # Verify default config is stored
            assert manager._default_model_specific_config == default_config

            # Verify it's used when building requests
            # Resolve with no per-request config
            resolved = manager._resolve_model_specific_config(
                model_specific_config=None,
                enable_extended_context=False,
            )

            assert resolved == default_config
