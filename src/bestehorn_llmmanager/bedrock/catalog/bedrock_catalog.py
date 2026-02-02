"""
Main BedrockModelCatalog class for unified model and CRIS data access.

This module provides the BedrockModelCatalog class which serves as the primary
interface for accessing AWS Bedrock model and CRIS data. It replaces the legacy
ModelManager, CRISManager, and UnifiedModelManager classes with a single,
streamlined implementation.
"""

import logging
from pathlib import Path
from typing import List, Optional

from ..auth.auth_manager import AuthManager
from ..exceptions.llm_manager_exceptions import CatalogUnavailableError
from ..models.catalog_constants import (
    CatalogDefaults,
    CatalogErrorMessages,
    CatalogLogMessages,
)
from ..models.catalog_structures import (
    CacheMode,
    CatalogMetadata,
    UnifiedCatalog,
)
from ..models.unified_structures import ModelAccessInfo, UnifiedModelInfo
from .api_fetcher import BedrockAPIFetcher
from .bundled_loader import BundledDataLoader
from .cache_manager import CacheManager
from .name_resolver import ModelNameResolver
from .transformer import CatalogTransformer


class BedrockModelCatalog:
    """
    Unified catalog for AWS Bedrock model and CRIS data.

    This class provides a single interface for accessing model availability,
    CRIS profiles, and access methods. It replaces the legacy ModelManager,
    CRISManager, and UnifiedModelManager classes.

    Features:
        - API-only data retrieval (no HTML parsing)
        - Configurable caching modes (FILE, MEMORY, NONE)
        - Bundled fallback data for offline/error scenarios
        - Single unified cache file
        - Lambda-friendly design
        - Parallel multi-region API fetching

    Initialization Strategy:
        1. Try: Load from cache (if enabled & valid)
        2. Try: Fetch from AWS APIs
        3. Fallback: Load bundled data

    Example Usage:
        >>> # Basic usage with file caching (default)
        >>> catalog = BedrockModelCatalog()
        >>> model_info = catalog.get_model_info("anthropic.claude-3-sonnet", "us-east-1")
        >>>
        >>> # Lambda-friendly: no file system access
        >>> catalog = BedrockModelCatalog(cache_mode=CacheMode.NONE)
        >>>
        >>> # Custom cache directory
        >>> catalog = BedrockModelCatalog(
        ...     cache_mode=CacheMode.FILE,
        ...     cache_directory="/tmp/bedrock_cache"
        ... )
    """

    def __init__(
        self,
        auth_manager: Optional[AuthManager] = None,
        cache_mode: CacheMode = CacheMode.FILE,
        cache_directory: Optional[Path] = None,
        cache_max_age_hours: float = CatalogDefaults.DEFAULT_CACHE_MAX_AGE_HOURS,
        force_refresh: bool = CatalogDefaults.DEFAULT_FORCE_REFRESH,
        timeout: int = CatalogDefaults.DEFAULT_API_TIMEOUT_SECONDS,
        max_workers: int = CatalogDefaults.DEFAULT_MAX_WORKERS,
        fallback_to_bundled: bool = CatalogDefaults.DEFAULT_FALLBACK_TO_BUNDLED,
        enable_fuzzy_matching: Optional[bool] = None,
    ) -> None:
        """
        Initialize the Bedrock model catalog.

        Args:
            auth_manager: Configured AuthManager for AWS authentication.
                         If None, creates a default AuthManager.
            cache_mode: Caching strategy (FILE, MEMORY, NONE)
            cache_directory: Directory for cache file (default: platform-specific)
            cache_max_age_hours: Maximum cache age before refresh
            force_refresh: Force API refresh even if cache is valid
            timeout: API call timeout in seconds
            max_workers: Parallel workers for multi-region API calls
            fallback_to_bundled: Use bundled data if API fails
            enable_fuzzy_matching: Enable fuzzy matching in model-CRIS correlation

        Raises:
            ValueError: If configuration parameters are invalid
        """
        self._logger = logging.getLogger(__name__)

        # Validate configuration parameters
        self._validate_configuration(
            cache_mode=cache_mode,
            cache_directory=cache_directory,
            cache_max_age_hours=cache_max_age_hours,
            timeout=timeout,
            max_workers=max_workers,
        )

        # Store configuration
        self._cache_mode = cache_mode
        self._force_refresh = force_refresh
        self._fallback_to_bundled = fallback_to_bundled

        # Initialize AuthManager
        self._auth_manager = auth_manager or AuthManager()

        # Initialize component managers
        self._cache_manager = CacheManager(
            mode=cache_mode,
            directory=cache_directory,
            max_age_hours=cache_max_age_hours,
        )

        self._api_fetcher = BedrockAPIFetcher(
            auth_manager=self._auth_manager,
            timeout=timeout,
            max_workers=max_workers,
        )

        self._transformer = CatalogTransformer(
            enable_fuzzy_matching=enable_fuzzy_matching,
        )

        # In-memory catalog cache (for subsequent queries)
        self._catalog: Optional[UnifiedCatalog] = None

        # Lazy-initialized name resolver
        self._name_resolver: Optional[ModelNameResolver] = None

        self._logger.info(CatalogLogMessages.CATALOG_INIT_STARTED.format(mode=cache_mode.value))

    def _validate_configuration(
        self,
        cache_mode: CacheMode,
        cache_directory: Optional[Path],
        cache_max_age_hours: float,
        timeout: int,
        max_workers: int,
    ) -> None:
        """
        Validate configuration parameters.

        Args:
            cache_mode: Caching strategy
            cache_directory: Cache directory path
            cache_max_age_hours: Maximum cache age
            timeout: API timeout
            max_workers: Maximum parallel workers

        Raises:
            ValueError: If any parameter is invalid
        """
        # Validate cache_mode
        if not isinstance(cache_mode, CacheMode):
            raise ValueError(CatalogErrorMessages.INVALID_CACHE_MODE.format(mode=cache_mode))

        # Validate cache_directory if provided
        if cache_directory is not None and not isinstance(cache_directory, Path):
            try:
                cache_directory = Path(cache_directory)
            except Exception as e:
                raise ValueError(
                    CatalogErrorMessages.INVALID_CACHE_DIRECTORY.format(path=cache_directory)
                ) from e

        # Validate cache_max_age_hours
        if cache_max_age_hours <= 0:
            raise ValueError(
                CatalogErrorMessages.INVALID_CACHE_MAX_AGE.format(value=cache_max_age_hours)
            )

        # Validate timeout
        if timeout <= 0:
            raise ValueError(CatalogErrorMessages.INVALID_TIMEOUT.format(value=timeout))

        # Validate max_workers
        if max_workers <= 0:
            raise ValueError(CatalogErrorMessages.INVALID_MAX_WORKERS.format(value=max_workers))

    def _get_name_resolver(self) -> ModelNameResolver:
        """
        Get or initialize the name resolver.

        The resolver is initialized lazily on first use to avoid overhead
        during catalog initialization.

        Returns:
            ModelNameResolver instance

        Raises:
            CatalogUnavailableError: If catalog cannot be loaded
        """
        if self._name_resolver is None:
            # Ensure catalog is available
            catalog = self.ensure_catalog_available()
            # Initialize resolver with catalog
            self._name_resolver = ModelNameResolver(catalog=catalog)
            self._logger.debug("ModelNameResolver initialized")
        return self._name_resolver

    def ensure_catalog_available(self) -> UnifiedCatalog:
        """
        Ensure catalog data is available using the initialization strategy.

        This method implements the three-tier initialization strategy:
        1. Try cache first (if enabled and not force_refresh)
        2. Try API fetch on cache miss/invalid
        3. Try bundled data on API failure

        The catalog is cached in memory after first successful load for
        subsequent queries.

        Returns:
            UnifiedCatalog with model and CRIS data

        Raises:
            CatalogUnavailableError: If all data sources fail
        """
        # Return cached catalog if already loaded
        if self._catalog is not None:
            self._logger.debug("Returning in-memory cached catalog")
            return self._catalog

        cache_error: Optional[str] = None
        api_error: Optional[str] = None
        bundled_error: Optional[str] = None

        # Step 1: Try cache (if enabled and not force_refresh)
        if not self._force_refresh and self._cache_mode != CacheMode.NONE:
            try:
                catalog = self._cache_manager.load_cache()
                if catalog is not None:
                    self._catalog = catalog
                    self._logger.info(
                        CatalogLogMessages.CATALOG_INIT_COMPLETED.format(
                            source="cache",
                            count=catalog.model_count,
                        )
                    )
                    return catalog
                else:
                    cache_error = "Cache miss or invalid"
                    self._logger.debug(f"Cache load failed: {cache_error}")
            except Exception as e:
                cache_error = str(e)
                self._logger.warning(
                    CatalogLogMessages.ERROR_CACHE_READ_FAILED.format(error=cache_error)
                )

        # Step 2: Try API fetch
        try:
            self._logger.info("Attempting to fetch catalog from AWS APIs")
            raw_data = self._api_fetcher.fetch_all_data()

            # Transform raw data to unified catalog
            catalog = self._transformer.transform_api_data(raw_data=raw_data)

            # Save to cache if enabled (never raises exception now)
            if self._cache_mode != CacheMode.NONE:
                self._cache_manager.save_cache(catalog=catalog)

            # Cache in memory
            self._catalog = catalog

            self._logger.info(
                CatalogLogMessages.CATALOG_INIT_COMPLETED.format(
                    source="API",
                    count=catalog.model_count,
                )
            )
            return catalog

        except Exception as e:
            api_error = str(e)
            self._logger.warning(CatalogLogMessages.ERROR_API_FETCH_FAILED.format(error=api_error))

        # Step 3: Try bundled data (if enabled)
        if self._fallback_to_bundled:
            try:
                self._logger.info("Attempting to load bundled fallback data")
                catalog = BundledDataLoader.load_bundled_catalog()

                # Cache in memory
                self._catalog = catalog

                self._logger.info(
                    CatalogLogMessages.CATALOG_INIT_COMPLETED.format(
                        source="bundled",
                        count=catalog.model_count,
                    )
                )
                return catalog

            except Exception as e:
                bundled_error = str(e)
                self._logger.error(
                    CatalogLogMessages.ERROR_BUNDLED_LOAD_FAILED.format(error=bundled_error)
                )
        else:
            bundled_error = "Bundled fallback disabled"

        # All sources failed - raise CatalogUnavailableError
        if self._fallback_to_bundled:
            error_msg = CatalogErrorMessages.CATALOG_UNAVAILABLE.format(
                cache_error=cache_error or "Not attempted",
                api_error=api_error or "Not attempted",
                bundled_error=bundled_error or "Not attempted",
            )
        else:
            error_msg = CatalogErrorMessages.CATALOG_UNAVAILABLE_NO_BUNDLED.format(
                cache_error=cache_error or "Not attempted",
                api_error=api_error or "Not attempted",
            )

        self._logger.error(CatalogLogMessages.ERROR_ALL_SOURCES_FAILED)
        raise CatalogUnavailableError(message=error_msg)

    def get_model_info(
        self,
        model_name: str,
        region: Optional[str] = None,
    ) -> Optional[ModelAccessInfo]:
        """
        Get access information for a model in a region.

        This method returns comprehensive access information including:
        - Direct model access (if available)
        - CRIS profile access (if available)
        - Streaming support
        - Modalities

        The method supports flexible model name resolution including:
        - Exact API names
        - Friendly aliases (e.g., "Claude 3 Haiku")
        - Legacy UnifiedModelManager names
        - Normalized variations (spacing, punctuation)

        Args:
            model_name: Model name or ID to query (supports aliases)
            region: AWS region to check availability. If None, returns info
                   for any region where model is available.

        Returns:
            ModelAccessInfo if model is available, None otherwise

        Raises:
            CatalogUnavailableError: If catalog cannot be loaded
        """
        self._logger.debug(
            CatalogLogMessages.QUERY_MODEL_INFO.format(
                model_name=model_name,
                region=region or "any",
            )
        )

        # Ensure catalog is available
        catalog = self.ensure_catalog_available()

        # Resolve model name using name resolver
        resolver = self._get_name_resolver()
        match = resolver.resolve_name(user_name=model_name, strict=False)

        # If name couldn't be resolved, return None
        if match is None:
            self._logger.debug(f"Model {model_name} not found in catalog")
            return None

        # Extract canonical name from match
        resolved_name = match.canonical_name

        # Get model from catalog using resolved name
        model_info = catalog.get_model(name=resolved_name)
        if model_info is None:
            self._logger.debug(f"Model {resolved_name} not found in catalog")
            return None

        # If region specified, get access info for that region
        if region:
            access_info = model_info.get_access_info_for_region(region=region)
            if access_info is None:
                self._logger.debug(f"Model {resolved_name} not available in region {region}")
            return access_info

        # If no region specified, return access info for first available region
        available_regions = model_info.get_supported_regions()
        if not available_regions:
            self._logger.debug(f"Model {resolved_name} has no available regions")
            return None

        # Return access info for first available region
        first_region = available_regions[0]
        return model_info.get_access_info_for_region(region=first_region)

    def is_model_available(
        self,
        model_name: str,
        region: str,
    ) -> bool:
        """
        Check if model is available in region.

        This method supports flexible model name resolution including:
        - Exact API names
        - Friendly aliases (e.g., "Claude 3 Haiku")
        - Legacy UnifiedModelManager names
        - Normalized variations (spacing, punctuation)

        Args:
            model_name: Model name or ID to check (supports aliases)
            region: AWS region to check

        Returns:
            True if model is available in region, False otherwise

        Raises:
            CatalogUnavailableError: If catalog cannot be loaded
        """
        # Ensure catalog is available
        catalog = self.ensure_catalog_available()

        # Resolve model name using name resolver
        resolver = self._get_name_resolver()
        match = resolver.resolve_name(user_name=model_name, strict=False)

        # If name couldn't be resolved, model is not available
        if match is None:
            return False

        # Extract canonical name from match
        resolved_name = match.canonical_name

        # Get model from catalog using resolved name
        model_info = catalog.get_model(name=resolved_name)
        if model_info is None:
            return False

        # Check if available in region
        return model_info.is_available_in_region(region=region)

    def list_models(
        self,
        region: Optional[str] = None,
        provider: Optional[str] = None,
        streaming_only: bool = False,
    ) -> List[UnifiedModelInfo]:
        """
        List models with optional filtering.

        Args:
            region: Filter by AWS region availability
            provider: Filter by model provider (e.g., "Anthropic", "Amazon")
            streaming_only: Only include streaming-capable models

        Returns:
            List of models matching all specified criteria

        Raises:
            CatalogUnavailableError: If catalog cannot be loaded
        """
        filters = {
            "region": region,
            "provider": provider,
            "streaming_only": streaming_only,
        }
        self._logger.debug(CatalogLogMessages.QUERY_LIST_MODELS.format(filters=filters))

        # Ensure catalog is available
        catalog = self.ensure_catalog_available()

        # Apply filters
        return catalog.filter_models(
            region=region,
            provider=provider,
            streaming_only=streaming_only,
        )

    def get_catalog_metadata(self) -> CatalogMetadata:
        """
        Get metadata about the catalog (source, timestamp, version).

        Returns:
            CatalogMetadata with information about catalog source and freshness

        Raises:
            CatalogUnavailableError: If catalog cannot be loaded
        """
        # Ensure catalog is available
        catalog = self.ensure_catalog_available()

        return catalog.metadata

    def clear_cache(self) -> None:
        """
        Clear both in-memory and persistent cache.

        This method clears:
        - In-memory catalog cache (self._catalog)
        - Name resolver cache (self._name_resolver)
        - Persistent cache (file or memory cache via CacheManager)

        After calling this method, the next query will trigger a fresh
        catalog load following the initialization strategy.
        """
        # Clear in-memory cache
        self._catalog = None
        self._name_resolver = None
        self._logger.debug("In-memory catalog cache cleared")

        # Clear persistent cache
        self._cache_manager.clear_cache()

    def refresh_catalog(self) -> UnifiedCatalog:
        """
        Force refresh the catalog from AWS APIs.

        This method bypasses cache and fetches fresh data from AWS APIs,
        then updates both in-memory and persistent caches.

        Returns:
            Freshly fetched UnifiedCatalog

        Raises:
            CatalogUnavailableError: If API fetch fails and no fallback available
        """
        self._logger.info("Forcing catalog refresh from AWS APIs")

        # Clear in-memory cache (including name resolver)
        self._catalog = None
        self._name_resolver = None

        # Temporarily set force_refresh
        original_force_refresh = self._force_refresh
        self._force_refresh = True

        try:
            # This will skip cache and fetch from API
            catalog = self.ensure_catalog_available()
            return catalog
        finally:
            # Restore original setting
            self._force_refresh = original_force_refresh

    @property
    def is_catalog_loaded(self) -> bool:
        """
        Check if catalog is currently loaded in memory.

        Returns:
            True if catalog is loaded, False otherwise
        """
        return self._catalog is not None

    @property
    def cache_mode(self) -> CacheMode:
        """Get the current cache mode."""
        return self._cache_mode

    @property
    def cache_file_path(self) -> Optional[Path]:
        """Get the cache file path (None for MEMORY and NONE modes)."""
        return self._cache_manager.cache_file_path

    def get_model_access_info(
        self,
        model_name: str,
        region: str,
    ) -> Optional[ModelAccessInfo]:
        """
        Get access information for a model in a region.

        This method provides backward compatibility with UnifiedModelManager's
        get_model_access_info method. It is an alias for get_model_info.

        Args:
            model_name: Model name or ID to query
            region: AWS region to check availability

        Returns:
            ModelAccessInfo if model is available, None otherwise

        Raises:
            CatalogUnavailableError: If catalog cannot be loaded
        """
        return self.get_model_info(model_name=model_name, region=region)
