"""
Property-based tests for cache manager location initialization.

This module contains property-based tests using Hypothesis to verify
universal properties of cache location initialization in the CacheManager.

**Feature: lambda-cache-fallback**

Properties tested:
1. Cache Write Location Priority
"""

from pathlib import Path
from typing import Optional

from hypothesis import given, settings
from hypothesis import strategies as st

from bestehorn_llmmanager.bedrock.catalog.cache_manager import CacheManager
from bestehorn_llmmanager.bedrock.models.catalog_constants import CatalogFilePaths
from bestehorn_llmmanager.bedrock.models.catalog_structures import CacheMode

# ============================================================================
# Hypothesis Strategies
# ============================================================================


@st.composite
def cache_configuration_strategy(draw: st.DrawFn) -> tuple[CacheMode, Optional[Path], float]:
    """
    Generate random cache configurations for testing.

    Generates configurations with:
    - Different cache modes (FILE, MEMORY, NONE)
    - Optional custom directories
    - Various max_age_hours values

    Returns:
        Tuple of (mode, directory, max_age_hours)
    """
    # Generate cache mode
    mode = draw(st.sampled_from([CacheMode.FILE, CacheMode.MEMORY, CacheMode.NONE]))

    # Generate optional directory (only relevant for FILE mode)
    if mode == CacheMode.FILE:
        # 50% chance of custom directory, 50% chance of None (use default)
        use_custom_dir = draw(st.booleans())
        if use_custom_dir:
            # Generate a custom directory path
            dir_names = ["custom_cache", "my_cache", "test_cache", "app_cache"]
            dir_name = draw(st.sampled_from(dir_names))
            directory = Path("/tmp") / dir_name
        else:
            directory = None
    else:
        directory = None

    # Generate max_age_hours (positive float)
    max_age_hours = draw(st.floats(min_value=0.1, max_value=168.0))  # 0.1h to 1 week

    return mode, directory, max_age_hours


# ============================================================================
# Property 1: Cache Write Location Priority
# **Feature: lambda-cache-fallback, Property 1: Cache Write Location Priority**
# **Validates: Requirements 1.1, 1.2**
# ============================================================================


