"""
JSON serializer for Amazon Bedrock model data.
Handles serialization of model catalog data to JSON format.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, cast

from ..models.constants import LogMessages
from ..models.data_structures import ModelCatalog


class JSONModelSerializer:
    """
    JSON serializer for Bedrock model catalog data.
    Provides methods to serialize model data to JSON format with proper formatting.
    """

    def __init__(self, indent: int = 2, ensure_ascii: bool = False) -> None:
        """
        Initialize the JSON serializer.

        Args:
            indent: Number of spaces for JSON indentation
            ensure_ascii: Whether to escape non-ASCII characters
        """
        self._indent = indent
        self._ensure_ascii = ensure_ascii
        self._logger = logging.getLogger(__name__)

    def serialize_to_file(self, catalog: ModelCatalog, output_path: Path) -> None:
        """
        Serialize model catalog to a JSON file.

        Args:
            catalog: The model catalog to serialize
            output_path: Path where the JSON file should be saved

        Raises:
            OSError: If file operations fail
            TypeError: If serialization fails
        """
        self._logger.info(LogMessages.JSON_EXPORT_STARTED)

        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert catalog to dictionary
            catalog_dict = catalog.to_dict()

            # Write JSON to file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    obj=catalog_dict,
                    fp=f,
                    indent=self._indent,
                    ensure_ascii=self._ensure_ascii,
                    sort_keys=True,
                )

            self._logger.info(LogMessages.JSON_EXPORT_COMPLETED.format(file_path=output_path))

        except OSError as e:
            error_msg = LogMessages.FILE_ERROR.format(error=str(e))
            self._logger.error(error_msg)
            raise OSError(error_msg) from e
        except (TypeError, ValueError) as e:
            error_msg = f"JSON serialization failed: {str(e)}"
            self._logger.error(error_msg)
            raise TypeError(error_msg) from e

    def serialize_to_string(self, catalog: ModelCatalog) -> str:
        """
        Serialize model catalog to a JSON string.

        Args:
            catalog: The model catalog to serialize

        Returns:
            JSON string representation of the catalog

        Raises:
            TypeError: If serialization fails
        """
        try:
            catalog_dict = catalog.to_dict()
            return json.dumps(
                obj=catalog_dict,
                indent=self._indent,
                ensure_ascii=self._ensure_ascii,
                sort_keys=True,
            )
        except (TypeError, ValueError) as e:
            error_msg = f"JSON serialization failed: {str(e)}"
            self._logger.error(error_msg)
            raise TypeError(error_msg) from e

    def serialize_dict_to_file(self, data: Dict[str, Any], output_path: Path) -> None:
        """
        Serialize a dictionary to a JSON file.

        Args:
            data: Dictionary data to serialize
            output_path: Path where the JSON file should be saved

        Raises:
            OSError: If file operations fail
            TypeError: If serialization fails
        """
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write JSON to file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    obj=data,
                    fp=f,
                    indent=self._indent,
                    ensure_ascii=self._ensure_ascii,
                    sort_keys=True,
                )

        except OSError as e:
            error_msg = LogMessages.FILE_ERROR.format(error=str(e))
            self._logger.error(error_msg)
            raise OSError(error_msg) from e
        except (TypeError, ValueError) as e:
            error_msg = f"JSON serialization failed: {str(e)}"
            self._logger.error(error_msg)
            raise TypeError(error_msg) from e

    def load_from_file(self, input_path: Path) -> Dict[str, Any]:
        """
        Load JSON data from a file.

        Args:
            input_path: Path to the JSON file to load

        Returns:
            Dictionary containing the loaded JSON data

        Raises:
            FileNotFoundError: If the input file doesn't exist
            OSError: If file operations fail
            ValueError: If JSON parsing fails
        """
        if not input_path.exists():
            raise FileNotFoundError(f"JSON file not found: {input_path}")

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                return cast(Dict[str, Any], json.load(fp=f))
        except OSError as e:
            error_msg = LogMessages.FILE_ERROR.format(error=str(e))
            self._logger.error(error_msg)
            raise OSError(error_msg) from e
        except json.JSONDecodeError as e:
            error_msg = f"JSON parsing failed: {str(e)}"
            self._logger.error(error_msg)
            raise ValueError(error_msg) from e
