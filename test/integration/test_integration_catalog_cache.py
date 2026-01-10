"""
Integration tests for catalog cache persistence with real file system.

These tests validate cache file creation, loading, and expiration with real
file system operations and actual catalog data.

Requirements tested:
- 6.1: Single cache file with unified data
- 6.2: Cache file writing and reading
- 6.3: Cache validation and expiration
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from bestehorn_llmmanager.bedrock.catalog.api_fetcher import BedrockAPIFetcher
from bestehorn_llmmanager.bedrock.catalog.cache_manager import CacheManager
from bestehorn_llmmanager.bedrock.catalog.transformer import CatalogTransformer
from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import CacheError
from bestehorn_llmmanager.bedrock.models.catalog_structures import CacheMode


@pytest.fixture
def temp_cache_dir(tmp_path: Path) -> Path:
    """
    Create a temporary cache directory for testing.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to temporary cache directory
    """
    cache_dir = tmp_path / "test_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@pytest.fixture
def sample_catalog(integration_config: Any, auth_manager_with_profile: Any) -> Any:
    """
    Fetch a real catalog for testing.

    Args:
        integration_config: Integration test configuration
        auth_manager_with_profile: AuthManager configured with test profile

    Returns:
        UnifiedCatalog with real data
    """
    # Fetch real data with profile-configured AuthManager
    fetcher = BedrockAPIFetcher(
        auth_manager=auth_manager_with_profile,
        timeout=integration_config.timeout_seconds,
    )

    region = integration_config.get_primary_test_region()
    raw_data = fetcher.fetch_all_data(regions=[region])

    # Transform to catalog
    transformer = CatalogTransformer()
    catalog = transformer.transform_api_data(raw_data=raw_data)

    return catalog


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestCacheFileCreation:
    """Integration tests for cache file creation."""

    def test_cache_file_creation_file_mode(self, temp_cache_dir: Path, sample_catalog: Any) -> None:
        """
        Test cache file creation in FILE mode.

        Validates Requirement 6.1: Single cache file with unified data
        Validates Requirement 6.2: Cache file writing

        Args:
            temp_cache_dir: Temporary cache directory
            sample_catalog: Sample catalog data
        """
        # Create cache manager in FILE mode
        cache_manager = CacheManager(
            mode=CacheMode.FILE,
            directory=temp_cache_dir,
            max_age_hours=24.0,
        )

        # Save catalog to cache
        cache_manager.save_cache(catalog=sample_catalog)

        # Verify cache file was created
        cache_file = temp_cache_dir / "bedrock_catalog.json"
        assert cache_file.exists()
        assert cache_file.is_file()

        # Verify file is not empty
        assert cache_file.stat().st_size > 0

        # Verify file contains valid JSON
        with open(cache_file, mode="r", encoding="utf-8") as f:
            cache_data = json.load(f)

        # Verify structure
        assert isinstance(cache_data, dict)
        assert "models" in cache_data
        assert "metadata" in cache_data

    def test_cache_file_content_structure(self, temp_cache_dir: Path, sample_catalog: Any) -> None:
        """
        Test cache file content structure.

        Validates Requirement 6.1: Single cache file with unified data

        Args:
            temp_cache_dir: Temporary cache directory
            sample_catalog: Sample catalog data
        """
        # Create cache manager and save catalog
        cache_manager = CacheManager(
            mode=CacheMode.FILE,
            directory=temp_cache_dir,
            max_age_hours=24.0,
        )
        cache_manager.save_cache(catalog=sample_catalog)

        # Load and verify cache file content
        cache_file = temp_cache_dir / "bedrock_catalog.json"
        with open(cache_file, mode="r", encoding="utf-8") as f:
            cache_data = json.load(f)

        # Verify models section
        assert "models" in cache_data
        assert isinstance(cache_data["models"], dict)
        assert len(cache_data["models"]) > 0

        # Verify metadata section
        assert "metadata" in cache_data
        metadata = cache_data["metadata"]
        assert "source" in metadata
        assert "retrieval_timestamp" in metadata
        assert "api_regions_queried" in metadata

        # Verify package version is included
        assert "package_version" in cache_data

    def test_cache_directory_creation(self, tmp_path: Path, sample_catalog: Any) -> None:
        """
        Test automatic cache directory creation.

        Args:
            tmp_path: Pytest temporary directory
            sample_catalog: Sample catalog data
        """
        # Use non-existent directory
        cache_dir = tmp_path / "nested" / "cache" / "dir"
        assert not cache_dir.exists()

        # Create cache manager
        cache_manager = CacheManager(
            mode=CacheMode.FILE,
            directory=cache_dir,
            max_age_hours=24.0,
        )

        # Save catalog - should create directory
        cache_manager.save_cache(catalog=sample_catalog)

        # Verify directory was created
        assert cache_dir.exists()
        assert cache_dir.is_dir()

        # Verify cache file exists
        cache_file = cache_dir / "bedrock_catalog.json"
        assert cache_file.exists()


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestCacheLoading:
    """Integration tests for cache loading."""

    def test_cache_loading_file_mode(self, temp_cache_dir: Path, sample_catalog: Any) -> None:
        """
        Test loading catalog from cache file.

        Validates Requirement 6.2: Cache file reading

        Args:
            temp_cache_dir: Temporary cache directory
            sample_catalog: Sample catalog data
        """
        # Save catalog to cache
        cache_manager = CacheManager(
            mode=CacheMode.FILE,
            directory=temp_cache_dir,
            max_age_hours=24.0,
        )
        cache_manager.save_cache(catalog=sample_catalog)

        # Create new cache manager instance
        new_cache_manager = CacheManager(
            mode=CacheMode.FILE,
            directory=temp_cache_dir,
            max_age_hours=24.0,
        )

        # Load catalog from cache
        loaded_catalog = new_cache_manager.load_cache()

        # Verify catalog was loaded
        assert loaded_catalog is not None
        assert loaded_catalog.model_count == sample_catalog.model_count
        assert len(loaded_catalog.models) == len(sample_catalog.models)

    def test_cache_round_trip_consistency(self, temp_cache_dir: Path, sample_catalog: Any) -> None:
        """
        Test cache save/load round trip preserves data.

        Validates Requirement 6.3: Cache validation

        Args:
            temp_cache_dir: Temporary cache directory
            sample_catalog: Sample catalog data
        """
        # Save catalog
        cache_manager = CacheManager(
            mode=CacheMode.FILE,
            directory=temp_cache_dir,
            max_age_hours=24.0,
        )
        cache_manager.save_cache(catalog=sample_catalog)

        # Load catalog
        loaded_catalog = cache_manager.load_cache()

        # Verify data consistency
        assert loaded_catalog is not None
        assert loaded_catalog.model_count == sample_catalog.model_count

        # Verify metadata
        assert loaded_catalog.metadata.source == sample_catalog.metadata.source
        assert (
            loaded_catalog.metadata.retrieval_timestamp
            == sample_catalog.metadata.retrieval_timestamp
        )

        # Verify models
        for model_name in sample_catalog.models.keys():
            assert model_name in loaded_catalog.models
            original_model = sample_catalog.models[model_name]
            loaded_model = loaded_catalog.models[model_name]
            assert loaded_model.model_id == original_model.model_id
            assert loaded_model.provider == original_model.provider

    def test_cache_loading_with_missing_file(self, temp_cache_dir: Path) -> None:
        """
        Test cache loading when file doesn't exist.

        Args:
            temp_cache_dir: Temporary cache directory
        """
        # Create cache manager with non-existent cache
        cache_manager = CacheManager(
            mode=CacheMode.FILE,
            directory=temp_cache_dir,
            max_age_hours=24.0,
        )

        # Load cache - should return None
        loaded_catalog = cache_manager.load_cache()
        assert loaded_catalog is None

    def test_cache_loading_with_corrupted_file(self, temp_cache_dir: Path) -> None:
        """
        Test cache loading with corrupted JSON file.

        Args:
            temp_cache_dir: Temporary cache directory
        """
        # Create corrupted cache file
        cache_file = temp_cache_dir / "bedrock_catalog.json"
        with open(cache_file, mode="w", encoding="utf-8") as f:
            f.write("{ invalid json content }")

        # Create cache manager
        cache_manager = CacheManager(
            mode=CacheMode.FILE,
            directory=temp_cache_dir,
            max_age_hours=24.0,
        )

        # Load cache - should return None for corrupted file
        loaded_catalog = cache_manager.load_cache()
        assert loaded_catalog is None


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestCacheExpiration:
    """Integration tests for cache expiration."""

    def test_cache_expiration_by_age(self, temp_cache_dir: Path, sample_catalog: Any) -> None:
        """
        Test cache expiration based on age.

        Validates Requirement 6.3: Cache expiration

        Args:
            temp_cache_dir: Temporary cache directory
            sample_catalog: Sample catalog data
        """
        # Save catalog with very short max age
        cache_manager = CacheManager(
            mode=CacheMode.FILE,
            directory=temp_cache_dir,
            max_age_hours=0.0001,  # ~0.36 seconds
        )
        cache_manager.save_cache(catalog=sample_catalog)

        # Wait for cache to expire
        time.sleep(1)

        # Check cache validity - should be expired
        assert not cache_manager.is_cache_valid()

        # Load cache - should return None for expired cache
        loaded_catalog = cache_manager.load_cache()
        assert loaded_catalog is None

    def test_cache_validity_within_max_age(self, temp_cache_dir: Path, sample_catalog: Any) -> None:
        """
        Test cache remains valid within max age.

        Args:
            temp_cache_dir: Temporary cache directory
            sample_catalog: Sample catalog data
        """
        # Save catalog with long max age
        cache_manager = CacheManager(
            mode=CacheMode.FILE,
            directory=temp_cache_dir,
            max_age_hours=24.0,
        )
        cache_manager.save_cache(catalog=sample_catalog)

        # Check cache validity immediately - should be valid
        assert cache_manager.is_cache_valid()

        # Load cache - should succeed
        loaded_catalog = cache_manager.load_cache()
        assert loaded_catalog is not None

    def test_cache_expiration_with_manual_timestamp_modification(
        self, temp_cache_dir: Path, sample_catalog: Any
    ) -> None:
        """
        Test cache expiration by manually modifying timestamp.

        Args:
            temp_cache_dir: Temporary cache directory
            sample_catalog: Sample catalog data
        """
        # Save catalog
        cache_manager = CacheManager(
            mode=CacheMode.FILE,
            directory=temp_cache_dir,
            max_age_hours=1.0,
        )
        cache_manager.save_cache(catalog=sample_catalog)

        # Modify cache file timestamp to be old
        cache_file = temp_cache_dir / "bedrock_catalog.json"
        with open(cache_file, mode="r", encoding="utf-8") as f:
            cache_data = json.load(f)

        # Set timestamp to 2 hours ago
        old_timestamp = datetime.now() - timedelta(hours=2)
        cache_data["metadata"]["retrieval_timestamp"] = old_timestamp.isoformat()

        with open(cache_file, mode="w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        # Check cache validity - should be expired
        assert not cache_manager.is_cache_valid()


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestCacheMemoryMode:
    """Integration tests for MEMORY cache mode."""

    def test_memory_cache_save_and_load(self, sample_catalog: Any) -> None:
        """
        Test memory cache save and load operations.

        Args:
            sample_catalog: Sample catalog data
        """
        # Create cache manager in MEMORY mode
        cache_manager = CacheManager(
            mode=CacheMode.MEMORY,
            max_age_hours=24.0,
        )

        # Save catalog to memory
        cache_manager.save_cache(catalog=sample_catalog)

        # Load catalog from memory
        loaded_catalog = cache_manager.load_cache()

        # Verify catalog was loaded
        assert loaded_catalog is not None
        assert loaded_catalog.model_count == sample_catalog.model_count

    def test_memory_cache_no_file_creation(self, tmp_path: Path, sample_catalog: Any) -> None:
        """
        Test that MEMORY mode doesn't create files.

        Args:
            tmp_path: Pytest temporary directory
            sample_catalog: Sample catalog data
        """
        cache_dir = tmp_path / "memory_cache"

        # Create cache manager in MEMORY mode
        cache_manager = CacheManager(
            mode=CacheMode.MEMORY,
            directory=cache_dir,  # Should be ignored
            max_age_hours=24.0,
        )

        # Save catalog
        cache_manager.save_cache(catalog=sample_catalog)

        # Verify no cache directory or file was created
        assert not cache_dir.exists()

    def test_memory_cache_process_lifetime(self, sample_catalog: Any) -> None:
        """
        Test memory cache persists within same process.

        Args:
            sample_catalog: Sample catalog data
        """
        # Create cache manager and save catalog
        cache_manager = CacheManager(
            mode=CacheMode.MEMORY,
            max_age_hours=24.0,
        )
        cache_manager.save_cache(catalog=sample_catalog)

        # Load multiple times - should return same data
        loaded_1 = cache_manager.load_cache()
        loaded_2 = cache_manager.load_cache()

        assert loaded_1 is not None
        assert loaded_2 is not None
        assert loaded_1.model_count == loaded_2.model_count


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestCacheNoneMode:
    """Integration tests for NONE cache mode."""

    def test_none_mode_no_caching(self, tmp_path: Path, sample_catalog: Any) -> None:
        """
        Test that NONE mode doesn't cache anything.

        Args:
            tmp_path: Pytest temporary directory
            sample_catalog: Sample catalog data
        """
        cache_dir = tmp_path / "none_cache"

        # Create cache manager in NONE mode
        cache_manager = CacheManager(
            mode=CacheMode.NONE,
            directory=cache_dir,
            max_age_hours=24.0,
        )

        # Save catalog - should do nothing
        cache_manager.save_cache(catalog=sample_catalog)

        # Verify no files created
        assert not cache_dir.exists()

        # Load cache - should return None
        loaded_catalog = cache_manager.load_cache()
        assert loaded_catalog is None

    def test_none_mode_always_invalid(self, tmp_path: Path) -> None:
        """
        Test that NONE mode cache is always invalid.

        Args:
            tmp_path: Pytest temporary directory
        """
        # Create cache manager in NONE mode
        cache_manager = CacheManager(
            mode=CacheMode.NONE,
            directory=tmp_path,
            max_age_hours=24.0,
        )

        # Cache should always be invalid
        assert not cache_manager.is_cache_valid()


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestCacheErrorHandling:
    """Integration tests for cache error handling."""

    def test_cache_write_to_readonly_directory(self, tmp_path: Path, sample_catalog: Any) -> None:
        """
        Test cache write error handling with read-only directory.

        Note: This test may not work on all platforms (Windows permissions differ).

        Args:
            tmp_path: Pytest temporary directory
            sample_catalog: Sample catalog data
        """
        import os
        import stat
        import sys

        # Skip on Windows as chmod doesn't work the same way
        if sys.platform == "win32":
            pytest.skip("chmod read-only test not reliable on Windows")

        # Create cache directory
        cache_dir = tmp_path / "readonly_cache"
        cache_dir.mkdir()

        # Make directory read-only (Unix-like systems)
        try:
            os.chmod(cache_dir, stat.S_IRUSR | stat.S_IXUSR)

            # Create cache manager
            cache_manager = CacheManager(
                mode=CacheMode.FILE,
                directory=cache_dir,
                max_age_hours=24.0,
            )

            # Try to save cache - should raise CacheError
            with pytest.raises(CacheError):
                cache_manager.save_cache(catalog=sample_catalog)

        finally:
            # Restore write permissions for cleanup
            try:
                os.chmod(cache_dir, stat.S_IRWXU)
            except Exception:
                pass

    def test_cache_clear_operation(self, temp_cache_dir: Path, sample_catalog: Any) -> None:
        """
        Test cache clear operation.

        Args:
            temp_cache_dir: Temporary cache directory
            sample_catalog: Sample catalog data
        """
        # Save catalog
        cache_manager = CacheManager(
            mode=CacheMode.FILE,
            directory=temp_cache_dir,
            max_age_hours=24.0,
        )
        cache_manager.save_cache(catalog=sample_catalog)

        # Verify cache file exists
        cache_file = temp_cache_dir / "bedrock_catalog.json"
        assert cache_file.exists()

        # Clear cache
        cache_manager.clear_cache()

        # Verify cache file was deleted
        assert not cache_file.exists()

        # Verify cache is invalid
        assert not cache_manager.is_cache_valid()
