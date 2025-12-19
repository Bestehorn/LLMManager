"""
Tests for CatalogTransformer class.

This module tests the data transformation functionality including:
- Model data transformation
- CRIS data transformation
- Data correlation
- Handling of missing data
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from bestehorn_llmmanager.bedrock.catalog.api_fetcher import RawCatalogData
from bestehorn_llmmanager.bedrock.catalog.transformer import CatalogTransformer
from bestehorn_llmmanager.bedrock.models.catalog_structures import (
    CatalogSource,
    UnifiedCatalog,
)
from bestehorn_llmmanager.bedrock.models.cris_structures import (
    CRISInferenceProfile,
    CRISModelInfo,
)
from bestehorn_llmmanager.bedrock.models.data_structures import BedrockModelInfo


@pytest.fixture
def sample_model_summary():
    """Sample foundation model API response."""
    return {
        "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
        "modelName": "Claude 3 Sonnet",
        "providerName": "Anthropic",
        "inputModalities": ["TEXT", "IMAGE"],
        "outputModalities": ["TEXT"],
        "responseStreamingSupported": True,
    }


@pytest.fixture
def sample_profile_summary():
    """Sample inference profile API response."""
    return {
        "inferenceProfileId": "us.anthropic.claude-3-sonnet-20240229-v1:0",
        "inferenceProfileName": "Claude 3 Sonnet",
        "type": "SYSTEM_DEFINED",
        "models": [
            {
                "modelArn": "arn:aws:bedrock:us-east-1:123456789012:foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
            }
        ],
    }


@pytest.fixture
def sample_global_profile_summary():
    """Sample global inference profile API response."""
    return {
        "inferenceProfileId": "global.anthropic.claude-3-sonnet-20240229-v1:0",
        "inferenceProfileName": "Claude 3 Sonnet Global",
        "type": "SYSTEM_DEFINED",
        "models": [
            {
                "modelArn": "arn:aws:bedrock:us-east-1:123456789012:foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
            },
            {
                "modelArn": "arn:aws:bedrock:us-west-2:123456789012:foundation-model/anthropic.claude-3-sonnet-20240229-v1:0"
            },
        ],
    }


@pytest.fixture
def raw_catalog_data_with_models(sample_model_summary):
    """RawCatalogData with foundation models."""
    data = RawCatalogData()
    data.add_region_data(
        region="us-east-1",
        models=[sample_model_summary],
        profiles=[],
    )
    return data


@pytest.fixture
def raw_catalog_data_with_profiles(sample_profile_summary):
    """RawCatalogData with inference profiles."""
    data = RawCatalogData()
    data.add_region_data(
        region="us-east-1",
        models=[],
        profiles=[sample_profile_summary],
    )
    return data


@pytest.fixture
def raw_catalog_data_complete(sample_model_summary, sample_profile_summary):
    """RawCatalogData with both models and profiles."""
    data = RawCatalogData()
    data.add_region_data(
        region="us-east-1",
        models=[sample_model_summary],
        profiles=[sample_profile_summary],
    )
    return data


class TestCatalogTransformerInit:
    """Tests for CatalogTransformer initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        transformer = CatalogTransformer()

        assert transformer._correlator is not None

    def test_init_with_fuzzy_matching_enabled(self):
        """Test initialization with fuzzy matching enabled."""
        transformer = CatalogTransformer(enable_fuzzy_matching=True)

        assert transformer._correlator is not None

    def test_init_with_fuzzy_matching_disabled(self):
        """Test initialization with fuzzy matching disabled."""
        transformer = CatalogTransformer(enable_fuzzy_matching=False)

        assert transformer._correlator is not None


