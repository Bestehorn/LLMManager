"""
Unit tests for src.bedrock.CRISManager module.

Tests the CRISManager class and its methods for downloading, parsing, and managing
Amazon Bedrock Cross-Region Inference model information.
"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from bestehorn_llmmanager.bedrock.CRISManager import CRISManager, CRISManagerError
from bestehorn_llmmanager.bedrock.downloaders.base_downloader import FileSystemError, NetworkError
from bestehorn_llmmanager.bedrock.models.cris_constants import (
    CRISErrorMessages,
    CRISFilePaths,
    CRISLogMessages,
    CRISURLs,
)
from bestehorn_llmmanager.bedrock.models.cris_structures import CRISCatalog, CRISModelInfo
from bestehorn_llmmanager.bedrock.parsers.base_parser import ParsingError


class TestCRISManagerInitialization:
    """Test CRISManager initialization and configuration."""

    def test_default_initialization(self):
        """Test CRISManager initialization with default parameters."""
        manager = CRISManager()

        assert manager.html_output_path == Path(CRISFilePaths.DEFAULT_HTML_OUTPUT)
        assert manager.json_output_path == Path(CRISFilePaths.DEFAULT_JSON_OUTPUT)
        assert manager.documentation_url == CRISURLs.DOCUMENTATION
        assert manager._cached_catalog is None

    def test_custom_initialization(self):
        """Test CRISManager initialization with custom parameters."""
        custom_html = Path("custom/cris.html")
        custom_json = Path("custom/cris.json")
        custom_url = "https://custom.example.com/cris"
        custom_timeout = 60

        manager = CRISManager(
            html_output_path=custom_html,
            json_output_path=custom_json,
            documentation_url=custom_url,
            download_timeout=custom_timeout,
        )

        assert manager.html_output_path == custom_html
        assert manager.json_output_path == custom_json
        assert manager.documentation_url == custom_url
        assert manager._cached_catalog is None

    def test_components_initialization(self):
        """Test that internal components are properly initialized."""
        manager = CRISManager()

        # Check that components exist and are properly configured
        assert hasattr(manager, "_downloader")
        assert hasattr(manager, "_parser")
        assert hasattr(manager, "_serializer")
        assert hasattr(manager, "_logger")

    def test_repr_method(self):
        """Test string representation of CRISManager."""
        manager = CRISManager()
        repr_str = repr(manager)

        assert "CRISManager(" in repr_str
        assert str(manager.html_output_path) in repr_str
        assert str(manager.json_output_path) in repr_str
        assert manager.documentation_url in repr_str


class TestCRISManagerRefreshData:
    """Test CRISManager refresh_cris_data method."""

    @patch("bestehorn_llmmanager.bedrock.CRISManager.datetime")
    def test_refresh_cris_data_success(self, mock_datetime, temp_dir):
        """Test successful refresh of CRIS data."""
        # Setup
        fixed_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time

        manager = CRISManager(
            html_output_path=temp_dir / "cris.html", json_output_path=temp_dir / "cris.json"
        )

        # Mock components
        manager._downloader = Mock()
        manager._parser = Mock()
        manager._serializer = Mock()
        manager._logger = Mock()

        # Setup mock returns
        mock_models_dict = {"Claude 3.5 Sonnet": Mock(spec=CRISModelInfo)}
        manager._parser.parse.return_value = mock_models_dict

        # Execute
        result = manager.refresh_cris_data(force_download=True)

        # Verify
        assert isinstance(result, CRISCatalog)
        assert result.retrieval_timestamp == fixed_time
        assert result.cris_models == mock_models_dict

        # Verify component calls
        manager._downloader.download.assert_called_once()
        manager._parser.parse.assert_called_once_with(file_path=manager.html_output_path)
        manager._serializer.serialize_dict_to_file.assert_called_once()

        # Verify caching
        assert manager._cached_catalog == result

    def test_refresh_cris_data_no_force_download_recent_file(self, temp_dir):
        """Test refresh without force download when HTML file is recent."""
        manager = CRISManager(
            html_output_path=temp_dir / "cris.html", json_output_path=temp_dir / "cris.json"
        )

        # Create a recent HTML file
        html_file = temp_dir / "cris.html"
        html_file.write_text("mock html content")

        # Mock components
        manager._downloader = Mock()
        manager._parser = Mock()
        manager._serializer = Mock()

        mock_models_dict = {"test": Mock(spec=CRISModelInfo)}
        manager._parser.parse.return_value = mock_models_dict

        # Execute
        result = manager.refresh_cris_data(force_download=False)

        # Verify download was not called
        manager._downloader.download.assert_not_called()

        # But parsing and serialization still occurred
        manager._parser.parse.assert_called_once()
        manager._serializer.serialize_dict_to_file.assert_called_once()

    def test_refresh_cris_data_network_error(self):
        """Test refresh handling of network errors."""
        manager = CRISManager()
        manager._downloader = Mock()
        manager._logger = Mock()

        # Setup network error
        manager._downloader.download.side_effect = NetworkError("Connection failed")

        # Execute and verify exception
        with pytest.raises(CRISManagerError) as exc_info:
            manager.refresh_cris_data()

        assert "Failed to refresh CRIS data" in str(exc_info.value)
        assert "Connection failed" in str(exc_info.value)

    def test_refresh_cris_data_parsing_error(self, temp_dir):
        """Test refresh handling of parsing errors."""
        manager = CRISManager(html_output_path=temp_dir / "cris.html")

        # Create HTML file
        html_file = temp_dir / "cris.html"
        html_file.write_text("invalid html")

        manager._downloader = Mock()
        manager._parser = Mock()
        manager._logger = Mock()

        # Setup parsing error
        manager._parser.parse.side_effect = ParsingError("Invalid HTML structure")

        # Execute and verify exception
        with pytest.raises(CRISManagerError) as exc_info:
            manager.refresh_cris_data()

        assert "Failed to refresh CRIS data" in str(exc_info.value)
        assert "Invalid HTML structure" in str(exc_info.value)

    def test_refresh_cris_data_file_system_error(self):
        """Test refresh handling of file system errors."""
        manager = CRISManager()
        manager._downloader = Mock()
        manager._logger = Mock()

        # Setup file system error
        manager._downloader.download.side_effect = FileSystemError("Permission denied")

        # Execute and verify exception
        with pytest.raises(CRISManagerError) as exc_info:
            manager.refresh_cris_data()

        assert "Failed to refresh CRIS data" in str(exc_info.value)
        assert "Permission denied" in str(exc_info.value)


class TestCRISManagerLoadCachedData:
    """Test CRISManager load_cached_data method."""

    def test_load_cached_data_success(self, temp_dir):
        """Test successful loading of cached data."""
        json_file = temp_dir / "cris.json"
        json_file.write_text('{"test": "data"}')  # Create the file so exists() returns True

        manager = CRISManager(json_output_path=json_file)

        # Create mock cached data
        mock_catalog_data = {
            "retrieval_timestamp": "2024-01-01T12:00:00",
            "cris_models": {"test_model": {"inference_profile_id": "test:profile"}},
        }

        # Setup mocks
        manager._serializer = Mock()
        manager._serializer.load_from_file.return_value = mock_catalog_data
        manager._logger = Mock()

        # Mock CRISCatalog.from_dict
        mock_catalog = Mock(spec=CRISCatalog)
        with patch("bestehorn_llmmanager.bedrock.CRISManager.CRISCatalog") as mock_catalog_class:
            mock_catalog_class.from_dict.return_value = mock_catalog

            # Execute
            result = manager.load_cached_data()

        # Verify
        assert result == mock_catalog
        assert manager._cached_catalog == mock_catalog
        manager._serializer.load_from_file.assert_called_once_with(
            input_path=manager.json_output_path
        )

    def test_load_cached_data_file_not_exists(self, temp_dir):
        """Test loading cached data when file doesn't exist."""
        manager = CRISManager(json_output_path=temp_dir / "nonexistent.json")
        manager._logger = Mock()

        # Execute
        result = manager.load_cached_data()

        # Verify
        assert result is None
        assert manager._cached_catalog is None

    def test_load_cached_data_invalid_file(self, temp_dir):
        """Test loading cached data with invalid JSON file."""
        json_file = temp_dir / "invalid.json"
        json_file.write_text("invalid json content")

        manager = CRISManager(json_output_path=json_file)
        manager._serializer = Mock()
        manager._serializer.load_from_file.side_effect = Exception("Invalid JSON")
        manager._logger = Mock()

        # Execute
        result = manager.load_cached_data()

        # Verify
        assert result is None
        assert manager._cached_catalog is None


