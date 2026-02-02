"""
Unit tests for catalog_constants module.

Tests the CatalogFilePaths class methods for cache location management,
specifically the new fallback cache location functionality for Lambda environments.
"""

from pathlib import Path

from bestehorn_llmmanager.bedrock.models.catalog_constants import CatalogFilePaths


class TestCatalogFilePathsCacheLocations:
    """Test CatalogFilePaths cache location methods."""

    def test_get_fallback_cache_directory_returns_path(self) -> None:
        """Test that get_fallback_cache_directory returns a Path object."""
        result = CatalogFilePaths.get_fallback_cache_directory()
        assert isinstance(result, Path)

    def test_get_fallback_cache_directory_returns_tmp_location(self) -> None:
        """Test that get_fallback_cache_directory returns /tmp/bestehorn-llmmanager-cache/."""
        result = CatalogFilePaths.get_fallback_cache_directory()
        expected = Path("/tmp") / "bestehorn-llmmanager-cache"
        assert result == expected

    def test_get_fallback_cache_directory_starts_with_tmp(self) -> None:
        """Test that fallback cache directory starts with /tmp."""
        result = CatalogFilePaths.get_fallback_cache_directory()
        # On Unix systems, /tmp is absolute; on Windows it's relative
        # but the path should still start with /tmp
        assert str(result).startswith("/tmp") or str(result).startswith("\\tmp")

    def test_get_all_cache_locations_returns_list(self) -> None:
        """Test that get_all_cache_locations returns a list."""
        result = CatalogFilePaths.get_all_cache_locations()
        assert isinstance(result, list)

    def test_get_all_cache_locations_returns_two_locations(self) -> None:
        """Test that get_all_cache_locations returns exactly two locations."""
        result = CatalogFilePaths.get_all_cache_locations()
        assert len(result) == 2

    def test_get_all_cache_locations_contains_path_objects(self) -> None:
        """Test that get_all_cache_locations returns list of Path objects."""
        result = CatalogFilePaths.get_all_cache_locations()
        assert all(isinstance(path, Path) for path in result)

    def test_get_all_cache_locations_priority_order(self) -> None:
        """Test that get_all_cache_locations returns locations in correct priority order.

        Priority order should be:
        1. Primary (platform-specific default)
        2. Fallback (/tmp)
        """
        result = CatalogFilePaths.get_all_cache_locations()

        # First location should be primary (platform-specific)
        expected_primary = CatalogFilePaths.get_default_cache_directory()
        assert result[0] == expected_primary

        # Second location should be fallback (/tmp)
        expected_fallback = CatalogFilePaths.get_fallback_cache_directory()
        assert result[1] == expected_fallback

    def test_get_all_cache_locations_primary_is_default(self) -> None:
        """Test that first location in get_all_cache_locations is the default cache directory."""
        result = CatalogFilePaths.get_all_cache_locations()
        default_dir = CatalogFilePaths.get_default_cache_directory()
        assert result[0] == default_dir

    def test_get_all_cache_locations_fallback_is_tmp(self) -> None:
        """Test that second location in get_all_cache_locations is the /tmp fallback."""
        result = CatalogFilePaths.get_all_cache_locations()
        fallback_dir = CatalogFilePaths.get_fallback_cache_directory()
        assert result[1] == fallback_dir

    def test_fallback_location_different_from_primary(self) -> None:
        """Test that fallback location is different from primary location."""
        primary = CatalogFilePaths.get_default_cache_directory()
        fallback = CatalogFilePaths.get_fallback_cache_directory()
        assert primary != fallback

    def test_all_cache_locations_contain_valid_paths(self) -> None:
        """Test that all cache locations returned are valid Path objects.

        Note: On Windows, /tmp paths are not absolute, but they are still valid paths.
        The primary location should always be absolute.
        """
        result = CatalogFilePaths.get_all_cache_locations()
        # Primary location should be absolute
        assert result[0].is_absolute()
        # All should be Path objects
        assert all(isinstance(path, Path) for path in result)

    def test_fallback_cache_directory_consistent_across_calls(self) -> None:
        """Test that get_fallback_cache_directory returns consistent results."""
        result1 = CatalogFilePaths.get_fallback_cache_directory()
        result2 = CatalogFilePaths.get_fallback_cache_directory()
        assert result1 == result2

    def test_all_cache_locations_consistent_across_calls(self) -> None:
        """Test that get_all_cache_locations returns consistent results."""
        result1 = CatalogFilePaths.get_all_cache_locations()
        result2 = CatalogFilePaths.get_all_cache_locations()
        assert result1 == result2

    def test_fallback_cache_directory_name(self) -> None:
        """Test that fallback cache directory has the correct name."""
        result = CatalogFilePaths.get_fallback_cache_directory()
        assert result.name == "bestehorn-llmmanager-cache"

    def test_fallback_cache_directory_parent_is_tmp(self) -> None:
        """Test that fallback cache directory parent is /tmp."""
        result = CatalogFilePaths.get_fallback_cache_directory()
        assert result.parent == Path("/tmp")
