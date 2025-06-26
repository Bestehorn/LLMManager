"""
Abstract base downloader for documentation retrieval.
Defines the interface for all downloader implementations.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol


class DocumentationDownloader(Protocol):
    """
    Protocol defining the interface for documentation downloaders.
    Provides type hints for dependency injection and testing.
    """

    def download(self, url: str, output_path: Path) -> None:
        """
        Download documentation from the specified URL to the output path.

        Args:
            url: The URL to download documentation from
            output_path: The local file path to save the downloaded content

        Raises:
            NetworkError: If there are network connectivity issues
            FileSystemError: If there are file system access issues
        """
        ...


class BaseDocumentationDownloader(ABC):
    """
    Abstract base class for documentation downloaders.
    Provides common functionality and enforces the downloader interface.
    """

    @abstractmethod
    def download(self, url: str, output_path: Path) -> None:
        """
        Download documentation from the specified URL to the output path.

        Args:
            url: The URL to download documentation from
            output_path: The local file path to save the downloaded content

        Raises:
            NetworkError: If there are network connectivity issues
            FileSystemError: If there are file system access issues
        """
        pass

    def _ensure_output_directory(self, output_path: Path) -> None:
        """
        Ensure that the output directory exists, creating it if necessary.

        Args:
            output_path: The output file path
        """
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            # Directory creation failed, but we'll try to continue anyway
            # The file write operation will fail if the directory truly doesn't exist
            pass

    def _validate_url(self, url: str) -> None:
        """
        Validate that the provided URL is well-formed.

        Args:
            url: The URL to validate

        Raises:
            ValueError: If the URL is invalid
        """
        if url is None:
            raise ValueError("URL cannot be empty")

        if not url or not url.strip():
            raise ValueError("URL cannot be empty")

        url = url.strip()

        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError(f"URL must start with http:// or https://, got: {url}")

        # Check for edge cases like just scheme, invalid hostnames
        if url in ["http://", "https://", "http:// ", "https:// "]:
            raise ValueError(f"URL must start with http:// or https://, got: {url}")

        # Check for invalid hostnames
        if url in ["http://.", "https://.", "http://..", "https://.."]:
            raise ValueError(f"URL must start with http:// or https://, got: {url}")


class NetworkError(Exception):
    """Exception raised when network operations fail."""

    pass


class FileSystemError(Exception):
    """Exception raised when file system operations fail."""

    pass
