"""
Unit tests for unified_structures module.

Tests the UnifiedModelInfo and UnifiedModelCatalog data structures that integrate
regular Bedrock model data with CRIS (Cross-Region Inference Service) information.
"""

from datetime import datetime
from typing import Dict

import pytest

from bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo
from bestehorn_llmmanager.bedrock.models.unified_structures import (
    UnifiedModelCatalog,
    UnifiedModelInfo,
)


class TestUnifiedModelInfo:
    """Test cases for UnifiedModelInfo class."""

    @pytest.fixture
    def valid_region_access(self) -> Dict[str, ModelAccessInfo]:
        """Create valid region access dictionary for testing."""
        return {
            "us-east-1": ModelAccessInfo(
                region="us-east-1",
                has_direct_access=True,
                model_id="anthropic.claude-3-haiku-20240307-v1:0",
            ),
            "us-west-2": ModelAccessInfo(
                region="us-west-2",
                has_direct_access=True,
                has_regional_cris=True,
                model_id="anthropic.claude-3-haiku-20240307-v1:0",
                regional_cris_profile_id="us.anthropic.claude-3-haiku-20240307-v1:0",
            ),
            "eu-west-1": ModelAccessInfo(
                region="eu-west-1",
                has_regional_cris=True,
                regional_cris_profile_id="eu.anthropic.claude-3-haiku-20240307-v1:0",
            ),
        }

    @pytest.fixture
    def valid_unified_model(self, valid_region_access) -> UnifiedModelInfo:
        """Create a valid UnifiedModelInfo for testing."""
        return UnifiedModelInfo(
            model_name="Claude 3 Haiku",
            provider="Anthropic",
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            input_modalities=["TEXT", "IMAGE"],
            output_modalities=["TEXT"],
            streaming_supported=True,
            inference_parameters_link="https://example.com/params",
            hyperparameters_link="https://example.com/hyperparams",
            region_access=valid_region_access,
        )

    def test_init_valid_model(self, valid_unified_model):
        """Test initialization with valid parameters."""
        assert valid_unified_model.model_name == "Claude 3 Haiku"
        assert valid_unified_model.provider == "Anthropic"
        assert valid_unified_model.model_id == "anthropic.claude-3-haiku-20240307-v1:0"
        assert valid_unified_model.streaming_supported is True
        assert len(valid_unified_model.region_access) == 3

    def test_init_empty_model_name(self, valid_region_access):
        """Test initialization with empty model name."""
        with pytest.raises(ValueError, match="Model name cannot be empty"):
            UnifiedModelInfo(
                model_name="",
                provider="Anthropic",
                model_id="test-id",
                input_modalities=["TEXT"],
                output_modalities=["TEXT"],
                streaming_supported=True,
                region_access=valid_region_access,
            )

    def test_init_whitespace_model_name(self, valid_region_access):
        """Test initialization with whitespace-only model name."""
        with pytest.raises(ValueError, match="Model name cannot be empty"):
            UnifiedModelInfo(
                model_name="   ",
                provider="Anthropic",
                model_id="test-id",
                input_modalities=["TEXT"],
                output_modalities=["TEXT"],
                streaming_supported=True,
                region_access=valid_region_access,
            )

    def test_init_empty_provider(self, valid_region_access):
        """Test initialization with empty provider."""
        with pytest.raises(ValueError, match="Provider cannot be empty"):
            UnifiedModelInfo(
                model_name="Test Model",
                provider="",
                model_id="test-id",
                input_modalities=["TEXT"],
                output_modalities=["TEXT"],
                streaming_supported=True,
                region_access=valid_region_access,
            )

    def test_init_empty_region_access(self):
        """Test initialization with empty region access."""
        with pytest.raises(ValueError, match="at least one region access option"):
            UnifiedModelInfo(
                model_name="Test Model",
                provider="Anthropic",
                model_id="test-id",
                input_modalities=["TEXT"],
                output_modalities=["TEXT"],
                streaming_supported=True,
                region_access={},
            )

    def test_get_supported_regions(self, valid_unified_model):
        """Test getting supported regions."""
        regions = valid_unified_model.get_supported_regions()
        assert regions == ["eu-west-1", "us-east-1", "us-west-2"]
        assert isinstance(regions, list)

    def test_get_direct_access_regions(self, valid_unified_model):
        """Test getting direct access regions."""
        regions = valid_unified_model.get_direct_access_regions()
        assert "us-east-1" in regions
        assert "us-west-2" in regions
        assert "eu-west-1" not in regions

    def test_get_cris_only_regions(self, valid_unified_model):
        """Test getting CRIS-only regions."""
        regions = valid_unified_model.get_cris_only_regions()
        assert "eu-west-1" in regions
        assert "us-east-1" not in regions

    def test_get_cris_access_regions(self, valid_unified_model):
        """Test getting regions with CRIS access."""
        regions = valid_unified_model.get_cris_access_regions()
        assert "us-west-2" in regions
        assert "eu-west-1" in regions

    def test_get_access_info_for_region_exists(self, valid_unified_model):
        """Test getting access info for existing region."""
        access_info = valid_unified_model.get_access_info_for_region("us-east-1")
        assert access_info is not None
        assert access_info.region == "us-east-1"

    def test_get_access_info_for_region_not_exists(self, valid_unified_model):
        """Test getting access info for non-existent region."""
        access_info = valid_unified_model.get_access_info_for_region("ap-south-1")
        assert access_info is None

    def test_is_available_in_region_true(self, valid_unified_model):
        """Test checking availability for existing region."""
        assert valid_unified_model.is_available_in_region("us-east-1") is True

    def test_is_available_in_region_false(self, valid_unified_model):
        """Test checking availability for non-existent region."""
        assert valid_unified_model.is_available_in_region("ap-south-1") is False

    def test_get_recommended_access_for_region(self, valid_unified_model):
        """Test getting recommended access for various regions."""
        recommended = valid_unified_model.get_recommended_access_for_region("us-east-1")
        assert recommended is not None

    def test_get_inference_profiles(self, valid_unified_model):
        """Test getting all inference profiles."""
        profiles = valid_unified_model.get_inference_profiles()
        assert len(profiles) >= 1
        assert isinstance(profiles, list)

    def test_to_dict(self, valid_unified_model):
        """Test converting model to dictionary."""
        result = valid_unified_model.to_dict()
        assert result["model_name"] == "Claude 3 Haiku"
        assert "region_access" in result

    def test_from_dict_valid_data(self, valid_unified_model):
        """Test creating model from valid dictionary."""
        data = valid_unified_model.to_dict()
        reconstructed = UnifiedModelInfo.from_dict(data)
        assert reconstructed.model_name == valid_unified_model.model_name


