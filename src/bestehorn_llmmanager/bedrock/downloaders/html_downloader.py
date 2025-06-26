"""
HTTP-based HTML documentation downloader.
Concrete implementation for downloading HTML documentation from web URLs.
"""

import logging
from pathlib import Path
from typing import Optional

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from ..models.constants import LogMessages
from .base_downloader import BaseDocumentationDownloader, FileSystemError, NetworkError


class HTMLDocumentationDownloader(BaseDocumentationDownloader):
    """
    HTTP-based downloader for HTML documentation.
    Downloads documentation from web URLs using the requests library.
    """

    def __init__(
        self, timeout: int = 30, user_agent: Optional[str] = None, verify_ssl: bool = True
    ) -> None:
        """
        Initialize the HTML downloader with configuration options.

        Args:
            timeout: Request timeout in seconds
            user_agent: Custom user agent string, uses default if None
            verify_ssl: Whether to verify SSL certificates
        """
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._user_agent = user_agent or self._get_default_user_agent()
        self._logger = logging.getLogger(__name__)

    def download(self, url: str, output_path: Path) -> None:
        """
        Download HTML documentation from the specified URL.

        Args:
            url: The URL to download documentation from
            output_path: The local file path to save the downloaded content

        Raises:
            NetworkError: If there are network connectivity issues
            FileSystemError: If there are file system access issues
            ValueError: If the URL is invalid
        """
        self._validate_url(url=url)
        self._ensure_output_directory(output_path=output_path)

        self._logger.info(LogMessages.DOWNLOAD_STARTED)

        try:
            response = self._make_request(url=url)
            self._save_content(content=response.text, output_path=output_path)

            self._logger.info(LogMessages.DOWNLOAD_COMPLETED.format(file_path=output_path))

        except RequestException as e:
            error_msg = LogMessages.NETWORK_ERROR.format(error=str(e))
            self._logger.error(error_msg)
            raise NetworkError(error_msg) from e
        except OSError as e:
            error_msg = LogMessages.FILE_ERROR.format(error=str(e))
            self._logger.error(error_msg)
            raise FileSystemError(error_msg) from e

    def _make_request(self, url: str) -> requests.Response:
        """
        Make HTTP request to download content.

        Args:
            url: The URL to request

        Returns:
            HTTP response object

        Raises:
            RequestException: If the HTTP request fails
        """
        headers = {
            "User-Agent": self._user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

        try:
            response = requests.get(
                url=url,
                headers=headers,
                timeout=self._timeout,
                verify=self._verify_ssl,
                stream=False,
            )
            response.raise_for_status()
            return response

        except Timeout as e:
            raise RequestException(f"Request timed out after {self._timeout} seconds") from e
        except ConnectionError as e:
            raise RequestException(f"Connection failed: {str(e)}") from e

    def _save_content(self, content: str, output_path: Path) -> None:
        """
        Save downloaded content to the specified file path.

        Args:
            content: The content to save
            output_path: The file path to save to

        Raises:
            OSError: If file operations fail
        """
        try:
            with open(output_path, "w", encoding="utf-8") as file:
                file.write(content)
        except OSError as e:
            raise OSError(f"Failed to save content to {output_path}: {str(e)}") from e

    def _get_default_user_agent(self) -> str:
        """
        Get the default user agent string.

        Returns:
            Default user agent string
        """
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
