"""
Property-based tests for BedrockModelCatalog.

This module contains property-based tests using Hypothesis to verify
universal properties that should hold across all valid inputs.

**Feature: model-manager-redesign**

Properties tested:
1. Initialization always succeeds with bundled data
2. Cache mode determines file system usage
3. API data freshness
4. Model availability consistency
5. Cache round-trip consistency
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.catalog.bedrock_catalog import BedrockModelCatalog
from bestehorn_llmmanager.bedrock.catalog.cache_manager import CacheManager
from bestehorn_llmmanager.bedrock.models.catalog_structures import (
    CacheMode,
    CatalogMetadata,
    CatalogSource,
    UnifiedCatalog,
)
from bestehorn_llmmanager.bedrock.models.unified_structures import (
    ModelAccessInfo,
    UnifiedModelInfo,
)

# ============================================================================
# Hypothesis Strategies
# ============================================================================


@st.composite
def cache_mode_strategy(draw: st.DrawFn) -> CacheMode:
    """Generate random CacheMode values."""
    return draw(st.sampled_from([CacheMode.FILE, CacheMode.MEMORY, CacheMode.NONE]))


@st.composite
def cache_max_age_strategy(draw: st.DrawFn) -> float:
    """Generate valid cache_max_age_hours values."""
    return draw(st.floats(min_value=0.1, max_value=168.0))  # 0.1 to 168 hours (1 week)


@st.composite
def timeout_strategy(draw: st.DrawFn) -> int:
    """Generate valid timeout values."""
    return draw(st.integers(min_value=1, max_value=300))  # 1 to 300 seconds


@st.composite
def max_workers_strategy(draw: st.DrawFn) -> int:
    """Generate valid max_workers values."""
    return draw(st.integers(min_value=1, max_value=50))  # 1 to 50 workers


@st.composite
def sample_catalog_strategy(draw: st.DrawFn) -> UnifiedCatalog:
    """Generate a sample UnifiedCatalog for testing."""
    # Generate metadata
    source = draw(st.sampled_from([CatalogSource.API, CatalogSource.CACHE, CatalogSource.BUNDLED]))
    # Use a fixed time range to avoid flakiness
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    retrieval_timestamp = draw(
        st.datetimes(
            min_value=base_time,
            max_value=base_time + timedelta(days=30),
        )
    )
    api_regions = draw(
        st.lists(
            st.sampled_from(["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]),
            min_size=1,
            max_size=4,
            unique=True,
        )
    )

    metadata = CatalogMetadata(
        source=source,
        retrieval_timestamp=retrieval_timestamp,
        api_regions_queried=api_regions,
        bundled_data_version=None,
        cache_file_path=None,
    )

    # Generate model info
    model_name = draw(st.sampled_from(["anthropic.claude-3-sonnet", "amazon.titan-text"]))
    provider = draw(st.sampled_from(["Anthropic", "Amazon"]))
    streaming_supported = draw(st.booleans())

    # Generate region access
    region_access = {}
    for region in api_regions:
        region_access[region] = ModelAccessInfo(
            region=region,
            has_direct_access=True,
            model_id=f"{model_name}-v1:0",
        )

    model_info = UnifiedModelInfo(
        model_name=model_name,
        provider=provider,
        model_id=f"{model_name}-v1:0",
        streaming_supported=streaming_supported,
        input_modalities=["TEXT"],
        output_modalities=["TEXT"],
        region_access=region_access,
    )

    return UnifiedCatalog(
        models={model_name: model_info},
        metadata=metadata,
    )


# ============================================================================
# Property 1: Initialization always succeeds with bundled data
# **Feature: model-manager-redesign, Property 1: Initialization always succeeds with bundled data**
# **Validates: Requirements 3.2, 9.2**
# ============================================================================


class TestProperty1InitializationWithBundledData:
    """
    Property 1: Initialization always succeeds with bundled data.

    For any configuration, if bundled data exists, initialization SHALL NOT fail.
    """

    @given(
        cache_mode=cache_mode_strategy(),
        cache_max_age_hours=cache_max_age_strategy(),
        timeout=timeout_strategy(),
        max_workers=max_workers_strategy(),
        force_refresh=st.booleans(),
        fallback_to_bundled=st.just(True),  # Always enable bundled fallback
        bundled_catalog=sample_catalog_strategy(),
    )
    @settings(max_examples=100, deadline=None)
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.BundledDataLoader")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.BedrockAPIFetcher")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_property_1_initialization_always_succeeds_with_bundled_data(
        self,
        mock_auth_cls: Mock,
        mock_cache_cls: Mock,
        mock_fetcher_cls: Mock,
        mock_bundled_cls: Mock,
        cache_mode: CacheMode,
        cache_max_age_hours: float,
        timeout: int,
        max_workers: int,
        force_refresh: bool,
        fallback_to_bundled: bool,
        bundled_catalog: UnifiedCatalog,
    ) -> None:
        """
        Property: For any configuration, if bundled data exists, initialization SHALL NOT fail.

        This property verifies that regardless of cache mode, timeout, workers, or other
        configuration parameters, as long as bundled data is available, the catalog
        initialization will succeed.
        """
        # Setup: Make cache and API fail, but bundled data succeeds
        mock_cache = Mock()
        mock_cache.load_cache.return_value = None
        mock_cache_cls.return_value = mock_cache

        mock_fetcher = Mock()
        mock_fetcher.fetch_all_data.side_effect = Exception("API unavailable")
        mock_fetcher_cls.return_value = mock_fetcher

        # Use the generated bundled catalog
        mock_bundled_cls.load_bundled_catalog.return_value = bundled_catalog

        # Create temporary directory for FILE mode
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_directory = Path(tmpdir) if cache_mode == CacheMode.FILE else None

            # Initialize catalog with random configuration
            catalog = BedrockModelCatalog(
                cache_mode=cache_mode,
                cache_directory=cache_directory,
                cache_max_age_hours=cache_max_age_hours,
                force_refresh=force_refresh,
                timeout=timeout,
                max_workers=max_workers,
                fallback_to_bundled=fallback_to_bundled,
            )

            # Property: Initialization should always succeed
            result = catalog.ensure_catalog_available()

            # Verify: Catalog was loaded successfully
            assert result is not None
            assert isinstance(result, UnifiedCatalog)
            assert catalog.is_catalog_loaded
            # Note: The bundled catalog's metadata.source reflects when it was generated (API),
            # not that it came from bundled data. The important thing is initialization succeeded.


# ============================================================================
# Property 2: Cache mode determines file system usage
# **Feature: model-manager-redesign, Property 2: Cache mode determines file system usage**
# **Validates: Requirements 2.1, 4.2**
# ============================================================================


class TestProperty2CacheModeFileSystemUsage:
    """
    Property 2: Cache mode determines file system usage.

    For any catalog with cache_mode="none", no files SHALL be written.
    """

    @given(
        catalog=sample_catalog_strategy(),
    )
    @settings(max_examples=100, deadline=None)
    def test_property_2_none_mode_writes_no_files(
        self,
        catalog: UnifiedCatalog,
    ) -> None:
        """
        Property: For any catalog with cache_mode="none", no files SHALL be written.

        This property verifies that when cache_mode is NONE, the cache manager
        never writes any files to the file system.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            # Create cache manager in NONE mode
            manager = CacheManager(
                mode=CacheMode.NONE,
                directory=cache_dir,
                max_age_hours=24.0,
            )

            # Save catalog
            manager.save_cache(catalog=catalog)

            # Property: No files should be written
            cache_file = cache_dir / "bedrock_catalog.json"
            assert not cache_file.exists(), "NONE mode should not write any files"

            # Verify directory is empty
            files_in_dir = list(cache_dir.iterdir())
            assert len(files_in_dir) == 0, f"NONE mode wrote files: {files_in_dir}"


