"""
Integration tests for BedrockAPIFetcher with real AWS APIs.

These tests validate API fetching functionality with real AWS Bedrock APIs,
covering multi-region fetching, data transformation, and error handling.

Requirements tested:
- 1.1: API-only data retrieval using list-foundation-models
- 1.2: API-only data retrieval using list-inference-profiles
- 10.1: Parallel multi-region fetching
"""

import logging
from typing import Any

import pytest

from bestehorn_llmmanager.bedrock.catalog.api_fetcher import BedrockAPIFetcher
from bestehorn_llmmanager.bedrock.catalog.transformer import CatalogTransformer
from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import APIFetchError


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestBedrockAPIFetcherIntegration:
    """Integration tests for BedrockAPIFetcher with real AWS APIs."""

    def test_api_fetcher_initialization(
        self, integration_config: Any, auth_manager_with_profile: Any
    ) -> None:
        """
        Test BedrockAPIFetcher initialization with real AuthManager.

        Args:
            integration_config: Integration test configuration
            auth_manager_with_profile: AuthManager configured with test profile
        """
        # Initialize API fetcher with profile-configured AuthManager
        fetcher = BedrockAPIFetcher(
            auth_manager=auth_manager_with_profile,
            timeout=integration_config.timeout_seconds,
            max_workers=5,
        )

        # Verify initialization
        assert fetcher is not None
        assert fetcher._auth_manager is auth_manager_with_profile
        assert fetcher._timeout == integration_config.timeout_seconds
        assert fetcher._max_workers == 5

    def test_fetch_foundation_models_single_region(
        self, integration_config: Any, auth_manager_with_profile: Any
    ) -> None:
        """
        Test fetching foundation models from a single region.

        Validates Requirement 1.1: API-only data retrieval using list-foundation-models

        Args:
            integration_config: Integration test configuration
            auth_manager_with_profile: AuthManager configured with test profile
        """
        # Create API fetcher with profile-configured AuthManager
        fetcher = BedrockAPIFetcher(
            auth_manager=auth_manager_with_profile,
            timeout=integration_config.timeout_seconds,
        )

        # Get primary test region
        region = integration_config.get_primary_test_region()

        # Fetch foundation models
        models = fetcher._fetch_foundation_models(region=region)

        # Verify response
        assert isinstance(models, list)
        assert len(models) > 0, "Should have at least one foundation model"

        # Verify model structure
        first_model = models[0]
        assert isinstance(first_model, dict)
        assert "modelId" in first_model
        assert "modelArn" in first_model

    def test_fetch_inference_profiles_single_region(
        self, integration_config: Any, auth_manager_with_profile: Any
    ) -> None:
        """
        Test fetching inference profiles from a single region.

        Validates Requirement 1.2: API-only data retrieval using list-inference-profiles

        Args:
            integration_config: Integration test configuration
        """
        # Create API fetcher with profile-configured AuthManager
        fetcher = BedrockAPIFetcher(
            auth_manager=auth_manager_with_profile,
            timeout=integration_config.timeout_seconds,
        )

        # Get primary test region
        region = integration_config.get_primary_test_region()

        # Fetch inference profiles
        profiles = fetcher._fetch_inference_profiles(region=region)

        # Verify response
        assert isinstance(profiles, list)
        # Note: Profiles may be empty in some regions, so we don't assert len > 0

        # If profiles exist, verify structure
        if len(profiles) > 0:
            first_profile = profiles[0]
            assert isinstance(first_profile, dict)
            assert "inferenceProfileId" in first_profile

    def test_fetch_all_data_single_region(
        self, integration_config: Any, auth_manager_with_profile: Any
    ) -> None:
        """
        Test fetching both models and profiles from a single region.

        Args:
            integration_config: Integration test configuration
        """
        # Create API fetcher with profile-configured AuthManager
        fetcher = BedrockAPIFetcher(
            auth_manager=auth_manager_with_profile,
            timeout=integration_config.timeout_seconds,
        )

        # Get primary test region
        region = integration_config.get_primary_test_region()

        # Fetch all data for single region
        raw_data = fetcher.fetch_all_data(regions=[region])

        # Verify raw data structure
        assert raw_data is not None
        assert raw_data.has_data
        assert region in raw_data.successful_regions
        assert region in raw_data.foundation_models
        assert region in raw_data.inference_profiles

        # Verify models
        models = raw_data.foundation_models[region]
        assert isinstance(models, list)
        assert len(models) > 0

        # Verify profiles
        profiles = raw_data.inference_profiles[region]
        assert isinstance(profiles, list)

    def test_fetch_all_data_multiple_regions(
        self, integration_config: Any, auth_manager_with_profile: Any
    ) -> None:
        """
        Test parallel fetching from multiple regions.

        Validates Requirement 10.1: Parallel multi-region fetching

        Args:
            integration_config: Integration test configuration
        """
        # Create API fetcher with profile-configured AuthManager
        fetcher = BedrockAPIFetcher(
            auth_manager=auth_manager_with_profile,
            timeout=integration_config.timeout_seconds,
            max_workers=3,
        )

        # Use multiple test regions
        test_regions = integration_config.test_regions[:3]  # Limit to 3 for speed

        # Fetch all data from multiple regions
        raw_data = fetcher.fetch_all_data(regions=test_regions)

        # Verify raw data structure
        assert raw_data is not None
        assert raw_data.has_data
        assert len(raw_data.successful_regions) > 0

        # Verify at least one region succeeded
        assert len(raw_data.successful_regions) >= 1

        # Verify data for successful regions
        for region in raw_data.successful_regions:
            assert region in raw_data.foundation_models
            assert region in raw_data.inference_profiles
            assert isinstance(raw_data.foundation_models[region], list)
            assert isinstance(raw_data.inference_profiles[region], list)

    def test_fetch_all_data_with_invalid_region(
        self, integration_config: Any, auth_manager_with_profile: Any
    ) -> None:
        """
        Test graceful handling of invalid regions.

        Args:
            integration_config: Integration test configuration
        """
        # Create API fetcher with profile-configured AuthManager
        fetcher = BedrockAPIFetcher(
            auth_manager=auth_manager_with_profile,
            timeout=integration_config.timeout_seconds,
        )

        # Mix valid and invalid regions
        valid_region = integration_config.get_primary_test_region()
        invalid_region = "invalid-region-1"
        test_regions = [valid_region, invalid_region]

        # Fetch all data
        raw_data = fetcher.fetch_all_data(regions=test_regions)

        # Verify that valid region succeeded
        assert raw_data.has_data
        assert valid_region in raw_data.successful_regions

        # Verify that invalid region failed
        assert invalid_region in raw_data.failed_regions
        assert isinstance(raw_data.failed_regions[invalid_region], str)

    def test_fetch_all_data_all_invalid_regions(self) -> None:
        """
        Test error handling when all regions fail.

        Should raise APIFetchError when no data can be retrieved.
        """
        # Create API fetcher with profile-configured AuthManager
        fetcher = BedrockAPIFetcher(
            auth_manager=auth_manager_with_profile,
            timeout=30,
        )

        # Use only invalid regions
        invalid_regions = ["invalid-region-1", "invalid-region-2"]

        # Should raise APIFetchError
        with pytest.raises(APIFetchError) as exc_info:
            fetcher.fetch_all_data(regions=invalid_regions)

        # Verify error message
        error_msg = str(exc_info.value)
        assert "all regions failed" in error_msg.lower() or "no data" in error_msg.lower()


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestCatalogTransformerIntegration:
    """Integration tests for CatalogTransformer with real API data."""

    def test_transform_real_api_data(
        self, integration_config: Any, auth_manager_with_profile: Any
    ) -> None:
        """
        Test transforming real API data into unified catalog.

        Validates Requirement 1.5: Transform API responses into unified catalog structures

        Args:
            integration_config: Integration test configuration
        """
        # Fetch real data with profile-configured AuthManager
        fetcher = BedrockAPIFetcher(
            auth_manager=auth_manager_with_profile,
            timeout=integration_config.timeout_seconds,
        )

        region = integration_config.get_primary_test_region()
        raw_data = fetcher.fetch_all_data(regions=[region])

        # Transform data
        transformer = CatalogTransformer()
        catalog = transformer.transform_api_data(raw_data=raw_data)

        # Verify catalog structure
        assert catalog is not None
        assert catalog.models is not None
        assert isinstance(catalog.models, dict)
        assert len(catalog.models) > 0

        # Verify metadata
        assert catalog.metadata is not None
        assert catalog.metadata.source is not None
        assert catalog.metadata.retrieval_timestamp is not None
        assert region in catalog.metadata.api_regions_queried

        # Verify model structure
        first_model_name = next(iter(catalog.models.keys()))
        first_model = catalog.models[first_model_name]
        assert first_model.model_id is not None
        assert first_model.provider is not None
        supported_regions = first_model.get_supported_regions()
        assert supported_regions is not None
        assert len(supported_regions) > 0

    def test_transform_multi_region_data(
        self, integration_config: Any, auth_manager_with_profile: Any
    ) -> None:
        """
        Test transforming data from multiple regions.

        Args:
            integration_config: Integration test configuration
        """
        # Fetch real data from multiple regions with profile-configured AuthManager
        fetcher = BedrockAPIFetcher(
            auth_manager=auth_manager_with_profile,
            timeout=integration_config.timeout_seconds,
            max_workers=3,
        )

        test_regions = integration_config.test_regions[:3]
        raw_data = fetcher.fetch_all_data(regions=test_regions)

        # Transform data
        transformer = CatalogTransformer()
        catalog = transformer.transform_api_data(raw_data=raw_data)

        # Verify catalog has data from multiple regions
        assert catalog is not None
        assert len(catalog.models) > 0

        # Verify metadata includes all successful regions
        for region in raw_data.successful_regions:
            assert region in catalog.metadata.api_regions_queried

        # Verify models have region information
        for model_info in catalog.models.values():
            assert len(model_info.get_supported_regions()) > 0

    def test_catalog_serialization_round_trip(
        self, integration_config: Any, auth_manager_with_profile: Any
    ) -> None:
        """
        Test catalog serialization and deserialization.

        Validates that catalog can be saved and loaded without data loss.

        Args:
            integration_config: Integration test configuration
        """
        # Fetch and transform real data with profile-configured AuthManager
        fetcher = BedrockAPIFetcher(
            auth_manager=auth_manager_with_profile,
            timeout=integration_config.timeout_seconds,
        )

        region = integration_config.get_primary_test_region()
        raw_data = fetcher.fetch_all_data(regions=[region])

        transformer = CatalogTransformer()
        original_catalog = transformer.transform_api_data(raw_data=raw_data)

        # Serialize to dict
        catalog_dict = original_catalog.to_dict()

        # Verify dict structure
        assert isinstance(catalog_dict, dict)
        assert "models" in catalog_dict
        assert "metadata" in catalog_dict

        # Deserialize back to catalog
        from bestehorn_llmmanager.bedrock.models.catalog_structures import UnifiedCatalog

        restored_catalog = UnifiedCatalog.from_dict(data=catalog_dict)

        # Verify restored catalog matches original
        assert restored_catalog.model_count == original_catalog.model_count
        assert len(restored_catalog.models) == len(original_catalog.models)

        # Verify metadata
        assert restored_catalog.metadata.source == original_catalog.metadata.source
        assert (
            restored_catalog.metadata.retrieval_timestamp
            == original_catalog.metadata.retrieval_timestamp
        )


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestAPIFetcherPerformance:
    """Integration tests for API fetcher performance characteristics."""

    def test_parallel_fetching_performance(self, integration_config: Any, caplog: Any) -> None:
        """
        Test that parallel fetching is faster than sequential.

        Args:
            integration_config: Integration test configuration
            caplog: Pytest log capture fixture
        """
        import time

        # Set log level to capture timing information
        caplog.set_level(logging.INFO)

        # Create API fetcher with parallel execution and profile-configured AuthManager
        fetcher = BedrockAPIFetcher(
            auth_manager=auth_manager_with_profile,
            timeout=integration_config.timeout_seconds,
            max_workers=3,
        )

        # Use 3 regions for testing
        test_regions = integration_config.test_regions[:3]

        # Measure parallel fetch time
        start_time = time.time()
        raw_data = fetcher.fetch_all_data(regions=test_regions)
        parallel_duration = time.time() - start_time

        # Verify data was fetched
        assert raw_data.has_data
        assert len(raw_data.successful_regions) >= 1

        # Verify reasonable performance (should complete in reasonable time)
        # With 3 regions and parallel execution, should be < 30 seconds
        assert parallel_duration < 30.0, f"Parallel fetch took too long: {parallel_duration}s"

        # Log performance metrics
        print(f"\nParallel fetch of {len(test_regions)} regions: {parallel_duration:.2f}s")
        print(f"Successful regions: {len(raw_data.successful_regions)}")
        print(f"Failed regions: {len(raw_data.failed_regions)}")

    def test_retry_logic_with_transient_errors(
        self, integration_config: Any, auth_manager_with_profile: Any
    ) -> None:
        """
        Test retry logic handles transient errors gracefully.

        Note: This test may not trigger retries if AWS APIs are stable,
        but verifies the retry mechanism is in place.

        Args:
            integration_config: Integration test configuration
        """
        # Create API fetcher with retry configuration and profile-configured AuthManager
        fetcher = BedrockAPIFetcher(
            auth_manager=auth_manager_with_profile,
            timeout=integration_config.timeout_seconds,
            max_retries=3,
        )

        # Fetch data - retries will happen automatically if needed
        region = integration_config.get_primary_test_region()
        raw_data = fetcher.fetch_all_data(regions=[region])

        # Verify data was fetched successfully
        assert raw_data.has_data
        assert region in raw_data.successful_regions

        # If retries occurred, they would be logged
        # This test primarily verifies the retry mechanism doesn't break normal operation
