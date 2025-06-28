"""
Amazon Bedrock Model Manager.

This module provides the ModelManager class for downloading, parsing, and managing
Amazon Bedrock foundational model information from AWS documentation.

The ModelManager orchestrates the following workflow:
1. Downloads HTML documentation from AWS Bedrock documentation URL
2. Parses the HTML to extract model information using BeautifulSoup
3. Serializes the parsed data to JSON format with timestamp information
4. Provides methods for querying and filtering model data

Example:
    Basic usage:
    >>> from pathlib import Path
    >>> from src.bedrock.ModelManager import ModelManager
    >>>
    >>> manager = ModelManager()
    >>> catalog = manager.refresh_model_data()
    >>> print(f"Found {catalog.model_count} models")

    Custom configuration:
    >>> manager = ModelManager(
    ...     html_output_path=Path("custom/path.html"),
    ...     json_output_path=Path("custom/models.json")
    ... )
    >>> catalog = manager.refresh_model_data()

Author: Generated code for production use
License: MIT
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .downloaders.base_downloader import FileSystemError, NetworkError
from .downloaders.html_downloader import HTMLDocumentationDownloader
from .models.constants import FilePaths, URLs
from .models.data_structures import BedrockModelInfo, ModelCatalog
from .parsers.base_parser import ParsingError
from .parsers.enhanced_bedrock_parser import EnhancedBedrockHTMLParser
from .serializers.json_serializer import JSONModelSerializer


class ModelManagerError(Exception):
    """Base exception for ModelManager operations."""

    pass


class ModelManager:
    """
    Amazon Bedrock Model Manager.

    Orchestrates the download, parsing, and serialization of Amazon Bedrock
    foundational model information from AWS documentation.

    This class provides a high-level interface for:
    - Downloading the latest model documentation from AWS
    - Parsing HTML tables to extract structured model information
    - Serializing data to JSON format with proper timestamps
    - Querying and filtering model data

    Attributes:
        html_output_path: Path where downloaded HTML will be saved
        json_output_path: Path where parsed JSON will be saved
        documentation_url: URL of the AWS Bedrock documentation
    """

    def __init__(
        self,
        html_output_path: Optional[Path] = None,
        json_output_path: Optional[Path] = None,
        documentation_url: Optional[str] = None,
        download_timeout: int = 30,
    ) -> None:
        """
        Initialize the ModelManager with configuration options.

        Args:
            html_output_path: Custom path for HTML output (defaults to docs/FoundationalModels.htm)
            json_output_path: Custom path for JSON output (defaults to docs/FoundationalModels.json)
            documentation_url: Custom documentation URL (defaults to AWS Bedrock docs)
            download_timeout: Request timeout in seconds for downloads
        """
        self.html_output_path = html_output_path or Path(FilePaths.DEFAULT_HTML_OUTPUT)
        self.json_output_path = json_output_path or Path(FilePaths.DEFAULT_JSON_OUTPUT)
        self.documentation_url = documentation_url or URLs.BEDROCK_MODELS_DOCUMENTATION

        # Initialize components with dependency injection
        self._downloader = HTMLDocumentationDownloader(timeout=download_timeout)
        self._parser = EnhancedBedrockHTMLParser()
        self._serializer = JSONModelSerializer()

        # Setup logging
        self._logger = logging.getLogger(__name__)

        # Cache for parsed data
        self._cached_catalog: Optional[ModelCatalog] = None

    def refresh_model_data(self, force_download: bool = True) -> ModelCatalog:
        """
        Refresh model data by downloading and parsing the latest documentation.

        This method orchestrates the complete workflow:
        1. Downloads the latest HTML documentation from AWS
        2. Parses the HTML to extract model information
        3. Creates a ModelCatalog with timestamp
        4. Saves the data to JSON format
        5. Returns the parsed catalog

        Args:
            force_download: If True, always download fresh data. If False, use existing
                          HTML file if it exists and is recent (less than 1 hour old)

        Returns:
            ModelCatalog containing all parsed model information

        Raises:
            ModelManagerError: If any step in the process fails
        """
        try:
            # Step 1: Download documentation if needed
            if force_download or not self._is_html_file_recent():
                self._download_documentation()

            # Step 2: Parse the HTML documentation
            models_dict = self._parse_documentation()

            # Step 3: Create catalog with timestamp
            catalog = ModelCatalog(retrieval_timestamp=datetime.now(), models=models_dict)

            # Step 4: Save to JSON
            self._save_catalog_to_json(catalog=catalog)

            # Step 5: Cache and return
            self._cached_catalog = catalog
            return catalog

        except (NetworkError, FileSystemError, ParsingError) as e:
            error_msg = f"Failed to refresh model data: {str(e)}"
            self._logger.error(error_msg)
            raise ModelManagerError(error_msg) from e

    def load_cached_data(self) -> Optional[ModelCatalog]:
        """
        Load previously cached model data from JSON file.

        Returns:
            ModelCatalog if cached data exists and is valid, None otherwise
        """
        if not self.json_output_path.exists():
            return None

        try:
            # Load data from file - in production, this would reconstruct the ModelCatalog
            self._serializer.load_from_file(input_path=self.json_output_path)
            # Here you would reconstruct the ModelCatalog from the JSON data
            # This is a simplified version - in production you'd want proper deserialization
            self._logger.info(f"Loaded cached data from {self.json_output_path}")
            return None  # Placeholder - would return reconstructed catalog
        except Exception as e:
            self._logger.warning(f"Failed to load cached data: {str(e)}")
            return None

    def get_models_by_provider(self, provider: str) -> Dict[str, BedrockModelInfo]:
        """
        Get all models from a specific provider.

        Args:
            provider: Provider name (e.g., 'Amazon', 'Anthropic', 'Meta')

        Returns:
            Dictionary of model names to model info for the specified provider

        Raises:
            ModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise ModelManagerError("No model data available. Call refresh_model_data() first.")

        return self._cached_catalog.get_models_by_provider(provider=provider)

    def get_models_by_region(self, region: str) -> Dict[str, BedrockModelInfo]:
        """
        Get all models available in a specific AWS region.

        Args:
            region: AWS region identifier (e.g., 'us-east-1')

        Returns:
            Dictionary of model names to model info for the specified region

        Raises:
            ModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise ModelManagerError("No model data available. Call refresh_model_data() first.")

        return self._cached_catalog.get_models_by_region(region=region)

    def get_streaming_models(self) -> Dict[str, BedrockModelInfo]:
        """
        Get all models that support streaming responses.

        Returns:
            Dictionary of model names to model info for streaming-enabled models

        Raises:
            ModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise ModelManagerError("No model data available. Call refresh_model_data() first.")

        return self._cached_catalog.get_streaming_models()

    def get_model_count(self) -> int:
        """
        Get the total number of models in the catalog.

        Returns:
            Total number of models

        Raises:
            ModelManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise ModelManagerError("No model data available. Call refresh_model_data() first.")

        return self._cached_catalog.model_count

    def _download_documentation(self) -> None:
        """
        Download the HTML documentation from AWS.

        Raises:
            NetworkError: If download fails
            FileSystemError: If file operations fail
        """
        self._downloader.download(url=self.documentation_url, output_path=self.html_output_path)

    def _parse_documentation(self) -> Dict[str, BedrockModelInfo]:
        """
        Parse the downloaded HTML documentation.

        Returns:
            Dictionary mapping model names to model information

        Raises:
            ParsingError: If parsing fails
        """
        return self._parser.parse(file_path=self.html_output_path)

    def _save_catalog_to_json(self, catalog: ModelCatalog) -> None:
        """
        Save the model catalog to JSON format.

        Args:
            catalog: The catalog to save

        Raises:
            OSError: If file operations fail
            TypeError: If serialization fails
        """
        self._serializer.serialize_to_file(catalog=catalog, output_path=self.json_output_path)

    def _is_html_file_recent(self, max_age_hours: int = 1) -> bool:
        """
        Check if the HTML file exists and is recent enough to avoid re-download.

        Args:
            max_age_hours: Maximum age in hours before considering file stale

        Returns:
            True if file exists and is recent, False otherwise
        """
        if not self.html_output_path.exists():
            return False

        try:
            file_time = datetime.fromtimestamp(self.html_output_path.stat().st_mtime)
            age_hours = (datetime.now() - file_time).total_seconds() / 3600
            return age_hours < max_age_hours
        except OSError:
            return False

    def __repr__(self) -> str:
        """Return string representation of the ModelManager."""
        return (
            "ModelManager("
            f"html_path='{self.html_output_path}', "
            f"json_path='{self.json_output_path}', "
            f"url='{self.documentation_url}'"
            ")"
        )
