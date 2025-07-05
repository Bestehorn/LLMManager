"""
Fixed unit tests for ModelManager class.
Tests the functionality of the Amazon Bedrock Model Manager.
"""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bestehorn_llmmanager.bedrock.downloaders.base_downloader import FileSystemError, NetworkError
from bestehorn_llmmanager.bedrock.ModelManager import ModelManager, ModelManagerError
from bestehorn_llmmanager.bedrock.models.constants import FilePaths, URLs
from bestehorn_llmmanager.bedrock.models.data_structures import BedrockModelInfo, ModelCatalog
from bestehorn_llmmanager.bedrock.parsers.base_parser import ParsingError


class TestModelManager:
    """Test cases for ModelManager class."""

    @pytest.fixture
    def mock_downloader(self):
        """Create a mock HTMLDocumentationDownloader."""
        return Mock()

    @pytest.fixture
    def mock_parser(self):
        """Create a mock EnhancedBedrockHTMLParser."""
        mock = Mock()
        mock.parse.return_value = {
            "Claude 3 Haiku": Mock(spec=BedrockModelInfo),
            "Claude 3 Sonnet": Mock(spec=BedrockModelInfo),
        }
        return mock

    @pytest.fixture
    def mock_serializer(self):
        """Create a mock JSONModelSerializer."""
        return Mock()

    @pytest.fixture
    def model_manager(self, mock_downloader, mock_parser, mock_serializer):
        """Create a ModelManager instance with mocked components."""
        with patch(
            "bestehorn_llmmanager.bedrock.downloaders.html_downloader.HTMLDocumentationDownloader",
            return_value=mock_downloader,
        ), patch(
            "bestehorn_llmmanager.bedrock.parsers.enhanced_bedrock_parser.EnhancedBedrockHTMLParser",
            return_value=mock_parser,
        ), patch(
            "bestehorn_llmmanager.bedrock.serializers.json_serializer.JSONModelSerializer",
            return_value=mock_serializer,
        ):
            manager = ModelManager()
            # Manually assign the mocks to ensure they're used
            manager._downloader = mock_downloader
            manager._parser = mock_parser
            manager._serializer = mock_serializer
            return manager

    def test_init_default_configuration(self):
        """Test default initialization of ModelManager."""
        manager = ModelManager()

        assert manager.html_output_path == Path(FilePaths.DEFAULT_HTML_OUTPUT)
        assert manager.json_output_path == Path(FilePaths.DEFAULT_JSON_OUTPUT)
        assert manager.documentation_url == URLs.BEDROCK_MODELS_DOCUMENTATION

    def test_init_custom_configuration(self):
        """Test initialization with custom configuration."""
        html_path = Path("custom/path.html")
        json_path = Path("custom/models.json")
        custom_url = "https://custom.url.com"

        manager = ModelManager(
            html_output_path=html_path,
            json_output_path=json_path,
            documentation_url=custom_url,
            download_timeout=60,
        )

        assert manager.html_output_path == html_path
        assert manager.json_output_path == json_path
        assert manager.documentation_url == custom_url

    def test_refresh_model_data_success(
        self, model_manager, mock_downloader, mock_parser, mock_serializer
    ):
        """Test successful model data refresh."""
        # Setup mocks
        models_dict = {
            "Claude 3 Haiku": Mock(spec=BedrockModelInfo),
            "Claude 3 Sonnet": Mock(spec=BedrockModelInfo),
        }
        mock_parser.parse.return_value = models_dict

        # Execute
        catalog = model_manager.refresh_model_data(force_download=True)

        # Verify
        assert isinstance(catalog, ModelCatalog)
        assert catalog.models == models_dict
        assert isinstance(catalog.retrieval_timestamp, datetime)
        mock_downloader.download.assert_called_once()
        mock_parser.parse.assert_called_once()
        mock_serializer.serialize_to_file.assert_called_once()

    def test_refresh_model_data_network_error(self, model_manager, mock_downloader):
        """Test model data refresh with network error."""
        mock_downloader.download.side_effect = NetworkError("Connection failed")

        with pytest.raises(
            ModelManagerError, match="Failed to refresh model data: Connection failed"
        ):
            model_manager.refresh_model_data()

    def test_refresh_model_data_parsing_error(self, model_manager, mock_parser):
        """Test model data refresh with parsing error."""
        mock_parser.parse.side_effect = ParsingError("Invalid HTML structure")

        with pytest.raises(
            ModelManagerError, match="Failed to refresh model data: Invalid HTML structure"
        ):
            model_manager.refresh_model_data()

    def test_refresh_model_data_file_system_error(self, model_manager, mock_serializer):
        """Test model data refresh with file system error."""
        mock_serializer.serialize_to_file.side_effect = FileSystemError("Permission denied")

        with pytest.raises(
            ModelManagerError, match="Failed to refresh model data: Permission denied"
        ):
            model_manager.refresh_model_data()

    def test_refresh_model_data_skip_download_if_recent(
        self, model_manager, mock_downloader, tmp_path
    ):
        """Test that download is skipped if HTML file is recent."""
        # Create a recent HTML file
        html_file = tmp_path / "test.html"
        html_file.write_text("test content")
        html_file.touch()  # Update modification time to now

        model_manager.html_output_path = html_file

        # Execute with force_download=False
        with patch.object(model_manager, "_parse_documentation", return_value={}):
            result = model_manager.refresh_model_data(force_download=False)

        # Verify download was not called
        mock_downloader.download.assert_not_called()

        # Verify result is valid
        assert isinstance(result, ModelCatalog)

    def test_load_cached_data_file_not_exists(self, model_manager):
        """Test loading cached data when file doesn't exist."""
        model_manager.json_output_path = Path("nonexistent.json")

        result = model_manager.load_cached_data()

        assert result is None

    def test_load_cached_data_success(self, model_manager, mock_serializer, tmp_path):
        """Test successful loading of cached data."""
        # Create a JSON file
        json_file = tmp_path / "models.json"
        json_file.write_text('{"models": {}}')
        model_manager.json_output_path = json_file

        mock_serializer.load_from_file.return_value = {"models": {}}

        model_manager.load_cached_data()

        mock_serializer.load_from_file.assert_called_once_with(input_path=json_file)

    def test_load_cached_data_error(self, model_manager, mock_serializer, tmp_path):
        """Test loading cached data with error."""
        json_file = tmp_path / "models.json"
        json_file.write_text("invalid json")
        model_manager.json_output_path = json_file

        mock_serializer.load_from_file.side_effect = Exception("JSON decode error")

        result = model_manager.load_cached_data()

        assert result is None

    def test_get_models_by_provider_no_data(self, model_manager):
        """Test getting models by provider when no data is available."""
        with pytest.raises(ModelManagerError, match="No model data available"):
            model_manager.get_models_by_provider("Amazon")

    def test_get_models_by_provider_success(self, model_manager):
        """Test successful retrieval of models by provider."""
        # Setup cached catalog
        mock_catalog = Mock(spec=ModelCatalog)
        mock_model = Mock()
        mock_catalog.get_models_by_provider.return_value = {"Model1": mock_model}
        model_manager._cached_catalog = mock_catalog

        result = model_manager.get_models_by_provider("Amazon")

        assert result == {"Model1": mock_model}
        mock_catalog.get_models_by_provider.assert_called_once_with(provider="Amazon")

    def test_get_models_by_region_no_data(self, model_manager):
        """Test getting models by region when no data is available."""
        with pytest.raises(ModelManagerError, match="No model data available"):
            model_manager.get_models_by_region("us-east-1")

    def test_get_models_by_region_success(self, model_manager):
        """Test successful retrieval of models by region."""
        # Setup cached catalog
        mock_catalog = Mock(spec=ModelCatalog)
        mock_model = Mock()
        mock_catalog.get_models_by_region.return_value = {"Model1": mock_model}
        model_manager._cached_catalog = mock_catalog

        result = model_manager.get_models_by_region("us-east-1")

        assert result == {"Model1": mock_model}
        mock_catalog.get_models_by_region.assert_called_once_with(region="us-east-1")

    def test_get_streaming_models_no_data(self, model_manager):
        """Test getting streaming models when no data is available."""
        with pytest.raises(ModelManagerError, match="No model data available"):
            model_manager.get_streaming_models()

    def test_get_streaming_models_success(self, model_manager):
        """Test successful retrieval of streaming models."""
        # Setup cached catalog
        mock_catalog = Mock(spec=ModelCatalog)
        mock_model = Mock()
        mock_catalog.get_streaming_models.return_value = {"Model1": mock_model}
        model_manager._cached_catalog = mock_catalog

        result = model_manager.get_streaming_models()

        assert result == {"Model1": mock_model}
        mock_catalog.get_streaming_models.assert_called_once()

    def test_get_model_count_no_data(self, model_manager):
        """Test getting model count when no data is available."""
        with pytest.raises(ModelManagerError, match="No model data available"):
            model_manager.get_model_count()

    def test_get_model_count_success(self, model_manager):
        """Test successful retrieval of model count."""
        # Setup cached catalog
        mock_catalog = Mock(spec=ModelCatalog)
        mock_catalog.model_count = 5
        model_manager._cached_catalog = mock_catalog

        result = model_manager.get_model_count()

        assert result == 5

    def test_is_html_file_recent_file_not_exists(self, model_manager):
        """Test checking if HTML file is recent when file doesn't exist."""
        model_manager.html_output_path = Path("nonexistent.html")

        result = model_manager._is_html_file_recent()

        assert result is False

    def test_is_html_file_recent_file_is_old(self, model_manager, tmp_path):
        """Test checking if HTML file is recent when file is old."""
        # Create an old file
        html_file = tmp_path / "old.html"
        html_file.write_text("content")

        # Set modification time to 2 hours ago
        old_time = datetime.now() - timedelta(hours=2)
        html_file.touch()

        model_manager.html_output_path = html_file

        # Mock the datetime methods in the ModelManager module
        with patch("bestehorn_llmmanager.bedrock.ModelManager.datetime") as mock_datetime_class:
            mock_datetime_class.now.return_value = datetime.now()
            mock_datetime_class.fromtimestamp.return_value = old_time

            result = model_manager._is_html_file_recent(max_age_hours=1)

        assert result is False

    def test_is_html_file_recent_file_is_recent(self, model_manager, tmp_path):
        """Test checking if HTML file is recent when file is recent."""
        # Create a recent file
        html_file = tmp_path / "recent.html"
        html_file.write_text("content")
        html_file.touch()  # Update modification time to now

        model_manager.html_output_path = html_file

        result = model_manager._is_html_file_recent(max_age_hours=1)

        assert result is True

    def test_is_html_file_recent_os_error(self, model_manager, tmp_path):
        """Test checking if HTML file is recent with OS error."""
        html_file = tmp_path / "test.html"
        html_file.write_text("test content")  # Create the file
        model_manager.html_output_path = html_file

        # Mock datetime.fromtimestamp to raise OSError
        with patch("bestehorn_llmmanager.bedrock.ModelManager.datetime") as mock_datetime_class:
            mock_datetime_class.fromtimestamp.side_effect = OSError("Permission denied")
            result = model_manager._is_html_file_recent()

        assert result is False

    def test_download_documentation(self, model_manager, mock_downloader):
        """Test downloading documentation."""
        model_manager._download_documentation()

        mock_downloader.download.assert_called_once_with(
            url=model_manager.documentation_url, output_path=model_manager.html_output_path
        )

    def test_parse_documentation(self, model_manager, mock_parser):
        """Test parsing documentation."""
        expected_models = {"Model1": Mock()}
        mock_parser.parse.return_value = expected_models

        result = model_manager._parse_documentation()

        assert result == expected_models
        mock_parser.parse.assert_called_once_with(file_path=model_manager.html_output_path)

    def test_save_catalog_to_json(self, model_manager, mock_serializer):
        """Test saving catalog to JSON."""
        catalog = Mock(spec=ModelCatalog)

        model_manager._save_catalog_to_json(catalog)

        mock_serializer.serialize_to_file.assert_called_once_with(
            catalog=catalog, output_path=model_manager.json_output_path
        )

    def test_repr(self, model_manager):
        """Test string representation of ModelManager."""
        repr_str = repr(model_manager)

        assert "ModelManager" in repr_str
        assert str(model_manager.html_output_path) in repr_str
        assert str(model_manager.json_output_path) in repr_str
        assert model_manager.documentation_url in repr_str


