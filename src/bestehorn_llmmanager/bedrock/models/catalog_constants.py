"""
Constants for the new BedrockModelCatalog system.

This module contains all string literals, API operation names, file paths,
and error messages used throughout the catalog implementation.
"""

import os
import platform
from pathlib import Path
from typing import Final, List


class CatalogAPIOperations:
    """AWS Bedrock API operation names for catalog data retrieval."""

    LIST_FOUNDATION_MODELS: Final[str] = "list_foundation_models"
    LIST_INFERENCE_PROFILES: Final[str] = "list_inference_profiles"


class CatalogAPIParameters:
    """Parameter names for AWS Bedrock API calls."""

    # For list-inference-profiles
    PROFILE_TYPE_EQUALS: Final[str] = "typeEquals"  # Correct AWS API parameter name
    SYSTEM_DEFINED: Final[str] = "SYSTEM_DEFINED"

    # Common parameters
    MAX_RESULTS: Final[str] = "maxResults"
    NEXT_TOKEN: Final[str] = "nextToken"


class CatalogAPIResponseFields:
    """Field names in AWS Bedrock API responses."""

    # list-foundation-models response fields
    MODEL_SUMMARIES: Final[str] = "modelSummaries"
    MODEL_ID: Final[str] = "modelId"
    MODEL_NAME: Final[str] = "modelName"
    PROVIDER_NAME: Final[str] = "providerName"
    MODEL_ARN: Final[str] = "modelArn"
    INPUT_MODALITIES: Final[str] = "inputModalities"
    OUTPUT_MODALITIES: Final[str] = "outputModalities"
    RESPONSE_STREAMING_SUPPORTED: Final[str] = "responseStreamingSupported"
    CUSTOMIZATIONS_SUPPORTED: Final[str] = "customizationsSupported"
    INFERENCE_TYPES_SUPPORTED: Final[str] = "inferenceTypesSupported"
    MODEL_LIFECYCLE: Final[str] = "modelLifecycle"

    # list-inference-profiles response fields
    INFERENCE_PROFILE_SUMMARIES: Final[str] = "inferenceProfileSummaries"
    INFERENCE_PROFILE_NAME: Final[str] = "inferenceProfileName"
    INFERENCE_PROFILE_ID: Final[str] = "inferenceProfileId"
    INFERENCE_PROFILE_ARN: Final[str] = "inferenceProfileArn"
    MODELS: Final[str] = "models"
    DESCRIPTION: Final[str] = "description"
    CREATED_AT: Final[str] = "createdAt"
    UPDATED_AT: Final[str] = "updatedAt"
    PROFILE_TYPE: Final[str] = "type"
    STATUS: Final[str] = "status"


class CatalogCacheFields:
    """Field names for catalog cache file structure."""

    MODELS: Final[str] = "models"
    METADATA: Final[str] = "metadata"
    SOURCE: Final[str] = "source"
    RETRIEVAL_TIMESTAMP: Final[str] = "retrieval_timestamp"
    API_REGIONS_QUERIED: Final[str] = "api_regions_queried"
    BUNDLED_DATA_VERSION: Final[str] = "bundled_data_version"
    CACHE_FILE_PATH: Final[str] = "cache_file_path"
    PACKAGE_VERSION: Final[str] = "package_version"


