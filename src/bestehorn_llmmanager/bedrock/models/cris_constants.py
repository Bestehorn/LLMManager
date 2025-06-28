"""
CRIS-specific constants for Amazon Bedrock Cross-Region Inference management.
Contains all string literals and configuration values used throughout the CRIS implementation.
"""

from typing import Final, List


class CRISJSONFields:
    """JSON field name constants for CRIS output structure."""

    RETRIEVAL_TIMESTAMP: Final[str] = "retrieval_timestamp"
    CRIS: Final[str] = "CRIS"
    MODEL_NAME: Final[str] = "model_name"
    INFERENCE_PROFILES: Final[str] = "inference_profiles"
    REGION_MAPPINGS: Final[str] = "region_mappings"

    # Backward compatibility field
    INFERENCE_PROFILE_ID: Final[str] = "inference_profile_id"

    # Regional variant fields
    REGION_PREFIX: Final[str] = "region_prefix"
    REGIONAL_VARIANTS: Final[str] = "regional_variants"
    ALL_INFERENCE_PROFILES: Final[str] = "all_inference_profiles"


class CRISHTMLSelectors:
    """HTML selectors and patterns for CRIS documentation parsing."""

    EXPANDABLE_SECTION: Final[str] = "awsui-expandable-section"
    CODE_BLOCK: Final[str] = "code"
    TABLE_CONTAINER: Final[str] = "table-container"
    TABLE_ROW: Final[str] = "tr"
    TABLE_CELL: Final[str] = "td"
    TABLE_HEADER: Final[str] = "th"
    PARAGRAPH: Final[str] = "p"


class CRISHTMLAttributes:
    """HTML attribute names for CRIS parsing."""

    HEADER: Final[str] = "header"
    ID: Final[str] = "id"
    VARIANT: Final[str] = "variant"
    EXPANDED: Final[str] = "expanded"
    TABINDEX: Final[str] = "tabindex"


class CRISTableColumns:
    """Expected table column names in CRIS documentation."""

    SOURCE_REGION: Final[str] = "Source Region"
    DESTINATION_REGIONS: Final[str] = "Destination Regions"


class CRISRegionPrefixes:
    """Common region prefixes found in CRIS model names."""

    US_PREFIX: Final[str] = "US "
    EU_PREFIX: Final[str] = "EU "
    APAC_PREFIX: Final[str] = "APAC "

    # Constants for region prefix identification
    US_IDENTIFIER: Final[str] = "US"
    EU_IDENTIFIER: Final[str] = "EU"
    APAC_IDENTIFIER: Final[str] = "APAC"

    # Default primary region preference order
    PRIMARY_PREFERENCE_ORDER: Final[List[str]] = [US_IDENTIFIER, EU_IDENTIFIER, APAC_IDENTIFIER]


class CRISInferenceProfileStructure:
    """Constants for the new inference profile structure in JSON."""

    PROFILE_DATA: Final[str] = "profile_data"
    REGION_MAPPINGS: Final[str] = "region_mappings"


class CRISURLs:
    """URL constants for CRIS documentation and API endpoints."""

    DOCUMENTATION: Final[str] = (
        "https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html#inference-profiles-support-system"
    )


class CRISFilePaths:
    """Default file path constants for CRIS operations."""

    DEFAULT_HTML_OUTPUT: Final[str] = "docs/CRIS.htm"
    DEFAULT_JSON_OUTPUT: Final[str] = "docs/CRIS.json"


class CRISLogMessages:
    """Logging message constants for CRIS operations."""

    DOWNLOAD_STARTED: Final[str] = "Starting download of CRIS documentation"
    DOWNLOAD_COMPLETED: Final[str] = "Successfully downloaded CRIS documentation to {file_path}"
    PARSING_STARTED: Final[str] = "Starting CRIS HTML parsing"
    PARSING_COMPLETED: Final[str] = "Successfully parsed {model_count} CRIS models"
    JSON_EXPORT_STARTED: Final[str] = "Starting CRIS JSON export"
    JSON_EXPORT_COMPLETED: Final[str] = "Successfully exported CRIS JSON to {file_path}"
    CACHE_LOADED: Final[str] = "Loaded cached CRIS data from {file_path}"
    CACHE_MISS: Final[str] = "No valid cached CRIS data found"
    SECTION_PARSED: Final[str] = "Parsed CRIS model: {model_name}"
    SECTION_SKIPPED: Final[str] = "Skipped invalid CRIS section: {section_id}"
    NETWORK_ERROR: Final[str] = "Network error during CRIS download: {error}"
    PARSING_ERROR: Final[str] = "Error parsing CRIS HTML: {error}"
    FILE_ERROR: Final[str] = "File operation error during CRIS processing: {error}"

    # Messages for inference profile processing
    INFERENCE_PROFILE_ADDED: Final[str] = (
        "Added inference profile {profile_id} for model {model_name}"
    )
    DUPLICATE_PROFILE_DETECTED: Final[str] = (
        "Duplicate inference profile {profile_id} detected for model {model_name}"
    )


class CRISErrorMessages:
    """Error message constants for CRIS operations."""

    NO_DATA_AVAILABLE: Final[str] = "No CRIS data available. Call refresh_cris_data() first."
    INVALID_MODEL_NAME: Final[str] = "Invalid model name: {model_name}"
    INVALID_REGION: Final[str] = "Invalid region: {region}"
    MALFORMED_SECTION: Final[str] = "Malformed expandable section: {section_id}"
    MISSING_INFERENCE_PROFILE: Final[str] = "Missing inference profile ID in section: {section_id}"
    MISSING_REGION_TABLE: Final[str] = "Missing region mapping table in section: {section_id}"
    EMPTY_MODEL_NAME: Final[str] = "Empty or invalid model name extracted from header: {header}"

    # Error messages for inference profile structure
    CONFLICTING_INFERENCE_PROFILES: Final[str] = (
        "Conflicting data for inference profile: {profile_id}"
    )
    INVALID_INFERENCE_PROFILE: Final[str] = "Invalid inference profile ID: {profile_id}"
    NO_INFERENCE_PROFILES: Final[str] = "Model {model_name} has no inference profiles"

    # Regional variant error messages
    INVALID_REGION_PREFIX: Final[str] = "Invalid region prefix: {region_prefix}"
    NO_REGIONAL_VARIANTS: Final[str] = "Model {model_name} has no regional variants"


class CRISValidationPatterns:
    """Regex patterns for CRIS data validation."""

    INFERENCE_PROFILE_PATTERN: Final[str] = r"^[a-z0-9\-\.]+([:-][a-z0-9\-]+)?$"
    AWS_REGION_PATTERN: Final[str] = r"^[a-z0-9\-]+$"
    MODEL_NAME_PATTERN: Final[str] = r"^[A-Za-z0-9\s\-\.]+$"
    REGION_PREFIX_PATTERN: Final[str] = r"^(US|EU|APAC)$"