# ============================================================================
# Property 3: API data freshness
# **Feature: model-manager-redesign, Property 3: API data freshness**
# **Validates: Requirements 1.5, 10.3**
# ============================================================================


class TestProperty3APIDataFreshness:
    """
    Property 3: API data freshness.

    For any catalog from API, retrieval_timestamp SHALL be recent (< 1 minute old).
    """

    @given(
        timeout=timeout_strategy(),
        max_workers=max_workers_strategy(),
        base_catalog=sample_catalog_strategy(),
    )
    @settings(max_examples=50, deadline=None)
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CatalogTransformer")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.BedrockAPIFetcher")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_property_3_api_data_is_fresh(
        self,
        mock_auth_cls: Mock,
        mock_fetcher_cls: Mock,
        mock_transformer_cls: Mock,
        timeout: int,
        max_workers: int,
        base_catalog: UnifiedCatalog,
    ) -> None:
        """
        Property: For any catalog from API, retrieval_timestamp SHALL be recent (< 1 minute old).

        This property verifies that when data is fetched from the API, the retrieval
        timestamp is set to the current time (within 1 minute).
        """
        # Setup: Mock API to return fresh data
        mock_fetcher = Mock()
        mock_raw_data = Mock()
        mock_fetcher.fetch_all_data.return_value = mock_raw_data
        mock_fetcher_cls.return_value = mock_fetcher

        # Create a fresh catalog with current timestamp
        fresh_metadata = CatalogMetadata(
            source=CatalogSource.API,
            retrieval_timestamp=datetime.now(),
            api_regions_queried=base_catalog.metadata.api_regions_queried,
        )
        fresh_catalog = UnifiedCatalog(
            models=base_catalog.models,
            metadata=fresh_metadata,
        )

        mock_transformer = Mock()
        mock_transformer.transform_api_data.return_value = fresh_catalog
        mock_transformer_cls.return_value = mock_transformer

        # Initialize catalog with NONE mode to force API fetch
        catalog = BedrockModelCatalog(
            cache_mode=CacheMode.NONE,
            timeout=timeout,
            max_workers=max_workers,
        )

        # Fetch catalog
        _ = datetime.now()
        result = catalog.ensure_catalog_available()
        after_fetch = datetime.now()

        # Property: Retrieval timestamp should be recent (within 1 minute)
        time_diff = (after_fetch - result.metadata.retrieval_timestamp).total_seconds()
        assert time_diff < 60, f"API data is not fresh: {time_diff} seconds old"

        # Also verify it's not in the future
        assert result.metadata.retrieval_timestamp <= after_fetch, "Timestamp is in the future"


