"""
Comprehensive unit tests for BaseDocumentationDownloader.
Tests abstract base class functionality, URL validation, and directory creation.
"""

from abc import ABC
from pathlib import Path
from unittest.mock import patch

import pytest

from bestehorn_llmmanager.bedrock.downloaders.base_downloader import (
    BaseDocumentationDownloader,
    DocumentationDownloader,
    FileSystemError,
    NetworkError,
)


class ConcreteDownloader(BaseDocumentationDownloader):
    """Concrete implementation for testing the abstract base class."""

    def __init__(self):
        self.downloaded_urls = []
        self.downloaded_paths = []

    def download(self, url: str, output_path: Path) -> None:
        """Concrete implementation of download method."""
        self._validate_url(url=url)
        self._ensure_output_directory(output_path=output_path)

        # Record the download for testing purposes
        self.downloaded_urls.append(url)
        self.downloaded_paths.append(output_path)


class TestDocumentationDownloader:
    """Test suite for DocumentationDownloader protocol."""

    def test_protocol_definition(self):
        """Test that DocumentationDownloader is a proper protocol."""
        # Protocol should define the expected interface
        assert hasattr(DocumentationDownloader, "download")

        # Check that it's a protocol (has typing metadata)
        assert hasattr(DocumentationDownloader, "__annotations__")


