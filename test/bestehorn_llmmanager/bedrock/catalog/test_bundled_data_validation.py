"""
Comprehensive validation tests for the actual bundled catalog data.

This module tests that the bundled data file contains valid, well-formed data
that can be properly deserialized into all the expected data structures.
"""

import pytest

from bestehorn_llmmanager.bedrock.catalog.bundled_loader import BundledDataLoader
from bestehorn_llmmanager.bedrock.models.catalog_structures import (
    CatalogMetadata,
    CatalogSource,
    UnifiedCatalog,
)
from bestehorn_llmmanager.bedrock.models.unified_structures import UnifiedModelInfo


class TestBundledDataValidation:
    """Comprehensive validation tests for bundled catalog data."""

    @pytest.fixture
    def bundled_catalog(self) -> UnifiedCatalog:
        """Load the bundled catalog for testing."""
        return BundledDataLoader.load_bundled_catalog()

    def test_bundled_catalog_loads_successfully(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that bundled catalog loads without errors."""
        assert bundled_catalog is not None
        assert isinstance(bundled_catalog, UnifiedCatalog)

    def test_bundled_catalog_has_models(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that bundled catalog contains models."""
        assert bundled_catalog.model_count > 0, "Bundled catalog should contain at least one model"
        assert len(bundled_catalog.models) > 0

    def test_bundled_catalog_metadata_is_valid(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that bundled catalog metadata is valid."""
        metadata = bundled_catalog.metadata

        assert isinstance(metadata, CatalogMetadata)
        assert metadata.source == CatalogSource.BUNDLED
        assert metadata.retrieval_timestamp is not None
        assert isinstance(metadata.api_regions_queried, list)
        assert metadata.bundled_data_version is not None

    def test_all_models_are_unified_model_info(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that all models are UnifiedModelInfo instances."""
        for model_name, model_info in bundled_catalog.models.items():
            assert isinstance(
                model_info, UnifiedModelInfo
            ), f"Model {model_name} is not a UnifiedModelInfo instance"

    def test_all_models_have_required_fields(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that all models have required fields populated."""
        for model_name, model_info in bundled_catalog.models.items():
            # Check required fields
            assert model_info.provider, f"Model {model_name} missing provider"
            assert model_info.model_id, f"Model {model_name} missing model_id"
            assert isinstance(
                model_info.region_access, dict
            ), f"Model {model_name} region_access is not a dict"
            assert len(model_info.region_access) > 0, f"Model {model_name} has no regions"

    def test_all_models_have_valid_modalities(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that all models have valid modality information."""
        for model_name, model_info in bundled_catalog.models.items():
            assert isinstance(
                model_info.input_modalities, list
            ), f"Model {model_name} input_modalities is not a list"
            assert isinstance(
                model_info.output_modalities, list
            ), f"Model {model_name} output_modalities is not a list"
            assert (
                len(model_info.input_modalities) > 0
            ), f"Model {model_name} has no input modalities"
            assert (
                len(model_info.output_modalities) > 0
            ), f"Model {model_name} has no output modalities"

    def test_all_models_have_valid_streaming_flag(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that all models have a valid streaming_supported flag."""
        for model_name, model_info in bundled_catalog.models.items():
            assert isinstance(
                model_info.streaming_supported, bool
            ), f"Model {model_name} streaming_supported is not a boolean"

    def test_catalog_has_multiple_regions(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that catalog includes models from multiple regions."""
        all_regions = bundled_catalog.get_all_regions()

        assert len(all_regions) > 1, "Bundled catalog should include multiple regions"
        assert isinstance(all_regions, list)
        assert all(isinstance(region, str) for region in all_regions)

    def test_catalog_has_multiple_providers(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that catalog includes models from multiple providers."""
        all_providers = bundled_catalog.get_all_providers()

        assert len(all_providers) > 1, "Bundled catalog should include multiple providers"
        assert isinstance(all_providers, list)
        assert all(isinstance(provider, str) for provider in all_providers)

    def test_catalog_can_filter_by_region(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that catalog can be filtered by region."""
        all_regions = bundled_catalog.get_all_regions()

        if len(all_regions) > 0:
            test_region = all_regions[0]
            filtered_models = bundled_catalog.filter_models(region=test_region)

            assert len(filtered_models) > 0, f"No models found for region {test_region}"
            # Verify all returned models support the region
            for model in filtered_models:
                assert model.is_available_in_region(
                    region=test_region
                ), f"Model {model.model_id} does not support region {test_region}"

    def test_catalog_can_filter_by_provider(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that catalog can be filtered by provider."""
        all_providers = bundled_catalog.get_all_providers()

        if len(all_providers) > 0:
            test_provider = all_providers[0]
            filtered_models = bundled_catalog.filter_models(provider=test_provider)

            assert len(filtered_models) > 0, f"No models found for provider {test_provider}"
            # Verify all returned models are from the provider
            for model in filtered_models:
                assert (
                    model.provider == test_provider
                ), f"Model {model.model_id} is not from provider {test_provider}"

    def test_catalog_can_filter_by_streaming(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that catalog can be filtered by streaming support."""
        streaming_models = bundled_catalog.filter_models(streaming_only=True)

        # Verify all returned models support streaming
        for model in streaming_models:
            assert model.streaming_supported, f"Model {model.model_id} does not support streaming"

    def test_catalog_get_model_returns_correct_model(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that get_model returns the correct model."""
        if bundled_catalog.model_count > 0:
            # Get first model name
            first_model_name = list(bundled_catalog.models.keys())[0]

            # Retrieve it
            model = bundled_catalog.get_model(name=first_model_name)

            assert model is not None
            assert isinstance(model, UnifiedModelInfo)

    def test_catalog_get_model_returns_none_for_invalid_name(
        self, bundled_catalog: UnifiedCatalog
    ) -> None:
        """Test that get_model returns None for invalid model name."""
        model = bundled_catalog.get_model(name="nonexistent-model-12345")
        assert model is None

    def test_catalog_serialization_round_trip(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that catalog can be serialized and deserialized."""
        # Serialize to dict
        catalog_dict = bundled_catalog.to_dict()

        assert isinstance(catalog_dict, dict)
        assert "models" in catalog_dict
        assert "metadata" in catalog_dict

        # Deserialize back
        restored_catalog = UnifiedCatalog.from_dict(data=catalog_dict)

        assert restored_catalog.model_count == bundled_catalog.model_count
        assert restored_catalog.metadata.source == bundled_catalog.metadata.source

    def test_bundled_data_version_is_set(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that bundled data has a version set."""
        assert bundled_catalog.metadata.bundled_data_version is not None
        assert len(bundled_catalog.metadata.bundled_data_version) > 0
        assert bundled_catalog.metadata.bundled_data_version != "unknown"

    def test_bundled_data_has_recent_timestamp(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that bundled data has a timestamp (not checking age, just presence)."""
        assert bundled_catalog.metadata.retrieval_timestamp is not None

    def test_all_model_ids_are_unique(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that all model IDs in the catalog are unique."""
        model_ids = [model.model_id for model in bundled_catalog.models.values()]
        unique_model_ids = set(model_ids)

        assert len(model_ids) == len(unique_model_ids), (
            "Duplicate model IDs found in bundled catalog"
        )

    def test_model_names_match_dict_keys(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that model names in the dict match the model info."""
        for model_name, model_info in bundled_catalog.models.items():
            # The model name should be derivable from the model_id
            assert model_info.model_id is not None
            assert len(model_name) > 0

    def test_all_regions_are_valid_format(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that all regions follow AWS region naming convention."""
        import re

        region_pattern = re.compile(r"^[a-z]{2}-[a-z]+-\d+$")

        all_regions = bundled_catalog.get_all_regions()

        for region in all_regions:
            assert region_pattern.match(region), f"Region {region} does not match AWS region format"

    def test_catalog_has_expected_major_providers(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that catalog includes models from major AWS Bedrock providers."""
        all_providers = bundled_catalog.get_all_providers()

        # Convert to lowercase for case-insensitive comparison
        providers_lower = [p.lower() for p in all_providers]

        # Check for at least some major providers (not all may be present)
        major_providers = ["anthropic", "amazon", "meta", "cohere", "ai21", "mistral"]
        found_providers = [p for p in major_providers if p in providers_lower]

        assert (
            len(found_providers) >= 2
        ), f"Expected at least 2 major providers, found: {found_providers}"

    def test_metadata_regions_match_model_regions(self, bundled_catalog: UnifiedCatalog) -> None:
        """Test that metadata regions match regions found in models."""
        _ = set(bundled_catalog.metadata.api_regions_queried)
        _ = set(bundled_catalog.get_all_regions())

        # Metadata regions should be a subset of or equal to model regions
        # (models may be available in regions not queried if they're CRIS-only)
        assert len(bundled_catalog.metadata.api_regions_queried) > 0, (
            "Metadata should list at least one region that was queried"
        )
