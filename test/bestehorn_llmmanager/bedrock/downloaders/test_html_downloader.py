"""
Comprehensive unit tests for HTMLDocumentationDownloader.
Tests HTTP downloading functionality, error handling, and configuration options.
"""

from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest
import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from bestehorn_llmmanager.bedrock.downloaders.base_downloader import FileSystemError, NetworkError
from bestehorn_llmmanager.bedrock.downloaders.html_downloader import HTMLDocumentationDownloader


class TestHTMLDocumentationDownloader:
    """Test suite for HTMLDocumentationDownloader."""

    @pytest.fixture
    def downloader(self) -> HTMLDocumentationDownloader:
        """Create a downloader instance for testing."""
        return HTMLDocumentationDownloader()

    @pytest.fixture
    def custom_downloader(self) -> HTMLDocumentationDownloader:
        """Create a downloader with custom configuration."""
        return HTMLDocumentationDownloader(timeout=60, user_agent="CustomBot/1.0", verify_ssl=False)

    def test_init_default_configuration(self):
        """Test downloader initialization with default configuration."""
        downloader = HTMLDocumentationDownloader()

        assert downloader._timeout == 30
        assert downloader._verify_ssl is True
        assert "Mozilla" in downloader._user_agent
        assert downloader._logger is not None

    def test_init_custom_configuration(self):
        """Test downloader initialization with custom configuration."""
        custom_user_agent = "TestBot/2.0"
        downloader = HTMLDocumentationDownloader(
            timeout=45, user_agent=custom_user_agent, verify_ssl=False
        )

        assert downloader._timeout == 45
        assert downloader._user_agent == custom_user_agent
        assert downloader._verify_ssl is False

    def test_init_none_user_agent(self):
        """Test initialization with None user agent uses default."""
        downloader = HTMLDocumentationDownloader(user_agent=None)

        assert "Mozilla" in downloader._user_agent
        assert "Chrome" in downloader._user_agent

    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_download_successful(self, mock_mkdir, mock_file, mock_get, downloader):
        """Test successful download operation."""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        url = "https://example.com/docs"
        output_path = Path("test_output.html")

        downloader.download(url=url, output_path=output_path)

        # Verify HTTP request was made correctly
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs["url"] == url
        assert kwargs["timeout"] == 30
        assert kwargs["verify"] is True
        assert "User-Agent" in kwargs["headers"]
        assert "Mozilla" in kwargs["headers"]["User-Agent"]

        # Verify file was written
        mock_file.assert_called_once_with(output_path, "w", encoding="utf-8")
        mock_file().write.assert_called_once_with(mock_response.text)

    @patch("requests.get")
    def test_download_invalid_url(self, mock_get, downloader):
        """Test download with invalid URL."""
        invalid_urls = ["", "   ", "not-a-url", "ftp://example.com", "file:///local/file"]

        for url in invalid_urls:
            with pytest.raises(ValueError) as exc_info:
                downloader.download(url=url, output_path=Path("output.html"))

            # Should raise ValueError for invalid URL format
            assert "URL" in str(exc_info.value)

        # Ensure no HTTP requests were made for invalid URLs
        mock_get.assert_not_called()

    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_download_custom_headers(self, mock_mkdir, mock_file, mock_get, custom_downloader):
        """Test download with custom configuration sends proper headers."""
        mock_response = Mock()
        mock_response.text = "Test content"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        url = "https://example.com/docs"
        custom_downloader.download(url=url, output_path=Path("output.html"))

        # Verify custom configuration was used
        args, kwargs = mock_get.call_args
        assert kwargs["timeout"] == 60
        assert kwargs["verify"] is False
        assert kwargs["headers"]["User-Agent"] == "CustomBot/1.0"

    @patch("requests.get")
    def test_download_timeout_error(self, mock_get, downloader):
        """Test download with timeout error."""
        mock_get.side_effect = Timeout("Request timed out")

        url = "https://example.com/docs"
        output_path = Path("output.html")

        with pytest.raises(NetworkError) as exc_info:
            downloader.download(url=url, output_path=output_path)

        assert "Request timed out after 30 seconds" in str(exc_info.value)

    @patch("requests.get")
    def test_download_connection_error(self, mock_get, downloader):
        """Test download with connection error."""
        mock_get.side_effect = ConnectionError("Connection failed")

        url = "https://example.com/docs"
        output_path = Path("output.html")

        with pytest.raises(NetworkError) as exc_info:
            downloader.download(url=url, output_path=output_path)

        assert "Connection failed" in str(exc_info.value)

    @patch("requests.get")
    def test_download_http_error(self, mock_get, downloader):
        """Test download with HTTP error response."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        url = "https://example.com/docs"
        output_path = Path("output.html")

        with pytest.raises(NetworkError) as exc_info:
            downloader.download(url=url, output_path=output_path)

        assert "404 Not Found" in str(exc_info.value)

    @patch("requests.get")
    @patch("builtins.open", side_effect=OSError("Permission denied"))
    @patch("pathlib.Path.mkdir")
    def test_download_file_write_error(self, mock_mkdir, mock_file, mock_get, downloader):
        """Test download with file write error."""
        mock_response = Mock()
        mock_response.text = "Test content"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        url = "https://example.com/docs"
        output_path = Path("output.html")

        with pytest.raises(FileSystemError) as exc_info:
            downloader.download(url=url, output_path=output_path)

        assert "Permission denied" in str(exc_info.value)

    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir", side_effect=OSError("Cannot create directory"))
    def test_download_directory_creation_error(self, mock_mkdir, mock_file, mock_get, downloader):
        """Test download with directory creation error."""
        mock_response = Mock()
        mock_response.text = "Test content"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        url = "https://example.com/docs"
        output_path = Path("subdir/output.html")

        # This should still work as mkdir is called with exist_ok=True
        downloader.download(url=url, output_path=output_path)

        # File should still be written even if directory creation fails
        mock_file.assert_called_once()

    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_download_large_content(self, mock_mkdir, mock_file, mock_get, downloader):
        """Test download with large content."""
        # Create large content
        large_content = "A" * 100000  # 100KB of content

        mock_response = Mock()
        mock_response.text = large_content
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        url = "https://example.com/large-doc"
        output_path = Path("large_output.html")

        downloader.download(url=url, output_path=output_path)

        # Verify large content was written
        mock_file().write.assert_called_once_with(large_content)

    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_download_unicode_content(self, mock_mkdir, mock_file, mock_get, downloader):
        """Test download with unicode content."""
        unicode_content = "<html><body>Unicode: émojis 🚀 and special chars: αβγ</body></html>"

        mock_response = Mock()
        mock_response.text = unicode_content
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        url = "https://example.com/unicode-doc"
        output_path = Path("unicode_output.html")

        downloader.download(url=url, output_path=output_path)

        # Verify unicode content was written with proper encoding
        mock_file.assert_called_once_with(output_path, "w", encoding="utf-8")
        mock_file().write.assert_called_once_with(unicode_content)

    def test_get_default_user_agent(self, downloader):
        """Test the default user agent string."""
        user_agent = downloader._get_default_user_agent()

        assert isinstance(user_agent, str)
        assert len(user_agent) > 0
        assert "Mozilla" in user_agent
        assert "Chrome" in user_agent
        assert "Safari" in user_agent

    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_make_request_headers(self, mock_mkdir, mock_file, mock_get, downloader):
        """Test that make_request sends proper headers."""
        mock_response = Mock()
        mock_response.text = "Test content"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        url = "https://example.com/docs"
        downloader.download(url=url, output_path=Path("output.html"))

        # Verify headers were set correctly
        args, kwargs = mock_get.call_args
        headers = kwargs["headers"]

        assert "User-Agent" in headers
        assert "Accept" in headers
        assert "Accept-Language" in headers
        assert "Accept-Encoding" in headers
        assert "Connection" in headers

        assert "text/html" in headers["Accept"]
        assert "en-US" in headers["Accept-Language"]
        assert "gzip" in headers["Accept-Encoding"]
        assert "keep-alive" in headers["Connection"]

    @patch("requests.get")
    def test_make_request_stream_disabled(self, mock_get, downloader):
        """Test that streaming is disabled in requests."""
        mock_response = Mock()
        mock_response.text = "Test content"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Call the private method directly to test it
        result = downloader._make_request("https://example.com/test")

        # Verify stream=False was passed
        args, kwargs = mock_get.call_args
        assert kwargs["stream"] is False
        assert result == mock_response

    @patch("requests.get")
    def test_make_request_timeout_exception_handling(self, mock_get, downloader):
        """Test timeout exception handling in _make_request."""
        mock_get.side_effect = Timeout("Original timeout message")

        with pytest.raises(RequestException) as exc_info:
            downloader._make_request("https://example.com/test")

        assert "Request timed out after 30 seconds" in str(exc_info.value)

    @patch("requests.get")
    def test_make_request_connection_exception_handling(self, mock_get, downloader):
        """Test connection exception handling in _make_request."""
        original_error = ConnectionError("DNS resolution failed")
        mock_get.side_effect = original_error

        with pytest.raises(RequestException) as exc_info:
            downloader._make_request("https://example.com/test")

        assert "Connection failed: DNS resolution failed" in str(exc_info.value)

    @patch("builtins.open", side_effect=OSError("Disk full"))
    def test_save_content_error_handling(self, mock_file, downloader):
        """Test error handling in _save_content method."""
        content = "Test content"
        output_path = Path("output.html")

        with pytest.raises(OSError) as exc_info:
            downloader._save_content(content=content, output_path=output_path)

        assert f"Failed to save content to {output_path}" in str(exc_info.value)
        assert "Disk full" in str(exc_info.value)

    @patch("builtins.open", new_callable=mock_open)
    def test_save_content_successful(self, mock_file, downloader):
        """Test successful content saving."""
        content = "Test HTML content"
        output_path = Path("test.html")

        downloader._save_content(content=content, output_path=output_path)

        mock_file.assert_called_once_with(output_path, "w", encoding="utf-8")
        mock_file().write.assert_called_once_with(content)

    def test_inheritance(self, downloader):
        """Test that HTMLDocumentationDownloader inherits from BaseDocumentationDownloader."""
        from bestehorn_llmmanager.bedrock.downloaders.base_downloader import (
            BaseDocumentationDownloader,
        )

        assert isinstance(downloader, BaseDocumentationDownloader)

    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_download_empty_content(self, mock_mkdir, mock_file, mock_get, downloader):
        """Test download with empty content."""
        mock_response = Mock()
        mock_response.text = ""
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        url = "https://example.com/empty"
        output_path = Path("empty.html")

        downloader.download(url=url, output_path=output_path)

        # Should still write empty content
        mock_file().write.assert_called_once_with("")

    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    def test_download_with_nested_directories(self, mock_mkdir, mock_file, mock_get, downloader):
        """Test download with deeply nested output directory."""
        mock_response = Mock()
        mock_response.text = "Test content"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        url = "https://example.com/docs"
        output_path = Path("deep/nested/directory/structure/output.html")

        downloader.download(url=url, output_path=output_path)

        # Verify directory creation was attempted
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file.assert_called_once_with(output_path, "w", encoding="utf-8")

    def test_url_validation_edge_cases(self, downloader):
        """Test URL validation with various edge cases."""
        valid_urls = [
            "http://example.com",
            "https://example.com",
            "http://example.com/path",
            "https://example.com/path?query=value",
            "http://subdomain.example.com:8080/path",
        ]

        for url in valid_urls:
            # Should not raise exception for valid URLs
            try:
                downloader._validate_url(url=url)
            except ValueError:
                pytest.fail(f"Valid URL {url} was rejected")

    @patch("requests.get")
    def test_request_exception_propagation(self, mock_get, downloader):
        """Test that various request exceptions are properly handled."""
        exceptions_to_test = [
            requests.exceptions.HTTPError("HTTP Error"),
            requests.exceptions.ConnectionError("Connection Error"),
            requests.exceptions.Timeout("Timeout Error"),
            requests.exceptions.RequestException("Generic Request Error"),
        ]

        for exception in exceptions_to_test:
            mock_get.side_effect = exception

            with pytest.raises(NetworkError):
                downloader.download(url="https://example.com/test", output_path=Path("test.html"))

            mock_get.reset_mock()