class TestUnifiedModelCatalog:
    """Test cases for UnifiedModelCatalog class."""

    @pytest.fixture
    def sample_models(self) -> Dict[str, UnifiedModelInfo]:
        """Create sample models for catalog testing."""
        return {
            "Claude 3 Haiku": UnifiedModelInfo(
                model_name="Claude 3 Haiku",
                provider="Anthropic",
                model_id="anthropic.claude-3-haiku-20240307-v1:0",
                input_modalities=["TEXT", "IMAGE"],
                output_modalities=["TEXT"],
                streaming_supported=True,
                region_access={
                    "us-east-1": ModelAccessInfo(
                        region="us-east-1",
                        has_direct_access=True,
                        model_id="anthropic.claude-3-haiku-20240307-v1:0",
                    ),
                },
            ),
            "Nova Micro": UnifiedModelInfo(
                model_name="Nova Micro",
                provider="Amazon",
                model_id="amazon.nova-micro-v1:0",
                input_modalities=["TEXT"],
                output_modalities=["TEXT"],
                streaming_supported=False,
                region_access={
                    "us-east-1": ModelAccessInfo(
                        region="us-east-1",
                        has_direct_access=True,
                        model_id="amazon.nova-micro-v1:0",
                    ),
                },
            ),
        }

    @pytest.fixture
    def valid_catalog(self, sample_models) -> UnifiedModelCatalog:
        """Create a valid catalog for testing."""
        return UnifiedModelCatalog(
            retrieval_timestamp=datetime(2024, 1, 1, 12, 0, 0),
            unified_models=sample_models,
        )

    def test_init_valid_catalog(self, valid_catalog):
        """Test initialization with valid parameters."""
        assert isinstance(valid_catalog.retrieval_timestamp, datetime)
        assert len(valid_catalog.unified_models) == 2

    def test_model_count_property(self, valid_catalog):
        """Test model_count property."""
        assert valid_catalog.model_count == 2

    def test_get_model_names(self, valid_catalog):
        """Test getting all model names."""
        names = valid_catalog.get_model_names()
        assert len(names) == 2

    def test_get_models_by_provider(self, valid_catalog):
        """Test filtering models by provider."""
        models = valid_catalog.get_models_by_provider("Anthropic")
        assert len(models) == 1

    def test_get_models_by_region(self, valid_catalog):
        """Test filtering models by region."""
        models = valid_catalog.get_models_by_region("us-east-1")
        assert len(models) == 2

    def test_get_direct_access_models_by_region(self, valid_catalog):
        """Test getting direct access models by region."""
        models = valid_catalog.get_direct_access_models_by_region("us-east-1")
        assert len(models) >= 1

    def test_get_streaming_models(self, valid_catalog):
        """Test getting streaming-enabled models."""
        models = valid_catalog.get_streaming_models()
        assert len(models) == 1

    def test_has_model(self, valid_catalog):
        """Test checking if model exists."""
        assert valid_catalog.has_model("Claude 3 Haiku") is True
        assert valid_catalog.has_model("Nonexistent") is False

    def test_get_all_supported_regions(self, valid_catalog):
        """Test getting all supported regions."""
        regions = valid_catalog.get_all_supported_regions()
        assert "us-east-1" in regions

    def test_to_dict(self, valid_catalog):
        """Test converting catalog to dictionary."""
        result = valid_catalog.to_dict()
        assert "unified_models" in result

    def test_from_dict_valid_data(self, valid_catalog):
        """Test creating catalog from valid dictionary."""
        data = valid_catalog.to_dict()
        reconstructed = UnifiedModelCatalog.from_dict(data)
        assert reconstructed.model_count == valid_catalog.model_count