class TestCRISManagerQueryMethods:
    """Test CRISManager query and filtering methods."""

    def setup_method(self):
        """Setup for query method tests."""
        self.manager = CRISManager()

        # Create mock CRIS models
        self.mock_model_info = Mock(spec=CRISModelInfo)
        self.mock_model_info.get_destinations_for_source.return_value = ["us-west-2"]

        # Create mock catalog
        self.mock_catalog = Mock(spec=CRISCatalog)
        self.mock_catalog.cris_models = {"test_model": self.mock_model_info}
        self.mock_catalog.get_models_by_source_region.return_value = {
            "test_model": self.mock_model_info
        }
        self.mock_catalog.get_models_by_destination_region.return_value = {
            "test_model": self.mock_model_info
        }
        self.mock_catalog.get_inference_profile_for_model.return_value = "test:profile"
        self.mock_catalog.get_all_source_regions.return_value = ["us-east-1", "us-west-2"]
        self.mock_catalog.get_all_destination_regions.return_value = ["us-west-2"]
        self.mock_catalog.get_model_names.return_value = ["test_model"]
        self.mock_catalog.model_count = 1
        self.mock_catalog.has_model.return_value = True

        # Set cached catalog
        self.manager._cached_catalog = self.mock_catalog

    def test_get_models_by_source_region_success(self):
        """Test getting models by source region."""
        result = self.manager.get_models_by_source_region("us-east-1")

        assert result == {"test_model": self.mock_model_info}
        self.mock_catalog.get_models_by_source_region.assert_called_once_with(
            source_region="us-east-1"
        )

    def test_get_models_by_source_region_no_data(self):
        """Test getting models by source region without cached data."""
        self.manager._cached_catalog = None

        with pytest.raises(CRISManagerError) as exc_info:
            self.manager.get_models_by_source_region("us-east-1")

        assert CRISErrorMessages.NO_DATA_AVAILABLE in str(exc_info.value)

    def test_get_models_by_destination_region_success(self):
        """Test getting models by destination region."""
        result = self.manager.get_models_by_destination_region("us-west-2")

        assert result == {"test_model": self.mock_model_info}
        self.mock_catalog.get_models_by_destination_region.assert_called_once_with(
            destination_region="us-west-2"
        )

    def test_get_models_by_destination_region_no_data(self):
        """Test getting models by destination region without cached data."""
        self.manager._cached_catalog = None

        with pytest.raises(CRISManagerError) as exc_info:
            self.manager.get_models_by_destination_region("us-west-2")

        assert CRISErrorMessages.NO_DATA_AVAILABLE in str(exc_info.value)

    def test_get_inference_profile_for_model_success(self):
        """Test getting inference profile for model."""
        result = self.manager.get_inference_profile_for_model("test_model")

        assert result == "test:profile"
        self.mock_catalog.get_inference_profile_for_model.assert_called_once_with(
            model_name="test_model"
        )

    def test_get_inference_profile_for_model_no_data(self):
        """Test getting inference profile without cached data."""
        self.manager._cached_catalog = None

        with pytest.raises(CRISManagerError) as exc_info:
            self.manager.get_inference_profile_for_model("test_model")

        assert CRISErrorMessages.NO_DATA_AVAILABLE in str(exc_info.value)

    def test_get_all_source_regions_success(self):
        """Test getting all source regions."""
        result = self.manager.get_all_source_regions()

        assert result == ["us-east-1", "us-west-2"]
        self.mock_catalog.get_all_source_regions.assert_called_once()

    def test_get_all_source_regions_no_data(self):
        """Test getting all source regions without cached data."""
        self.manager._cached_catalog = None

        with pytest.raises(CRISManagerError) as exc_info:
            self.manager.get_all_source_regions()

        assert CRISErrorMessages.NO_DATA_AVAILABLE in str(exc_info.value)

    def test_get_all_destination_regions_success(self):
        """Test getting all destination regions."""
        result = self.manager.get_all_destination_regions()

        assert result == ["us-west-2"]
        self.mock_catalog.get_all_destination_regions.assert_called_once()

    def test_get_all_destination_regions_no_data(self):
        """Test getting all destination regions without cached data."""
        self.manager._cached_catalog = None

        with pytest.raises(CRISManagerError) as exc_info:
            self.manager.get_all_destination_regions()

        assert CRISErrorMessages.NO_DATA_AVAILABLE in str(exc_info.value)

    def test_get_model_names_success(self):
        """Test getting model names."""
        result = self.manager.get_model_names()

        assert result == ["test_model"]
        self.mock_catalog.get_model_names.assert_called_once()

    def test_get_model_names_no_data(self):
        """Test getting model names without cached data."""
        self.manager._cached_catalog = None

        with pytest.raises(CRISManagerError) as exc_info:
            self.manager.get_model_names()

        assert CRISErrorMessages.NO_DATA_AVAILABLE in str(exc_info.value)

    def test_get_model_count_success(self):
        """Test getting model count."""
        result = self.manager.get_model_count()

        assert result == 1

    def test_get_model_count_no_data(self):
        """Test getting model count without cached data."""
        self.manager._cached_catalog = None

        with pytest.raises(CRISManagerError) as exc_info:
            self.manager.get_model_count()

        assert CRISErrorMessages.NO_DATA_AVAILABLE in str(exc_info.value)

    def test_has_model_success(self):
        """Test checking if model exists."""
        result = self.manager.has_model("test_model")

        assert result is True
        self.mock_catalog.has_model.assert_called_once_with(model_name="test_model")

    def test_has_model_no_data(self):
        """Test checking if model exists without cached data."""
        self.manager._cached_catalog = None

        with pytest.raises(CRISManagerError) as exc_info:
            self.manager.has_model("test_model")

        assert CRISErrorMessages.NO_DATA_AVAILABLE in str(exc_info.value)

    def test_get_destinations_for_source_and_model_success(self):
        """Test getting destinations for source and model."""
        result = self.manager.get_destinations_for_source_and_model("test_model", "us-east-1")

        assert result == ["us-west-2"]
        self.mock_model_info.get_destinations_for_source.assert_called_once_with(
            source_region="us-east-1"
        )

    def test_get_destinations_for_source_and_model_nonexistent_model(self):
        """Test getting destinations for nonexistent model."""
        self.mock_catalog.cris_models = {}

        result = self.manager.get_destinations_for_source_and_model("nonexistent", "us-east-1")

        assert result == []

    def test_get_destinations_for_source_and_model_no_data(self):
        """Test getting destinations without cached data."""
        self.manager._cached_catalog = None

        with pytest.raises(CRISManagerError) as exc_info:
            self.manager.get_destinations_for_source_and_model("test_model", "us-east-1")

        assert CRISErrorMessages.NO_DATA_AVAILABLE in str(exc_info.value)


