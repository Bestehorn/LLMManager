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
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .ModelManager import ModelManager
from .CRISManager import CRISManager
from .correlators.model_cris_correlator import ModelCRISCorrelator, ModelCRISCorrelationError
from .models.unified_structures import UnifiedModelInfo, UnifiedModelCatalog
from .models.access_method import ModelAccessMethod, ModelAccessInfo, AccessRecommendation
from .models.unified_constants import (
    UnifiedJSONFields,
    UnifiedLogMessages,
    UnifiedErrorMessages,
    UnifiedFilePaths,
    AccessMethodPriority
)
from .serializers.json_serializer import JSONModelSerializer
from .downloaders.base_downloader import NetworkError, FileSystemError
from .parsers.base_parser import ParsingError


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
        force_download: bool = True,
        download_timeout: int = 30,
        enable_fuzzy_matching: Optional[bool] = None
    ) -> None:
        """
        Initialize the UnifiedModelManager with configuration options.
        
        Args:
            json_output_path: Custom path for unified JSON output
            force_download: Whether to always download fresh data
            download_timeout: Request timeout in seconds for downloads
            enable_fuzzy_matching: Whether to enable fuzzy model name matching. 
                                 If None, uses default (True). Fuzzy matching is used
                                 as a last resort when exact mappings fail.
        """
        self.json_output_path = json_output_path or Path(UnifiedFilePaths.DEFAULT_UNIFIED_JSON_OUTPUT)
        self.force_download = force_download
        
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
        effective_force_download = force_download if force_download is not None else self.force_download
        
        try:
            self._logger.info("Starting unified model data refresh")
            
            # Step 1: Refresh regular model data
            self._logger.info("Refreshing regular Bedrock model data")
            model_catalog = self._model_manager.refresh_model_data(force_download=effective_force_download)
            
            # Step 2: Refresh CRIS data
            self._logger.info("Refreshing CRIS model data")
            cris_catalog = self._cris_manager.refresh_cris_data(force_download=effective_force_download)
            
            # Step 3: Correlate and merge data
            self._logger.info("Correlating model and CRIS data")
            unified_catalog = self._correlator.correlate_catalogs(
                model_catalog=model_catalog,
                cris_catalog=cris_catalog
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
    
    def load_cached_data(self) -> Optional[UnifiedModelCatalog]:
        """
        Load previously cached unified data from JSON file.
        
        Returns:
            UnifiedModelCatalog if cached data exists and is valid, None otherwise
        """
        if not self.json_output_path.exists():
            self._logger.info("No cached unified data found")
            return None
        
        try:
            data = self._serializer.load_from_file(input_path=self.json_output_path)
            catalog = UnifiedModelCatalog.from_dict(data=data)
            self._cached_catalog = catalog
            self._logger.info(f"Loaded cached unified data from {self.json_output_path}")
            return catalog
        except Exception as e:
            self._logger.warning(f"Failed to load cached unified data: {str(e)}")
            return None
    
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
    
    def get_recommended_access(self, model_name: str, region: str) -> Optional[AccessRecommendation]:
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
                alternatives=[]
            )
        elif access_info.access_method == ModelAccessMethod.CRIS_ONLY:
            return AccessRecommendation(
                recommended_access=access_info,
                rationale=AccessMethodPriority.PRIORITY_RATIONALES["cris_only"],
                alternatives=[]
            )
        elif access_info.access_method == ModelAccessMethod.BOTH:
            # Recommend direct access, provide CRIS as alternative
            direct_access = ModelAccessInfo(
                access_method=ModelAccessMethod.DIRECT,
                region=region,
                model_id=access_info.model_id,
                inference_profile_id=access_info.inference_profile_id
            )
            
            cris_access = ModelAccessInfo(
                access_method=ModelAccessMethod.CRIS_ONLY,
                region=region,
                model_id=None,
                inference_profile_id=access_info.inference_profile_id
            )
            
            return AccessRecommendation(
                recommended_access=direct_access,
                rationale=AccessMethodPriority.PRIORITY_RATIONALES["direct_preferred"],
                alternatives=[cris_access]
            )
        
        return None
    
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
            data=catalog_dict,
            output_path=self.json_output_path
        )
        
        self._logger.info(f"Successfully saved unified catalog to {self.json_output_path}")
    
    def __repr__(self) -> str:
        """Return string representation of the UnifiedModelManager."""
        return (
            f"UnifiedModelManager("
            f"json_path='{self.json_output_path}', "
            f"force_download={self.force_download}, "
            f"fuzzy_matching={self.is_fuzzy_matching_enabled()}"
            f")"
        )
