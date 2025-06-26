"""
Constants module for Amazon Bedrock model management.
Contains all string literals used throughout the application to ensure maintainability.
"""

from typing import Final


class JSONFields:
    """JSON field name constants for the output structure."""

    RETRIEVAL_TIMESTAMP: Final[str] = "retrieval_timestamp"
    MODELS: Final[str] = "models"
    PROVIDER: Final[str] = "provider"
    MODEL_ID: Final[str] = "model_id"
    REGIONS_SUPPORTED: Final[str] = "regions_supported"
    INPUT_MODALITIES: Final[str] = "input_modalities"
    OUTPUT_MODALITIES: Final[str] = "output_modalities"
    STREAMING_SUPPORTED: Final[str] = "streaming_supported"
    INFERENCE_PARAMETERS_LINK: Final[str] = "inference_parameters_link"
    HYPERPARAMETERS_LINK: Final[str] = "hyperparameters_link"


class HTMLTableColumns:
    """HTML table column name constants for parsing."""

    PROVIDER: Final[str] = "Provider"
    MODEL_NAME: Final[str] = "Model name"
    MODEL_ID: Final[str] = "Model ID"
    REGIONS_SUPPORTED: Final[str] = "Regions supported"
    INPUT_MODALITIES: Final[str] = "Input modalities"
    OUTPUT_MODALITIES: Final[str] = "Output modalities"
    STREAMING_SUPPORTED: Final[str] = "Streaming supported"
    INFERENCE_PARAMETERS: Final[str] = "Inference parameters"
    HYPERPARAMETERS: Final[str] = "Hyperparameters"


class BooleanValues:
    """Constants for boolean value conversion."""

    YES: Final[str] = "Yes"
    NO: Final[str] = "No"
    NOT_AVAILABLE: Final[str] = "N/A"


class URLs:
    """URL constants for documentation and API endpoints."""

    BEDROCK_MODELS_DOCUMENTATION: Final[str] = (
        "https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html"
    )


class FilePaths:
    """Default file path constants."""

    DEFAULT_HTML_OUTPUT: Final[str] = "docs/FoundationalModels.htm"
    DEFAULT_JSON_OUTPUT: Final[str] = "docs/FoundationalModels.json"


class LogMessages:
    """Logging message constants."""

    DOWNLOAD_STARTED: Final[str] = "Starting download of Bedrock documentation"
    DOWNLOAD_COMPLETED: Final[str] = "Successfully downloaded documentation to {file_path}"
    PARSING_STARTED: Final[str] = "Starting HTML parsing"
    PARSING_COMPLETED: Final[str] = "Successfully parsed {model_count} models"
    JSON_EXPORT_STARTED: Final[str] = "Starting JSON export"
    JSON_EXPORT_COMPLETED: Final[str] = "Successfully exported JSON to {file_path}"
    NETWORK_ERROR: Final[str] = "Network error during download: {error}"
    PARSING_ERROR: Final[str] = "Error parsing HTML: {error}"
    FILE_ERROR: Final[str] = "File operation error: {error}"
