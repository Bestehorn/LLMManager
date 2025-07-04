"""
Unified Amazon Bedrock Model Manager.

This module provides the UnifiedModelManager class that serves as the single source
of truth for Amazon Bedrock model information by integrating regular model data
with CRIS (Cross-Region Inference Service) data.

The UnifiedModelManager orchestrates the following workflow:
1. Downloads and parses regular Bedrock model documentation
2. Downloads and parses CRIS model documentation
3. Correlates and merges the data into a unified view
4. Provides comprehensive query methods for model access information
5. Serializes the unified data to JSON format

Example:
    Basic usage:
    >>> from pathlib import Path
    >>> from src.bedrock.UnifiedModelManager import UnifiedModelManager
    >>>
    >>> manager = UnifiedModelManager()
    >>> catalog = manager.refresh_unified_data()
    >>> print(f"Found {catalog.model_count} unified models")

    Query model access information:
    >>> access_info = manager.get_model_access_info("Claude 3 Haiku", "us-east-1")
    >>> print(f"Access method: {access_info.access_method}")
    >>> print(f"Model ID: {access_info.model_id}")
    >>> print(f"Inference profile: {access_info.inference_profile_id}")

Author: Generated code for production use
License: MIT
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from typing_extensions import assert_never

from .correlators.model_cris_correlator import ModelCRISCorrelationError, ModelCRISCorrelator
from .CRISManager import CRISManager
from .downloaders.base_downloader import FileSystemError, NetworkError
from .ModelManager import ModelManager
from .models.access_method import AccessRecommendation, ModelAccessInfo, ModelAccessMethod
from .models.unified_constants import (
    AccessMethodPriority,
    CacheManagementConstants,
    UnifiedErrorMessages,
    UnifiedFilePaths,
    UnifiedJSONFields,
)
from .models.unified_structures import UnifiedModelCatalog, UnifiedModelInfo
from .parsers.base_parser import ParsingError
from .serializers.json_serializer import JSONModelSerializer


class UnifiedModelManagerError(Exception):
    """Base exception for UnifiedModelManager operations."""

    pass


class UnifiedModelManager:
    """
    Unified Amazon Bedrock Model Manager.

    Serves as the single source of truth for Amazon Bedrock model information by
    integrating regular model data with CRIS data. Provides comprehensive methods
    for querying model availability and access methods across all AWS regions.

    This class orchestrates:
    - Regular Bedrock model data retrieval and parsing
    - CRIS model data retrieval and parsing
    - Correlation and merging of the two data sources
    - Unified querying interface for model access information
    - JSON serialization of the unified catalog

    Attributes:
        json_output_path: Path where unified JSON will be saved
        force_download: Whether to always download fresh data
    """

    def __init__(
        self,
        json_output_path: Optional[Path] = None,
        force_download: bool = False,
        download_timeout: int = 30,
        enable_fuzzy_matching: Optional[bool] = None,
        max_cache_age_hours: float = CacheManagementConstants.DEFAULT_MAX_CACHE_AGE_HOURS,
    ) -> None:
        """
        Initialize the UnifiedModelManager with configuration options.

        Args:
            json_output_path: Custom path for unified JSON output
            force_download: Whether to always download fresh data (default: False for auto-management)
            download_timeout: Request timeout in seconds for downloads
            enable_fuzzy_matching: Whether to enable fuzzy model name matching.
                                 If None, uses default (True). Fuzzy matching is used
                                 as a last resort when exact mappings fail.
            max_cache_age_hours: Maximum age of cache data in hours before refresh (default: 24.0)
        """
        self.json_output_path = json_output_path or Path(
            UnifiedFilePaths.DEFAULT_UNIFIED_JSON_OUTPUT
        )
        self.force_download = force_download

        # Validate cache age parameter
        if not (
            CacheManagementConstants.MIN_CACHE_AGE_HOURS
            <= max_cache_age_hours
            <= CacheManagementConstants.MAX_CACHE_AGE_HOURS
        ):
            raise UnifiedModelManagerError(
                f"max_cache_age_hours must be between {CacheManagementConstants.MIN_CACHE_AGE_HOURS} "
                f"and {CacheManagementConstants.MAX_CACHE_AGE_HOURS} hours"
            )
        self.max_cache_age_hours = max_cache_age_hours

        # Initialize component managers
        self._model_manager = ModelManager(download_timeout=download_timeout)
        self._cris_manager = CRISManager(download_timeout=download_timeout)
        self._correlator = ModelCRISCorrelator(enable_fuzzy_matching=enable_fuzzy_matching)
        self._serializer = JSONModelSerializer()

        # Setup logging
        self._logger = logging.getLogger(__name__)

        # Cache for unified data
        self._cached_catalog: Optional[UnifiedModelCatalog] = None

    def refresh_unified_data(self, force_download: Optional[bool] = None) -> UnifiedModelCatalog:
        """
        Refresh unified model data by downloading and correlating all sources.

        This method orchestrates the complete workflow:
        1. Refreshes regular Bedrock model data
        2. Refreshes CRIS model data
        3. Correlates and merges the data sources
        4. Creates a unified catalog with comprehensive access information
        5. Saves the unified data to JSON format
        6. Returns the unified catalog

        Args:
            force_download: Override the default force_download setting

        Returns:
            UnifiedModelCatalog containing all integrated model information

        Raises:
            UnifiedModelManagerError: If any step in the process fails
        """
        effective_force_download = (
            force_download if force_download is not None else self.force_download
        )

        try:
            self._logger.info("Starting unified model data refresh")

            # Step 1: Refresh regular model data
            self._logger.info("Refreshing regular Bedrock model data")
            model_catalog = self._model_manager.refresh_model_data(
                force_download=effective_force_download
            )

            # Step 2: Refresh CRIS data
            self._logger.info("Refreshing CRIS model data")
            cris_catalog = self._cris_manager.refresh_cris_data(
                force_download=effective_force_download
            )

            # Step 3: Correlate and merge data
            self._logger.info("Correlating model and CRIS data")
            unified_catalog = self._correlator.correlate_catalogs(
                model_catalog=model_catalog, cris_catalog=cris_catalog
            )

            # Step 4: Save unified catalog
            self._save_unified_catalog(catalog=unified_catalog)

            # Step 5: Cache and return
            self._cached_catalog = unified_catalog

            # Log correlation statistics
            correlation_stats = self._correlator.get_correlation_stats()
            self._logger.info(f"Correlation completed with {correlation_stats}")

            return unified_catalog

        except (NetworkError, FileSystemError, ParsingError, ModelCRISCorrelationError) as e:
            error_msg = f"Failed to refresh unified model data: {str(e)}"
            self._logger.error(error_msg)
            raise UnifiedModelManagerError(error_msg) from e

    def ensure_data_available(self) -> UnifiedModelCatalog:
        """
        Ensure model data is available and up-to-date.

        This method implements the automatic cache management logic:
        1. Validates existing cache (exists, not corrupted, not expired)
        2. Automatically refreshes data if cache is invalid
        3. Returns the available unified catalog

        Returns:
            UnifiedModelCatalog with current model data

        Raises:
            UnifiedModelManagerError: If data cannot be obtained or refreshed
        """
        try:
            # Check if we need to refresh data
            cache_status, reason = self._validate_cache()

            if cache_status == CacheManagementConstants.CACHE_VALID and self._cached_catalog:
                self._logger.debug("Using valid cached model data")
                return self._cached_catalog

            # Cache is invalid, need to refresh
            self._logger.info(
                f"Cache validation failed ({cache_status}): {reason}. Refreshing model data..."
            )

            try:
                # Force download when cache is invalid to ensure fresh data
                catalog = self.refresh_unified_data(force_download=True)
                self._logger.info(
                    "Successfully refreshed model data after cache validation failure"
                )
                return catalog

            except Exception as refresh_error:
                error_msg = UnifiedErrorMessages.AUTO_REFRESH_FAILED.format(
                    error=str(refresh_error)
                )
                self._logger.error(error_msg)
                raise UnifiedModelManagerError(error_msg) from refresh_error

        except UnifiedModelManagerError:
            # Re-raise UnifiedModelManagerError as-is
            raise
        except Exception as exc:
            error_msg = f"Critical error in data availability check: {str(exc)}"
            self._logger.error(error_msg)
            raise UnifiedModelManagerError(error_msg) from exc

    def load_cached_data(self) -> Optional[UnifiedModelCatalog]:
        """
        Load previously cached unified data from JSON file.

        This method loads cache data but does not validate its age or integrity.
        For automatic cache management, use ensure_data_available() instead.

        Returns:
            UnifiedModelCatalog if cached data exists and is readable, None otherwise
        """
        if not self.json_output_path.exists():
            self._logger.debug("No cached unified data file found")
            return None

        try:
            data = self._serializer.load_from_file(input_path=self.json_output_path)
            catalog = UnifiedModelCatalog.from_dict(data=data)
            self._cached_catalog = catalog
            self._logger.debug(f"Loaded cached unified data from {self.json_output_path}")
            return catalog
        except Exception as e:
            self._logger.warning(f"Failed to load cached unified data: {str(e)}")
            return None

    def _validate_cache(self) -> Tuple[str, str]:
        """
        Validate the current cache state.

        Returns:
            Tuple of (cache_status, reason) where cache_status is one of:
            - CACHE_VALID: Cache is valid and current
            - CACHE_MISSING: No cache file exists
            - CACHE_CORRUPTED: Cache file exists but is unreadable
            - CACHE_EXPIRED: Cache file is readable but data is too old
        """
        # Check if cache file exists
        if not self.json_output_path.exists():
            return CacheManagementConstants.CACHE_MISSING, "Cache file does not exist"

        # Try to load and validate cache
        try:
            data = self._serializer.load_from_file(input_path=self.json_output_path)

            # Check if data has required structure
            if not isinstance(data, dict) or UnifiedJSONFields.RETRIEVAL_TIMESTAMP not in data:
                return (
                    CacheManagementConstants.CACHE_CORRUPTED,
                    "Cache missing required timestamp field",
                )

            # Parse and validate timestamp
            timestamp_str = data[UnifiedJSONFields.RETRIEVAL_TIMESTAMP]
            cache_age_hours = self._get_cache_age_hours(timestamp_str=timestamp_str)

            # Check if cache is expired
            if cache_age_hours > self.max_cache_age_hours:
                return (
                    CacheManagementConstants.CACHE_EXPIRED,
                    UnifiedErrorMessages.CACHE_EXPIRED.format(
                        age_hours=cache_age_hours, max_age_hours=self.max_cache_age_hours
                    ),
                )

            # Validate catalog structure
            try:
                catalog = UnifiedModelCatalog.from_dict(data=data)
                if catalog.model_count == 0:
                    return (
                        CacheManagementConstants.CACHE_CORRUPTED,
                        "Cache contains no model data",
                    )
                # Cache catalog for efficiency
                self._cached_catalog = catalog

            except Exception as e:
                return (
                    CacheManagementConstants.CACHE_CORRUPTED,
                    f"Cache data structure is invalid: {str(e)}",
                )

            return (
                CacheManagementConstants.CACHE_VALID,
                f"Cache is valid (age: {cache_age_hours:.1f} hours)",
            )

        except Exception:
            return (
                CacheManagementConstants.CACHE_CORRUPTED,
                UnifiedErrorMessages.CACHE_CORRUPTED.format(path=self.json_output_path),
            )

    def _get_cache_age_hours(self, timestamp_str: str) -> float:
        """
        Calculate the age of cached data in hours.

        Args:
            timestamp_str: ISO timestamp string from cache

        Returns:
            Age of cache data in hours

        Raises:
            UnifiedModelManagerError: If timestamp cannot be parsed
        """
        try:
            cache_time = None

            # Try multiple timestamp formats in order of preference
            timestamp_formats = [
                CacheManagementConstants.TIMESTAMP_FORMAT,  # With Z suffix and microseconds
                CacheManagementConstants.TIMESTAMP_FORMAT_FALLBACK,  # With Z suffix, no microseconds
                "%Y-%m-%dT%H:%M:%S.%",  # ISO format with microseconds, no Z
                "%Y-%m-%dT%H:%M:%S",  # ISO format without microseconds, no Z
            ]

            for fmt in timestamp_formats:
                try:
                    cache_time = datetime.strptime(timestamp_str, fmt)
                    break
                except ValueError:
                    continue

            if cache_time is None:
                raise ValueError(f"No matching timestamp format found for: {timestamp_str}")

            # Ensure timezone awareness (assume UTC if no timezone)
            if cache_time.tzinfo is None:
                cache_time = cache_time.replace(tzinfo=timezone.utc)

            # Calculate age
            current_time = datetime.now(timezone.utc)
            age_delta = current_time - cache_time
            age_hours = age_delta.total_seconds() / 3600.0

            return age_hours

        except Exception as e:
            error_msg = UnifiedErrorMessages.TIMESTAMP_PARSE_FAILED.format(timestamp=timestamp_str)
            self._logger.error(f"{error_msg}: {str(e)}")
            raise UnifiedModelManagerError(error_msg) from e

    def get_cache_status(self) -> Dict[str, Any]:
        """
        Get detailed information about the current cache status.

        Returns:
            Dictionary with cache status information including:
            - status: Current cache status
            - reason: Detailed reason for the status
            - age_hours: Age of cache in hours (if applicable)
            - max_age_hours: Maximum allowed cache age
            - path: Path to cache file
            - exists: Whether cache file exists
        """
        status, reason = self._validate_cache()

        result = {
            "status": status,
            "reason": reason,
            "max_age_hours": self.max_cache_age_hours,
            "path": str(self.json_output_path),
            "exists": self.json_output_path.exists(),
        }

        # Add age information if cache is readable
        if status in [CacheManagementConstants.CACHE_VALID, CacheManagementConstants.CACHE_EXPIRED]:
            try:
                data = self._serializer.load_from_file(input_path=self.json_output_path)
                if UnifiedJSONFields.RETRIEVAL_TIMESTAMP in data:
                    age_hours = self._get_cache_age_hours(
                        data[UnifiedJSONFields.RETRIEVAL_TIMESTAMP]
                    )
                    result["age_hours"] = age_hours
            except Exception:
                pass  # Age calculation failed, but status is already set

        return result

    def get_model_access_info(self, model_name: str, region: str) -> Optional[ModelAccessInfo]:
        """
        Get access information for a specific model in a specific region.

        This is one of the core methods that provides the information specified
        in the requirements: which model identifier / CRIS profile ID to use
        for accessing a model in a given region.

        Args:
            model_name: The name of the model
            region: The AWS region

        Returns:
            ModelAccessInfo containing access method and identifiers, None if not available

        Raises:
            UnifiedModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise UnifiedModelManagerError(UnifiedErrorMessages.NO_MODEL_DATA)

        if model_name not in self._cached_catalog.unified_models:
            return None

        model_info = self._cached_catalog.unified_models[model_name]
        return model_info.get_access_info_for_region(region=region)

    def get_recommended_access(
        self, model_name: str, region: str
    ) -> Optional[AccessRecommendation]:
        """
        Get recommended access method for a model in a region.

        Provides not just the access information but also rationale for the
        recommendation and alternative options if available.

        Args:
            model_name: The name of the model
            region: The AWS region

        Returns:
            AccessRecommendation with primary choice and alternatives

        Raises:
            UnifiedModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise UnifiedModelManagerError(UnifiedErrorMessages.NO_MODEL_DATA)

        if model_name not in self._cached_catalog.unified_models:
            return None

        model_info = self._cached_catalog.unified_models[model_name]
        access_info = model_info.get_access_info_for_region(region=region)

        if not access_info:
            return None

        # Generate recommendation based on access method
        if access_info.access_method == ModelAccessMethod.DIRECT:
            return AccessRecommendation(
                recommended_access=access_info,
                rationale=AccessMethodPriority.PRIORITY_RATIONALES["direct_preferred"],
                alternatives=[],
            )
        elif access_info.access_method == ModelAccessMethod.CRIS_ONLY:
            return AccessRecommendation(
                recommended_access=access_info,
                rationale=AccessMethodPriority.PRIORITY_RATIONALES["cris_only"],
                alternatives=[],
            )
        elif access_info.access_method == ModelAccessMethod.BOTH:
            # Recommend direct access, provide CRIS as alternative
            direct_access = ModelAccessInfo(
                access_method=ModelAccessMethod.DIRECT,
                region=region,
                model_id=access_info.model_id,
                inference_profile_id=access_info.inference_profile_id,
            )

            cris_access = ModelAccessInfo(
                access_method=ModelAccessMethod.CRIS_ONLY,
                region=region,
                model_id=None,
                inference_profile_id=access_info.inference_profile_id,
            )

            return AccessRecommendation(
                recommended_access=direct_access,
                rationale=AccessMethodPriority.PRIORITY_RATIONALES["direct_preferred"],
                alternatives=[cris_access],
            )

        assert_never(access_info.access_method)

    def is_model_available_in_region(self, model_name: str, region: str) -> bool:
        """
        Check if a model is available in a specific region via any access method.

        Args:
            model_name: The name of the model
            region: The AWS region

        Returns:
            True if model is available in the region

        Raises:
            UnifiedModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise UnifiedModelManagerError(UnifiedErrorMessages.NO_MODEL_DATA)

        if model_name not in self._cached_catalog.unified_models:
            return False

        model_info = self._cached_catalog.unified_models[model_name]
        return model_info.is_available_in_region(region=region)

    def get_models_by_region(self, region: str) -> Dict[str, UnifiedModelInfo]:
        """
        Get all models available in a specific region.

        Args:
            region: The AWS region to filter by

        Returns:
            Dictionary of model names to unified model info

        Raises:
            UnifiedModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise UnifiedModelManagerError(UnifiedErrorMessages.NO_MODEL_DATA)

        return self._cached_catalog.get_models_by_region(region=region)

    def get_models_by_provider(self, provider: str) -> Dict[str, UnifiedModelInfo]:
        """
        Get all models from a specific provider.

        Args:
            provider: The provider name to filter by

        Returns:
            Dictionary of model names to unified model info

        Raises:
            UnifiedModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise UnifiedModelManagerError(UnifiedErrorMessages.NO_MODEL_DATA)

        return self._cached_catalog.get_models_by_provider(provider=provider)

    def get_direct_access_models_by_region(self, region: str) -> Dict[str, UnifiedModelInfo]:
        """
        Get models with direct access in a specific region.

        Args:
            region: The AWS region to filter by

        Returns:
            Dictionary of model names to unified model info with direct access

        Raises:
            UnifiedModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise UnifiedModelManagerError(UnifiedErrorMessages.NO_MODEL_DATA)

        return self._cached_catalog.get_direct_access_models_by_region(region=region)

    def get_cris_only_models_by_region(self, region: str) -> Dict[str, UnifiedModelInfo]:
        """
        Get models with CRIS-only access in a specific region.

        Args:
            region: The AWS region to filter by

        Returns:
            Dictionary of model names to unified model info with CRIS-only access

        Raises:
            UnifiedModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise UnifiedModelManagerError(UnifiedErrorMessages.NO_MODEL_DATA)

        return self._cached_catalog.get_cris_only_models_by_region(region=region)

    def get_all_supported_regions(self) -> List[str]:
        """
        Get all unique regions supported across all models.

        Returns:
            Sorted list of all supported regions

        Raises:
            UnifiedModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise UnifiedModelManagerError(UnifiedErrorMessages.NO_MODEL_DATA)

        return self._cached_catalog.get_all_supported_regions()

    def get_model_names(self) -> List[str]:
        """
        Get all model names in the unified catalog.

        Returns:
            Sorted list of model names

        Raises:
            UnifiedModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise UnifiedModelManagerError(UnifiedErrorMessages.NO_MODEL_DATA)

        return self._cached_catalog.get_model_names()

    def get_streaming_models(self) -> Dict[str, UnifiedModelInfo]:
        """
        Get all models that support streaming.

        Returns:
            Dictionary of model names to unified model info for streaming-enabled models

        Raises:
            UnifiedModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise UnifiedModelManagerError(UnifiedErrorMessages.NO_MODEL_DATA)

        return self._cached_catalog.get_streaming_models()

    def get_model_count(self) -> int:
        """
        Get the total number of models in the unified catalog.

        Returns:
            Total number of models

        Raises:
            UnifiedModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise UnifiedModelManagerError(UnifiedErrorMessages.NO_MODEL_DATA)

        return self._cached_catalog.model_count

    def has_model(self, model_name: str) -> bool:
        """
        Check if a model exists in the unified catalog.

        Args:
            model_name: The model name to check

        Returns:
            True if model exists in catalog

        Raises:
            UnifiedModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise UnifiedModelManagerError(UnifiedErrorMessages.NO_MODEL_DATA)

        return self._cached_catalog.has_model(model_name=model_name)

    def get_regions_for_model(self, model_name: str) -> List[str]:
        """
        Get all regions where a specific model is available.

        Args:
            model_name: The name of the model

        Returns:
            Sorted list of regions where the model is available

        Raises:
            UnifiedModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise UnifiedModelManagerError(UnifiedErrorMessages.NO_MODEL_DATA)

        if model_name not in self._cached_catalog.unified_models:
            return []

        model_info = self._cached_catalog.unified_models[model_name]
        available_regions = []

        # Check all supported regions
        for region in self._cached_catalog.get_all_supported_regions():
            if model_info.is_available_in_region(region=region):
                available_regions.append(region)

        return sorted(available_regions)

    def get_correlation_stats(self) -> Dict[str, int]:
        """
        Get statistics from the last correlation operation.

        Returns:
            Dictionary with correlation statistics
        """
        return self._correlator.get_correlation_stats()

    def is_fuzzy_matching_enabled(self) -> bool:
        """
        Check if fuzzy matching is currently enabled.

        Returns:
            True if fuzzy matching is enabled
        """
        return self._correlator.is_fuzzy_matching_enabled()

    def set_fuzzy_matching_enabled(self, enabled: bool) -> None:
        """
        Enable or disable fuzzy matching for model name correlation.

        Fuzzy matching is used as a last resort when exact model name mappings
        fail. When enabled, it logs warnings about which models are being
        fuzzy matched to provide transparency.

        Args:
            enabled: Whether to enable fuzzy matching
        """
        self._correlator.set_fuzzy_matching_enabled(enabled=enabled)

    def _save_unified_catalog(self, catalog: UnifiedModelCatalog) -> None:
        """
        Save the unified catalog to JSON format.

        Args:
            catalog: The catalog to save

        Raises:
            OSError: If file operations fail
            TypeError: If serialization fails
        """
        self._logger.info("Saving unified catalog to JSON")

        # Convert catalog to dictionary for serialization
        catalog_dict = catalog.to_dict()

        self._serializer.serialize_dict_to_file(
            data=catalog_dict, output_path=self.json_output_path
        )

        self._logger.info(f"Successfully saved unified catalog to {self.json_output_path}")

    def __repr__(self) -> str:
        """Return string representation of the UnifiedModelManager."""
        return (
            "UnifiedModelManager("
            f"json_path='{self.json_output_path}', "
            f"force_download={self.force_download}, "
            f"fuzzy_matching={self.is_fuzzy_matching_enabled()}"
            ")"
        )
