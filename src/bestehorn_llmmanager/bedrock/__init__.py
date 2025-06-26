"""
Amazon Bedrock Model Management Package.

This package provides comprehensive tools for downloading, parsing, and managing
Amazon Bedrock foundational model information from AWS documentation.

Main Components:
    ModelManager: High-level orchestrator for all operations
    BedrockHTMLParser: Parses AWS documentation HTML tables
    JSONModelSerializer: Serializes model data to JSON format
    HTMLDocumentationDownloader: Downloads documentation from AWS URLs

Example Usage:
    >>> from src.bedrock import ModelManager
    >>>
    >>> # Basic usage with defaults
    >>> manager = ModelManager()
    >>> catalog = manager.refresh_model_data()
    >>> print(f"Found {catalog.model_count} models")
    >>>
    >>> # Get models by provider
    >>> amazon_models = manager.get_models_by_provider("Amazon")
    >>> print(f"Amazon has {len(amazon_models)} models")
    >>>
    >>> # Get models available in specific region
    >>> us_east_models = manager.get_models_by_region("us-east-1")
    >>> print(f"US East 1 has {len(us_east_models)} models")

Package Structure:
    models/: Data structures, constants, and type definitions
    downloaders/: HTTP downloaders for documentation retrieval
    parsers/: HTML parsers using BeautifulSoup
    serializers/: JSON serialization utilities
"""

from .downloaders.html_downloader import HTMLDocumentationDownloader
from .ModelManager import ModelManager, ModelManagerError
from .models.aws_regions import AWSRegions
from .models.constants import FilePaths, HTMLTableColumns, JSONFields, URLs
from .models.data_structures import BedrockModelInfo, ModelCatalog
from .parsers.bedrock_parser import BedrockHTMLParser
from .serializers.json_serializer import JSONModelSerializer

# Package metadata
__version__ = "1.0.0"
__author__ = "Generated for Production Use"
__description__ = "Amazon Bedrock Model Management Tools"

# Public API
__all__ = [
    # Main classes
    "ModelManager",
    "ModelManagerError",
    # Data structures
    "ModelCatalog",
    "BedrockModelInfo",
    # Constants
    "JSONFields",
    "HTMLTableColumns",
    "URLs",
    "FilePaths",
    "AWSRegions",
    # Component classes for advanced usage
    "BedrockHTMLParser",
    "HTMLDocumentationDownloader",
    "JSONModelSerializer",
]
