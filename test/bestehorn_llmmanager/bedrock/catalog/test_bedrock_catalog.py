"""
Tests for BedrockModelCatalog class.

This module tests the main BedrockModelCatalog functionality including:
- Initialization with different cache modes
- Initialization strategy (cache → API → bundled)
- Query methods (get_model_info, is_model_available, list_models)
- Error handling
- In-memory caching
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bestehorn_llmmanager.bedrock.catalog.bedrock_catalog import BedrockModelCatalog
from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
    CatalogUnavailableError,
)
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


@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for cache testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_catalog():
    """Create a sample UnifiedCatalog for testing."""
    from bestehorn_llmmanager.bedrock.models.access_method import ModelAccessInfo

    metadata = CatalogMetadata(
        source=CatalogSource.API,
        retrieval_timestamp=datetime.now(),
        api_regions_queried=["us-east-1", "us-west-2"],
        bundled_data_version=None,
        cache_file_path=None,
    )

    # Create sample model access info for regions
    region_access = {
        "us-east-1": ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        ),
        "us-west-2": ModelAccessInfo(
            region="us-west-2",
            has_direct_access=True,
            model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        ),
    }

    # Create sample model info
    model_info = UnifiedModelInfo(
        model_name="anthropic.claude-3-sonnet-20240229-v1:0",
        provider="Anthropic",
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        streaming_supported=True,
        input_modalities=["TEXT", "IMAGE"],
        output_modalities=["TEXT"],
        region_access=region_access,
    )

    return UnifiedCatalog(
        models={"anthropic.claude-3-sonnet-20240229-v1:0": model_info},
        metadata=metadata,
    )


class TestBedrockModelCatalogInit:
    """Tests for BedrockModelCatalog initialization."""

    def test_init_default_parameters(self):
        """Test initialization with default parameters."""
        with patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager"):
            catalog = BedrockModelCatalog()

            assert catalog.cache_mode == CacheMode.FILE
            assert not catalog.is_catalog_loaded

    def test_init_file_mode_with_custom_directory(self, temp_cache_dir):
        """Test initialization in FILE mode with custom directory."""
        with patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager"):
            catalog = BedrockModelCatalog(
                cache_mode=CacheMode.FILE,
                cache_directory=temp_cache_dir,
            )

            assert catalog.cache_mode == CacheMode.FILE
            assert catalog.cache_file_path == temp_cache_dir / "bedrock_catalog.json"

    def test_init_memory_mode(self):
        """Test initialization in MEMORY mode."""
        with patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager"):
            catalog = BedrockModelCatalog(cache_mode=CacheMode.MEMORY)

            assert catalog.cache_mode == CacheMode.MEMORY
            assert catalog.cache_file_path is None

    def test_init_none_mode(self):
        """Test initialization in NONE mode."""
        with patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager"):
            catalog = BedrockModelCatalog(cache_mode=CacheMode.NONE)

            assert catalog.cache_mode == CacheMode.NONE
            assert catalog.cache_file_path is None

    def test_init_with_auth_manager(self):
        """Test initialization with provided AuthManager."""
        mock_auth = Mock()
        catalog = BedrockModelCatalog(auth_manager=mock_auth)

        assert catalog._auth_manager is mock_auth

    def test_init_invalid_cache_mode(self):
        """Test initialization with invalid cache mode."""
        with pytest.raises(ValueError, match="Invalid cache_mode"):
            BedrockModelCatalog(cache_mode="invalid")

    def test_init_invalid_cache_max_age(self):
        """Test initialization with invalid cache_max_age_hours."""
        with pytest.raises(ValueError, match="Invalid cache_max_age_hours"):
            BedrockModelCatalog(cache_max_age_hours=-1.0)

        with pytest.raises(ValueError, match="Invalid cache_max_age_hours"):
            BedrockModelCatalog(cache_max_age_hours=0.0)

    def test_init_invalid_timeout(self):
        """Test initialization with invalid timeout."""
        with pytest.raises(ValueError, match="Invalid timeout"):
            BedrockModelCatalog(timeout=-1)

        with pytest.raises(ValueError, match="Invalid timeout"):
            BedrockModelCatalog(timeout=0)

    def test_init_invalid_max_workers(self):
        """Test initialization with invalid max_workers."""
        with pytest.raises(ValueError, match="Invalid max_workers"):
            BedrockModelCatalog(max_workers=-1)

        with pytest.raises(ValueError, match="Invalid max_workers"):
            BedrockModelCatalog(max_workers=0)


class TestBedrockModelCatalogInitializationStrategy:
    """Tests for the three-tier initialization strategy."""

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_strategy_cache_hit(self, mock_auth_cls, mock_cache_cls, sample_catalog):
        """Test initialization strategy: cache hit returns cached data."""
        # Setup mock cache manager to return catalog
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)
        result = catalog.ensure_catalog_available()

        assert result is sample_catalog
        assert catalog.is_catalog_loaded
        mock_cache.load_cache.assert_called_once()

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CatalogTransformer")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.BedrockAPIFetcher")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_strategy_cache_miss_api_success(
        self,
        mock_auth_cls,
        mock_cache_cls,
        mock_fetcher_cls,
        mock_transformer_cls,
        sample_catalog,
    ):
        """Test initialization strategy: cache miss, API fetch succeeds."""
        # Setup mock cache manager to return None (cache miss)
        mock_cache = Mock()
        mock_cache.load_cache.return_value = None
        mock_cache_cls.return_value = mock_cache

        # Setup mock API fetcher
        mock_fetcher = Mock()
        mock_raw_data = Mock()
        mock_fetcher.fetch_all_data.return_value = mock_raw_data
        mock_fetcher_cls.return_value = mock_fetcher

        # Setup mock transformer
        mock_transformer = Mock()
        mock_transformer.transform_api_data.return_value = sample_catalog
        mock_transformer_cls.return_value = mock_transformer

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)
        result = catalog.ensure_catalog_available()

        assert result is sample_catalog
        assert catalog.is_catalog_loaded
        mock_cache.load_cache.assert_called_once()
        mock_fetcher.fetch_all_data.assert_called_once()
        mock_transformer.transform_api_data.assert_called_once_with(raw_data=mock_raw_data)
        mock_cache.save_cache.assert_called_once_with(catalog=sample_catalog)

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.BundledDataLoader")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.BedrockAPIFetcher")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_strategy_cache_miss_api_fail_bundled_success(
        self,
        mock_auth_cls,
        mock_cache_cls,
        mock_fetcher_cls,
        mock_bundled_cls,
        sample_catalog,
    ):
        """Test initialization strategy: cache miss, API fails, bundled succeeds."""
        # Setup mock cache manager to return None (cache miss)
        mock_cache = Mock()
        mock_cache.load_cache.return_value = None
        mock_cache_cls.return_value = mock_cache

        # Setup mock API fetcher to fail
        mock_fetcher = Mock()
        mock_fetcher.fetch_all_data.side_effect = Exception("API error")
        mock_fetcher_cls.return_value = mock_fetcher

        # Setup mock bundled loader
        mock_bundled_cls.load_bundled_catalog.return_value = sample_catalog

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE, fallback_to_bundled=True)
        result = catalog.ensure_catalog_available()

        assert result is sample_catalog
        assert catalog.is_catalog_loaded
        mock_bundled_cls.load_bundled_catalog.assert_called_once()

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.BundledDataLoader")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.BedrockAPIFetcher")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_strategy_all_sources_fail(
        self,
        mock_auth_cls,
        mock_cache_cls,
        mock_fetcher_cls,
        mock_bundled_cls,
    ):
        """Test initialization strategy: all sources fail raises error."""
        # Setup mock cache manager to return None (cache miss)
        mock_cache = Mock()
        mock_cache.load_cache.return_value = None
        mock_cache_cls.return_value = mock_cache

        # Setup mock API fetcher to fail
        mock_fetcher = Mock()
        mock_fetcher.fetch_all_data.side_effect = Exception("API error")
        mock_fetcher_cls.return_value = mock_fetcher

        # Setup mock bundled loader to fail
        mock_bundled_cls.load_bundled_catalog.side_effect = Exception("Bundled error")

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE, fallback_to_bundled=True)

        with pytest.raises(CatalogUnavailableError):
            catalog.ensure_catalog_available()

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.BedrockAPIFetcher")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_strategy_bundled_disabled_api_fails(
        self,
        mock_auth_cls,
        mock_cache_cls,
        mock_fetcher_cls,
    ):
        """Test initialization strategy: bundled disabled, API fails."""
        # Setup mock cache manager to return None (cache miss)
        mock_cache = Mock()
        mock_cache.load_cache.return_value = None
        mock_cache_cls.return_value = mock_cache

        # Setup mock API fetcher to fail
        mock_fetcher = Mock()
        mock_fetcher.fetch_all_data.side_effect = Exception("API error")
        mock_fetcher_cls.return_value = mock_fetcher

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE, fallback_to_bundled=False)

        with pytest.raises(CatalogUnavailableError):
            catalog.ensure_catalog_available()

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CatalogTransformer")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.BedrockAPIFetcher")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_strategy_none_mode_skips_cache(
        self,
        mock_auth_cls,
        mock_fetcher_cls,
        mock_transformer_cls,
        sample_catalog,
    ):
        """Test initialization strategy: NONE mode skips cache."""
        # Setup mock API fetcher
        mock_fetcher = Mock()
        mock_raw_data = Mock()
        mock_fetcher.fetch_all_data.return_value = mock_raw_data
        mock_fetcher_cls.return_value = mock_fetcher

        # Setup mock transformer
        mock_transformer = Mock()
        mock_transformer.transform_api_data.return_value = sample_catalog
        mock_transformer_cls.return_value = mock_transformer

        catalog = BedrockModelCatalog(cache_mode=CacheMode.NONE)
        result = catalog.ensure_catalog_available()

        assert result is sample_catalog
        mock_fetcher.fetch_all_data.assert_called_once()

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CatalogTransformer")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.BedrockAPIFetcher")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_strategy_force_refresh_skips_cache(
        self,
        mock_auth_cls,
        mock_cache_cls,
        mock_fetcher_cls,
        mock_transformer_cls,
        sample_catalog,
    ):
        """Test initialization strategy: force_refresh skips cache."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        # Setup mock API fetcher
        mock_fetcher = Mock()
        mock_raw_data = Mock()
        mock_fetcher.fetch_all_data.return_value = mock_raw_data
        mock_fetcher_cls.return_value = mock_fetcher

        # Setup mock transformer
        mock_transformer = Mock()
        mock_transformer.transform_api_data.return_value = sample_catalog
        mock_transformer_cls.return_value = mock_transformer

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE, force_refresh=True)
        result = catalog.ensure_catalog_available()

        assert result is sample_catalog
        # Cache should not be loaded when force_refresh is True
        mock_cache.load_cache.assert_not_called()
        mock_fetcher.fetch_all_data.assert_called_once()