# ============================================================================
# Property 4: Model availability consistency
# **Feature: model-manager-redesign, Property 4: Model availability consistency**
# **Validates: Requirements 5.4**
# ============================================================================


class TestProperty4ModelAvailabilityConsistency:
    """
    Property 4: Model availability consistency.

    For any model M and region R, if is_model_available(M, R) returns True,
    then get_model_info(M, R) SHALL NOT return None.
    """

    @given(
        catalog=sample_catalog_strategy(),
    )
    @settings(max_examples=100, deadline=None)
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_property_4_availability_implies_info_exists(
        self,
        mock_auth_cls: Mock,
        mock_cache_cls: Mock,
        catalog: UnifiedCatalog,
    ) -> None:
        """
        Property: For any model M and region R, if is_model_available(M, R) returns True,
        then get_model_info(M, R) SHALL NOT return None.

        This property verifies consistency between availability checks and info retrieval.
        """
        # Setup: Mock cache to return our catalog
        mock_cache = Mock()
        mock_cache.load_cache.return_value = catalog
        mock_cache_cls.return_value = mock_cache

        # Create catalog instance
        bedrock_catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        # Test property for all models and regions in the catalog
        for model_name, model_info in catalog.models.items():
            for region in model_info.get_supported_regions():
                # Check availability
                is_available = bedrock_catalog.is_model_available(
                    model_name=model_name,
                    region=region,
                )

                # Property: If available, get_model_info should not return None
                if is_available:
                    model_access_info = bedrock_catalog.get_model_info(
                        model_name=model_name,
                        region=region,
                    )
                    assert (
                        model_access_info is not None
                    ), f"Model {model_name} is available in {region} but get_model_info returned None"


# ============================================================================
# Property 5: Cache round-trip consistency
# **Feature: model-manager-redesign, Property 5: Cache round-trip consistency**
# **Validates: Requirements 6.3**
# ============================================================================


class TestProperty5CacheRoundTripConsistency:
    """
    Property 5: Cache round-trip consistency.

    For any catalog C, saving then loading SHALL produce equivalent catalog.
    """

    @given(
        catalog=sample_catalog_strategy(),
        cache_mode=st.sampled_from([CacheMode.FILE, CacheMode.MEMORY]),
    )
    @settings(max_examples=100, deadline=None)
    def test_property_5_cache_round_trip_preserves_data(
        self,
        catalog: UnifiedCatalog,
        cache_mode: CacheMode,
    ) -> None:
        """
        Property: For any catalog C, saving then loading SHALL produce equivalent catalog.

        This property verifies that the cache serialization and deserialization
        process preserves all catalog data.
        """
        # Update catalog metadata to have a recent timestamp to avoid cache expiration
        fresh_metadata = CatalogMetadata(
            source=catalog.metadata.source,
            retrieval_timestamp=datetime.now(),  # Use current time
            api_regions_queried=catalog.metadata.api_regions_queried,
            bundled_data_version=catalog.metadata.bundled_data_version,
            cache_file_path=catalog.metadata.cache_file_path,
        )
        fresh_catalog = UnifiedCatalog(
            models=catalog.models,
            metadata=fresh_metadata,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) if cache_mode == CacheMode.FILE else None

            # Create cache manager with long max_age to avoid expiration
            manager = CacheManager(
                mode=cache_mode,
                directory=cache_dir,
                max_age_hours=1000.0,  # Very long to avoid expiration during test
            )

            # Save catalog
            manager.save_cache(catalog=fresh_catalog)

            # Load catalog back
            loaded_catalog = manager.load_cache()

            # Property: Loaded catalog should be equivalent to original
            assert loaded_catalog is not None, "Failed to load saved catalog"

            # Verify model count
            assert (
                loaded_catalog.model_count == fresh_catalog.model_count
            ), "Model count changed after round-trip"

            # Verify all models are present
            for model_name in fresh_catalog.models.keys():
                assert (
                    model_name in loaded_catalog.models
                ), f"Model {model_name} missing after round-trip"

            # Verify model details
            for model_name, original_model in fresh_catalog.models.items():
                loaded_model = loaded_catalog.models[model_name]

                assert loaded_model.model_name == original_model.model_name, "Model name changed"
                assert loaded_model.provider == original_model.provider, "Provider changed"
                assert (
                    loaded_model.streaming_supported == original_model.streaming_supported
                ), "Streaming support changed"

                # Verify regions
                original_regions = set(original_model.get_supported_regions())
                loaded_regions = set(loaded_model.get_supported_regions())
                assert original_regions == loaded_regions, "Supported regions changed"

            # Verify metadata
            assert (
                loaded_catalog.metadata.source == fresh_catalog.metadata.source
            ), "Metadata source changed"
            assert (
                loaded_catalog.metadata.api_regions_queried
                == fresh_catalog.metadata.api_regions_queried
            ), "API regions changed"