class TestCatalogTransformerTransformApiData:
    """Tests for transform_api_data method."""

    def test_transform_api_data_success(self, raw_catalog_data_complete):
        """Test successful transformation of complete API data."""
        transformer = CatalogTransformer()

        # Mock the correlator to return a simple unified catalog
        with patch.object(transformer, "_correlate_data") as mock_correlate:
            mock_unified_catalog_data = MagicMock()
            mock_unified_catalog_data.unified_models = {}
            mock_correlate.return_value = mock_unified_catalog_data

            result = transformer.transform_api_data(raw_data=raw_catalog_data_complete)

            assert isinstance(result, UnifiedCatalog)
            assert result.metadata.source == CatalogSource.API
            assert isinstance(result.metadata.retrieval_timestamp, datetime)
            assert "us-east-1" in result.metadata.api_regions_queried

    def test_transform_api_data_with_custom_timestamp(self, raw_catalog_data_complete):
        """Test transformation with custom retrieval timestamp."""
        transformer = CatalogTransformer()
        custom_timestamp = datetime(2024, 1, 1, 12, 0, 0)

        with patch.object(transformer, "_correlate_data") as mock_correlate:
            mock_unified_catalog_data = MagicMock()
            mock_unified_catalog_data.unified_models = {}
            mock_correlate.return_value = mock_unified_catalog_data

            result = transformer.transform_api_data(
                raw_data=raw_catalog_data_complete,
                retrieval_timestamp=custom_timestamp,
            )

            assert result.metadata.retrieval_timestamp == custom_timestamp

    def test_transform_api_data_no_data_raises_error(self):
        """Test that transformation fails when no data is available."""
        transformer = CatalogTransformer()
        empty_data = RawCatalogData()

        with pytest.raises(ValueError, match="No data available"):
            transformer.transform_api_data(raw_data=empty_data)

    def test_transform_api_data_handles_transformation_error(self, raw_catalog_data_complete):
        """Test handling of transformation errors."""
        transformer = CatalogTransformer()

        with patch.object(transformer, "_transform_models", side_effect=Exception("Test error")):
            with pytest.raises(ValueError, match="Data transformation failed"):
                transformer.transform_api_data(raw_data=raw_catalog_data_complete)


class TestCatalogTransformerTransformModels:
    """Tests for _transform_models method."""

    def test_transform_models_success(self, raw_catalog_data_with_models):
        """Test successful model transformation."""
        transformer = CatalogTransformer()
        timestamp = datetime.now()

        result = transformer._transform_models(
            raw_data=raw_catalog_data_with_models,
            retrieval_timestamp=timestamp,
        )

        assert result.retrieval_timestamp == timestamp
        assert len(result.models) > 0

    def test_transform_models_extracts_model_info(self, sample_model_summary):
        """Test that model info is correctly extracted."""
        transformer = CatalogTransformer()
        raw_data = RawCatalogData()
        raw_data.add_region_data(
            region="us-east-1",
            models=[sample_model_summary],
            profiles=[],
        )

        result = transformer._transform_models(
            raw_data=raw_data,
            retrieval_timestamp=datetime.now(),
        )

        # Check that at least one model was extracted
        assert len(result.models) > 0

        # Get the first model
        model = list(result.models.values())[0]
        assert isinstance(model, BedrockModelInfo)
        assert model.provider == "Anthropic"
        assert "us-east-1" in model.regions_supported

    def test_transform_models_merges_multi_region_data(self):
        """Test that models from multiple regions are merged."""
        transformer = CatalogTransformer()
        model_summary = {
            "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
            "providerName": "Anthropic",
            "inputModalities": ["TEXT"],
            "outputModalities": ["TEXT"],
            "responseStreamingSupported": True,
        }

        raw_data = RawCatalogData()
        raw_data.add_region_data(region="us-east-1", models=[model_summary], profiles=[])
        raw_data.add_region_data(region="us-west-2", models=[model_summary], profiles=[])

        result = transformer._transform_models(
            raw_data=raw_data,
            retrieval_timestamp=datetime.now(),
        )

        # Should have one model with multiple regions
        assert len(result.models) == 1
        model = list(result.models.values())[0]
        assert "us-east-1" in model.regions_supported
        assert "us-west-2" in model.regions_supported

    def test_transform_models_handles_malformed_data(self):
        """Test handling of malformed model summaries."""
        transformer = CatalogTransformer()
        malformed_summary = {
            # Missing modelId
            "providerName": "Test",
        }

        raw_data = RawCatalogData()
        raw_data.add_region_data(
            region="us-east-1",
            models=[malformed_summary],
            profiles=[],
        )

        # Should not raise, but skip malformed data
        result = transformer._transform_models(
            raw_data=raw_data,
            retrieval_timestamp=datetime.now(),
        )

        assert len(result.models) == 0


