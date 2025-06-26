"""
Abstract base parser for documentation parsing.
Defines the interface for all parser implementations.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Protocol

from ..models.data_structures import BedrockModelInfo


class DocumentationParser(Protocol):
    """
    Protocol defining the interface for documentation parsers.
    Provides type hints for dependency injection and testing.
    """

    def parse(self, file_path: Path) -> Dict[str, BedrockModelInfo]:
        """
        Parse documentation file and extract model information.

        Args:
            file_path: Path to the documentation file to parse

        Returns:
            Dictionary mapping model names to model information

        Raises:
            ParsingError: If parsing fails
            FileNotFoundError: If the input file doesn't exist
        """
        ...


class BaseDocumentationParser(ABC):
    """
    Abstract base class for documentation parsers.
    Provides common functionality and enforces the parser interface.
    """

    @abstractmethod
    def parse(self, file_path: Path) -> Dict[str, BedrockModelInfo]:
        """
        Parse documentation file and extract model information.

        Args:
            file_path: Path to the documentation file to parse

        Returns:
            Dictionary mapping model names to model information

        Raises:
            ParsingError: If parsing fails
            FileNotFoundError: If the input file doesn't exist
        """
        pass

    def _validate_file_exists(self, file_path: Path) -> None:
        """
        Validate that the input file exists and is readable.

        Args:
            file_path: Path to validate

        Raises:
            FileNotFoundError: If the file doesn't exist
            PermissionError: If the file isn't readable
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Documentation file not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                # Just try to read the first byte to check permissions
                f.read(1)
        except PermissionError as e:
            raise PermissionError(f"Cannot read file: {file_path}") from e
        except UnicodeDecodeError as e:
            raise ValueError(f"File is not valid UTF-8: {file_path}") from e


class ParsingError(Exception):
    """Exception raised when document parsing fails."""

    pass