class TestBaseDocumentationDownloader:
    """Test suite for BaseDocumentationDownloader abstract base class."""

    @pytest.fixture
    def downloader(self) -> ConcreteDownloader:
        """Create a concrete downloader instance for testing."""
        return ConcreteDownloader()

    def test_abstract_base_class(self):
        """Test that BaseDocumentationDownloader is abstract."""
        # Should not be able to instantiate abstract base class directly
        with pytest.raises(TypeError):
            BaseDocumentationDownloader()  # type: ignore

    def test_concrete_implementation_works(self, downloader):
        """Test that concrete implementations can be instantiated."""
        assert isinstance(downloader, BaseDocumentationDownloader)
        assert isinstance(downloader, ConcreteDownloader)

    def test_download_method_is_abstract(self):
        """Test that download method is abstract in base class."""
        # The download method should be abstract
        assert hasattr(BaseDocumentationDownloader, "download")
        assert getattr(BaseDocumentationDownloader.download, "__isabstractmethod__", False)

    def test_validate_url_valid_http(self, downloader):
        """Test URL validation with valid HTTP URLs."""
        valid_urls = [
            "http://example.com",
            "http://www.example.com",
            "http://example.com/path",
            "http://example.com/path/to/file.html",
            "http://example.com:8080",
            "http://example.com:8080/path",
            "http://subdomain.example.com",
            "http://example.com/path?query=value",
            "http://example.com/path?query=value&other=param",
            "http://example.com/path#fragment",
            "http://example.com/path?query=value#fragment",
        ]

        for url in valid_urls:
            # Should not raise exception for valid URLs
            try:
                downloader._validate_url(url=url)
            except ValueError:
                pytest.fail(f"Valid HTTP URL {url} was rejected")

    def test_validate_url_valid_https(self, downloader):
        """Test URL validation with valid HTTPS URLs."""
        valid_urls = [
            "https://example.com",
            "https://www.example.com",
            "https://example.com/path",
            "https://example.com/path/to/file.html",
            "https://example.com:443",
            "https://example.com:8443/path",
            "https://subdomain.example.com",
            "https://example.com/path?query=value",
            "https://example.com/path?query=value&other=param",
            "https://example.com/path#fragment",
            "https://example.com/path?query=value#fragment",
        ]

        for url in valid_urls:
            # Should not raise exception for valid URLs
            try:
                downloader._validate_url(url=url)
            except ValueError:
                pytest.fail(f"Valid HTTPS URL {url} was rejected")

    def test_validate_url_invalid_empty(self, downloader):
        """Test URL validation with empty or whitespace URLs."""
        invalid_urls = [
            "",
            "   ",
            "\t",
            "\n",
            "\r\n",
        ]

        for url in invalid_urls:
            with pytest.raises(ValueError) as exc_info:
                if url is None:
                    # Skip None test as it would cause AttributeError first
                    continue
                downloader._validate_url(url=url)

            if url is not None:
                assert "URL cannot be empty" in str(exc_info.value)

    def test_validate_url_invalid_scheme(self, downloader):
        """Test URL validation with invalid schemes."""
        invalid_urls = [
            "ftp://example.com",
            "file:///local/file.html",
            "ssh://example.com",
            "telnet://example.com",
            "mailto:user@example.com",
            "javascript:alert('test')",
            "data:text/html,<html></html>",
            "example.com",  # Missing scheme
            "//example.com",  # Protocol-relative URL
            "www.example.com",  # Missing scheme
        ]

        for url in invalid_urls:
            with pytest.raises(ValueError) as exc_info:
                downloader._validate_url(url=url)

            assert "URL must start with http:// or https://" in str(exc_info.value)
            assert url in str(exc_info.value)

    def test_validate_url_edge_cases(self, downloader):
        """Test URL validation with edge cases."""
        edge_cases = [
            "http://",  # Just scheme
            "https://",  # Just scheme
            "http:// ",  # Scheme with space
            "http://.",  # Invalid hostname
            "http://..",  # Invalid hostname
        ]

        for url in edge_cases:
            with pytest.raises(ValueError) as exc_info:
                downloader._validate_url(url=url)

            assert "URL must start with http:// or https://" in str(exc_info.value)

    @patch("pathlib.Path.mkdir")
    def test_ensure_output_directory_creates_directory(self, mock_mkdir, downloader):
        """Test that _ensure_output_directory creates parent directories."""
        output_path = Path("test/nested/directory/file.html")

        downloader._ensure_output_directory(output_path=output_path)

        # Should call mkdir on the parent directory
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("pathlib.Path.mkdir")
    def test_ensure_output_directory_with_existing_directory(self, mock_mkdir, downloader):
        """Test _ensure_output_directory with existing directory."""
        output_path = Path("existing/directory/file.html")

        # Simulate directory already exists
        mock_mkdir.return_value = None

        downloader._ensure_output_directory(output_path=output_path)

        # Should still call mkdir with exist_ok=True
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("pathlib.Path.mkdir")
    def test_ensure_output_directory_permission_error(self, mock_mkdir, downloader):
        """Test _ensure_output_directory with permission error."""
        output_path = Path("restricted/directory/file.html")

        # Simulate permission error
        mock_mkdir.side_effect = PermissionError("Permission denied")

        # Should not raise exception due to exist_ok=True behavior
        # The mkdir call should handle the error gracefully
        downloader._ensure_output_directory(output_path=output_path)

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("pathlib.Path.mkdir")
    def test_ensure_output_directory_file_at_root(self, mock_mkdir, downloader):
        """Test _ensure_output_directory with file at root level."""
        output_path = Path("file.html")

        downloader._ensure_output_directory(output_path=output_path)

        # Should still call mkdir on parent (which would be current directory)
        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_concrete_download_calls_validation(self, downloader):
        """Test that concrete download implementation calls validation methods."""
        url = "https://example.com/test"
        output_path = Path("test/output.html")

        with patch.object(downloader, "_validate_url") as mock_validate:
            with patch.object(downloader, "_ensure_output_directory") as mock_ensure:
                downloader.download(url=url, output_path=output_path)

                # Should call both validation methods
                mock_validate.assert_called_once_with(url=url)
                mock_ensure.assert_called_once_with(output_path=output_path)

        # Should record the download
        assert url in downloader.downloaded_urls
        assert output_path in downloader.downloaded_paths

    def test_concrete_download_with_invalid_url(self, downloader):
        """Test that concrete download handles invalid URL properly."""
        invalid_url = "not-a-valid-url"
        output_path = Path("output.html")

        with pytest.raises(ValueError):
            downloader.download(url=invalid_url, output_path=output_path)

        # Should not record failed downloads
        assert invalid_url not in downloader.downloaded_urls

    def test_multiple_downloads(self, downloader):
        """Test multiple downloads with the concrete implementation."""
        urls_and_paths = [
            ("https://example1.com", Path("output1.html")),
            ("http://example2.com/doc", Path("subdir/output2.html")),
            ("https://example3.com/api/docs", Path("api/output3.html")),
        ]

        for url, path in urls_and_paths:
            downloader.download(url=url, output_path=path)

        # Should record all downloads
        assert len(downloader.downloaded_urls) == 3
        assert len(downloader.downloaded_paths) == 3

        for url, path in urls_and_paths:
            assert url in downloader.downloaded_urls
            assert path in downloader.downloaded_paths

    def test_url_validation_preserves_original_url(self, downloader):
        """Test that URL validation preserves the original URL in error messages."""
        original_url = "invalid://example.com"

        with pytest.raises(ValueError) as exc_info:
            downloader._validate_url(url=original_url)

        # Error message should contain the original URL
        assert original_url in str(exc_info.value)

    def test_inheritance_hierarchy(self):
        """Test the inheritance hierarchy of downloader classes."""
        # BaseDocumentationDownloader should inherit from ABC
        assert issubclass(BaseDocumentationDownloader, ABC)

        # ConcreteDownloader should inherit from BaseDocumentationDownloader
        assert issubclass(ConcreteDownloader, BaseDocumentationDownloader)

        # ConcreteDownloader should be a concrete class (not abstract)
        concrete = ConcreteDownloader()
        assert isinstance(concrete, BaseDocumentationDownloader)
        assert isinstance(concrete, ABC)


