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

        # Write invalid JSON to cache file
        cache_file = temp_cache_dir / "bedrock_catalog.json"
        cache_file.write_text("{ invalid json }", encoding="utf-8")

        result = manager.load_cache()

        assert result is None

    def test_load_cache_file_mode_invalid_structure(self, temp_cache_dir):
        """Test load_cache returns None for invalid cache structure."""
        manager = CacheManager(mode=CacheMode.FILE, directory=temp_cache_dir, max_age_hours=24.0)

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
