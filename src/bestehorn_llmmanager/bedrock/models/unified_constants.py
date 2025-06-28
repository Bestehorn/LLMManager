"""
Constants for unified model management system.
Contains string constants for the integrated model and CRIS data.
"""

from typing import Dict, Final


class UnifiedJSONFields:
    """JSON field constants for the unified model catalog structure."""

    # Root level fields
    RETRIEVAL_TIMESTAMP: Final[str] = "retrieval_timestamp"
    UNIFIED_MODELS: Final[str] = "unified_models"

    # Model information fields
    MODEL_NAME: Final[str] = "model_name"
    PROVIDER: Final[str] = "provider"
    MODEL_ID: Final[str] = "model_id"
    INPUT_MODALITIES: Final[str] = "input_modalities"
    OUTPUT_MODALITIES: Final[str] = "output_modalities"
    STREAMING_SUPPORTED: Final[str] = "streaming_supported"
    INFERENCE_PARAMETERS_LINK: Final[str] = "inference_parameters_link"
    HYPERPARAMETERS_LINK: Final[str] = "hyperparameters_link"

    # Region access information
    REGION_ACCESS: Final[str] = "region_access"
    ACCESS_METHOD: Final[str] = "access_method"
    REGION: Final[str] = "region"
    INFERENCE_PROFILE_ID: Final[str] = "inference_profile_id"

    # Access method values
    ACCESS_DIRECT: Final[str] = "direct"
    ACCESS_CRIS_ONLY: Final[str] = "cris_only"
    ACCESS_BOTH: Final[str] = "both"


class ModelCorrelationConstants:
    """Constants for model name correlation between systems."""

    # Common prefixes to normalize
    ANTHROPIC_PREFIX: Final[str] = "anthropic."
    META_PREFIX: Final[str] = "meta."
    AMAZON_PREFIX: Final[str] = "amazon."
    MISTRAL_PREFIX: Final[str] = "mistral."

    # Model name mappings (CRIS name -> Standard name)
    MODEL_NAME_MAPPINGS: Final[Dict[str, str]] = {
        "Anthropic Claude 3 Haiku": "Claude 3 Haiku",
        "Anthropic Claude 3 Sonnet": "Claude 3 Sonnet",
        "Anthropic Claude 3 Opus": "Claude 3 Opus",
        "Anthropic Claude 3.5 Haiku": "Claude 3.5 Haiku",
        "Anthropic Claude 3.5 Sonnet": "Claude 3.5 Sonnet",
        "Anthropic Claude 3.5 Sonnet v2": "Claude 3.5 Sonnet v2",
        "Anthropic Claude 3.7 Sonnet": "Claude 3.7 Sonnet",
        "Meta Llama 3.1 8B Instruct": "Llama 3.1 8B Instruct",
        "Meta Llama 3.1 70B Instruct": "Llama 3.1 70B Instruct",
        "Meta Llama 3.1 Instruct 405B": "Llama 3.1 405B Instruct",
        "Meta Llama 3.2 1B Instruct": "Llama 3.2 1B Instruct",
        "Meta Llama 3.2 3B Instruct": "Llama 3.2 3B Instruct",
        "Meta Llama 3.2 11B Instruct": "Llama 3.2 11B Instruct",
        "Meta Llama 3.2 90B Instruct": "Llama 3.2 90B Instruct",
        "Meta Llama 3.3 70B Instruct": "Llama 3.3 70B Instruct",
        "Mistral Pixtral Large 25.02": "Pixtral Large (25.02)",
    }


class ModelCorrelationConfig:
    """Configuration constants for model correlation behavior."""

    # Fuzzy matching configuration
    ENABLE_FUZZY_MATCHING_DEFAULT: Final[bool] = True
    FUZZY_MATCHING_ENABLED_KEY: Final[str] = "fuzzy_matching_enabled"

    # Correlation matching strategy order
    EXACT_MAPPING_PRIORITY: Final[int] = 1
    FUZZY_MATCHING_PRIORITY: Final[int] = 2