class TestCRISManagerPrivateMethods:
    """Test CRISManager private helper methods."""

    def test_download_documentation(self):
        """Test downloading documentation."""
        manager = CRISManager()
        manager._downloader = Mock()
        manager._logger = Mock()

        # Execute
        manager._download_documentation()

        # Verify
        manager._downloader.download.assert_called_once_with(
            url=manager.documentation_url, output_path=manager.html_output_path
        )

    def test_parse_documentation(self):
        """Test parsing documentation."""
        manager = CRISManager()
        manager._parser = Mock()

        expected_result = {"test": Mock(spec=CRISModelInfo)}
        manager._parser.parse.return_value = expected_result

        # Execute
        result = manager._parse_documentation()

        # Verify
        assert result == expected_result
        manager._parser.parse.assert_called_once_with(file_path=manager.html_output_path)

    def test_save_catalog_to_json(self):
        """Test saving catalog to JSON."""
        manager = CRISManager()
        manager._serializer = Mock()
        manager._logger = Mock()

        # Create mock catalog
        mock_catalog = Mock(spec=CRISCatalog)
        mock_catalog.to_dict.return_value = {"test": "data"}

        # Execute
        manager._save_catalog_to_json(mock_catalog)

        # Verify
        mock_catalog.to_dict.assert_called_once()
        manager._serializer.serialize_dict_to_file.assert_called_once_with(
            data={"test": "data"}, output_path=manager.json_output_path
        )

    def test_is_html_file_recent_file_not_exists(self, temp_dir):
        """Test checking if HTML file is recent when file doesn't exist."""
        manager = CRISManager(html_output_path=temp_dir / "nonexistent.html")

        result = manager._is_html_file_recent()

        assert result is False

    def test_is_html_file_recent_file_is_recent(self, temp_dir):
        """Test checking if HTML file is recent when file is recent."""
        html_file = temp_dir / "recent.html"
        html_file.write_text("content")

        manager = CRISManager(html_output_path=html_file)

        result = manager._is_html_file_recent(max_age_hours=24)

        assert result is True

    def test_is_html_file_recent_file_is_old(self, temp_dir):
        """Test checking if HTML file is recent when file is old."""
        html_file = temp_dir / "old.html"
        html_file.write_text("content")

        # Modify file timestamp to be old using os.utime
        import os

        old_time = datetime.now() - timedelta(hours=2)
        old_timestamp = old_time.timestamp()
        os.utime(html_file, (old_timestamp, old_timestamp))

        manager = CRISManager(html_output_path=html_file)

        result = manager._is_html_file_recent(max_age_hours=1)

        assert result is False

    def test_is_html_file_recent_os_error(self, temp_dir):
        """Test checking if HTML file is recent with OS error."""
        html_file = temp_dir / "test.html"
        html_file.write_text("content")  # Create the file first so exists() passes

        manager = CRISManager(html_output_path=html_file)

        # Mock the html_output_path with a mock that raises OSError on stat()
        mock_path = Mock()
        mock_path.exists.return_value = True  # File exists
        mock_path.stat.side_effect = OSError("Permission denied")  # But stat() fails

        # Replace the manager's path with our mock
        manager.html_output_path = mock_path

        result = manager._is_html_file_recent()

        assert result is False


