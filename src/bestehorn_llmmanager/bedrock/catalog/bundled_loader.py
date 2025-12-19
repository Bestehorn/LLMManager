"""
Bundled data loader for BedrockModelCatalog.

This module provides functionality to load pre-packaged fallback catalog data
that is distributed with the package. This ensures basic functionality even
when API calls fail or network connectivity is unavailable.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

try:
    # Python 3.9+
    from importlib.resources import files
except ImportError:
    # Python 3.7-3.8 fallback
    from importlib_resources import files  # type: ignore

from ..exceptions.llm_manager_exceptions import BundledDataError
from ..models.catalog_constants import (
    CatalogErrorMessages,
    CatalogFilePaths,
    CatalogLogMessages,
)
from ..models.catalog_structures import UnifiedCatalog

logger = logging.getLogger(__name__)


class BundledDataLoader:
    """
    Loads pre-packaged fallback data from the package.

    This class provides static methods to load bundled catalog data that is
    distributed with the package. The bundled data serves as a fallback when
    API calls fail or when operating in offline environments.

    The bundled data is located at:
    src/bestehorn_llmmanager/bedrock/package_data/bedrock_catalog_bundled.json
    """

    @staticmethod
    def get_bundled_data_path() -> Path:
        """
        Get path to bundled data file in package.

        Returns:
            Path to bundled catalog JSON file

        Raises:
            BundledDataError: If bundled data file cannot be located
        """
        try:
            # Use importlib.resources to locate the bundled data file
            package_files = files("bestehorn_llmmanager.bedrock")
            bundled_file = (
                package_files
                / CatalogFilePaths.BUNDLED_DATA_DIRECTORY
                / CatalogFilePaths.BUNDLED_DATA_FILENAME
            )

            # Convert to Path object
            if hasattr(bundled_file, "__fspath__"):
                # Python 3.9+ returns a Traversable that can be converted to Path
                return Path(str(bundled_file))
            else:
                # Fallback for older versions
                return Path(str(bundled_file))

        except Exception as e:
            error_msg = CatalogErrorMessages.BUNDLED_DATA_MISSING.format(
                path=f"{CatalogFilePaths.BUNDLED_DATA_DIRECTORY}/"
                f"{CatalogFilePaths.BUNDLED_DATA_FILENAME}"
            )
            logger.error(error_msg)
            raise BundledDataError(message=error_msg) from e

    @staticmethod
    def load_bundled_catalog() -> UnifiedCatalog:
        """
        Load bundled catalog from package data.

        This method loads the pre-packaged catalog data that is distributed
        with the package. The data is validated using UnifiedCatalog.from_dict()
        to ensure structural integrity.

        Returns:
            UnifiedCatalog loaded from bundled data

        Raises:
            BundledDataError: If bundled data is missing, corrupt, or invalid
        """
        logger.info(CatalogLogMessages.BUNDLED_LOADING)

        try:
            # Get the bundled data file path
            bundled_path = BundledDataLoader.get_bundled_data_path()

            # Check if file exists
            if not bundled_path.exists():
                error_msg = CatalogErrorMessages.BUNDLED_DATA_MISSING.format(path=str(bundled_path))
                logger.error(error_msg)
                raise BundledDataError(message=error_msg)

            # Read and parse JSON
            try:
                with open(file=bundled_path, mode="r", encoding="utf-8") as f:
                    data = json.load(fp=f)
            except json.JSONDecodeError as e:
                error_msg = CatalogErrorMessages.BUNDLED_DATA_INVALID_JSON.format(error=str(e))
                logger.error(error_msg)
                raise BundledDataError(message=error_msg) from e

            # Validate and construct UnifiedCatalog
            try:
                catalog = UnifiedCatalog.from_dict(data=data)
            except ValueError as e:
                error_msg = CatalogErrorMessages.BUNDLED_DATA_INVALID_STRUCTURE.format(error=str(e))
                logger.error(error_msg)
                raise BundledDataError(message=error_msg) from e

            # Log success with metadata
            metadata = BundledDataLoader.get_bundled_data_metadata(catalog=catalog)
            logger.info(
                CatalogLogMessages.BUNDLED_LOADED.format(
                    version=metadata.get("version", "unknown"),
                    count=catalog.model_count,
                    timestamp=metadata.get("generation_timestamp", "unknown"),
                )
            )

            # Log warning about potentially stale data
            logger.warning(CatalogLogMessages.BUNDLED_WARNING)

            return catalog

        except BundledDataError:
            # Re-raise BundledDataError as-is
            raise
        except Exception as e:
            # Wrap unexpected errors
            error_msg = CatalogErrorMessages.BUNDLED_DATA_MISSING.format(
                path=CatalogFilePaths.BUNDLED_DATA_FILENAME
            )
            logger.error(f"{error_msg}: {e}")
            raise BundledDataError(message=error_msg) from e

    @staticmethod
    def get_bundled_data_metadata(catalog: Optional[UnifiedCatalog] = None) -> Dict[str, Any]:
        """
        Get metadata about bundled data.

        This method extracts metadata from the bundled catalog, including
        generation timestamp and data version. If no catalog is provided,
        it loads the bundled catalog to extract metadata.

        Args:
            catalog: Optional UnifiedCatalog to extract metadata from.
                    If None, loads bundled catalog.

        Returns:
            Dictionary containing:
                - generation_timestamp: When the bundled data was generated
                - version: Version identifier for the bundled data
                - model_count: Number of models in the bundled data
                - source: Always "bundled"

        Raises:
            BundledDataError: If bundled data cannot be loaded or is invalid
        """
        try:
            # Load catalog if not provided
            if catalog is None:
                catalog = BundledDataLoader.load_bundled_catalog()

            # Extract metadata from catalog
            metadata: Dict[str, Any] = {
                "source": catalog.metadata.source.value,
                "generation_timestamp": catalog.metadata.retrieval_timestamp.isoformat(),
                "version": catalog.metadata.bundled_data_version or "unknown",
                "model_count": catalog.model_count,
                "regions": catalog.metadata.api_regions_queried,
            }

            return metadata

        except Exception as e:
            error_msg = f"Failed to extract bundled data metadata: {e}"
            logger.error(error_msg)
            raise BundledDataError(message=error_msg) from e