class TestModelManagerIntegration:
    """Integration tests for ModelManager."""

    def test_full_refresh_workflow(self, tmp_path):
        """Test the complete refresh workflow."""
        # Create temporary paths
        html_path = tmp_path / "models.html"
        json_path = tmp_path / "models.json"

        # Create mock components
        mock_downloader = Mock()
        mock_parser = Mock()
        mock_serializer = Mock()

        # Setup parser to return test data
        test_models = {
            "Claude 3 Haiku": Mock(spec=BedrockModelInfo),
            "Claude 3 Sonnet": Mock(spec=BedrockModelInfo),
        }
        mock_parser.parse.return_value = test_models

        # Create manager with mocked components
        # Patch the imported classes in the ModelManager module
        with patch.object(
            ModelManager, "_downloader", mock_downloader, create=True
        ), patch.object(
            ModelManager, "_parser", mock_parser, create=True
        ), patch.object(
            ModelManager, "_serializer", mock_serializer, create=True
        ):

            manager = ModelManager(html_output_path=html_path, json_output_path=json_path)

            # Manually assign the mocks to ensure they're used
            manager._downloader = mock_downloader
            manager._parser = mock_parser
            manager._serializer = mock_serializer

            # Execute refresh with force_download=True to ensure download is called
            catalog = manager.refresh_model_data(force_download=True)

            # Verify workflow completed successfully
            assert isinstance(catalog, ModelCatalog)
            assert isinstance(catalog.retrieval_timestamp, datetime)

            # Verify all components were called in order
            mock_downloader.download.assert_called_once()
            mock_parser.parse.assert_called_once()
            mock_serializer.serialize_to_file.assert_called_once()

            # Verify catalog was cached
            assert manager._cached_catalog == catalog

            # Verify model names are correct (the parser mock returns our test_models)
            assert "Claude 3 Haiku" in catalog.models
            assert "Claude 3 Sonnet" in catalog.models
            assert len(catalog.models) == 2

            # Verify the parser was called with the correct path
            mock_parser.parse.assert_called_with(file_path=html_path)

            # Verify the serializer was called with the catalog
            mock_serializer.serialize_to_file.assert_called_with(
                catalog=catalog, output_path=json_path
            )
