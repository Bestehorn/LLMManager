"""
Tests for CacheManager class.

This module tests the cache management functionality including FILE, MEMORY,
and NONE modes, cache validation, and cache loading/saving.
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from bestehorn_llmmanager.bedrock.catalog.cache_manager import CacheManager
from bestehorn_llmmanager.bedrock.models.catalog_constants import CatalogCacheFields
from bestehorn_llmmanager.bedrock.models.catalog_structures import (
    CacheMode,
    CatalogMetadata,
    CatalogSource,
    UnifiedCatalog,
)


@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for cache testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_catalog():
    """Create a sample UnifiedCatalog for testing."""
    metadata = CatalogMetadata(
        source=CatalogSource.API,
        retrieval_timestamp=datetime.now(),
        api_regions_queried=["us-east-1", "us-west-2"],
        bundled_data_version=None,
        cache_file_path=None,
    )
    return UnifiedCatalog(models={}, metadata=metadata)


class TestCacheManagerInit:
    """Tests for CacheManager initialization."""

    def test_init_file_mode_with_directory(self, temp_cache_dir):
        """Test initialization in FILE mode with custom directory."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        assert manager.mode == CacheMode.FILE
        assert manager.cache_file_path == temp_cache_dir / "bedrock_catalog.json"

    def test_init_file_mode_default_directory(self):
        """Test initialization in FILE mode with default directory."""
        manager = CacheManager(mode=CacheMode.FILE, max_age_hours=24.0)

        assert manager.mode == CacheMode.FILE
        assert manager.cache_file_path is not None
        assert manager.cache_file_path.name == "bedrock_catalog.json"

    def test_init_memory_mode(self):
        """Test initialization in MEMORY mode."""
        manager = CacheManager(mode=CacheMode.MEMORY, max_age_hours=24.0)

        assert manager.mode == CacheMode.MEMORY
        assert manager.cache_file_path is None

    def test_init_none_mode(self):
        """Test initialization in NONE mode."""
        manager = CacheManager(mode=CacheMode.NONE, max_age_hours=24.0)

        assert manager.mode == CacheMode.NONE
        assert manager.cache_file_path is None

    def test_init_invalid_max_age(self):
        """Test initialization with invalid max_age_hours."""
        with pytest.raises(ValueError, match="Invalid cache_max_age_hours"):
            CacheManager(mode=CacheMode.FILE, max_age_hours=-1.0)

        with pytest.raises(ValueError, match="Invalid cache_max_age_hours"):
            CacheManager(mode=CacheMode.FILE, max_age_hours=0.0)


