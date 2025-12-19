"""
Catalog data structures for the new BedrockModelCatalog system.

This module contains the core data structures for the redesigned model catalog
that uses API-only data retrieval and supports multiple caching strategies.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .unified_structures import UnifiedModelInfo


class CacheMode(Enum):
    """
    Caching strategy for the catalog.

    Attributes:
        FILE: Cache to file system (persistent across process restarts)
        MEMORY: Cache in memory only (process lifetime, no file I/O)
        NONE: No caching, always fetch fresh data from API
    """

    FILE = "file"
    MEMORY = "memory"
    NONE = "none"


class CatalogSource(Enum):
    """
    Source of catalog data.

    Attributes:
        API: Data retrieved from AWS Bedrock APIs
        CACHE: Data loaded from cache file or memory
        BUNDLED: Data loaded from bundled package data (fallback)
    """

    API = "api"
    CACHE = "cache"
    BUNDLED = "bundled"


@dataclass(frozen=True)
class CatalogMetadata:
    """
    Metadata about the catalog source and freshness.

    Attributes:
        source: Where the catalog data came from (API, CACHE, or BUNDLED)
        retrieval_timestamp: When the data was originally retrieved
        api_regions_queried: List of AWS regions queried for API data
        bundled_data_version: Version of bundled data if used
        cache_file_path: Path to cache file if FILE mode is used
    """

    source: CatalogSource
    retrieval_timestamp: datetime
    api_regions_queried: List[str]
    bundled_data_version: Optional[str] = None
    cache_file_path: Optional[Path] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metadata to dictionary for serialization.

        Returns:
            Dictionary representation of metadata
        """
        return {
            "source": self.source.value,
            "retrieval_timestamp": self.retrieval_timestamp.isoformat(),
            "api_regions_queried": self.api_regions_queried,
            "bundled_data_version": self.bundled_data_version,
            "cache_file_path": str(self.cache_file_path) if self.cache_file_path else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CatalogMetadata":
        """
        Create CatalogMetadata from dictionary data.

        Args:
            data: Dictionary containing metadata

        Returns:
            CatalogMetadata instance

        Raises:
            ValueError: If data structure is invalid
        """
        try:
            source = CatalogSource(data["source"])
            retrieval_timestamp = datetime.fromisoformat(data["retrieval_timestamp"])
            api_regions_queried = data["api_regions_queried"]

            cache_file_path_str = data.get("cache_file_path")
            cache_file_path = Path(cache_file_path_str) if cache_file_path_str else None

            return cls(
                source=source,
                retrieval_timestamp=retrieval_timestamp,
                api_regions_queried=api_regions_queried,
                bundled_data_version=data.get("bundled_data_version"),
                cache_file_path=cache_file_path,
            )
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Invalid catalog metadata structure: {e}") from e


@dataclass(frozen=True)
class UnifiedCatalog:
    """
    Unified catalog containing all model and CRIS information.

    This is the main data structure for the new catalog system, containing
    both model information and metadata about the catalog itself.

    Attributes:
        models: Dictionary mapping model names to their unified information
        metadata: Metadata about the catalog source and freshness
    """

    models: Dict[str, UnifiedModelInfo]
    metadata: CatalogMetadata

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize catalog to dictionary for caching.

        Returns:
            Dictionary representation suitable for JSON serialization
        """
        return {
            "models": {
                model_name: model_info.to_dict() for model_name, model_info in self.models.items()
            },
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnifiedCatalog":
        """
        Deserialize catalog from dictionary.

        Args:
            data: Dictionary containing catalog data

        Returns:
            UnifiedCatalog instance

        Raises:
            ValueError: If data structure is invalid
        """
        try:
            models_data = data["models"]
            if not isinstance(models_data, dict):
                raise ValueError("Models data must be a dictionary")

            models = {}
            for model_name, model_data in models_data.items():
                if not isinstance(model_data, dict):
                    raise ValueError(f"Model data for {model_name} must be a dictionary")
                models[model_name] = UnifiedModelInfo.from_dict(data=model_data)

            metadata = CatalogMetadata.from_dict(data=data["metadata"])

            return cls(models=models, metadata=metadata)

        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Invalid catalog data structure: {e}") from e

    def get_model(self, name: str) -> Optional[UnifiedModelInfo]:
        """
        Get model by name.

        Args:
            name: Model name to retrieve

        Returns:
            UnifiedModelInfo if found, None otherwise
        """
        return self.models.get(name)

    def filter_models(
        self,
        region: Optional[str] = None,
        provider: Optional[str] = None,
        streaming_only: bool = False,
    ) -> List[UnifiedModelInfo]:
        """
        Filter models by criteria.

        Args:
            region: Filter by AWS region availability
            provider: Filter by model provider
            streaming_only: Only include streaming-capable models

        Returns:
            List of models matching all specified criteria
        """
        filtered = list(self.models.values())

        if region:
            filtered = [m for m in filtered if m.is_available_in_region(region=region)]

        if provider:
            filtered = [m for m in filtered if m.provider == provider]

        if streaming_only:
            filtered = [m for m in filtered if m.streaming_supported]

        return filtered

    @property
    def model_count(self) -> int:
        """Get the total number of models in the catalog."""
        return len(self.models)

    def get_all_regions(self) -> List[str]:
        """
        Get all unique regions across all models.

        Returns:
            Sorted list of all regions
        """
        all_regions = set()
        for model_info in self.models.values():
            all_regions.update(model_info.get_supported_regions())
        return sorted(list(all_regions))

    def get_all_providers(self) -> List[str]:
        """
        Get all unique providers in the catalog.

        Returns:
            Sorted list of all providers
        """
        providers = {model_info.provider for model_info in self.models.values()}
        return sorted(list(providers))


# Type aliases for better code readability
CatalogDict = Dict[str, Any]
ModelName = str