class TestCatalogTransformerTransformCris:
    """Tests for _transform_cris method."""

    def test_transform_cris_success(self, raw_catalog_data_with_profiles):
        """Test successful CRIS transformation."""
        transformer = CatalogTransformer()
        timestamp = datetime.now()

        result = transformer._transform_cris(
            raw_data=raw_catalog_data_with_profiles,
            retrieval_timestamp=timestamp,
        )

        assert result.retrieval_timestamp == timestamp
        assert len(result.cris_models) > 0

    def test_transform_cris_extracts_profile_info(self, sample_profile_summary):
        """Test that profile info is correctly extracted."""
        transformer = CatalogTransformer()
        raw_data = RawCatalogData()
        raw_data.add_region_data(
            region="us-east-1",
            models=[],
            profiles=[sample_profile_summary],
        )

        result = transformer._transform_cris(
            raw_data=raw_data,
            retrieval_timestamp=datetime.now(),
        )

        # Check that at least one CRIS model was extracted
        assert len(result.cris_models) > 0

        # Get the first CRIS model
        cris_model = list(result.cris_models.values())[0]
        assert isinstance(cris_model, CRISModelInfo)
        assert len(cris_model.inference_profiles) > 0

    def test_transform_cris_identifies_global_profiles(self, sample_global_profile_summary):
        """Test that global profiles are correctly identified."""
        transformer = CatalogTransformer()
        raw_data = RawCatalogData()
        raw_data.add_region_data(
            region="us-east-1",
            models=[],
            profiles=[sample_global_profile_summary],
        )

        result = transformer._transform_cris(
            raw_data=raw_data,
            retrieval_timestamp=datetime.now(),
        )

        # Get the CRIS model
        cris_model = list(result.cris_models.values())[0]
        profile = list(cris_model.inference_profiles.values())[0]

        assert isinstance(profile, CRISInferenceProfile)
        assert profile.is_global is True

    def test_transform_cris_builds_region_mappings(self, sample_profile_summary):
        """Test that region mappings are built from models array."""
        transformer = CatalogTransformer()
        raw_data = RawCatalogData()
        raw_data.add_region_data(
            region="us-east-1",
            models=[],
            profiles=[sample_profile_summary],
        )

        result = transformer._transform_cris(
            raw_data=raw_data,
            retrieval_timestamp=datetime.now(),
        )

        # Get the CRIS model
        cris_model = list(result.cris_models.values())[0]
        profile = list(cris_model.inference_profiles.values())[0]

        assert len(profile.region_mappings) > 0

    def test_transform_cris_handles_malformed_data(self):
        """Test handling of malformed profile summaries."""
        transformer = CatalogTransformer()
        malformed_summary = {
            # Missing inferenceProfileId
            "inferenceProfileName": "Test",
        }

        raw_data = RawCatalogData()
        raw_data.add_region_data(
            region="us-east-1",
            models=[],
            profiles=[malformed_summary],
        )

        # Should not raise, but skip malformed data
        result = transformer._transform_cris(
            raw_data=raw_data,
            retrieval_timestamp=datetime.now(),
        )

        assert len(result.cris_models) == 0


class TestCatalogTransformerCorrelateData:
    """Tests for _correlate_data method."""

    def test_correlate_data_calls_correlator(self):
        """Test that correlation delegates to ModelCRISCorrelator."""
        transformer = CatalogTransformer()

        # Create mock catalogs
        mock_model_catalog = MagicMock()
        mock_cris_catalog = MagicMock()

        # Mock the correlator
        with patch.object(transformer._correlator, "correlate_catalogs") as mock_correlate:
            mock_unified = MagicMock()
            mock_correlate.return_value = mock_unified

            with patch.object(transformer._correlator, "get_correlation_stats") as mock_stats:
                mock_stats.return_value = {
                    "matched_models": 1,
                    "fuzzy_matched_models": 0,
                    "cris_only_models": 0,
                    "unmatched_regular_models": 0,
                }

                result = transformer._correlate_data(
                    model_catalog=mock_model_catalog,
                    cris_catalog=mock_cris_catalog,
                )

                assert result == mock_unified
                mock_correlate.assert_called_once_with(
                    model_catalog=mock_model_catalog,
                    cris_catalog=mock_cris_catalog,
                )

    def test_correlate_data_handles_correlation_error(self):
        """Test handling of correlation errors."""
        transformer = CatalogTransformer()

        mock_model_catalog = MagicMock()
        mock_cris_catalog = MagicMock()

        with patch.object(
            transformer._correlator,
            "correlate_catalogs",
            side_effect=Exception("Correlation failed"),
        ):
            with pytest.raises(ValueError, match="Correlation failed"):
                transformer._correlate_data(
                    model_catalog=mock_model_catalog,
                    cris_catalog=mock_cris_catalog,
                )


