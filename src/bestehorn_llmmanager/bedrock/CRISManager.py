"""
Amazon Bedrock CRIS (Cross-Region Inference) Manager.

This module provides the CRISManager class for downloading, parsing, and managing
Amazon Bedrock Cross-Region Inference model information from AWS documentation.

The CRISManager orchestrates the following workflow:
1. Downloads HTML documentation from AWS Bedrock CRIS documentation URL
2. Parses the HTML to extract CRIS model information using BeautifulSoup
3. Serializes the parsed data to JSON format with timestamp information
4. Provides methods for querying and filtering CRIS model data

Example:
    Basic usage:
    >>> from pathlib import Path
    >>> from src.bedrock.CRISManager import CRISManager
    >>>
    >>> manager = CRISManager()
    >>> catalog = manager.refresh_cris_data()
    >>> print(f"Found {catalog.model_count} CRIS models")

    Custom configuration:
    >>> manager = CRISManager(
    ...     html_output_path=Path("custom/cris.html"),
    ...     json_output_path=Path("custom/cris.json")
    ... )
    >>> catalog = manager.refresh_cris_data()

Author: Generated code for production use
License: MIT
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .auth.auth_manager import AuthManager
from .discovery.region_discovery import BedrockRegionDiscovery
from .downloaders.html_downloader import HTMLDocumentationDownloader
from .fetchers.cris_api_fetcher import CRISAPIFetcher, CRISAPIFetcherError
from .models.cris_constants import CRISErrorMessages, CRISFilePaths, CRISLogMessages, CRISURLs
from .models.cris_structures import CRISCatalog, CRISModelInfo
from .parsers.cris_parser import CRISHTMLParser
from .serializers.json_serializer import JSONModelSerializer


class CRISManagerError(Exception):
    """Base exception for CRISManager operations."""

    pass


class CRISManager:
    """
    Amazon Bedrock CRIS (Cross-Region Inference) Manager.

    Orchestrates the download, parsing, and serialization of Amazon Bedrock
    Cross-Region Inference model information from AWS documentation.

    This class provides a high-level interface for:
    - Downloading the latest CRIS documentation from AWS
    - Parsing HTML expandable sections to extract structured CRIS model information
    - Serializing data to JSON format with proper timestamps
    - Querying and filtering CRIS model data by source/destination regions

    Attributes:
        html_output_path: Path where downloaded HTML will be saved
        json_output_path: Path where parsed JSON will be saved
        documentation_url: URL of the AWS Bedrock CRIS documentation
    """

    def __init__(
        self,
        html_output_path: Optional[Path] = None,
        json_output_path: Optional[Path] = None,
        documentation_url: Optional[str] = None,
        download_timeout: int = 30,
        use_api: bool = True,
        auth_manager: Optional[AuthManager] = None,
    ) -> None:
        """
        Initialize the CRISManager with configuration options.

        Args:
            html_output_path: Custom path for HTML output (defaults to docs/CRIS.htm)
            json_output_path: Custom path for JSON output (defaults to docs/CRIS.json)
            documentation_url: Custom documentation URL (defaults to AWS Bedrock CRIS docs)
            download_timeout: Request timeout in seconds for downloads
            use_api: If True, use AWS Bedrock API for CRIS data (recommended). If False, use HTML parsing.
            auth_manager: Optional AuthManager for AWS authentication. If None and use_api=True, a default will be created.
        """
        self.html_output_path = html_output_path or Path(CRISFilePaths.DEFAULT_HTML_OUTPUT)
        self.json_output_path = json_output_path or Path(CRISFilePaths.DEFAULT_JSON_OUTPUT)
        self.documentation_url = documentation_url or CRISURLs.DOCUMENTATION
        self._use_api = use_api

        # Initialize components with dependency injection
        self._downloader = HTMLDocumentationDownloader(timeout=download_timeout)
        self._parser = CRISHTMLParser()
        self._serializer = JSONModelSerializer()

        # Initialize API components based on use_api flag
        self._auth_manager: Optional[AuthManager] = (
            auth_manager or AuthManager() if self._use_api else None
        )
        self._region_discovery: Optional[BedrockRegionDiscovery] = (
            BedrockRegionDiscovery() if self._use_api else None
        )
        self._api_fetcher: Optional[CRISAPIFetcher] = (
            CRISAPIFetcher(auth_manager=self._auth_manager) if self._use_api and self._auth_manager else None
        )

        # Setup logging
        self._logger = logging.getLogger(__name__)

        # Cache for parsed data
        self._cached_catalog: Optional[CRISCatalog] = None

    def refresh_cris_data(self, force_download: bool = True) -> CRISCatalog:
        """
        Refresh CRIS data using API (preferred) or HTML parsing (fallback).

        This method uses the AWS Bedrock API by default for more reliable data fetching.
        If API fetching fails, it automatically falls back to HTML parsing.

        Args:
            force_download: If True, always fetch fresh data. If False, use cached data if available.

        Returns:
            CRISCatalog containing all parsed CRIS model information

        Raises:
            CRISManagerError: If both API and HTML methods fail
        """
        try:
            if self._use_api:
                # Try API method first
                try:
                    return self._refresh_via_api()
                except Exception as e:
                    self._logger.warning(f"API fetch failed: {e}. Falling back to HTML parsing...")
                    # Fall through to HTML method

            # Use HTML method (either by choice or as fallback)
            return self._refresh_via_html(force_download)

        except Exception as e:
            error_msg = f"Failed to refresh CRIS data: {str(e)}"
            self._logger.error(error_msg)
            raise CRISManagerError(error_msg) from e

    def _refresh_via_api(self) -> CRISCatalog:
        """
        Refresh CRIS data using AWS Bedrock API.

        Returns:
            CRISCatalog containing all parsed CRIS model information

        Raises:
            Exception: If API fetch fails
        """
        if not self._region_discovery or not self._api_fetcher:
            raise CRISManagerError("API components not initialized. Set use_api=True during initialization.")
        
        self._logger.info("Refreshing CRIS data via AWS Bedrock API")

        # Step 1: Discover Bedrock-enabled regions
        regions = self._region_discovery.get_bedrock_regions()
        self._logger.info(f"Discovered {len(regions)} Bedrock-enabled regions")

        # Step 2: Fetch CRIS data from all regions in parallel
        models_dict = self._api_fetcher.fetch_cris_data(regions)

        if not models_dict:
            raise CRISAPIFetcherError("No CRIS models found via API")

        # Step 3: Create catalog with timestamp
        catalog = CRISCatalog(retrieval_timestamp=datetime.now(), cris_models=models_dict)

        # Step 4: Save to JSON
        self._save_catalog_to_json(catalog=catalog)

        # Step 5: Cache and return
        self._cached_catalog = catalog
        self._logger.info(f"Successfully fetched {len(models_dict)} CRIS models via API")
        return catalog

    def _refresh_via_html(self, force_download: bool) -> CRISCatalog:
        """
        Refresh CRIS data using HTML parsing (legacy method).

        Args:
            force_download: If True, always download fresh HTML

        Returns:
            CRISCatalog containing all parsed CRIS model information

        Raises:
            Exception: If HTML fetch/parse fails
        """
        self._logger.info("Refreshing CRIS data via HTML parsing")

        # Step 1: Download documentation if needed
        if force_download or not self._is_html_file_recent():
            self._download_documentation()

        # Step 2: Parse the HTML documentation
        models_dict = self._parse_documentation()

        # Step 3: Create catalog with timestamp
        catalog = CRISCatalog(retrieval_timestamp=datetime.now(), cris_models=models_dict)

        # Step 4: Save to JSON
        self._save_catalog_to_json(catalog=catalog)

        # Step 5: Cache and return
        self._cached_catalog = catalog
        self._logger.info(f"Successfully parsed {len(models_dict)} CRIS models from HTML")
        return catalog

    def load_cached_data(self) -> Optional[CRISCatalog]:
        """
        Load previously cached CRIS data from JSON file.

        Returns:
            CRISCatalog if cached data exists and is valid, None otherwise
        """
        if not self.json_output_path.exists():
            self._logger.info(CRISLogMessages.CACHE_MISS)
            return None

        try:
            data = self._serializer.load_from_file(input_path=self.json_output_path)
            catalog = CRISCatalog.from_dict(data=data)
            self._cached_catalog = catalog
            self._logger.info(CRISLogMessages.CACHE_LOADED.format(file_path=self.json_output_path))
            return catalog
        except Exception as e:
            self._logger.warning(f"Failed to load cached CRIS data: {str(e)}")
            return None

    def get_models_by_source_region(self, source_region: str) -> Dict[str, CRISModelInfo]:
        """
        Get all CRIS models that can be called from a specific source region.

        Args:
            source_region: Source region identifier (e.g., 'us-east-1')

        Returns:
            Dictionary of model names to CRIS model info for the specified source region

        Raises:
            CRISManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise CRISManagerError(CRISErrorMessages.NO_DATA_AVAILABLE)

        return self._cached_catalog.get_models_by_source_region(source_region=source_region)

    def get_models_by_destination_region(self, destination_region: str) -> Dict[str, CRISModelInfo]:
        """
        Get all CRIS models that can route requests to a specific destination region.

        Args:
            destination_region: Destination region identifier (e.g., 'us-west-2')

        Returns:
            Dictionary of model names to CRIS model info for the specified destination region

        Raises:
            CRISManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise CRISManagerError(CRISErrorMessages.NO_DATA_AVAILABLE)

        return self._cached_catalog.get_models_by_destination_region(
            destination_region=destination_region
        )

    def get_inference_profile_for_model(self, model_name: str) -> Optional[str]:
        """
        Get the inference profile ID for a specific CRIS model.

        Args:
            model_name: The name of the model to look up

        Returns:
            Inference profile ID if model exists, None otherwise

        Raises:
            CRISManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise CRISManagerError(CRISErrorMessages.NO_DATA_AVAILABLE)

        return self._cached_catalog.get_inference_profile_for_model(model_name=model_name)

    def get_all_source_regions(self) -> List[str]:
        """
        Get all unique source regions across all CRIS models.

        Returns:
            Sorted list of all source regions

        Raises:
            CRISManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise CRISManagerError(CRISErrorMessages.NO_DATA_AVAILABLE)

        return self._cached_catalog.get_all_source_regions()

    def get_all_destination_regions(self) -> List[str]:
        """
        Get all unique destination regions across all CRIS models.

        Returns:
            Sorted list of all destination regions

        Raises:
            CRISManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise CRISManagerError(CRISErrorMessages.NO_DATA_AVAILABLE)

        return self._cached_catalog.get_all_destination_regions()

    def get_model_names(self) -> List[str]:
        """
        Get all CRIS model names in the catalog.

        Returns:
            Sorted list of model names

        Raises:
            CRISManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise CRISManagerError(CRISErrorMessages.NO_DATA_AVAILABLE)

        return self._cached_catalog.get_model_names()

    def get_model_count(self) -> int:
        """
        Get the total number of CRIS models in the catalog.

        Returns:
            Total number of CRIS models

        Raises:
            CRISManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise CRISManagerError(CRISErrorMessages.NO_DATA_AVAILABLE)

        return self._cached_catalog.model_count

    def has_model(self, model_name: str) -> bool:
        """
        Check if a CRIS model exists in the catalog.

        Args:
            model_name: The model name to check

        Returns:
            True if model exists in catalog

        Raises:
            CRISManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise CRISManagerError(CRISErrorMessages.NO_DATA_AVAILABLE)

        return self._cached_catalog.has_model(model_name=model_name)

    def get_destinations_for_source_and_model(
        self, model_name: str, source_region: str
    ) -> List[str]:
        """
        Get destination regions available for a specific model from a specific source region.

        Args:
            model_name: The name of the CRIS model
            source_region: The source region to query from

        Returns:
            List of destination regions, empty if model/source combination not supported

        Raises:
            CRISManagerError: If no data is available
        """
        if not self._cached_catalog:
            raise CRISManagerError(CRISErrorMessages.NO_DATA_AVAILABLE)

        if model_name not in self._cached_catalog.cris_models:
            return []

        model_info = self._cached_catalog.cris_models[model_name]
        return model_info.get_destinations_for_source(source_region=source_region)

    def _download_documentation(self) -> None:
        """
        Download the HTML documentation from AWS.

        Raises:
            NetworkError: If download fails
            FileSystemError: If file operations fail
        """
        self._logger.info(CRISLogMessages.DOWNLOAD_STARTED)
        self._downloader.download(url=self.documentation_url, output_path=self.html_output_path)
        self._logger.info(
            CRISLogMessages.DOWNLOAD_COMPLETED.format(file_path=self.html_output_path)
        )

    def _parse_documentation(self) -> Dict[str, CRISModelInfo]:
        """
        Parse the downloaded HTML documentation.

        Returns:
            Dictionary mapping model names to CRIS model information

        Raises:
            ParsingError: If parsing fails
        """
        return self._parser.parse(file_path=self.html_output_path)

    def _save_catalog_to_json(self, catalog: CRISCatalog) -> None:
        """
        Save the CRIS catalog to JSON format.

        Args:
            catalog: The catalog to save

        Raises:
            OSError: If file operations fail
            TypeError: If serialization fails
        """
        self._logger.info(CRISLogMessages.JSON_EXPORT_STARTED)

        # Convert catalog to dictionary for serialization
        catalog_dict = catalog.to_dict()

        self._serializer.serialize_dict_to_file(
            data=catalog_dict, output_path=self.json_output_path
        )

        self._logger.info(
            CRISLogMessages.JSON_EXPORT_COMPLETED.format(file_path=self.json_output_path)
        )

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
        """Return string representation of the CRISManager."""
        return (
            "CRISManager("
            f"html_path='{self.html_output_path}', "
            f"json_path='{self.json_output_path}', "
            f"url='{self.documentation_url}'"
            ")"
        )
