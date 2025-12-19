"""
Cache manager for BedrockModelCatalog.

This module provides caching functionality with support for FILE, MEMORY, and NONE modes.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ..exceptions.llm_manager_exceptions import CacheError
from ..models.catalog_constants import (
    CatalogCacheFields,
    CatalogErrorMessages,
    CatalogFilePaths,
    CatalogLogMessages,
)
from ..models.catalog_structures import CacheMode, UnifiedCatalog

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages catalog caching with configurable modes.

    Supports three caching strategies:
    - FILE: Persistent cache to file system
    - MEMORY: In-memory cache (process lifetime)
    - NONE: No caching (always fetch fresh)
    """

    def __init__(
        self,
        mode: CacheMode,
        directory: Optional[Path] = None,
        max_age_hours: float = 24.0,
    ) -> None:
        """
        Initialize cache manager with mode and settings.

        Args:
            mode: Caching strategy (FILE, MEMORY, or NONE)
            directory: Directory for cache file (only used for FILE mode)
            max_age_hours: Maximum cache age before expiration

        Raises:
            ValueError: If max_age_hours is not positive
        """
        if max_age_hours <= 0:
            raise ValueError(CatalogErrorMessages.INVALID_CACHE_MAX_AGE.format(value=max_age_hours))

        self._mode = mode
        self._max_age_hours = max_age_hours

        # Set up cache directory for FILE mode
        self._cache_directory: Optional[Path]
        self._cache_file_path: Optional[Path]

        if self._mode == CacheMode.FILE:
            self._cache_directory = directory or CatalogFilePaths.get_default_cache_directory()
            self._cache_file_path = self._cache_directory / CatalogFilePaths.CACHE_FILENAME
        else:
            self._cache_directory = None
            self._cache_file_path = None

        # In-memory cache storage for MEMORY mode
        self._memory_cache: Optional[UnifiedCatalog] = None

    @property
    def mode(self) -> CacheMode:
        """Get the cache mode."""
        return self._mode

    @property
    def cache_file_path(self) -> Optional[Path]:
        """Get the cache file path (None for MEMORY and NONE modes)."""
        return self._cache_file_path

    def load_cache(self) -> Optional[UnifiedCatalog]:
        """
        Load catalog from cache if valid.

        Returns:
            UnifiedCatalog if cache is valid, None otherwise

        Behavior by mode:
        - FILE: Load from cache file if valid
        - MEMORY: Return in-memory cache if available
        - NONE: Always return None
        """
        if self._mode == CacheMode.NONE:
            logger.debug(CatalogLogMessages.CACHE_SKIPPED.format(mode=self._mode.value))
            return None

        if self._mode == CacheMode.MEMORY:
            if self._memory_cache is not None:
                logger.debug("Returning catalog from memory cache")
                return self._memory_cache
            logger.debug("Memory cache is empty")
            return None

        # FILE mode
        if not self.is_cache_valid():
            return None

        try:
            assert self._cache_file_path is not None  # For mypy
            logger.info(CatalogLogMessages.CACHE_LOADING.format(path=self._cache_file_path))

            with open(self._cache_file_path, mode="r", encoding="utf-8") as f:
                cache_data = json.load(f)

            catalog = UnifiedCatalog.from_dict(data=cache_data)

            logger.info(CatalogLogMessages.CACHE_LOADED.format(count=catalog.model_count))
            return catalog

        except (OSError, IOError) as e:
            logger.warning(CatalogLogMessages.ERROR_CACHE_READ_FAILED.format(error=str(e)))
            return None
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                CatalogLogMessages.CACHE_INVALID.format(reason=f"Invalid JSON or structure: {e}")
            )
            return None

    def save_cache(self, catalog: UnifiedCatalog) -> None:
        """
        Save catalog to cache based on mode.

        Args:
            catalog: Catalog to cache

        Behavior by mode:
        - FILE: Write to cache file
        - MEMORY: Store in memory
        - NONE: Do nothing

        Raises:
            CacheError: If cache write fails (FILE mode only)
        """
        if self._mode == CacheMode.NONE:
            logger.debug(CatalogLogMessages.CACHE_SKIPPED.format(mode=self._mode.value))
            return

        if self._mode == CacheMode.MEMORY:
            self._memory_cache = catalog
            logger.debug("Catalog saved to memory cache")
            return

        # FILE mode
        try:
            assert self._cache_directory is not None  # For mypy
            assert self._cache_file_path is not None  # For mypy

            # Create cache directory if it doesn't exist
            if not self._cache_directory.exists():
                logger.debug(f"Creating cache directory: {self._cache_directory}")
                self._cache_directory.mkdir(parents=True, exist_ok=True)

            logger.info(CatalogLogMessages.CACHE_SAVING.format(path=self._cache_file_path))

            # Serialize catalog to JSON
            cache_data = catalog.to_dict()

            # Add package version for compatibility checking
            try:
                from ..._version import __version__

                cache_data[CatalogCacheFields.PACKAGE_VERSION] = __version__
            except (ImportError, AttributeError):
                # If version is not available, don't add it
                # This might happen during development
                logger.warning("Package version not available, cache may not be version-checked")

            # Write to file with proper encoding
            with open(self._cache_file_path, mode="w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            logger.info(CatalogLogMessages.CACHE_SAVED)

        except (OSError, IOError) as e:
            error_msg = CatalogErrorMessages.CACHE_WRITE_ERROR.format(
                path=self._cache_file_path, error=str(e)
            )
            logger.error(error_msg)
            raise CacheError(message=error_msg, cache_path=str(self._cache_file_path)) from e
        except (TypeError, ValueError) as e:
            error_msg = CatalogErrorMessages.CACHE_INVALID_STRUCTURE.format(error=str(e))
            logger.error(error_msg)
            raise CacheError(message=error_msg, cache_path=str(self._cache_file_path)) from e

    def is_cache_valid(self) -> bool:
        """
        Check if cache exists and is not expired.

        Returns:
            True if cache is valid, False otherwise

        Behavior by mode:
        - FILE: Check file existence and age
        - MEMORY: Check if in-memory cache exists
        - NONE: Always return False
        """
        if self._mode == CacheMode.NONE:
            return False

        if self._mode == CacheMode.MEMORY:
            return self._memory_cache is not None

        # FILE mode
        if not self._cache_file_path or not self._cache_file_path.exists():
            logger.debug(CatalogLogMessages.CACHE_MISS.format(reason="Cache file does not exist"))
            return False

        try:
            # Check file age
            with open(self._cache_file_path, mode="r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # Validate structure
            if not self._validate_cache_structure(data=cache_data):
                logger.debug(
                    CatalogLogMessages.CACHE_INVALID.format(reason="Invalid cache structure")
                )
                return False

            # Check timestamp freshness
            timestamp_str = cache_data[CatalogCacheFields.METADATA][
                CatalogCacheFields.RETRIEVAL_TIMESTAMP
            ]
            cache_timestamp = datetime.fromisoformat(timestamp_str)
            cache_age = datetime.now() - cache_timestamp

            if cache_age > timedelta(hours=self._max_age_hours):
                logger.debug(
                    CatalogLogMessages.CACHE_INVALID.format(
                        reason=f"Cache expired (age: {cache_age.total_seconds() / 3600:.1f}h)"
                    )
                )
                return False

            # Check package version compatibility
            if not self._check_version_compatibility(cache_data=cache_data):
                logger.debug(
                    CatalogLogMessages.CACHE_INVALID.format(reason="Package version incompatible")
                )
                return False

            return True

        except (OSError, IOError, json.JSONDecodeError, KeyError, ValueError) as e:
            logger.debug(CatalogLogMessages.CACHE_INVALID.format(reason=f"Validation error: {e}"))
            return False

    def _validate_cache_structure(self, data: dict) -> bool:
        """
        Validate cache file structure.

        Args:
            data: Cache data dictionary

        Returns:
            True if structure is valid, False otherwise
        """
        try:
            # Check required top-level fields
            if CatalogCacheFields.MODELS not in data:
                return False
            if CatalogCacheFields.METADATA not in data:
                return False

            # Check metadata fields
            metadata = data[CatalogCacheFields.METADATA]
            required_metadata_fields = [
                CatalogCacheFields.SOURCE,
                CatalogCacheFields.RETRIEVAL_TIMESTAMP,
                CatalogCacheFields.API_REGIONS_QUERIED,
            ]

            for field in required_metadata_fields:
                if field not in metadata:
                    return False

            return True

        except (TypeError, KeyError):
            return False

    def _check_version_compatibility(self, cache_data: dict) -> bool:
        """
        Check package version compatibility.

        Cache is compatible if major.minor versions match.

        Args:
            cache_data: Cache data dictionary

        Returns:
            True if versions are compatible, False otherwise
        """
        try:
            # Import version here to avoid circular imports
            from ..._version import __version__

            current_version = __version__

            # Get cached version if available
            cached_version = cache_data.get(CatalogCacheFields.PACKAGE_VERSION)
            if not cached_version:
                # Old cache format without version - consider invalid
                return False

            # Parse versions (major.minor.patch)
            current_parts = current_version.split(".")
            cached_parts = cached_version.split(".")

            # Compare major.minor versions
            if len(current_parts) < 2 or len(cached_parts) < 2:
                return False

            current_major_minor = f"{current_parts[0]}.{current_parts[1]}"
            cached_major_minor = f"{cached_parts[0]}.{cached_parts[1]}"

            return current_major_minor == cached_major_minor

        except (AttributeError, IndexError, ValueError):
            # If version parsing fails, consider incompatible
            return False

    def clear_cache(self) -> None:
        """
        Clear the cache.

        Behavior by mode:
        - FILE: Delete cache file
        - MEMORY: Clear in-memory cache
        - NONE: Do nothing
        """
        if self._mode == CacheMode.NONE:
            return

        if self._mode == CacheMode.MEMORY:
            self._memory_cache = None
            logger.debug("Memory cache cleared")
            return

        # FILE mode
        if self._cache_file_path and self._cache_file_path.exists():
            try:
                self._cache_file_path.unlink()
                logger.info(f"Cache file deleted: {self._cache_file_path}")
            except OSError as e:
                logger.warning(f"Failed to delete cache file: {e}")