class TestCatalogTransformerExtractModelInfo:
    """Tests for _extract_model_info method."""

    def test_extract_model_info_success(self, sample_model_summary):
        """Test successful model info extraction."""
        transformer = CatalogTransformer()

        result = transformer._extract_model_info(
            model_summary=sample_model_summary,
            source_region="us-east-1",
        )

        assert result is not None
        assert isinstance(result, BedrockModelInfo)
        assert result.model_id == "anthropic.claude-3-sonnet-20240229-v1:0"
        assert result.provider == "Anthropic"
        assert "us-east-1" in result.regions_supported
        assert result.streaming_supported is True

    def test_extract_model_info_missing_model_id(self):
        """Test handling of missing modelId."""
        transformer = CatalogTransformer()
        summary = {
            "providerName": "Test",
        }

        result = transformer._extract_model_info(
            model_summary=summary,
            source_region="us-east-1",
        )

        assert result is None

    def test_extract_model_info_invalid_modalities(self):
        """Test handling of invalid modalities."""
        transformer = CatalogTransformer()
        summary = {
            "modelId": "test.model-v1",
            "providerName": "Test",
            "inputModalities": "not a list",  # Invalid
            "outputModalities": ["TEXT"],
        }

        result = transformer._extract_model_info(
            model_summary=summary,
            source_region="us-east-1",
        )

        # Should use default modalities
        assert result is not None
        assert result.input_modalities == ["Text"]

    def test_extract_model_info_invalid_streaming_flag(self):
        """Test handling of invalid streaming flag."""
        transformer = CatalogTransformer()
        summary = {
            "modelId": "test.model-v1",
            "providerName": "Test",
            "responseStreamingSupported": "not a bool",  # Invalid
        }

        result = transformer._extract_model_info(
            model_summary=summary,
            source_region="us-east-1",
        )

        # Should use default (False)
        assert result is not None
        assert result.streaming_supported is False


class TestCatalogTransformerExtractProfileInfo:
    """Tests for _extract_profile_info method."""

    def test_extract_profile_info_success(self, sample_profile_summary):
        """Test successful profile info extraction."""
        transformer = CatalogTransformer()

        result = transformer._extract_profile_info(
            profile_summary=sample_profile_summary,
            source_region="us-east-1",
        )

        assert result is not None
        assert isinstance(result, CRISInferenceProfile)
        assert result.inference_profile_id == "us.anthropic.claude-3-sonnet-20240229-v1:0"
        assert result.is_global is False

    def test_extract_profile_info_global_profile(self, sample_global_profile_summary):
        """Test extraction of global profile."""
        transformer = CatalogTransformer()

        result = transformer._extract_profile_info(
            profile_summary=sample_global_profile_summary,
            source_region="us-east-1",
        )

        assert result is not None
        assert result.is_global is True

    def test_extract_profile_info_missing_profile_id(self):
        """Test handling of missing inferenceProfileId."""
        transformer = CatalogTransformer()
        summary = {
            "inferenceProfileName": "Test",
        }

        result = transformer._extract_profile_info(
            profile_summary=summary,
            source_region="us-east-1",
        )

        assert result is None

    def test_extract_profile_info_invalid_models_field(self):
        """Test handling of invalid models field."""
        transformer = CatalogTransformer()
        summary = {
            "inferenceProfileId": "us.test.model-v1",
            "models": "not a list",  # Invalid
        }

        result = transformer._extract_profile_info(
            profile_summary=summary,
            source_region="us-east-1",
        )

        # Should still create profile with default region mapping
        assert result is not None
        assert len(result.region_mappings) > 0


class TestCatalogTransformerExtractModelName:
    """Tests for _extract_model_name method."""

    def test_extract_model_name_with_provider_prefix(self):
        """Test extraction with provider prefix."""
        transformer = CatalogTransformer()

        result = transformer._extract_model_name(
            model_id="anthropic.claude-3-5-haiku-20241022-v1:0"
        )

        assert "Claude" in result
        assert "Haiku" in result

    def test_extract_model_name_without_provider_prefix(self):
        """Test extraction without provider prefix."""
        transformer = CatalogTransformer()

        result = transformer._extract_model_name(model_id="claude-3-sonnet-v1")

        assert "Claude" in result
        assert "Sonnet" in result

    def test_extract_model_name_removes_version_suffix(self):
        """Test that version suffixes are removed."""
        transformer = CatalogTransformer()

        result = transformer._extract_model_name(model_id="amazon.titan-text-express-v1:0")

        assert "Titan" in result
        assert "Express" in result
        assert ":0" not in result