class CatalogFilePaths:
    """Default file paths for catalog operations."""

    # Cache file name
    CACHE_FILENAME: Final[str] = "bedrock_catalog.json"

    # Bundled data location (relative to package root)
    BUNDLED_DATA_FILENAME: Final[str] = "bedrock_catalog_bundled.json"
    BUNDLED_DATA_DIRECTORY: Final[str] = "package_data"

    @staticmethod
    def get_default_cache_directory() -> Path:
        """
        Get platform-appropriate default cache directory.

        Returns:
            Path to default cache directory following OS conventions

        Implementation follows XDG Cache Standard:
        - Linux/Mac: ~/.cache/bestehorn-llmmanager/
        - Windows: %LOCALAPPDATA%\\bestehorn-llmmanager\\cache\\
        """
        if platform.system() == "Windows":
            # Windows: Use LOCALAPPDATA
            local_app_data = os.environ.get("LOCALAPPDATA")
            if local_app_data:
                return Path(local_app_data) / "bestehorn-llmmanager" / "cache"
            # Fallback to user home
            return Path.home() / ".bestehorn-llmmanager" / "cache"
        else:
            # Linux/Mac: Use XDG_CACHE_HOME or default
            xdg_cache = os.environ.get("XDG_CACHE_HOME")
            if xdg_cache:
                return Path(xdg_cache) / "bestehorn-llmmanager"
            return Path.home() / ".cache" / "bestehorn-llmmanager"

    @staticmethod
    def get_default_cache_file_path() -> Path:
        """
        Get the full path to the default cache file.

        Returns:
            Path to default cache file
        """
        return CatalogFilePaths.get_default_cache_directory() / CatalogFilePaths.CACHE_FILENAME

    @staticmethod
    def get_fallback_cache_directory() -> Path:
        """
        Get fallback cache directory (writable in Lambda).

        Returns:
            Path to /tmp/bestehorn-llmmanager-cache/
        """
        return Path("/tmp") / "bestehorn-llmmanager-cache"

    @staticmethod
    def get_all_cache_locations() -> List[Path]:
        """
        Get all cache locations in priority order.

        Returns:
            List of cache directory paths:
            1. Primary (platform-specific)
            2. Fallback (/tmp)
        """
        return [
            CatalogFilePaths.get_default_cache_directory(),
            CatalogFilePaths.get_fallback_cache_directory(),
        ]


class CatalogDefaults:
    """Default configuration values for catalog operations."""

    # Cache settings
    DEFAULT_CACHE_MAX_AGE_HOURS: Final[float] = 24.0
    DEFAULT_FORCE_REFRESH: Final[bool] = False
    DEFAULT_FALLBACK_TO_BUNDLED: Final[bool] = True

    # API settings
    DEFAULT_API_TIMEOUT_SECONDS: Final[int] = 30
    DEFAULT_MAX_WORKERS: Final[int] = 10
    DEFAULT_MAX_RETRIES: Final[int] = 3

    # Retry settings
    DEFAULT_RETRY_MIN_WAIT_SECONDS: Final[float] = 1.0
    DEFAULT_RETRY_MAX_WAIT_SECONDS: Final[float] = 10.0
    DEFAULT_RETRY_MULTIPLIER: Final[float] = 1.0

    # AWS regions to query (comprehensive list as of 2025)
    DEFAULT_AWS_REGIONS: Final[List[str]] = [
        "us-east-1",
        "us-east-2",
        "us-west-1",
        "us-west-2",
        "ca-central-1",
        "eu-west-1",
        "eu-west-2",
        "eu-west-3",
        "eu-central-1",
        "eu-north-1",
        "eu-south-1",
        "eu-south-2",
        "ap-northeast-1",
        "ap-northeast-2",
        "ap-northeast-3",
        "ap-southeast-1",
        "ap-southeast-2",
        "ap-southeast-3",
        "ap-southeast-4",
        "ap-south-1",
        "ap-south-2",
        "sa-east-1",
        "af-south-1",
        "me-south-1",
        "me-central-1",
    ]