class TestCacheManagerLoadCache:
    """Tests for load_cache() method."""

    def test_load_cache_none_mode(self):
        """Test load_cache returns None in NONE mode."""
        manager = CacheManager(mode=CacheMode.NONE, max_age_hours=24.0)
        result = manager.load_cache()

        assert result is None

    def test_load_cache_memory_mode_empty(self):
        """Test load_cache returns None when memory cache is empty."""
        manager = CacheManager(mode=CacheMode.MEMORY, max_age_hours=24.0)
        result = manager.load_cache()

        assert result is None

    def test_load_cache_memory_mode_with_data(self, sample_catalog):
        """Test load_cache returns data from memory cache."""
        manager = CacheManager(mode=CacheMode.MEMORY, max_age_hours=24.0)
        manager.save_cache(catalog=sample_catalog)

        result = manager.load_cache()

        assert result is not None
        assert result.model_count == sample_catalog.model_count

    def test_load_cache_file_mode_no_file(self, temp_cache_dir):
        """Test load_cache returns None when cache file doesn't exist."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Clean up fallback location if it exists
        fallback_path = manager._cache_locations[1]
        if fallback_path.exists():
            fallback_path.unlink()

        result = manager.load_cache()

        assert result is None

    def test_load_cache_file_mode_valid_cache(self, temp_cache_dir, sample_catalog):
        """Test load_cache successfully loads valid cache file."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Save catalog first
        manager.save_cache(catalog=sample_catalog)

        # Load it back
        result = manager.load_cache()

        assert result is not None
        assert result.model_count == sample_catalog.model_count

    def test_load_cache_file_mode_expired_cache(self, temp_cache_dir, sample_catalog):
        """Test load_cache returns None for expired cache."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=1.0)

        # Clean up fallback location if it exists
        fallback_path = manager._cache_locations[1]
        if fallback_path.exists():
            fallback_path.unlink()

        # Create an old catalog
        old_metadata = CatalogMetadata(
            source=CatalogSource.API,
            retrieval_timestamp=datetime.now() - timedelta(hours=2),
            api_regions_queried=["us-east-1"],
        )
        old_catalog = UnifiedCatalog(models={}, metadata=old_metadata)

        # Save it
        manager.save_cache(catalog=old_catalog)

        # Try to load - should return None because it's expired
        result = manager.load_cache()

        assert result is None

    def test_load_cache_file_mode_invalid_json(self, temp_cache_dir):
        """Test load_cache returns None for invalid JSON."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Clean up fallback location if it exists
        fallback_path = manager._cache_locations[1]
        if fallback_path.exists():
            fallback_path.unlink()

        # Write invalid JSON to cache file
        cache_file = temp_cache_dir / "bedrock_catalog.json"
        cache_file.write_text("{ invalid json }", encoding="utf-8")

        result = manager.load_cache()

        assert result is None

    def test_load_cache_file_mode_invalid_structure(self, temp_cache_dir):
        """Test load_cache returns None for invalid cache structure."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Clean up fallback location if it exists
        fallback_path = manager._cache_locations[1]
        if fallback_path.exists():
            fallback_path.unlink()

        # Write valid JSON but invalid structure
        cache_file = temp_cache_dir / "bedrock_catalog.json"
        cache_file.write_text('{"invalid": "structure"}', encoding="utf-8")

        result = manager.load_cache()

        assert result is None

    def test_load_cache_file_mode_version_mismatch(self, temp_cache_dir, sample_catalog):
        """Test load_cache returns None for version mismatch."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Mock version during save
        with patch("bestehorn_llmmanager._version.__version__", "2.0.0"):
            # Save catalog with version 2.0.0
            manager.save_cache(catalog=sample_catalog)

        # Mock different version during load
        with patch("bestehorn_llmmanager._version.__version__", "3.0.0"):
            # Try to load - should return None because major version changed
            result = manager.load_cache()

            assert result is None


class TestCacheManagerSaveCache:
    """Tests for save_cache() method."""

    def test_save_cache_none_mode(self, sample_catalog):
        """Test save_cache does nothing in NONE mode."""
        manager = CacheManager(mode=CacheMode.NONE, max_age_hours=24.0)
        manager.save_cache(catalog=sample_catalog)

        # Should not raise any errors

    def test_save_cache_memory_mode(self, sample_catalog):
        """Test save_cache stores in memory."""
        manager = CacheManager(mode=CacheMode.MEMORY, max_age_hours=24.0)
        manager.save_cache(catalog=sample_catalog)

        # Verify it's stored
        result = manager.load_cache()
        assert result is not None
        assert result.model_count == sample_catalog.model_count

    def test_save_cache_file_mode_creates_directory(self, temp_cache_dir, sample_catalog):
        """Test save_cache creates cache directory if it doesn't exist."""
        cache_subdir = temp_cache_dir / "subdir"
        manager = CacheManager(mode=CacheMode.FILE, directory=cache_subdir, max_age_hours=24.0)

        manager.save_cache(catalog=sample_catalog)

        assert cache_subdir.exists()
        assert (cache_subdir / "bedrock_catalog.json").exists()

    def test_save_cache_file_mode_writes_json(self, temp_cache_dir, sample_catalog):
        """Test save_cache writes valid JSON."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        manager.save_cache(catalog=sample_catalog)

        cache_file = temp_cache_dir / "bedrock_catalog.json"
        assert cache_file.exists()

        # Verify it's valid JSON
        with open(cache_file, mode="r", encoding="utf-8") as f:
            data = json.load(f)

        assert CatalogCacheFields.MODELS in data
        assert CatalogCacheFields.METADATA in data

    def test_save_cache_file_mode_includes_version(self, temp_cache_dir, sample_catalog):
        """Test save_cache includes package version."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        with patch("bestehorn_llmmanager._version.__version__", "1.2.3"):
            manager.save_cache(catalog=sample_catalog)

        cache_file = temp_cache_dir / "bedrock_catalog.json"
        with open(cache_file, mode="r", encoding="utf-8") as f:
            data = json.load(f)

        assert data[CatalogCacheFields.PACKAGE_VERSION] == "1.2.3"