class UnifiedLogMessages:
    """Logging message constants for unified model management."""

    CORRELATION_STARTED: Final[str] = "Starting model-CRIS correlation process"
    CORRELATION_COMPLETED: Final[str] = (
        "Model-CRIS correlation completed. Matched {matched_count} models"
    )
    UNMATCHED_MODELS: Final[str] = "Found {count} unmatched models: {models}"
    UNMATCHED_CRIS: Final[str] = "Found {count} unmatched CRIS models: {models}"
    UNIFIED_CATALOG_CREATED: Final[str] = "Created unified catalog with {model_count} models"
    REGION_MERGE_COMPLETED: Final[str] = "Region access merge completed for model {model_name}"
    CRIS_MARKER_DETECTED: Final[str] = (
        "Detected CRIS-only region marker (*) for model {model_name} in region {region}"
    )
    FUZZY_MATCH_APPLIED: Final[str] = (
        "Applied fuzzy matching for model '{regular_model}' -> CRIS model '{cris_model}'. No exact mapping was found, falling back to normalized name matching"
    )
    FUZZY_MATCHING_DISABLED: Final[str] = (
        "Fuzzy matching is disabled. Model '{model_name}' could not be matched to any CRIS model"
    )
    CORRELATION_CONFIG_LOADED: Final[str] = (
        "Model correlation configuration loaded. Fuzzy matching enabled: {fuzzy_enabled}"
    )


class UnifiedErrorMessages:
    """Error message constants for unified model management."""

    NO_MODEL_DATA: Final[str] = "No model data available. Call refresh_unified_data() first"
    MODEL_NOT_FOUND: Final[str] = "Model '{model_name}' not found in catalog"
    REGION_NOT_SUPPORTED: Final[str] = "Region '{region}' not supported for model '{model_name}'"
    INVALID_ACCESS_METHOD: Final[str] = "Invalid access method: {method}"
    CORRELATION_FAILED: Final[str] = "Failed to correlate model and CRIS data: {error}"
    CACHE_VALIDATION_FAILED: Final[str] = "Cache validation failed: {reason}"
    CACHE_CORRUPTED: Final[str] = "Cache file is corrupted or unreadable: {path}"
    CACHE_EXPIRED: Final[str] = (
        "Cache data is expired (age: {age_hours:.1f} hours, max: {max_age_hours:.1f} hours)"
    )
    AUTO_REFRESH_FAILED: Final[str] = "Automatic cache refresh failed: {error}"
    TIMESTAMP_PARSE_FAILED: Final[str] = "Failed to parse cache timestamp: {timestamp}"


class UnifiedFilePaths:
    """Default file path constants for unified system."""

    DEFAULT_UNIFIED_JSON_OUTPUT: Final[str] = "src/docs/UnifiedModels.json"
    DEFAULT_CORRELATION_LOG: Final[str] = "src/docs/ModelCorrelation.log"


class CacheManagementConstants:
    """Constants for cache management and validation."""

    # Default cache age settings
    DEFAULT_MAX_CACHE_AGE_HOURS: Final[float] = 24.0
    MIN_CACHE_AGE_HOURS: Final[float] = 0.1
    MAX_CACHE_AGE_HOURS: Final[float] = 168.0  # 1 week

    # Cache validation status
    CACHE_VALID: Final[str] = "valid"
    CACHE_MISSING: Final[str] = "missing"
    CACHE_CORRUPTED: Final[str] = "corrupted"
    CACHE_EXPIRED: Final[str] = "expired"

    # Timestamp format
    TIMESTAMP_FORMAT: Final[str] = "%Y-%m-%dT%H:%M:%S.%fZ"
    TIMESTAMP_FORMAT_FALLBACK: Final[str] = "%Y-%m-%dT%H:%M:%SZ"


class RegionMarkers:
    """Constants for region availability markers."""

    CRIS_ONLY_MARKER: Final[str] = "*"
    REGION_SEPARATOR: Final[str] = ","


class AccessMethodPriority:
    """Priority constants for access method recommendations."""

    # Lower numbers indicate higher priority
    DIRECT_PRIORITY: Final[int] = 1
    CRIS_PRIORITY: Final[int] = 2

    PRIORITY_RATIONALES: Final[Dict[str, str]] = {
        "direct_preferred": "Direct access provides lower latency and simpler configuration",
        "cris_only": "Only available through Cross-Region Inference Service",
        "cris_preferred": "CRIS provides better quota management and routing optimization",
    }