class TestCRISManagerIntegration:
    """Integration tests for CRISManager."""

    def test_full_workflow_integration(self, temp_dir):
        """Test the complete workflow from refresh to queries."""
        manager = CRISManager(
            html_output_path=temp_dir / "cris.html", json_output_path=temp_dir / "cris.json"
        )

        # Mock all components for integration test
        manager._downloader = Mock()
        manager._parser = Mock()
        manager._serializer = Mock()
        manager._logger = Mock()

        # Setup mock data
        mock_model_info = Mock(spec=CRISModelInfo)
        mock_models_dict = {"Claude 3.5 Sonnet": mock_model_info}
        manager._parser.parse.return_value = mock_models_dict

        # Mock catalog methods
        with patch("bestehorn_llmmanager.bedrock.CRISManager.CRISCatalog") as mock_catalog_class:
            mock_catalog = Mock(spec=CRISCatalog)
            mock_catalog.cris_models = mock_models_dict
            mock_catalog.get_model_names.return_value = ["Claude 3.5 Sonnet"]
            mock_catalog.model_count = 1
            mock_catalog_class.return_value = mock_catalog

            # Execute workflow
            catalog = manager.refresh_cris_data()
            model_names = manager.get_model_names()
            model_count = manager.get_model_count()

            # Verify results
            assert catalog is not None
            assert model_names == ["Claude 3.5 Sonnet"]
            assert model_count == 1

            # Verify all components were called
            manager._downloader.download.assert_called_once()
            manager._parser.parse.assert_called_once()
            manager._serializer.serialize_dict_to_file.assert_called_once()