class TestCacheManagerIsCacheValid:
    """Tests for is_cache_valid() method."""

    def test_is_cache_valid_none_mode(self):
        """Test is_cache_valid returns False in NONE mode."""
        manager = CacheManager(mode=CacheMode.NONE, max_age_hours=24.0)
        assert manager.is_cache_valid() is False

    def test_is_cache_valid_memory_mode_empty(self):
        """Test is_cache_valid returns False when memory cache is empty."""
        manager = CacheManager(mode=CacheMode.MEMORY, max_age_hours=24.0)
        assert manager.is_cache_valid() is False

    def test_is_cache_valid_memory_mode_with_data(self, sample_catalog):
        """Test is_cache_valid returns True when memory cache has data."""
        manager = CacheManager(mode=CacheMode.MEMORY, max_age_hours=24.0)
        manager.save_cache(catalog=sample_catalog)

        assert manager.is_cache_valid() is True

    def test_is_cache_valid_file_mode_no_file(self, temp_cache_dir):
        """Test is_cache_valid returns False when file doesn't exist."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)
        assert manager.is_cache_valid() is False

    def test_is_cache_valid_file_mode_valid_cache(self, temp_cache_dir, sample_catalog):
        """Test is_cache_valid returns True for valid cache."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)
        manager.save_cache(catalog=sample_catalog)

        assert manager.is_cache_valid() is True

    def test_is_cache_valid_file_mode_expired(self, temp_cache_dir):
        """Test is_cache_valid returns False for expired cache."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=1.0)

        # Create expired catalog
        old_metadata = CatalogMetadata(
            source=CatalogSource.API,
            retrieval_timestamp=datetime.now() - timedelta(hours=2),
            api_regions_queried=["us-east-1"],
        )
        old_catalog = UnifiedCatalog(models={}, metadata=old_metadata)
        manager.save_cache(catalog=old_catalog)

        assert manager.is_cache_valid() is False


class TestCacheManagerClearCache:
    """Tests for clear_cache() method."""

    def test_clear_cache_none_mode(self):
        """Test clear_cache does nothing in NONE mode."""
        manager = CacheManager(mode=CacheMode.NONE, max_age_hours=24.0)
        manager.clear_cache()
        # Should not raise any errors

    def test_clear_cache_memory_mode(self, sample_catalog):
        """Test clear_cache clears memory cache."""
        manager = CacheManager(mode=CacheMode.MEMORY, max_age_hours=24.0)
        manager.save_cache(catalog=sample_catalog)

        assert manager.is_cache_valid() is True

        manager.clear_cache()

        assert manager.is_cache_valid() is False

    def test_clear_cache_file_mode(self, temp_cache_dir, sample_catalog):
        """Test clear_cache deletes cache file."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)
        manager.save_cache(catalog=sample_catalog)

        cache_file = temp_cache_dir / "bedrock_catalog.json"
        assert cache_file.exists()

        manager.clear_cache()

        assert not cache_file.exists()