class CatalogLogMessages:
    """Logging message templates for catalog operations."""

    # Initialization messages
    CATALOG_INIT_STARTED: Final[str] = "Initializing BedrockModelCatalog with cache_mode={mode}"
    CATALOG_INIT_COMPLETED: Final[str] = (
        "Catalog initialized successfully from {source} with {count} models"
    )

    # Cache messages
    CACHE_LOADING: Final[str] = "Loading catalog from cache: {path}"
    CACHE_LOADED: Final[str] = "Successfully loaded catalog from cache ({count} models)"
    CACHE_MISS: Final[str] = "Cache miss: {reason}"
    CACHE_INVALID: Final[str] = "Cache invalid: {reason}"
    CACHE_SAVING: Final[str] = "Saving catalog to cache: {path}"
    CACHE_SAVED: Final[str] = "Successfully saved catalog to cache"
    CACHE_SKIPPED: Final[str] = "Cache skipped (mode={mode})"
    CACHE_LOAD_ATTEMPT: Final[str] = "Attempting to load cache from: {path}"
    CACHE_LOAD_SUCCESS: Final[str] = "Loaded model catalog cache from {path}"
    CACHE_LOAD_FAILED: Final[str] = "Failed to load model catalog cache from {path}"
    CACHE_WRITE_ATTEMPT: Final[str] = "Attempting to write cache to: {path}"
    CACHE_WRITE_SUCCESS_PRIMARY: Final[str] = "Successfully saved catalog to cache: {path}"
    CACHE_WRITE_SUCCESS_FALLBACK: Final[str] = "Cache written to alternative location: {path}"
    CACHE_WRITE_FAILED: Final[str] = "Failed to write cache to {path}: {error}"
    CACHE_ALL_WRITES_FAILED: Final[str] = (
        "Cache data retrieved successfully but could not be written to disk. "
        "Using retrieved data in memory."
    )
    CATALOG_LOADED_INFO: Final[str] = (
        "Model catalog loaded: {model_count} models across {region_count} regions"
    )

    # API fetch messages
    API_FETCH_STARTED: Final[str] = "Fetching catalog data from AWS APIs ({regions} regions)"
    API_FETCH_COMPLETED: Final[str] = (
        "Successfully fetched data from {success}/{total} regions in {duration:.2f}s"
    )
    API_FETCH_REGION_STARTED: Final[str] = "Fetching data from region: {region}"
    API_FETCH_REGION_COMPLETED: Final[str] = "Region {region}: {models} models, {profiles} profiles"
    API_FETCH_REGION_FAILED: Final[str] = "Region {region} failed: {error}"
    API_RETRY_ATTEMPT: Final[str] = "Retrying API call (attempt {attempt}/{max_attempts}): {error}"

    # Bundled data messages
    BUNDLED_LOADING: Final[str] = "Loading bundled fallback data"
    BUNDLED_LOADED: Final[str] = (
        "Loaded bundled data (version={version}, {count} models, generated={timestamp})"
    )
    BUNDLED_WARNING: Final[str] = (
        "Using bundled fallback data which may be stale. "
        "Consider checking network connectivity or AWS credentials."
    )

    # Transformation messages
    TRANSFORMATION_STARTED: Final[str] = "Transforming API data to unified catalog"
    TRANSFORMATION_MODELS_COMPLETED: Final[str] = "Model transformation completed: {count} models"
    TRANSFORMATION_CRIS_COMPLETED: Final[str] = "CRIS transformation completed: {count} models"
    TRANSFORMATION_COMPLETED: Final[str] = "Transformation completed: {count} unified models"
    TRANSFORM_STARTED: Final[str] = "Transforming API data to unified catalog"
    TRANSFORM_COMPLETED: Final[str] = (
        "Transformation completed: {models} models, {profiles} profiles"
    )

    # Query messages
    QUERY_MODEL_INFO: Final[str] = "Querying model info: {model_name} in {region}"
    QUERY_LIST_MODELS: Final[str] = "Listing models with filters: {filters}"

    # Error messages
    ERROR_ALL_SOURCES_FAILED: Final[str] = (
        "Failed to load catalog from all sources (cache, API, bundled)"
    )
    ERROR_API_FETCH_FAILED: Final[str] = "API fetch failed: {error}"
    ERROR_CACHE_READ_FAILED: Final[str] = "Cache read failed: {error}"
    ERROR_CACHE_WRITE_FAILED: Final[str] = "Cache write failed: {error}"
    ERROR_BUNDLED_LOAD_FAILED: Final[str] = "Bundled data load failed: {error}"
    ERROR_TRANSFORM_FAILED: Final[str] = "Data transformation failed: {error}"