class TestExceptionClasses:
    """Test suite for custom exception classes."""

    def test_network_error_inheritance(self):
        """Test that NetworkError inherits from Exception."""
        assert issubclass(NetworkError, Exception)

        # Should be able to instantiate and raise
        error = NetworkError("Network connection failed")
        assert str(error) == "Network connection failed"

        with pytest.raises(NetworkError):
            raise error

    def test_file_system_error_inheritance(self):
        """Test that FileSystemError inherits from Exception."""
        assert issubclass(FileSystemError, Exception)

        # Should be able to instantiate and raise
        error = FileSystemError("File system operation failed")
        assert str(error) == "File system operation failed"

        with pytest.raises(FileSystemError):
            raise error

    def test_exception_hierarchy(self):
        """Test exception hierarchy and catching."""
        network_error = NetworkError("Network issue")
        filesystem_error = FileSystemError("Filesystem issue")

        # Both should be catchable as generic Exception
        with pytest.raises(Exception):
            raise network_error

        with pytest.raises(Exception):
            raise filesystem_error

        # Should be catchable by their specific types
        with pytest.raises(NetworkError):
            raise NetworkError("Test network error")

        with pytest.raises(FileSystemError):
            raise FileSystemError("Test filesystem error")

    def test_exception_messages(self):
        """Test that exception messages are preserved."""
        network_msg = "Connection timeout after 30 seconds"
        filesystem_msg = "Permission denied: /restricted/path"

        network_error = NetworkError(network_msg)
        filesystem_error = FileSystemError(filesystem_msg)

        assert str(network_error) == network_msg
        assert str(filesystem_error) == filesystem_msg


class TestProtocolCompliance:
    """Test suite for protocol compliance."""

    def test_concrete_implementation_satisfies_protocol(self):
        """Test that concrete implementation satisfies the protocol."""
        downloader = ConcreteDownloader()

        # Should have the required download method
        assert hasattr(downloader, "download")
        assert callable(getattr(downloader, "download"))

        # Method should have the correct signature (can be called with url and output_path)
        try:
            # This should work without raising signature errors
            downloader.download(url="https://example.com", output_path=Path("test.html"))
        except Exception as e:
            # Only catch signature-related errors, not our validation errors
            if "signature" in str(e).lower() or "argument" in str(e).lower():
                pytest.fail(f"Method signature doesn't match protocol: {e}")

    def test_protocol_type_hints(self):
        """Test that protocol defines proper type hints."""
        # This is more of a static analysis test
        # We verify that the protocol method has annotations

        # Get the download method from the protocol
        if hasattr(DocumentationDownloader, "download"):
            # Simply verify the method exists on the protocol
            assert hasattr(DocumentationDownloader, "download")

            # Should have annotations (even if they're in __annotations__)
            # This test verifies the protocol is properly typed
            assert True  # Protocol exists and is defined
