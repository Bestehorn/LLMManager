"""
Property-based tests for multi-location cache read functionality.

Feature: lambda-cache-fallback
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.catalog.cache_manager import CacheManager
from bestehorn_llmmanager.bedrock.models.catalog_constants import CatalogCacheFields
from bestehorn_llmmanager.bedrock.models.catalog_structures import CacheMode


# Strategy for generating valid catalog data
def valid_catalog_data_strategy():
    """Generate valid catalog data for testing."""
    timestamp = datetime.now().isoformat()

    return st.just(
        {
            CatalogCacheFields.MODELS: {},
            CatalogCacheFields.METADATA: {
                CatalogCacheFields.SOURCE: "api",
                CatalogCacheFields.RETRIEVAL_TIMESTAMP: timestamp,
                CatalogCacheFields.API_REGIONS_QUERIED: ["us-east-1"],
            },
            CatalogCacheFields.PACKAGE_VERSION: "1.0.0",
        }
    )


@settings(max_examples=100)
@given(st.integers(min_value=1, max_value=48))
def test_property_cache_read_failure_returns_none(max_age_hours):
    """
    Property 3: Cache Read Failure Returns None

    Feature: lambda-cache-fallback, Property 3: Cache Read Failure Returns None
    Validates: Requirements 2.5, 7.2

    For any cache manager configuration, if all cache read attempts fail
    (all locations are unavailable or invalid), the cache manager should
    return None to indicate no cache is available.
    """
    # Create cache manager with random max_age_hours
    cache_manager = CacheManager(mode=CacheMode.FILE, max_age_hours=float(max_age_hours))

    # Mock all locations to not exist
    with patch.object(Path, "exists", return_value=False):
        # Load cache
        result = cache_manager.load_cache()

        # Verify None is returned
        assert result is None


@settings(max_examples=100)
@given(st.integers(min_value=1, max_value=48))
def test_property_cache_manager_has_multiple_locations(max_age_hours):
    """
    Property: Cache Manager Initializes Multiple Locations

    Feature: lambda-cache-fallback, Property 1: Cache Write Location Priority
    Validates: Requirements 1.1, 4.2

    For any cache manager configuration, the cache manager should initialize
    with multiple cache locations in priority order (primary, fallback).
    """
    # Create cache manager with random max_age_hours
    cache_manager = CacheManager(mode=CacheMode.FILE, max_age_hours=float(max_age_hours))

    # Verify multiple locations are configured
    assert len(cache_manager._cache_locations) == 2

    # Verify primary location is first
    primary_path = cache_manager._cache_locations[0]
    assert "bestehorn-llmmanager" in str(primary_path)

    # Verify fallback location is second
    fallback_path = cache_manager._cache_locations[1]
    assert "/tmp" in str(fallback_path) or "\\tmp" in str(fallback_path)


@settings(max_examples=100)
@given(st.integers(min_value=1, max_value=48))
def test_property_cache_file_path_returns_primary(max_age_hours):
    """
    Property: Cache File Path Returns Primary Location

    Feature: lambda-cache-fallback
    Validates: Requirements 5.4 (backward compatibility)

    For any cache manager configuration, the cache_file_path property
    should return the primary cache location for backward compatibility.
    """
    # Create cache manager with random max_age_hours
    cache_manager = CacheManager(mode=CacheMode.FILE, max_age_hours=float(max_age_hours))

    # Get cache file path
    cache_file_path = cache_manager.cache_file_path

    # Verify it matches the first location
    assert cache_file_path == cache_manager._cache_locations[0]
