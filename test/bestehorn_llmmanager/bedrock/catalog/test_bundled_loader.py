"""
Tests for BundledDataLoader.

This module tests the bundled data loading functionality, including:
- Loading bundled catalog data
- Extracting metadata
- Error handling for missing/corrupt data
"""

import json
from pathlib import Path

from bestehorn_llmmanager.bedrock.catalog.bundled_loader import BundledDataLoader
from bestehorn_llmmanager.bedrock.models.catalog_structures import (
    CatalogMetadata,
    CatalogSource,
    UnifiedCatalog,
)


class TestBundledDataLoader:
    """Test suite for BundledDataLoader class."""

    def test_get_bundled_data_path_returns_path(self) -> None:
        """Test that get_bundled_data_path returns a valid Path object."""
        path = BundledDataLoader.get_bundled_data_path()

        assert isinstance(path, Path)
        assert str(path).endswith("bedrock_catalog_bundled.json")

    def test_load_bundled_catalog_returns_unified_catalog(self) -> None:
        """Test that load_bundled_catalog returns a UnifiedCatalog instance."""
        catalog = BundledDataLoader.load_bundled_catalog()

        assert isinstance(catalog, UnifiedCatalog)
        assert isinstance(catalog.metadata, CatalogMetadata)
        assert catalog.metadata.source == CatalogSource.BUNDLED

    def test_load_bundled_catalog_has_valid_structure(self) -> None:
        """Test that loaded catalog has valid structure."""
        catalog = BundledDataLoader.load_bundled_catalog()

        # Check that models is a dictionary
        assert isinstance(catalog.models, dict)

        # Check metadata fields
        assert catalog.metadata.source == CatalogSource.BUNDLED
        assert catalog.metadata.retrieval_timestamp is not None
        assert isinstance(catalog.metadata.api_regions_queried, list)

    def test_get_bundled_data_metadata_without_catalog(self) -> None:
        """Test getting metadata without providing a catalog."""
        metadata = BundledDataLoader.get_bundled_data_metadata()

        assert isinstance(metadata, dict)
        assert "source" in metadata
        assert "generation_timestamp" in metadata
        assert "version" in metadata
        assert "model_count" in metadata
        assert "regions" in metadata

    def test_get_bundled_data_metadata_with_catalog(self) -> None:
        """Test getting metadata with a provided catalog."""
        catalog = BundledDataLoader.load_bundled_catalog()
        metadata = BundledDataLoader.get_bundled_data_metadata(catalog=catalog)

        assert isinstance(metadata, dict)
        assert metadata["source"] == "bundled"
        assert metadata["model_count"] == catalog.model_count

    def test_bundled_data_file_exists(self) -> None:
        """Test that the bundled data file actually exists."""
        path = BundledDataLoader.get_bundled_data_path()
        assert path.exists(), f"Bundled data file not found at {path}"

    def test_bundled_data_is_valid_json(self) -> None:
        """Test that the bundled data file contains valid JSON."""
        path = BundledDataLoader.get_bundled_data_path()

        with open(file=path, mode="r", encoding="utf-8") as f:
            data = json.load(fp=f)

        assert isinstance(data, dict)
        assert "models" in data
        assert "metadata" in data

    def test_bundled_data_has_required_metadata_fields(self) -> None:
        """Test that bundled data has all required metadata fields."""
        path = BundledDataLoader.get_bundled_data_path()

        with open(file=path, mode="r", encoding="utf-8") as f:
            data = json.load(fp=f)

        metadata = data["metadata"]
        assert "source" in metadata
        assert "retrieval_timestamp" in metadata
        assert "api_regions_queried" in metadata

    def test_load_bundled_catalog_is_idempotent(self) -> None:
        """Test that loading bundled catalog multiple times returns consistent data."""
        catalog1 = BundledDataLoader.load_bundled_catalog()
        catalog2 = BundledDataLoader.load_bundled_catalog()

        assert catalog1.model_count == catalog2.model_count
        assert catalog1.metadata.source == catalog2.metadata.source

    def test_metadata_extraction_matches_catalog(self) -> None:
        """Test that extracted metadata matches the catalog's metadata."""
        catalog = BundledDataLoader.load_bundled_catalog()
        metadata = BundledDataLoader.get_bundled_data_metadata(catalog=catalog)

        assert metadata["model_count"] == catalog.model_count
        assert metadata["source"] == catalog.metadata.source.value