class TestCacheManagerIsCacheFileValid:
    """Tests for _is_cache_file_valid() helper method."""

    def test_is_cache_file_valid_with_valid_cache(self, temp_cache_dir, sample_catalog):
        """Test validation with valid cache file."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Save a valid cache
        manager.save_cache(catalog=sample_catalog)
        cache_path = temp_cache_dir / "bedrock_catalog.json"

        # Validate it
        result = manager._is_cache_file_valid(cache_path=cache_path)

        assert result is True

    def test_is_cache_file_valid_with_expired_cache(self, temp_cache_dir):
        """Test validation with expired cache file."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=1.0)

        # Create an expired catalog
        old_metadata = CatalogMetadata(
            source=CatalogSource.API,
            retrieval_timestamp=datetime.now() - timedelta(hours=2),
            api_regions_queried=["us-east-1"],
        )
        old_catalog = UnifiedCatalog(models={}, metadata=old_metadata)

        # Save it
        manager.save_cache(catalog=old_catalog)
        cache_path = temp_cache_dir / "bedrock_catalog.json"

        # Validate - should return False because it's expired
        result = manager._is_cache_file_valid(cache_path=cache_path)

        assert result is False

    def test_is_cache_file_valid_with_invalid_json(self, temp_cache_dir):
        """Test validation with invalid JSON."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Write invalid JSON to cache file
        cache_path = temp_cache_dir / "bedrock_catalog.json"
        cache_path.write_text("{ invalid json }", encoding="utf-8")

        # Validate - should return False
        result = manager._is_cache_file_valid(cache_path=cache_path)

        assert result is False

    def test_is_cache_file_valid_with_version_mismatch(self, temp_cache_dir, sample_catalog):
        """Test validation with version mismatch."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Save with version 2.0.0
        with patch("bestehorn_llmmanager._version.__version__", "2.0.0"):
            manager.save_cache(catalog=sample_catalog)

        cache_path = temp_cache_dir / "bedrock_catalog.json"

        # Validate with version 3.0.0 (major version mismatch)
        with patch("bestehorn_llmmanager._version.__version__", "3.0.0"):
            result = manager._is_cache_file_valid(cache_path=cache_path)

            assert result is False

    def test_is_cache_file_valid_with_missing_file(self, temp_cache_dir):
        """Test validation with non-existent file."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Try to validate a file that doesn't exist
        cache_path = temp_cache_dir / "nonexistent.json"

        result = manager._is_cache_file_valid(cache_path=cache_path)

        assert result is False

    def test_is_cache_file_valid_with_invalid_structure(self, temp_cache_dir):
        """Test validation with invalid cache structure."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Write valid JSON but invalid structure
        cache_path = temp_cache_dir / "bedrock_catalog.json"
        cache_path.write_text('{"invalid": "structure"}', encoding="utf-8")

        result = manager._is_cache_file_valid(cache_path=cache_path)

        assert result is False

    def test_is_cache_file_valid_with_missing_metadata_fields(self, temp_cache_dir):
        """Test validation with missing required metadata fields."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Create cache data with missing metadata fields
        cache_data = {
            CatalogCacheFields.MODELS: {},
            CatalogCacheFields.METADATA: {
                # Missing RETRIEVAL_TIMESTAMP and API_REGIONS_QUERIED
                CatalogCacheFields.SOURCE: "api"
            },
        }

        cache_path = temp_cache_dir / "bedrock_catalog.json"
        with open(cache_path, mode="w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        result = manager._is_cache_file_valid(cache_path=cache_path)

        assert result is False

    def test_is_cache_file_valid_with_malformed_timestamp(self, temp_cache_dir):
        """Test validation with malformed timestamp."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Create cache data with invalid timestamp format
        cache_data = {
            CatalogCacheFields.MODELS: {},
            CatalogCacheFields.METADATA: {
                CatalogCacheFields.SOURCE: "api",
                CatalogCacheFields.RETRIEVAL_TIMESTAMP: "not-a-valid-timestamp",
                CatalogCacheFields.API_REGIONS_QUERIED: ["us-east-1"],
            },
            CatalogCacheFields.PACKAGE_VERSION: "1.0.0",
        }

        cache_path = temp_cache_dir / "bedrock_catalog.json"
        with open(cache_path, mode="w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        result = manager._is_cache_file_valid(cache_path=cache_path)

        assert result is False

    def test_is_cache_file_valid_with_missing_version(self, temp_cache_dir):
        """Test validation with missing package version."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Create cache data without package version
        cache_data = {
            CatalogCacheFields.MODELS: {},
            CatalogCacheFields.METADATA: {
                CatalogCacheFields.SOURCE: "api",
                CatalogCacheFields.RETRIEVAL_TIMESTAMP: datetime.now().isoformat(),
                CatalogCacheFields.API_REGIONS_QUERIED: ["us-east-1"],
            },
            # No PACKAGE_VERSION field
        }

        cache_path = temp_cache_dir / "bedrock_catalog.json"
        with open(cache_path, mode="w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        result = manager._is_cache_file_valid(cache_path=cache_path)

        # Should return False because old cache format without version is invalid
        assert result is False

    def test_is_cache_file_valid_with_compatible_minor_version(
        self, temp_cache_dir, sample_catalog
    ):
        """Test validation with compatible minor version difference."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Save with version 2.1.0
        with patch("bestehorn_llmmanager._version.__version__", "2.1.0"):
            manager.save_cache(catalog=sample_catalog)

        cache_path = temp_cache_dir / "bedrock_catalog.json"

        # Validate with version 2.2.0 (same major.minor, different patch)
        with patch("bestehorn_llmmanager._version.__version__", "2.1.5"):
            result = manager._is_cache_file_valid(cache_path=cache_path)

            # Should be valid because major.minor versions match (2.1)
            assert result is True

    def test_is_cache_file_valid_with_read_permission_error(self, temp_cache_dir):
        """Test validation handles read permission errors gracefully."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        cache_path = temp_cache_dir / "bedrock_catalog.json"
        cache_path.write_text('{"test": "data"}', encoding="utf-8")

        # Mock open to raise PermissionError
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            result = manager._is_cache_file_valid(cache_path=cache_path)

            assert result is False


class TestCacheManagerMultiLocationRead:
    """Tests for multi-location cache read scenarios."""

    def test_cache_exists_in_primary_only(self, temp_cache_dir, sample_catalog):
        """Test cache exists in primary location only (fallback not attempted)."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Save to primary location
        manager.save_cache(catalog=sample_catalog)

        # Load cache
        result = manager.load_cache()

        # Verify it loaded successfully
        assert result is not None
        assert result.model_count == sample_catalog.model_count

    def test_cache_exists_in_fallback_only(self, temp_cache_dir, sample_catalog):
        """Test cache exists in fallback location only (primary fails, fallback succeeds)."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Get fallback location
        fallback_path = manager._cache_locations[1]

        # Create fallback directory and save cache there
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        cache_data = sample_catalog.to_dict()

        # Mock version to ensure compatibility
        with patch("bestehorn_llmmanager._version.__version__", "1.0.0"):
            cache_data[CatalogCacheFields.PACKAGE_VERSION] = "1.0.0"

            with open(fallback_path, mode="w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)

            # Load cache (primary doesn't exist, should load from fallback)
            result = manager.load_cache()

            # Verify it loaded from fallback
            assert result is not None
            assert result.model_count == sample_catalog.model_count

    def test_cache_exists_in_both_locations(self, temp_cache_dir, sample_catalog):
        """Test cache exists in both locations (primary wins, fallback not attempted)."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Save to primary location
        manager.save_cache(catalog=sample_catalog)

        # Create different catalog for fallback
        fallback_metadata = CatalogMetadata(
            source=CatalogSource.BUNDLED,
            retrieval_timestamp=datetime.now(),
            api_regions_queried=["eu-west-1"],
        )
        fallback_catalog = UnifiedCatalog(models={}, metadata=fallback_metadata)

        # Save to fallback location
        fallback_path = manager._cache_locations[1]
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        cache_data = fallback_catalog.to_dict()
        cache_data[CatalogCacheFields.PACKAGE_VERSION] = "1.0.0"

        with open(fallback_path, mode="w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=2)

        # Load cache
        result = manager.load_cache()

        # Verify it loaded from primary (not fallback)
        assert result is not None
        assert result.metadata.source == CatalogSource.API  # From primary
        assert "us-east-1" in result.metadata.api_regions_queried  # From primary

    def test_no_cache_exists_in_any_location(self, temp_cache_dir):
        """Test no cache exists in any location (returns None)."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Load cache (no files exist)
        result = manager.load_cache()

        # Verify None is returned
        assert result is None

    def test_invalid_cache_in_primary_valid_in_fallback(self, temp_cache_dir, sample_catalog):
        """Test invalid cache in primary, valid in fallback (fallback succeeds)."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Write invalid JSON to primary location
        primary_path = manager._cache_locations[0]
        primary_path.parent.mkdir(parents=True, exist_ok=True)
        primary_path.write_text("{ invalid json }", encoding="utf-8")

        # Write valid cache to fallback location
        fallback_path = manager._cache_locations[1]
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        cache_data = sample_catalog.to_dict()

        # Mock version to ensure compatibility
        with patch("bestehorn_llmmanager._version.__version__", "1.0.0"):
            cache_data[CatalogCacheFields.PACKAGE_VERSION] = "1.0.0"

            with open(fallback_path, mode="w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)

            # Load cache
            result = manager.load_cache()

            # Verify it loaded from fallback
            assert result is not None
            assert result.model_count == sample_catalog.model_count


class TestCacheManagerMultiLocationWrite:
    """Tests for multi-location cache write scenarios."""

    def test_primary_location_writable(self, temp_cache_dir, sample_catalog, caplog):
        """Test primary location writable (fallback not attempted, INFO log)."""
        import logging

        caplog.set_level(logging.INFO)

        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Clean up fallback location if it exists from previous tests
        fallback_path = manager._cache_locations[1]
        if fallback_path.exists():
            fallback_path.unlink()

        # Save cache
        manager.save_cache(catalog=sample_catalog)

        # Verify cache was written to primary location
        primary_path = manager._cache_locations[0]
        assert primary_path.exists()

        # Verify INFO log for primary success
        assert any(
            "Successfully saved catalog to cache" in record.message for record in caplog.records
        )

        # Verify fallback was not attempted (should not exist after this test)
        assert not fallback_path.exists()

    def test_primary_readonly_fallback_succeeds(self, temp_cache_dir, sample_catalog, caplog):
        """Test primary location read-only, fallback succeeds (WARNING log for fallback)."""
        import logging

        caplog.set_level(logging.WARNING)

        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Mock primary location to raise PermissionError
        primary_path = manager._cache_locations[0]

        original_open = open

        def mock_open_func(path, *args, **kwargs):
            if str(path) == str(primary_path):
                raise PermissionError("Read-only filesystem")
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_func):
            # Save cache
            manager.save_cache(catalog=sample_catalog)

        # Verify fallback was written
        fallback_path = manager._cache_locations[1]
        assert fallback_path.exists()

        # Verify WARNING logs
        assert any("Failed to write cache" in record.message for record in caplog.records)
        assert any("alternative location" in record.message for record in caplog.records)

    def test_both_locations_readonly(self, temp_cache_dir, sample_catalog, caplog):
        """Test both locations read-only (all writes fail, WARNING log)."""
        import logging

        caplog.set_level(logging.WARNING)

        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Mock all locations to raise PermissionError
        with patch("builtins.open", side_effect=PermissionError("Read-only filesystem")):
            # Save cache - should not raise exception
            manager.save_cache(catalog=sample_catalog)

        # Verify WARNING log for all writes failed
        assert any("could not be written to disk" in record.message for record in caplog.records)

    def test_directory_creation_succeeds_at_primary(self, temp_cache_dir, sample_catalog):
        """Test directory creation succeeds at primary."""
        # Use a subdirectory that doesn't exist
        cache_subdir = temp_cache_dir / "subdir" / "nested"
        manager = CacheManager(mode=CacheMode.FILE, directory=cache_subdir, max_age_hours=24.0)

        # Save cache
        manager.save_cache(catalog=sample_catalog)

        # Verify directory was created
        assert cache_subdir.exists()

        # Verify cache file was written
        primary_path = manager._cache_locations[0]
        assert primary_path.exists()

    def test_directory_creation_fails_primary_succeeds_fallback(
        self, temp_cache_dir, sample_catalog, caplog
    ):
        """Test directory creation fails at primary, succeeds at fallback."""
        import logging

        caplog.set_level(logging.WARNING)

        # Use a non-writable path for primary (simulating Lambda HOME directory)
        # On Windows, we can't easily create a truly read-only directory in tests
        # So we'll just verify the fallback mechanism works when primary fails
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Mock open to fail for primary location only
        primary_path = manager._cache_locations[0]
        original_open = open

        def mock_open_func(path, *args, **kwargs):
            if str(path) == str(primary_path):
                raise PermissionError("Cannot write to primary location")
            return original_open(path, *args, **kwargs)

        with patch("builtins.open", side_effect=mock_open_func):
            # Save cache
            manager.save_cache(catalog=sample_catalog)

        # Verify fallback was written
        fallback_path = manager._cache_locations[1]
        assert fallback_path.exists()

        # Verify WARNING logs indicate fallback was used
        log_messages = [record.message for record in caplog.records]
        assert any("Failed to write cache" in msg for msg in log_messages) or any(
            "alternative location" in msg for msg in log_messages
        )

    def test_serialization_error_handling(self, temp_cache_dir, caplog):
        """Test serialization error handling (TypeError, ValueError)."""
        import logging

        caplog.set_level(logging.WARNING)

        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Create a catalog that will fail serialization
        metadata = CatalogMetadata(
            source=CatalogSource.API,
            retrieval_timestamp=datetime.now(),
            api_regions_queried=["us-east-1"],
        )
        catalog = UnifiedCatalog(models={}, metadata=metadata)

        # Mock to_dict to raise TypeError
        with patch.object(UnifiedCatalog, "to_dict", side_effect=TypeError("Cannot serialize")):
            # Save cache - should not raise exception
            manager.save_cache(catalog=catalog)

        # Verify WARNING log for serialization error
        assert any("Failed to serialize" in record.message for record in caplog.records)

    def test_no_cache_error_exceptions_raised(self, temp_cache_dir, sample_catalog):
        """Verify no CacheError exceptions are raised in any scenario."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

        # Test 1: Normal save - should not raise
        try:
            manager.save_cache(catalog=sample_catalog)
        except Exception as e:
            pytest.fail(f"save_cache raised unexpected exception: {e}")

        # Test 2: Permission error - should not raise
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            try:
                manager.save_cache(catalog=sample_catalog)
            except Exception as e:
                pytest.fail(f"save_cache raised unexpected exception on PermissionError: {e}")

        # Test 3: Serialization error - should not raise
        with patch.object(UnifiedCatalog, "to_dict", side_effect=TypeError("Cannot serialize")):
            try:
                manager.save_cache(catalog=sample_catalog)
            except Exception as e:
                pytest.fail(f"save_cache raised unexpected exception on TypeError: {e}")
