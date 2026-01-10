"""
Amazon Bedrock Model Catalog Module.

This module provides a unified, API-based approach to managing AWS Bedrock model
and CRIS (Cross-Region Inference Service) data. It replaces the legacy HTML-based
ModelManager, CRISManager, and UnifiedModelManager with a single, streamlined
BedrockModelCatalog class.

Key Features:
    - API-only data retrieval (no HTML parsing)
    - Configurable caching modes (FILE, MEMORY, NONE)
    - Bundled fallback data for offline/error scenarios
    - Single unified cache file
    - Lambda-friendly design
    - Parallel multi-region API fetching

Main Components:
    BedrockModelCatalog: Main class for accessing model and CRIS data
    CacheMode: Enum defining caching strategies
    CatalogMetadata: Metadata about catalog source and freshness
    UnifiedCatalog: Unified data structure containing all model information

Example Usage:
    >>> from bestehorn_llmmanager.bedrock.catalog import BedrockModelCatalog, CacheMode
    >>>
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
    >>>
    >>> # Check model availability
    >>> if catalog.is_model_available("anthropic.claude-3-sonnet", "us-west-2"):
    ...     print("Model available!")
    >>>
    >>> # List all models with filtering
    >>> streaming_models = catalog.list_models(streaming_only=True)
    >>> amazon_models = catalog.list_models(provider="Amazon")

Architecture:
    The catalog module follows a layered architecture:

    1. BedrockModelCatalog (Main Interface)
       - Orchestrates initialization strategy
       - Provides query methods
       - Manages in-memory caching

    2. Data Sources (Priority Order)
       - CacheManager: Loads from file/memory cache
       - BedrockAPIFetcher: Fetches from AWS APIs
       - BundledDataLoader: Loads pre-packaged fallback data

    3. Data Processing
       - CatalogTransformer: Transforms API responses to unified format
       - Correlates model and CRIS data

    4. Data Models
       - UnifiedCatalog: Main data structure
       - CatalogMetadata: Source and freshness information
       - CacheMode: Caching strategy enum

Migration from Legacy Managers:
    The new BedrockModelCatalog replaces three legacy classes:
    - ModelManager (deprecated)
    - CRISManager (deprecated)
    - UnifiedModelManager (deprecated)

    See migration guide for detailed upgrade instructions.

Requirements Addressed:
    - Requirement 5.1: Single unified manager class
    - Requirement 5.2: Automatic correlation of model and CRIS data
"""

# Import exceptions
from ..exceptions.llm_manager_exceptions import (
    APIFetchError,
    BundledDataError,
    CacheError,
    CatalogError,
    CatalogUnavailableError,
)

# Import data structures from models
from ..models.catalog_structures import (
    CacheMode,
    CatalogMetadata,
    CatalogSource,
    UnifiedCatalog,
)

# Import main catalog class
from .bedrock_catalog import BedrockModelCatalog

# Import component classes
from .bundled_loader import BundledDataLoader
from .cache_manager import CacheManager

# Import name resolution structures
from .name_resolution_structures import (
    AliasGenerationConfig,
    ErrorType,
    MatchType,
    ModelNameMatch,
    ModelResolutionError,
)

# Public API
__all__ = [
    # Main class
    "BedrockModelCatalog",
    # Component classes
    "BundledDataLoader",
    "CacheManager",
    # Data structures
    "CacheMode",
    "CatalogMetadata",
    "CatalogSource",
    "UnifiedCatalog",
    # Name resolution structures
    "AliasGenerationConfig",
    "ErrorType",
    "MatchType",
    "ModelNameMatch",
    "ModelResolutionError",
    # Exceptions
    "APIFetchError",
    "BundledDataError",
    "CacheError",
    "CatalogError",
    "CatalogUnavailableError",
]

# Module metadata
__version__ = "1.0.0"
__author__ = "bestehorn-llmmanager"
__description__ = "Unified API-based Bedrock Model Catalog"