class CatalogErrorMessages:
    """Error message templates for catalog exceptions."""

    # CatalogUnavailableError messages
    CATALOG_UNAVAILABLE: Final[str] = (
        "Catalog data unavailable from all sources. "
        "Cache: {cache_error}. API: {api_error}. Bundled: {bundled_error}."
    )
    CATALOG_UNAVAILABLE_NO_BUNDLED: Final[str] = (
        "Catalog data unavailable and bundled fallback is disabled. "
        "Cache: {cache_error}. API: {api_error}."
    )

    # APIFetchError messages
    API_FETCH_ALL_REGIONS_FAILED: Final[str] = (
        "Failed to fetch data from all {count} regions. Last error: {error}"
    )
    API_FETCH_TIMEOUT: Final[str] = "API call timed out after {timeout}s: {operation}"
    API_FETCH_AUTH_ERROR: Final[str] = (
        "AWS authentication failed. Check credentials and permissions: {error}"
    )
    API_FETCH_THROTTLED: Final[str] = (
        "API rate limit exceeded. Consider reducing max_workers or retry later: {error}"
    )
    API_FETCH_INVALID_RESPONSE: Final[str] = "Invalid API response structure: {error}"

    # CacheError messages
    CACHE_READ_ERROR: Final[str] = "Failed to read cache file {path}: {error}"
    CACHE_WRITE_ERROR: Final[str] = "Failed to write cache file {path}: {error}"
    CACHE_INVALID_JSON: Final[str] = "Cache file contains invalid JSON: {path}"
    CACHE_INVALID_STRUCTURE: Final[str] = "Cache file has invalid structure: {error}"
    CACHE_DIRECTORY_ERROR: Final[str] = "Failed to create cache directory {path}: {error}"
    CACHE_PERMISSION_ERROR: Final[str] = (
        "Permission denied for cache directory {path}. "
        "Consider using cache_mode='memory' or cache_mode='none'."
    )

    # BundledDataError messages
    BUNDLED_DATA_MISSING: Final[str] = (
        "Bundled data file not found: {path}. Package may be corrupted."
    )
    BUNDLED_DATA_INVALID_JSON: Final[str] = "Bundled data contains invalid JSON: {error}"
    BUNDLED_DATA_INVALID_STRUCTURE: Final[str] = "Bundled data has invalid structure: {error}"
    BUNDLED_DATA_TOO_OLD: Final[str] = (
        "Bundled data is too old ({age} days). Consider updating the package."
    )

    # Transformation error messages
    TRANSFORMATION_NO_DATA: Final[str] = "No data available for transformation"
    TRANSFORMATION_FAILED: Final[str] = "Data transformation failed: {error}"

    # Validation error messages
    INVALID_CACHE_MODE: Final[str] = (
        "Invalid cache_mode: {mode}. Must be 'file', 'memory', or 'none'."
    )
    INVALID_CACHE_DIRECTORY: Final[str] = "Invalid cache_directory: {path}"
    INVALID_CACHE_MAX_AGE: Final[str] = (
        "Invalid cache_max_age_hours: {value}. Must be positive number."
    )
    INVALID_TIMEOUT: Final[str] = "Invalid timeout: {value}. Must be positive integer."
    INVALID_MAX_WORKERS: Final[str] = "Invalid max_workers: {value}. Must be positive integer."
    INVALID_MODEL_NAME: Final[str] = "Invalid model name: {name}"
    INVALID_REGION: Final[str] = "Invalid AWS region: {region}"

    # General error messages
    UNEXPECTED_ERROR: Final[str] = "Unexpected error during catalog operation: {error}"


class CatalogVersioning:
    """Constants for catalog versioning and compatibility."""

    # Bundled data version format
    VERSION_FORMAT: Final[str] = "YYYY-MM-DD"

    # Cache compatibility
    CACHE_FORMAT_VERSION: Final[str] = "1.0"

    # Package version compatibility
    # Cache is compatible if major.minor versions match
    VERSION_COMPATIBILITY_LEVEL: Final[str] = "major.minor"


class CatalogMetrics:
    """Constants for catalog performance metrics and monitoring."""

    # Metric names
    METRIC_CACHE_HIT: Final[str] = "catalog.cache.hit"
    METRIC_CACHE_MISS: Final[str] = "catalog.cache.miss"
    METRIC_API_FETCH_DURATION: Final[str] = "catalog.api.fetch.duration"
    METRIC_API_FETCH_SUCCESS: Final[str] = "catalog.api.fetch.success"
    METRIC_API_FETCH_FAILURE: Final[str] = "catalog.api.fetch.failure"
    METRIC_BUNDLED_FALLBACK: Final[str] = "catalog.bundled.fallback"
    METRIC_TRANSFORM_DURATION: Final[str] = "catalog.transform.duration"
    METRIC_QUERY_DURATION: Final[str] = "catalog.query.duration"

    # Metric labels
    LABEL_CACHE_MODE: Final[str] = "cache_mode"
    LABEL_SOURCE: Final[str] = "source"
    LABEL_REGION: Final[str] = "region"
    LABEL_OPERATION: Final[str] = "operation"