class TestBedrockModelCatalogInMemoryCaching:
    """Tests for in-memory catalog caching."""

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_in_memory_cache_reused(self, mock_auth_cls, mock_cache_cls, sample_catalog):
        """Test that in-memory cache is reused for subsequent queries."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        # First call loads from cache
        result1 = catalog.ensure_catalog_available()
        assert result1 is sample_catalog
        assert mock_cache.load_cache.call_count == 1

        # Second call uses in-memory cache
        result2 = catalog.ensure_catalog_available()
        assert result2 is sample_catalog
        # Cache should still only be called once
        assert mock_cache.load_cache.call_count == 1

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_clear_cache_clears_in_memory(self, mock_auth_cls, mock_cache_cls, sample_catalog):
        """Test that clear_cache clears in-memory cache."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        # Load catalog
        catalog.ensure_catalog_available()
        assert catalog.is_catalog_loaded

        # Clear cache
        catalog.clear_cache()
        assert not catalog.is_catalog_loaded
        mock_cache.clear_cache.assert_called_once()

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CatalogTransformer")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.BedrockAPIFetcher")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_refresh_catalog_bypasses_cache(
        self,
        mock_auth_cls,
        mock_cache_cls,
        mock_fetcher_cls,
        mock_transformer_cls,
        sample_catalog,
    ):
        """Test that refresh_catalog bypasses cache and fetches fresh data."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        # Setup mock API fetcher
        mock_fetcher = Mock()
        mock_raw_data = Mock()
        mock_fetcher.fetch_all_data.return_value = mock_raw_data
        mock_fetcher_cls.return_value = mock_fetcher

        # Setup mock transformer
        mock_transformer = Mock()
        mock_transformer.transform_api_data.return_value = sample_catalog
        mock_transformer_cls.return_value = mock_transformer

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        # Refresh should bypass cache
        result = catalog.refresh_catalog()

        assert result is sample_catalog
        mock_cache.load_cache.assert_not_called()
        mock_fetcher.fetch_all_data.assert_called_once()


class TestBedrockModelCatalogQueryMethods:
    """Tests for query methods."""

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_get_model_info_returns_access_info(
        self, mock_auth_cls, mock_cache_cls, sample_catalog
    ):
        """Test get_model_info returns ModelAccessInfo for available model."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        result = catalog.get_model_info(
            model_name="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1",
        )

        assert result is not None
        assert isinstance(result, ModelAccessInfo)

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_get_model_info_returns_none_for_unavailable_model(
        self, mock_auth_cls, mock_cache_cls, sample_catalog
    ):
        """Test get_model_info returns None for unavailable model."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        result = catalog.get_model_info(
            model_name="nonexistent.model",
            region="us-east-1",
        )

        assert result is None

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_get_model_info_returns_none_for_unavailable_region(
        self, mock_auth_cls, mock_cache_cls, sample_catalog
    ):
        """Test get_model_info returns None for unavailable region."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        result = catalog.get_model_info(
            model_name="anthropic.claude-3-sonnet-20240229-v1:0",
            region="eu-central-1",
        )

        assert result is None

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_get_model_info_without_region(self, mock_auth_cls, mock_cache_cls, sample_catalog):
        """Test get_model_info without region returns first available region."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        result = catalog.get_model_info(
            model_name="anthropic.claude-3-sonnet-20240229-v1:0",
        )

        assert result is not None
        assert isinstance(result, ModelAccessInfo)

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_is_model_available_returns_true(self, mock_auth_cls, mock_cache_cls, sample_catalog):
        """Test is_model_available returns True for available model."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        result = catalog.is_model_available(
            model_name="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1",
        )

        assert result is True

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_is_model_available_returns_false(self, mock_auth_cls, mock_cache_cls, sample_catalog):
        """Test is_model_available returns False for unavailable model."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        result = catalog.is_model_available(
            model_name="nonexistent.model",
            region="us-east-1",
        )

        assert result is False

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_list_models_no_filters(self, mock_auth_cls, mock_cache_cls, sample_catalog):
        """Test list_models without filters returns all models."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        result = catalog.list_models()

        assert len(result) == 1
        assert result[0].model_name == "anthropic.claude-3-sonnet-20240229-v1:0"

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_list_models_with_region_filter(self, mock_auth_cls, mock_cache_cls, sample_catalog):
        """Test list_models with region filter."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        result = catalog.list_models(region="us-east-1")

        assert len(result) == 1

        # Test with unavailable region
        result = catalog.list_models(region="eu-central-1")
        assert len(result) == 0

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_list_models_with_provider_filter(self, mock_auth_cls, mock_cache_cls, sample_catalog):
        """Test list_models with provider filter."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        result = catalog.list_models(provider="Anthropic")

        assert len(result) == 1

        # Test with different provider
        result = catalog.list_models(provider="Amazon")
        assert len(result) == 0

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_list_models_with_streaming_filter(self, mock_auth_cls, mock_cache_cls, sample_catalog):
        """Test list_models with streaming_only filter."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        result = catalog.list_models(streaming_only=True)

        assert len(result) == 1
        assert result[0].streaming_supported is True

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_get_catalog_metadata(self, mock_auth_cls, mock_cache_cls, sample_catalog):
        """Test get_catalog_metadata returns metadata."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        result = catalog.get_catalog_metadata()

        assert isinstance(result, CatalogMetadata)
        assert result.source == CatalogSource.API

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_get_model_access_info_backward_compatibility(
        self, mock_auth_cls, mock_cache_cls, sample_catalog
    ):
        """Test get_model_access_info provides backward compatibility."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        result = catalog.get_model_access_info(
            model_name="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1",
        )

        assert result is not None
        assert isinstance(result, ModelAccessInfo)


class TestBedrockModelCatalogErrorHandling:
    """Tests for error handling."""

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_query_before_catalog_loaded_triggers_load(
        self, mock_auth_cls, mock_cache_cls, sample_catalog
    ):
        """Test that querying before catalog is loaded triggers load."""
        # Setup mock cache manager
        mock_cache = Mock()
        mock_cache.load_cache.return_value = sample_catalog
        mock_cache_cls.return_value = mock_cache

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE)

        # Catalog not loaded yet
        assert not catalog.is_catalog_loaded

        # Query should trigger load
        result = catalog.get_model_info(
            model_name="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1",
        )

        assert result is not None
        assert catalog.is_catalog_loaded

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.BundledDataLoader")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.BedrockAPIFetcher")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_catalog_unavailable_error_message(
        self,
        mock_auth_cls,
        mock_cache_cls,
        mock_fetcher_cls,
        mock_bundled_cls,
    ):
        """Test that CatalogUnavailableError has informative message."""
        # Setup all sources to fail
        mock_cache = Mock()
        mock_cache.load_cache.return_value = None
        mock_cache_cls.return_value = mock_cache

        mock_fetcher = Mock()
        mock_fetcher.fetch_all_data.side_effect = Exception("API error")
        mock_fetcher_cls.return_value = mock_fetcher

        mock_bundled_cls.load_bundled_catalog.side_effect = Exception("Bundled error")

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE, fallback_to_bundled=True)

        with pytest.raises(CatalogUnavailableError) as exc_info:
            catalog.ensure_catalog_available()

        # Error message should mention all sources
        error_msg = str(exc_info.value)
        assert "cache" in error_msg.lower() or "api" in error_msg.lower()

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.BundledDataLoader")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CatalogTransformer")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.BedrockAPIFetcher")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.CacheManager")
    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_cache_write_failure_does_not_prevent_api_success(
        self,
        mock_auth_cls,
        mock_cache_cls,
        mock_fetcher_cls,
        mock_transformer_cls,
        mock_bundled_cls,
        sample_catalog,
    ):
        """Test that cache write failure doesn't prevent API success."""
        # Setup mock cache manager to fail on save
        mock_cache = Mock()
        mock_cache.load_cache.return_value = None
        mock_cache.save_cache.side_effect = Exception("Cache write error")
        mock_cache_cls.return_value = mock_cache

        # Setup mock API fetcher to fail (simulating the error path)
        mock_fetcher = Mock()
        mock_fetcher.fetch_all_data.side_effect = Exception("Cache write error")
        mock_fetcher_cls.return_value = mock_fetcher

        # Setup mock transformer (won't be called in this scenario)
        mock_transformer = Mock()
        mock_transformer_cls.return_value = mock_transformer

        # Setup bundled loader to provide fallback data
        mock_bundled_cls.load_bundled_catalog.return_value = sample_catalog

        catalog = BedrockModelCatalog(cache_mode=CacheMode.FILE, fallback_to_bundled=True)

        # Should succeed using bundled data as fallback
        result = catalog.ensure_catalog_available()

        assert result is not None
        assert catalog.is_catalog_loaded
        mock_bundled_cls.load_bundled_catalog.assert_called_once()


