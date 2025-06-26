"""
Comprehensive unit tests for ModelCRISCorrelator.
Tests correlation logic, fuzzy matching, error handling, and edge cases.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

from bestehorn_llmmanager.bedrock.correlators.model_cris_correlator import (
    ModelCRISCorrelationError,
    ModelCRISCorrelator,
)
from bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo, ModelAccessMethod
from bestehorn_llmmanager.bedrock.models.cris_structures import (
    CRISCatalog,
    CRISInferenceProfile,
    CRISModelInfo,
)
from bestehorn_llmmanager.bedrock.models.data_structures import BedrockModelInfo, ModelCatalog
from bestehorn_llmmanager.bedrock.models.unified_constants import (
    AccessMethodPriority,
    ModelCorrelationConfig,
    ModelCorrelationConstants,
    RegionMarkers,
    UnifiedErrorMessages,
    UnifiedLogMessages,
)
from bestehorn_llmmanager.bedrock.models.unified_structures import (
    UnifiedModelCatalog,
    UnifiedModelInfo,
)


class TestModelCRISCorrelator:
    """Test suite for ModelCRISCorrelator."""

    @pytest.fixture
    def correlator(self) -> ModelCRISCorrelator:
        """Create a correlator instance for testing."""
        return ModelCRISCorrelator()

    @pytest.fixture
    def correlator_fuzzy_enabled(self) -> ModelCRISCorrelator:
        """Create a correlator instance with fuzzy matching enabled."""
        return ModelCRISCorrelator(enable_fuzzy_matching=True)

    @pytest.fixture
    def correlator_fuzzy_disabled(self) -> ModelCRISCorrelator:
        """Create a correlator instance with fuzzy matching disabled."""
        return ModelCRISCorrelator(enable_fuzzy_matching=False)

    @pytest.fixture
    def sample_bedrock_model(self) -> BedrockModelInfo:
        """Create a sample bedrock model for testing."""
        return BedrockModelInfo(
            provider="Anthropic",
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
            regions_supported=["us-east-1", "us-west-2", "eu-west-1*"],
            input_modalities=["Text"],
            output_modalities=["Text"],
            streaming_supported=True,
            inference_parameters_link="https://example.com/params",
            hyperparameters_link="https://example.com/hyper",
        )

    @pytest.fixture
    def sample_cris_model(self) -> CRISModelInfo:
        """Create a sample CRIS model for testing."""
        inference_profile = CRISInferenceProfile(
            inference_profile_id="anthropic.claude-3-sonnet-profile",
            region_mappings={
                "us-east-1": ["us-east-1", "us-west-2"],
                "us-west-2": ["us-west-2", "us-east-1"],
                "eu-west-1": ["eu-west-1", "eu-central-1"],
            },
        )

        return CRISModelInfo(
            model_name="anthropic.claude-3-sonnet",
            inference_profiles={"anthropic.claude-3-sonnet-profile": inference_profile},
        )

    @pytest.fixture
    def sample_model_catalog(self, sample_bedrock_model: BedrockModelInfo) -> ModelCatalog:
        """Create a sample model catalog for testing."""
        return ModelCatalog(
            retrieval_timestamp=datetime.now(), models={"claude-3-sonnet": sample_bedrock_model}
        )

    @pytest.fixture
    def sample_cris_catalog(self, sample_cris_model: CRISModelInfo) -> CRISCatalog:
        """Create a sample CRIS catalog for testing."""
        return CRISCatalog(
            retrieval_timestamp=datetime.now(),
            cris_models={"anthropic.claude-3-sonnet": sample_cris_model},
        )

    def test_init_default_fuzzy_matching(self):
        """Test correlator initialization with default fuzzy matching."""
        correlator = ModelCRISCorrelator()
        assert (
            correlator._fuzzy_matching_enabled
            == ModelCorrelationConfig.ENABLE_FUZZY_MATCHING_DEFAULT
        )
        assert isinstance(correlator._correlation_stats, dict)
        assert correlator._correlation_stats["matched_models"] == 0

    def test_init_fuzzy_matching_enabled(self):
        """Test correlator initialization with fuzzy matching explicitly enabled."""
        correlator = ModelCRISCorrelator(enable_fuzzy_matching=True)
        assert correlator._fuzzy_matching_enabled is True

    def test_init_fuzzy_matching_disabled(self):
        """Test correlator initialization with fuzzy matching explicitly disabled."""
        correlator = ModelCRISCorrelator(enable_fuzzy_matching=False)
        assert correlator._fuzzy_matching_enabled is False

    def test_correlate_catalogs_successful_match(
        self,
        correlator: ModelCRISCorrelator,
        sample_model_catalog: ModelCatalog,
        sample_cris_catalog: CRISCatalog,
    ):
        """Test successful correlation of model and CRIS catalogs."""
        result = correlator.correlate_catalogs(
            model_catalog=sample_model_catalog, cris_catalog=sample_cris_catalog
        )

        assert isinstance(result, UnifiedModelCatalog)
        assert result.model_count > 0
        assert "claude-3-sonnet" in result.unified_models

        unified_model = result.unified_models["claude-3-sonnet"]
        assert unified_model.model_name == "claude-3-sonnet"
        assert unified_model.provider == "Anthropic"
        assert len(unified_model.region_access) > 0

    def test_correlate_catalogs_empty_catalogs(self, correlator: ModelCRISCorrelator):
        """Test correlation with empty catalogs."""
        empty_model_catalog = ModelCatalog(retrieval_timestamp=datetime.now(), models={})
        empty_cris_catalog = CRISCatalog(retrieval_timestamp=datetime.now(), cris_models={})

        result = correlator.correlate_catalogs(
            model_catalog=empty_model_catalog, cris_catalog=empty_cris_catalog
        )

        assert isinstance(result, UnifiedModelCatalog)
        assert result.model_count == 0

    def test_correlate_catalogs_model_processing_error(
        self,
        correlator: ModelCRISCorrelator,
        sample_model_catalog: ModelCatalog,
        sample_cris_catalog: CRISCatalog,
    ):
        """Test correlation with model processing error - should skip problematic models."""
        # Create a mock model that will cause an error
        bad_model = Mock(spec=BedrockModelInfo)
        bad_model.model_id = "bad-model"
        bad_model.provider = "Test"
        bad_model.regions_supported = ["invalid-region"]

        # Add the bad model to the catalog
        sample_model_catalog.models["bad-model"] = bad_model

        with patch.object(correlator, "_create_unified_model") as mock_create_unified:
            # Make _create_unified_model fail only for the bad model
            def side_effect(model_info, cris_model_info, canonical_name):
                if canonical_name == "bad-model":
                    raise Exception("Test error for bad model")
                # For claude-3-sonnet, return a valid unified model
                return UnifiedModelInfo(
                    model_name=canonical_name,
                    provider=model_info.provider,
                    model_id=model_info.model_id,
                    input_modalities=model_info.input_modalities,
                    output_modalities=model_info.output_modalities,
                    streaming_supported=model_info.streaming_supported,
                    inference_parameters_link=model_info.inference_parameters_link,
                    hyperparameters_link=model_info.hyperparameters_link,
                    region_access={
                        "us-east-1": ModelAccessInfo(
                            access_method=ModelAccessMethod.DIRECT,
                            region="us-east-1",
                            model_id=model_info.model_id,
                            inference_profile_id=None,
                        )
                    },
                )

            mock_create_unified.side_effect = side_effect

            # Should not raise an exception - only the bad model is skipped
            result = correlator.correlate_catalogs(
                model_catalog=sample_model_catalog, cris_catalog=sample_cris_catalog
            )

            # Result should be a valid catalog with only the good model
            assert isinstance(result, UnifiedModelCatalog)
            # Only the bad model should be skipped
            assert result.model_count == 1
            assert "claude-3-sonnet" in result.unified_models
            assert "bad-model" not in result.unified_models

    def test_correlate_catalogs_cris_processing_error(
        self, correlator: ModelCRISCorrelator, sample_cris_catalog: CRISCatalog
    ):
        """Test correlation with CRIS model processing error."""
        empty_model_catalog = ModelCatalog(retrieval_timestamp=datetime.now(), models={})

        with patch.object(
            correlator, "_create_cris_only_unified_model", side_effect=Exception("CRIS error")
        ):
            with pytest.raises(ModelCRISCorrelationError) as exc_info:
                correlator.correlate_catalogs(
                    model_catalog=empty_model_catalog, cris_catalog=sample_cris_catalog
                )

            assert "CRIS model correlation failed" in str(exc_info.value)

    def test_create_model_name_mapping(
        self, correlator: ModelCRISCorrelator, sample_cris_model: CRISModelInfo
    ):
        """Test creation of model name mapping."""
        cris_models = {"anthropic.claude-3-sonnet": sample_cris_model}

        mapping = correlator._create_model_name_mapping(cris_models=cris_models)

        assert isinstance(mapping, dict)
        assert "anthropic.claude-3-sonnet" in mapping

    def test_normalize_model_name(self, correlator: ModelCRISCorrelator):
        """Test model name normalization."""
        # Test anthropic prefix removal
        result = correlator._normalize_model_name("anthropic.claude-3-sonnet")
        assert result == "claude-3-sonnet"

        # Test meta prefix removal
        result = correlator._normalize_model_name("meta.llama2-13b")
        assert result == "llama2-13b"

        # Test amazon prefix removal
        result = correlator._normalize_model_name("amazon.titan-text")
        assert result == "titan-text"

        # Test mistral prefix removal
        result = correlator._normalize_model_name("mistral.7b-instruct")
        assert result == "7b-instruct"

        # Test no prefix
        result = correlator._normalize_model_name("some-model")
        assert result == "some-model"

    def test_find_matching_cris_model_exact_match(
        self, correlator: ModelCRISCorrelator, sample_cris_model: CRISModelInfo
    ):
        """Test finding exact matching CRIS model."""
        cris_models = {"anthropic.claude-3-sonnet": sample_cris_model}
        name_mapping = {"anthropic.claude-3-sonnet": "claude-3-sonnet"}

        result, match_type = correlator._find_matching_cris_model(
            model_name="claude-3-sonnet", cris_models=cris_models, name_mapping=name_mapping
        )

        assert result == sample_cris_model
        assert match_type == "exact"

    def test_find_matching_cris_model_no_match(
        self, correlator: ModelCRISCorrelator, sample_cris_model: CRISModelInfo
    ):
        """Test finding no matching CRIS model."""
        cris_models = {"anthropic.claude-3-sonnet": sample_cris_model}
        name_mapping = {"anthropic.claude-3-sonnet": "claude-3-sonnet"}

        result, match_type = correlator._find_matching_cris_model(
            model_name="non-existent-model", cris_models=cris_models, name_mapping=name_mapping
        )

        assert result is None
        assert match_type == "none"

    def test_find_matching_cris_model_fuzzy_enabled(
        self, correlator_fuzzy_enabled: ModelCRISCorrelator, sample_cris_model: CRISModelInfo
    ):
        """Test fuzzy matching when enabled."""
        cris_models = {"anthropic.claude-3-sonnet": sample_cris_model}
        name_mapping = {"anthropic.claude-3-sonnet": "claude-3-sonnet"}

        # Test fuzzy match
        result, match_type = correlator_fuzzy_enabled._find_matching_cris_model(
            model_name="claude-3-sonnet",  # This should match the normalized CRIS name
            cris_models=cris_models,
            name_mapping={},  # Empty mapping to force fuzzy matching
        )

        assert result == sample_cris_model
        assert match_type == "fuzzy"

    def test_find_matching_cris_model_fuzzy_disabled(
        self, correlator_fuzzy_disabled: ModelCRISCorrelator, sample_cris_model: CRISModelInfo
    ):
        """Test fuzzy matching when disabled."""
        cris_models = {"anthropic.claude-3-sonnet": sample_cris_model}
        name_mapping = {}  # Empty mapping

        result, match_type = correlator_fuzzy_disabled._find_matching_cris_model(
            model_name="claude-3-sonnet", cris_models=cris_models, name_mapping=name_mapping
        )

        assert result is None
        assert match_type == "none"

    def test_create_unified_model(
        self,
        correlator: ModelCRISCorrelator,
        sample_bedrock_model: BedrockModelInfo,
        sample_cris_model: CRISModelInfo,
    ):
        """Test creation of unified model."""
        result = correlator._create_unified_model(
            model_info=sample_bedrock_model,
            cris_model_info=sample_cris_model,
            canonical_name="claude-3-sonnet",
        )

        assert isinstance(result, UnifiedModelInfo)
        assert result.model_name == "claude-3-sonnet"
        assert result.provider == "Anthropic"
        assert result.model_id == sample_bedrock_model.model_id
        assert len(result.region_access) > 0

    def test_extract_provider_from_cris_model_anthropic(self, correlator: ModelCRISCorrelator):
        """Test provider extraction for Anthropic models."""
        cris_model = Mock(spec=CRISModelInfo)
        cris_model.model_name = "anthropic.claude-3-sonnet"
        cris_model.inference_profile_id = "anthropic-profile"

        result = correlator._extract_provider_from_cris_model(cris_model_info=cris_model)
        assert result == "Anthropic"

    def test_extract_provider_from_cris_model_meta(self, correlator: ModelCRISCorrelator):
        """Test provider extraction for Meta models."""
        cris_model = Mock(spec=CRISModelInfo)
        cris_model.model_name = "meta.llama2-13b"
        cris_model.inference_profile_id = "meta-profile"

        result = correlator._extract_provider_from_cris_model(cris_model_info=cris_model)
        assert result == "Meta"

    def test_extract_provider_from_cris_model_amazon(self, correlator: ModelCRISCorrelator):
        """Test provider extraction for Amazon models."""
        cris_model = Mock(spec=CRISModelInfo)
        cris_model.model_name = "amazon.titan-text"
        cris_model.inference_profile_id = "amazon-profile"

        result = correlator._extract_provider_from_cris_model(cris_model_info=cris_model)
        assert result == "Amazon"

    def test_extract_provider_from_cris_model_mistral(self, correlator: ModelCRISCorrelator):
        """Test provider extraction for Mistral models."""
        cris_model = Mock(spec=CRISModelInfo)
        cris_model.model_name = "mistral.7b-instruct"
        cris_model.inference_profile_id = "mistral-profile"

        result = correlator._extract_provider_from_cris_model(cris_model_info=cris_model)
        assert result == "Mistral AI"

    def test_extract_provider_from_cris_model_unknown(self, correlator: ModelCRISCorrelator):
        """Test provider extraction for unknown models."""
        cris_model = Mock(spec=CRISModelInfo)
        cris_model.model_name = "unknown.model"
        cris_model.inference_profile_id = "unknown-profile"

        result = correlator._extract_provider_from_cris_model(cris_model_info=cris_model)
        assert result == "Unknown"

    def test_get_correlation_stats(self, correlator: ModelCRISCorrelator):
        """Test getting correlation statistics."""
        # Set some values
        correlator._correlation_stats["matched_models"] = 5
        correlator._correlation_stats["fuzzy_matched_models"] = 2

        result = correlator.get_correlation_stats()

        assert isinstance(result, dict)
        assert result["matched_models"] == 5
        assert result["fuzzy_matched_models"] == 2

        # Ensure it returns a copy
        result["matched_models"] = 10
        assert correlator._correlation_stats["matched_models"] == 5

    def test_is_fuzzy_matching_enabled(self):
        """Test checking if fuzzy matching is enabled."""
        correlator_enabled = ModelCRISCorrelator(enable_fuzzy_matching=True)
        correlator_disabled = ModelCRISCorrelator(enable_fuzzy_matching=False)

        assert correlator_enabled.is_fuzzy_matching_enabled() is True
        assert correlator_disabled.is_fuzzy_matching_enabled() is False

    def test_set_fuzzy_matching_enabled(self, correlator: ModelCRISCorrelator):
        """Test setting fuzzy matching enabled state."""
        initial_state = correlator.is_fuzzy_matching_enabled()

        correlator.set_fuzzy_matching_enabled(True)
        assert correlator.is_fuzzy_matching_enabled() is True

        correlator.set_fuzzy_matching_enabled(False)
        assert correlator.is_fuzzy_matching_enabled() is False

        # Restore original state
        correlator.set_fuzzy_matching_enabled(initial_state)