class TestCatalogTransformerExtractModelNameFromProfile:
    """Tests for _extract_model_name_from_profile method."""

    def test_extract_model_name_from_global_profile(self):
        """Test extraction from global profile ID."""
        transformer = CatalogTransformer()

        result = transformer._extract_model_name_from_profile(
            profile_id="global.anthropic.claude-3-5-haiku-20241022-v1:0"
        )

        assert "Global" in result
        assert "Anthropic" in result
        assert "Claude" in result

    def test_extract_model_name_from_regional_profile(self):
        """Test extraction from regional profile ID."""
        transformer = CatalogTransformer()

        result = transformer._extract_model_name_from_profile(
            profile_id="us.anthropic.claude-3-sonnet-20240229-v1:0"
        )

        assert "Anthropic" in result
        assert "Claude" in result
        assert "Global" not in result


class TestCatalogTransformerMergeModelInfo:
    """Tests for _merge_model_info method."""

    def test_merge_model_info_combines_regions(self):
        """Test that regions are merged."""
        transformer = CatalogTransformer()

        existing = BedrockModelInfo(
            provider="Anthropic",
            model_id="anthropic.claude-3-sonnet-v1",
            regions_supported=["us-east-1"],
            input_modalities=["TEXT"],
            output_modalities=["TEXT"],
            streaming_supported=True,
        )

        new = BedrockModelInfo(
            provider="Anthropic",
            model_id="anthropic.claude-3-sonnet-v1",
            regions_supported=["us-west-2"],
            input_modalities=["TEXT"],
            output_modalities=["TEXT"],
            streaming_supported=True,
        )

        result = transformer._merge_model_info(existing=existing, new=new)

        assert "us-east-1" in result.regions_supported
        assert "us-west-2" in result.regions_supported

    def test_merge_model_info_combines_modalities(self):
        """Test that modalities are merged."""
        transformer = CatalogTransformer()

        existing = BedrockModelInfo(
            provider="Anthropic",
            model_id="anthropic.claude-3-sonnet-v1",
            regions_supported=["us-east-1"],
            input_modalities=["TEXT"],
            output_modalities=["TEXT"],
            streaming_supported=True,
        )

        new = BedrockModelInfo(
            provider="Anthropic",
            model_id="anthropic.claude-3-sonnet-v1",
            regions_supported=["us-east-1"],
            input_modalities=["TEXT", "IMAGE"],
            output_modalities=["TEXT"],
            streaming_supported=True,
        )

        result = transformer._merge_model_info(existing=existing, new=new)

        assert "TEXT" in result.input_modalities
        assert "IMAGE" in result.input_modalities

    def test_merge_model_info_combines_streaming_support(self):
        """Test that streaming support is OR'd."""
        transformer = CatalogTransformer()

        existing = BedrockModelInfo(
            provider="Anthropic",
            model_id="anthropic.claude-3-sonnet-v1",
            regions_supported=["us-east-1"],
            input_modalities=["TEXT"],
            output_modalities=["TEXT"],
            streaming_supported=False,
        )

        new = BedrockModelInfo(
            provider="Anthropic",
            model_id="anthropic.claude-3-sonnet-v1",
            regions_supported=["us-east-1"],
            input_modalities=["TEXT"],
            output_modalities=["TEXT"],
            streaming_supported=True,
        )

        result = transformer._merge_model_info(existing=existing, new=new)

        assert result.streaming_supported is True


class TestCatalogTransformerMergeRegionMappings:
    """Tests for _merge_region_mappings method."""

    def test_merge_region_mappings_combines_mappings(self):
        """Test that region mappings are merged."""
        transformer = CatalogTransformer()

        existing = {
            "us-east-1": ["us-east-1", "us-west-2"],
        }

        new = {
            "us-east-1": ["eu-west-1"],
            "eu-west-1": ["eu-west-1"],
        }

        result = transformer._merge_region_mappings(existing=existing, new=new)

        assert "us-east-1" in result
        assert "eu-west-1" in result
        assert "us-east-1" in result["us-east-1"]
        assert "us-west-2" in result["us-east-1"]
        assert "eu-west-1" in result["us-east-1"]

    def test_merge_region_mappings_removes_duplicates(self):
        """Test that duplicate regions are removed."""
        transformer = CatalogTransformer()

        existing = {
            "us-east-1": ["us-east-1", "us-west-2"],
        }

        new = {
            "us-east-1": ["us-east-1", "us-west-2"],
        }

        result = transformer._merge_region_mappings(existing=existing, new=new)

        # Should have unique regions
        assert len(result["us-east-1"]) == 2