class TestBedrockModelCatalogProperties:
    """Tests for catalog properties."""

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_is_catalog_loaded_property(self, mock_auth_cls):
        """Test is_catalog_loaded property."""
        catalog = BedrockModelCatalog(cache_mode=CacheMode.NONE)

        assert catalog.is_catalog_loaded is False

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_cache_mode_property(self, mock_auth_cls):
        """Test cache_mode property."""
        catalog = BedrockModelCatalog(cache_mode=CacheMode.MEMORY)

        assert catalog.cache_mode == CacheMode.MEMORY

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_cache_file_path_property_file_mode(self, mock_auth_cls, temp_cache_dir):
        """Test cache_file_path property in FILE mode."""
        catalog = BedrockModelCatalog(
            cache_mode=CacheMode.FILE,
            cache_directory=temp_cache_dir,
        )

        assert catalog.cache_file_path == temp_cache_dir / "bedrock_catalog.json"

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_cache_file_path_property_memory_mode(self, mock_auth_cls):
        """Test cache_file_path property in MEMORY mode."""
        catalog = BedrockModelCatalog(cache_mode=CacheMode.MEMORY)

        assert catalog.cache_file_path is None

    @patch("bestehorn_llmmanager.bedrock.catalog.bedrock_catalog.AuthManager")
    def test_cache_file_path_property_none_mode(self, mock_auth_cls):
        """Test cache_file_path property in NONE mode."""
        catalog = BedrockModelCatalog(cache_mode=CacheMode.NONE)

        assert catalog.cache_file_path is None