class TestProperty1CacheWriteLocationPriority:
    """
    Property 1: Cache Write Location Priority.

    For any cache manager configuration, when attempting to write cache data,
    the cache manager should try the primary cache location first, and only
    attempt the fallback location if the primary write fails.
    """

    @given(config=cache_configuration_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_1_primary_location_is_first_in_list(
        self, config: tuple[CacheMode, Optional[Path], float]
    ) -> None:
        """
        Property: For any cache configuration, primary location is first in cache locations list.

        This property verifies that when a CacheManager is initialized with FILE mode,
        the primary cache location (either user-specified or platform default) is
        always the first element in the _cache_locations list.
        """
        mode, directory, max_age_hours = config

        # Create cache manager
        cache_manager = CacheManager(mode=mode, directory=directory, max_age_hours=max_age_hours)

        # Property only applies to FILE mode
        if mode == CacheMode.FILE:
            # Verify _cache_locations exists and is a list
            assert hasattr(
                cache_manager, "_cache_locations"
            ), "CacheManager should have _cache_locations attribute"
            assert isinstance(
                cache_manager._cache_locations, list
            ), "_cache_locations should be a list"

            # Verify list has at least 2 elements (primary + fallback)
            assert (
                len(cache_manager._cache_locations) >= 2
            ), "FILE mode should have at least 2 cache locations"

            # Determine expected primary location
            if directory is not None:
                expected_primary = directory / CatalogFilePaths.CACHE_FILENAME
            else:
                expected_primary = (
                    CatalogFilePaths.get_default_cache_directory() / CatalogFilePaths.CACHE_FILENAME
                )

            # Property: Primary location is first in list
            actual_primary = cache_manager._cache_locations[0]
            assert (
                actual_primary == expected_primary
            ), f"Primary location should be first: expected {expected_primary}, got {actual_primary}"

        else:
            # For MEMORY and NONE modes, _cache_locations should be empty
            assert (
                cache_manager._cache_locations == []
            ), f"Non-FILE modes should have empty _cache_locations, got {cache_manager._cache_locations}"

    @given(config=cache_configuration_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_1_fallback_location_is_second_in_list(
        self, config: tuple[CacheMode, Optional[Path], float]
    ) -> None:
        """
        Property: For any cache configuration, fallback location is second in cache locations list.

        This property verifies that when a CacheManager is initialized with FILE mode,
        the fallback cache location (/tmp/bestehorn-llmmanager-cache/) is always
        the second element in the _cache_locations list.
        """
        mode, directory, max_age_hours = config

        # Create cache manager
        cache_manager = CacheManager(mode=mode, directory=directory, max_age_hours=max_age_hours)

        # Property only applies to FILE mode
        if mode == CacheMode.FILE:
            # Verify _cache_locations exists and has at least 2 elements
            assert hasattr(cache_manager, "_cache_locations"), "Should have _cache_locations"
            assert len(cache_manager._cache_locations) >= 2, "Should have at least 2 locations"

            # Determine expected fallback location
            expected_fallback = (
                CatalogFilePaths.get_fallback_cache_directory() / CatalogFilePaths.CACHE_FILENAME
            )

            # Property: Fallback location is second in list
            actual_fallback = cache_manager._cache_locations[1]
            assert (
                actual_fallback == expected_fallback
            ), f"Fallback location should be second: expected {expected_fallback}, got {actual_fallback}"

    @given(config=cache_configuration_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_1_cache_locations_list_has_exactly_two_elements(
        self, config: tuple[CacheMode, Optional[Path], float]
    ) -> None:
        """
        Property: For any FILE mode configuration, cache locations list has exactly 2 elements.

        This property verifies that the _cache_locations list contains exactly
        two elements: primary and fallback locations, no more, no less.
        """
        mode, directory, max_age_hours = config

        # Create cache manager
        cache_manager = CacheManager(mode=mode, directory=directory, max_age_hours=max_age_hours)

        # Property only applies to FILE mode
        if mode == CacheMode.FILE:
            # Property: Exactly 2 locations
            assert (
                len(cache_manager._cache_locations) == 2
            ), f"FILE mode should have exactly 2 cache locations, got {len(cache_manager._cache_locations)}"

            # Verify both are Path objects
            assert all(
                isinstance(loc, Path) for loc in cache_manager._cache_locations
            ), "All cache locations should be Path objects"

        else:
            # For MEMORY and NONE modes, should be empty
            assert (
                len(cache_manager._cache_locations) == 0
            ), f"Non-FILE modes should have 0 cache locations, got {len(cache_manager._cache_locations)}"

    @given(config=cache_configuration_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_1_primary_and_fallback_are_different(
        self, config: tuple[CacheMode, Optional[Path], float]
    ) -> None:
        """
        Property: For any FILE mode configuration, primary and fallback locations are different.

        This property verifies that the primary and fallback cache locations
        are distinct paths, ensuring fallback provides an alternative location.
        """
        mode, directory, max_age_hours = config

        # Create cache manager
        cache_manager = CacheManager(mode=mode, directory=directory, max_age_hours=max_age_hours)

        # Property only applies to FILE mode
        if mode == CacheMode.FILE:
            primary = cache_manager._cache_locations[0]
            fallback = cache_manager._cache_locations[1]

            # Property: Primary and fallback are different
            assert (
                primary != fallback
            ), f"Primary and fallback locations should be different: {primary} vs {fallback}"

    @given(
        mode=st.just(CacheMode.FILE),
        max_age_hours=st.floats(min_value=0.1, max_value=168.0),
    )
    @settings(max_examples=100, deadline=None)
    def test_property_1_default_directory_uses_platform_default(
        self, mode: CacheMode, max_age_hours: float
    ) -> None:
        """
        Property: When no directory is specified, primary location uses platform default.

        This property verifies that when directory=None, the CacheManager uses
        the platform-specific default cache directory as the primary location.
        """
        # Create cache manager with no custom directory
        cache_manager = CacheManager(mode=mode, directory=None, max_age_hours=max_age_hours)

        # Expected primary location (platform default)
        expected_primary = (
            CatalogFilePaths.get_default_cache_directory() / CatalogFilePaths.CACHE_FILENAME
        )

        # Property: Primary location is platform default
        actual_primary = cache_manager._cache_locations[0]
        assert (
            actual_primary == expected_primary
        ), f"Default primary location should be platform default: expected {expected_primary}, got {actual_primary}"

    @given(
        mode=st.just(CacheMode.FILE),
        max_age_hours=st.floats(min_value=0.1, max_value=168.0),
    )
    @settings(max_examples=100, deadline=None)
    def test_property_1_custom_directory_overrides_default(
        self, mode: CacheMode, max_age_hours: float
    ) -> None:
        """
        Property: When custom directory is specified, it becomes the primary location.

        This property verifies that when a custom directory is provided,
        it is used as the primary cache location instead of the platform default.
        """
        # Generate a custom directory
        custom_dir = Path("/tmp") / "custom_test_cache"

        # Create cache manager with custom directory
        cache_manager = CacheManager(mode=mode, directory=custom_dir, max_age_hours=max_age_hours)

        # Expected primary location (custom directory)
        expected_primary = custom_dir / CatalogFilePaths.CACHE_FILENAME

        # Property: Primary location is custom directory
        actual_primary = cache_manager._cache_locations[0]
        assert (
            actual_primary == expected_primary
        ), f"Custom primary location should be used: expected {expected_primary}, got {actual_primary}"

        # Property: Fallback is still /tmp
        expected_fallback = (
            CatalogFilePaths.get_fallback_cache_directory() / CatalogFilePaths.CACHE_FILENAME
        )
        actual_fallback = cache_manager._cache_locations[1]
        assert (
            actual_fallback == expected_fallback
        ), f"Fallback should always be /tmp: expected {expected_fallback}, got {actual_fallback}"

    @given(config=cache_configuration_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_1_cache_file_path_property_returns_primary_location(
        self, config: tuple[CacheMode, Optional[Path], float]
    ) -> None:
        """
        Property: cache_file_path property returns the primary location for FILE mode.

        This property verifies backward compatibility - the cache_file_path property
        should return the first (primary) location from _cache_locations.
        """
        mode, directory, max_age_hours = config

        # Create cache manager
        cache_manager = CacheManager(mode=mode, directory=directory, max_age_hours=max_age_hours)

        if mode == CacheMode.FILE:
            # Property: cache_file_path returns primary location
            expected = cache_manager._cache_locations[0]
            actual = cache_manager.cache_file_path

            assert (
                actual == expected
            ), f"cache_file_path should return primary location: expected {expected}, got {actual}"
        else:
            # For non-FILE modes, should return None
            assert (
                cache_manager.cache_file_path is None
            ), f"Non-FILE modes should return None for cache_file_path, got {cache_manager.cache_file_path}"

    @given(config=cache_configuration_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_1_fallback_location_is_always_tmp(
        self, config: tuple[CacheMode, Optional[Path], float]
    ) -> None:
        """
        Property: Fallback location is always /tmp regardless of primary location.

        This property verifies that the fallback location is consistently
        /tmp/bestehorn-llmmanager-cache/ regardless of what the primary location is.
        """
        mode, directory, max_age_hours = config

        # Create cache manager
        cache_manager = CacheManager(mode=mode, directory=directory, max_age_hours=max_age_hours)

        if mode == CacheMode.FILE:
            # Expected fallback is always /tmp
            expected_fallback = (
                CatalogFilePaths.get_fallback_cache_directory() / CatalogFilePaths.CACHE_FILENAME
            )

            # Property: Fallback is always /tmp
            actual_fallback = cache_manager._cache_locations[1]
            assert (
                actual_fallback == expected_fallback
            ), f"Fallback should always be /tmp: expected {expected_fallback}, got {actual_fallback}"

            # Verify fallback parent is /tmp
            assert actual_fallback.parent.parent == Path(
                "/tmp"
            ), f"Fallback parent should be under /tmp, got {actual_fallback.parent}"
