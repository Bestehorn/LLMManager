"""
Unit tests for UnifiedModelManager class.
Tests the functionality of the Unified Amazon Bedrock Model Manager.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bestehorn_llmmanager.bedrock.correlators.model_cris_correlator import ModelCRISCorrelationError
from bestehorn_llmmanager.bedrock.downloaders.base_downloader import FileSystemError, NetworkError
from bestehorn_llmmanager.bedrock.models.access_method import (
    AccessRecommendation,
    ModelAccessInfo,
)
from bestehorn_llmmanager.bedrock.models.cris_structures import CRISCatalog
from bestehorn_llmmanager.bedrock.models.data_structures import ModelCatalog
from bestehorn_llmmanager.bedrock.models.unified_constants import (
    AccessMethodPriority,
    CacheManagementConstants,
    UnifiedFilePaths,
)
from bestehorn_llmmanager.bedrock.models.unified_structures import (
    UnifiedModelCatalog,
    UnifiedModelInfo,
)
from bestehorn_llmmanager.bedrock.parsers.base_parser import ParsingError
from bestehorn_llmmanager.bedrock.UnifiedModelManager import (
    UnifiedModelManager,
    UnifiedModelManagerError,
)


class TestUnifiedModelManager:
    """Test cases for UnifiedModelManager class."""

    @pytest.fixture
    def mock_model_manager(self):
        """Create a mock ModelManager."""
        mock = Mock()
        model_catalog = Mock(spec=ModelCatalog)
        model_catalog.models = {}  # Add required attribute
        model_catalog.retrieval_timestamp = datetime.now()  # Add required timestamp
        mock.refresh_model_data.return_value = model_catalog
        return mock

    @pytest.fixture
    def mock_cris_manager(self):
        """Create a mock CRISManager."""
        mock = Mock()
        cris_catalog = Mock(spec=CRISCatalog)
        cris_catalog.cris_models = {}  # Add required attribute
        mock.refresh_cris_data.return_value = cris_catalog
        return mock

    @pytest.fixture
    def mock_unified_catalog(self):
        """Create a mock UnifiedModelCatalog with test data."""
        catalog = Mock(spec=UnifiedModelCatalog)
        catalog.unified_models = {
            "Claude 3 Haiku": Mock(spec=UnifiedModelInfo),
            "Claude 3 Sonnet": Mock(spec=UnifiedModelInfo),
        }
        catalog.to_dict.return_value = {"unified_models": {}}
        catalog.model_count = 2
        return catalog

    @pytest.fixture
    def mock_correlator(self, mock_unified_catalog):
        """Create a mock ModelCRISCorrelator."""
        mock = Mock()
        mock.correlate_catalogs.return_value = mock_unified_catalog
        mock.get_correlation_stats.return_value = {
            "total_models": 2,
            "correlated": 2,
            "uncorrelated": 0,
        }
        mock.is_fuzzy_matching_enabled.return_value = True
        return mock

    @pytest.fixture
    def mock_serializer(self):
        """Create a mock JSONModelSerializer."""
        return Mock()

    @pytest.fixture
    def unified_manager(
        self,
        mock_model_manager,
        mock_cris_manager,
        mock_correlator,
        mock_serializer,
        mock_unified_catalog,
    ):
        """Create a UnifiedModelManager instance with mocked components."""
        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelManager",
                return_value=mock_model_manager,
            ),
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.CRISManager",
                return_value=mock_cris_manager,
            ),
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelCRISCorrelator",
                return_value=mock_correlator,
            ),
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer",
                return_value=mock_serializer,
            ),
        ):
            manager = UnifiedModelManager()
            # Pre-populate the cached catalog for tests that expect it
            manager._cached_catalog = mock_unified_catalog
            return manager

    def test_init_default_configuration(self):
        """Test default initialization of UnifiedModelManager."""
        manager = UnifiedModelManager()

        assert manager.json_output_path == Path(UnifiedFilePaths.DEFAULT_UNIFIED_JSON_OUTPUT)
        assert manager.force_download is False

    def test_init_custom_configuration(self):
        """Test initialization with custom configuration."""
        json_path = Path("custom/unified.json")

        manager = UnifiedModelManager(
            json_output_path=json_path,
            force_download=False,
            download_timeout=60,
            enable_fuzzy_matching=False,
        )

        assert manager.json_output_path == json_path
        assert manager.force_download is False

    def test_refresh_unified_data_success(
        self, mock_model_manager, mock_cris_manager, mock_correlator, mock_serializer
    ):
        """Test successful unified data refresh."""
        # Create a fresh manager without pre-populated cache
        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelManager",
                return_value=mock_model_manager,
            ),
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.CRISManager",
                return_value=mock_cris_manager,
            ),
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelCRISCorrelator",
                return_value=mock_correlator,
            ),
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer",
                return_value=mock_serializer,
            ),
        ):

            manager = UnifiedModelManager()

            # Execute
            catalog = manager.refresh_unified_data()

            # Verify workflow (uses default force_download=False)
            mock_model_manager.refresh_model_data.assert_called_once_with(force_download=False)
            mock_cris_manager.refresh_cris_data.assert_called_once_with(force_download=False)
            mock_correlator.correlate_catalogs.assert_called_once()
            mock_serializer.serialize_dict_to_file.assert_called_once()

            # Verify catalog was cached
            assert manager._cached_catalog == catalog

    def test_refresh_unified_data_force_download_override(
        self, mock_model_manager, mock_cris_manager
    ):
        """Test unified data refresh with force_download override."""
        # Create a fresh manager
        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelManager",
                return_value=mock_model_manager,
            ),
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.CRISManager",
                return_value=mock_cris_manager,
            ),
        ):

            manager = UnifiedModelManager()

            # Execute with force_download=False
            manager.refresh_unified_data(force_download=False)

            # Verify force_download was passed correctly
            mock_model_manager.refresh_model_data.assert_called_once_with(force_download=False)
            mock_cris_manager.refresh_cris_data.assert_called_once_with(force_download=False)

    def test_refresh_unified_data_network_error(self, mock_model_manager):
        """Test unified data refresh with network error."""
        with patch(
            "bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelManager",
            return_value=mock_model_manager,
        ):
            manager = UnifiedModelManager()

            mock_model_manager.refresh_model_data.side_effect = NetworkError("Connection failed")

            with pytest.raises(
                UnifiedModelManagerError,
                match="Failed to refresh unified model data: Connection failed",
            ):
                manager.refresh_unified_data()

    def test_refresh_unified_data_parsing_error(
        self, mock_cris_manager, mock_model_manager, mock_correlator
    ):
        """Test unified data refresh with CRIS parsing error (non-fatal)."""
        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelManager",
                return_value=mock_model_manager,
            ),
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.CRISManager",
                return_value=mock_cris_manager,
            ),
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelCRISCorrelator",
                return_value=mock_correlator,
            ),
        ):

            manager = UnifiedModelManager()

            # Model manager succeeds but CRIS manager fails (should be non-fatal)
            mock_cris_manager.refresh_cris_data.side_effect = ParsingError("Invalid CRIS data")

            # Should succeed without CRIS data (CRIS failures are non-fatal)
            catalog = manager.refresh_unified_data()

            # Verify workflow continued with model data only
            mock_model_manager.refresh_model_data.assert_called_once()
            # CRIS manager was called but failed
            mock_cris_manager.refresh_cris_data.assert_called_once()
            # Correlator was called with None for CRIS catalog
            mock_correlator.correlate_catalogs.assert_called_once()
            # Verify cris_catalog argument was None
            call_args = mock_correlator.correlate_catalogs.call_args
            assert call_args.kwargs["cris_catalog"] is None

            # Catalog should still be returned
            assert catalog is not None

    def test_refresh_unified_data_correlation_error(self, mock_correlator):
        """Test unified data refresh with correlation error."""
        with patch(
            "bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelCRISCorrelator",
            return_value=mock_correlator,
        ):
            manager = UnifiedModelManager()

            mock_correlator.correlate_catalogs.side_effect = ModelCRISCorrelationError(
                "Correlation failed"
            )

            with pytest.raises(
                UnifiedModelManagerError,
                match="Failed to refresh unified model data: Correlation failed",
            ):
                manager.refresh_unified_data()

    def test_refresh_unified_data_file_system_error(self, mock_serializer):
        """Test unified data refresh with file system error."""
        with patch(
            "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer",
            return_value=mock_serializer,
        ):
            manager = UnifiedModelManager()

            mock_serializer.serialize_dict_to_file.side_effect = FileSystemError(
                "Permission denied"
            )

            with pytest.raises(
                UnifiedModelManagerError,
                match="Failed to refresh unified model data: Permission denied",
            ):
                manager.refresh_unified_data()

    def test_load_cached_data_file_not_exists(self, unified_manager):
        """Test loading cached data when file doesn't exist."""
        unified_manager.json_output_path = Path("nonexistent.json")
        unified_manager._cached_catalog = None  # Reset cache

        result = unified_manager.load_cached_data()

        assert result is None

    def test_load_cached_data_success(self, unified_manager, mock_serializer, tmp_path):
        """Test successful loading of cached data."""
        # Create a JSON file
        json_file = tmp_path / "unified.json"
        json_file.write_text('{"unified_models": {}}')
        unified_manager.json_output_path = json_file
        unified_manager._cached_catalog = None  # Reset cache

        # Mock serializer and UnifiedModelCatalog.from_dict
        mock_data = {"unified_models": {}}
        mock_serializer.load_from_file.return_value = mock_data

        mock_catalog = Mock(spec=UnifiedModelCatalog)
        with patch.object(UnifiedModelCatalog, "from_dict", return_value=mock_catalog):
            result = unified_manager.load_cached_data()

        assert result == mock_catalog
        assert unified_manager._cached_catalog == mock_catalog
        mock_serializer.load_from_file.assert_called_once_with(input_path=json_file)

    def test_load_cached_data_error(self, unified_manager, mock_serializer, tmp_path):
        """Test loading cached data with error."""
        json_file = tmp_path / "unified.json"
        json_file.write_text("invalid json")
        unified_manager.json_output_path = json_file
        unified_manager._cached_catalog = None  # Reset cache

        mock_serializer.load_from_file.side_effect = Exception("JSON decode error")

        result = unified_manager.load_cached_data()

        assert result is None

    def test_get_model_access_info_no_data(self):
        """Test getting model access info when no data is available."""
        manager = UnifiedModelManager()
        # Ensure _cached_catalog is None
        manager._cached_catalog = None

        with pytest.raises(
            UnifiedModelManagerError,
            match=r"No model data available\. Call refresh_unified_data\(\) first",
        ):
            manager.get_model_access_info("Claude 3 Haiku", "us-east-1")

    def test_get_model_access_info_model_not_found(self, unified_manager):
        """Test getting model access info for non-existent model."""
        result = unified_manager.get_model_access_info("NonExistent Model", "us-east-1")

        assert result is None

    def test_get_model_access_info_success(self, unified_manager):
        """Test successful retrieval of model access info."""
        # Setup mock access info using new orthogonal flags
        mock_access_info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            model_id="test-model-id",
        )

        model = unified_manager._cached_catalog.unified_models["Claude 3 Haiku"]
        model.get_access_info_for_region.return_value = mock_access_info

        result = unified_manager.get_model_access_info("Claude 3 Haiku", "us-east-1")

        assert result == mock_access_info
        model.get_access_info_for_region.assert_called_once_with(region="us-east-1")

    def test_get_recommended_access_no_data(self):
        """Test getting recommended access when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None

        with pytest.raises(
            UnifiedModelManagerError,
            match=r"No model data available\. Call refresh_unified_data\(\) first",
        ):
            manager.get_recommended_access("Claude 3 Haiku", "us-east-1")

    def test_get_recommended_access_model_not_found(self, unified_manager):
        """Test getting recommended access for non-existent model."""
        result = unified_manager.get_recommended_access("NonExistent Model", "us-east-1")

        assert result is None

    def test_get_recommended_access_no_access_info(self, unified_manager):
        """Test getting recommended access when no access info available."""
        model = unified_manager._cached_catalog.unified_models["Claude 3 Haiku"]
        model.get_access_info_for_region.return_value = None

        result = unified_manager.get_recommended_access("Claude 3 Haiku", "us-east-1")

        assert result is None

    def test_get_recommended_access_direct_only(self, unified_manager):
        """Test getting recommended access for direct-only model."""
        # Setup mock access info using new orthogonal flags
        mock_access_info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            model_id="test-model-id",
        )

        model = unified_manager._cached_catalog.unified_models["Claude 3 Haiku"]
        model.get_access_info_for_region.return_value = mock_access_info

        result = unified_manager.get_recommended_access("Claude 3 Haiku", "us-east-1")

        assert isinstance(result, AccessRecommendation)
        assert result.recommended_access == mock_access_info
        assert result.rationale == AccessMethodPriority.PRIORITY_RATIONALES["direct_preferred"]
        assert len(result.alternatives) == 0

    def test_get_recommended_access_cris_only(self, unified_manager):
        """Test getting recommended access for CRIS-only model."""
        # Setup mock access info
        mock_access_info = ModelAccessInfo(
            region="us-east-1",
            has_regional_cris=True,
            regional_cris_profile_id="test-profile-id",
        )

        model = unified_manager._cached_catalog.unified_models["Claude 3 Haiku"]
        model.get_access_info_for_region.return_value = mock_access_info

        result = unified_manager.get_recommended_access("Claude 3 Haiku", "us-east-1")

        assert isinstance(result, AccessRecommendation)
        assert result.recommended_access == mock_access_info
        assert result.rationale == AccessMethodPriority.PRIORITY_RATIONALES["cris_only"]
        assert len(result.alternatives) == 0

    def test_get_recommended_access_both_methods(self, unified_manager):
        """Test getting recommended access for model with both access methods."""
        # Setup mock access info with both direct and regional CRIS
        mock_access_info = ModelAccessInfo(
            region="us-east-1",
            has_direct_access=True,
            has_regional_cris=True,
            model_id="test-model-id",
            regional_cris_profile_id="test-profile-id",
        )

        model = unified_manager._cached_catalog.unified_models["Claude 3 Haiku"]
        model.get_access_info_for_region.return_value = mock_access_info

        result = unified_manager.get_recommended_access("Claude 3 Haiku", "us-east-1")

        assert isinstance(result, AccessRecommendation)
        # Should recommend direct access
        assert result.recommended_access.has_direct_access is True
        assert result.recommended_access.model_id == "test-model-id"
        assert result.rationale == AccessMethodPriority.PRIORITY_RATIONALES["direct_preferred"]
        # Should have CRIS as alternative
        assert len(result.alternatives) == 1
        assert result.alternatives[0].has_regional_cris is True
        assert result.alternatives[0].regional_cris_profile_id == "test-profile-id"

    def test_is_model_available_in_region_no_data(self):
        """Test checking model availability when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None

        with pytest.raises(
            UnifiedModelManagerError,
            match=r"No model data available\. Call refresh_unified_data\(\) first",
        ):
            manager.is_model_available_in_region("Claude 3 Haiku", "us-east-1")

    def test_is_model_available_in_region_model_not_found(self, unified_manager):
        """Test checking availability for non-existent model."""
        result = unified_manager.is_model_available_in_region("NonExistent Model", "us-east-1")

        assert result is False

    def test_is_model_available_in_region_success(self, unified_manager):
        """Test successful model availability check."""
        model = unified_manager._cached_catalog.unified_models["Claude 3 Haiku"]
        model.is_available_in_region.return_value = True

        result = unified_manager.is_model_available_in_region("Claude 3 Haiku", "us-east-1")

        assert result is True
        model.is_available_in_region.assert_called_once_with(region="us-east-1")

    def test_get_models_by_region_no_data(self):
        """Test getting models by region when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None

        with pytest.raises(
            UnifiedModelManagerError,
            match=r"No model data available\. Call refresh_unified_data\(\) first",
        ):
            manager.get_models_by_region("us-east-1")

    def test_get_models_by_region_success(self, unified_manager):
        """Test successful retrieval of models by region."""
        expected_models = {"Model1": Mock()}
        unified_manager._cached_catalog.get_models_by_region.return_value = expected_models

        result = unified_manager.get_models_by_region("us-east-1")

        assert result == expected_models
        unified_manager._cached_catalog.get_models_by_region.assert_called_once_with(
            region="us-east-1"
        )

    def test_get_models_by_provider_no_data(self):
        """Test getting models by provider when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None

        with pytest.raises(
            UnifiedModelManagerError,
            match=r"No model data available\. Call refresh_unified_data\(\) first",
        ):
            manager.get_models_by_provider("Amazon")

    def test_get_models_by_provider_success(self, unified_manager):
        """Test successful retrieval of models by provider."""
        expected_models = {"Model1": Mock()}
        unified_manager._cached_catalog.get_models_by_provider.return_value = expected_models

        result = unified_manager.get_models_by_provider("Amazon")

        assert result == expected_models
        unified_manager._cached_catalog.get_models_by_provider.assert_called_once_with(
            provider="Amazon"
        )

    def test_get_direct_access_models_by_region_no_data(self):
        """Test getting direct access models when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None

        with pytest.raises(
            UnifiedModelManagerError,
            match=r"No model data available\. Call refresh_unified_data\(\) first",
        ):
            manager.get_direct_access_models_by_region("us-east-1")

    def test_get_direct_access_models_by_region_success(self, unified_manager):
        """Test successful retrieval of direct access models by region."""
        expected_models = {"Model1": Mock()}
        unified_manager._cached_catalog.get_direct_access_models_by_region.return_value = (
            expected_models
        )

        result = unified_manager.get_direct_access_models_by_region("us-east-1")

        assert result == expected_models
        unified_manager._cached_catalog.get_direct_access_models_by_region.assert_called_once_with(
            region="us-east-1"
        )

    def test_get_cris_only_models_by_region_no_data(self):
        """Test getting CRIS-only models when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None

        with pytest.raises(
            UnifiedModelManagerError,
            match=r"No model data available\. Call refresh_unified_data\(\) first",
        ):
            manager.get_cris_only_models_by_region("us-east-1")

    def test_get_cris_only_models_by_region_success(self, unified_manager):
        """Test successful retrieval of CRIS-only models by region."""
        expected_models = {"Model1": Mock()}
        unified_manager._cached_catalog.get_cris_only_models_by_region.return_value = (
            expected_models
        )

        result = unified_manager.get_cris_only_models_by_region("us-east-1")

        assert result == expected_models
        unified_manager._cached_catalog.get_cris_only_models_by_region.assert_called_once_with(
            region="us-east-1"
        )

    def test_get_all_supported_regions_no_data(self):
        """Test getting all supported regions when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None

        with pytest.raises(
            UnifiedModelManagerError,
            match=r"No model data available\. Call refresh_unified_data\(\) first",
        ):
            manager.get_all_supported_regions()

    def test_get_all_supported_regions_success(self, unified_manager):
        """Test successful retrieval of all supported regions."""
        expected_regions = ["us-east-1", "us-west-2", "eu-west-1"]
        unified_manager._cached_catalog.get_all_supported_regions.return_value = expected_regions

        result = unified_manager.get_all_supported_regions()

        assert result == expected_regions
        unified_manager._cached_catalog.get_all_supported_regions.assert_called_once()

    def test_get_model_names_no_data(self):
        """Test getting model names when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None

        with pytest.raises(
            UnifiedModelManagerError,
            match=r"No model data available\. Call refresh_unified_data\(\) first",
        ):
            manager.get_model_names()

    def test_get_model_names_success(self, unified_manager):
        """Test successful retrieval of model names."""
        expected_names = ["Claude 3 Haiku", "Claude 3 Sonnet"]
        unified_manager._cached_catalog.get_model_names.return_value = expected_names

        result = unified_manager.get_model_names()

        assert result == expected_names
        unified_manager._cached_catalog.get_model_names.assert_called_once()

    def test_get_streaming_models_no_data(self):
        """Test getting streaming models when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None

        with pytest.raises(
            UnifiedModelManagerError,
            match=r"No model data available\. Call refresh_unified_data\(\) first",
        ):
            manager.get_streaming_models()

    def test_get_streaming_models_success(self, unified_manager):
        """Test successful retrieval of streaming models."""
        expected_models = {"Model1": Mock()}
        unified_manager._cached_catalog.get_streaming_models.return_value = expected_models

        result = unified_manager.get_streaming_models()

        assert result == expected_models
        unified_manager._cached_catalog.get_streaming_models.assert_called_once()

    def test_get_model_count_no_data(self):
        """Test getting model count when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None

        with pytest.raises(
            UnifiedModelManagerError,
            match=r"No model data available\. Call refresh_unified_data\(\) first",
        ):
            manager.get_model_count()

    def test_get_model_count_success(self, unified_manager):
        """Test successful retrieval of model count."""
        unified_manager._cached_catalog.model_count = 10

        result = unified_manager.get_model_count()

        assert result == 10

    def test_has_model_no_data(self):
        """Test checking if model exists when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None

        with pytest.raises(
            UnifiedModelManagerError,
            match=r"No model data available\. Call refresh_unified_data\(\) first",
        ):
            manager.has_model("Claude 3 Haiku")

    def test_has_model_success(self, unified_manager):
        """Test successful check for model existence."""
        unified_manager._cached_catalog.has_model.return_value = True

        result = unified_manager.has_model("Claude 3 Haiku")

        assert result is True
        unified_manager._cached_catalog.has_model.assert_called_once_with(
            model_name="Claude 3 Haiku"
        )

    def test_get_regions_for_model_no_data(self):
        """Test getting regions for model when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None

        with pytest.raises(
            UnifiedModelManagerError,
            match=r"No model data available\. Call refresh_unified_data\(\) first",
        ):
            manager.get_regions_for_model("Claude 3 Haiku")

    def test_get_regions_for_model_model_not_found(self, unified_manager):
        """Test getting regions for non-existent model."""
        result = unified_manager.get_regions_for_model("NonExistent Model")

        assert result == []

    def test_get_regions_for_model_success(self, unified_manager):
        """Test successful retrieval of regions for a model."""
        # Mock all supported regions
        all_regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
        unified_manager._cached_catalog.get_all_supported_regions.return_value = all_regions

        # Mock model info with availability in some regions
        model_info = unified_manager._cached_catalog.unified_models["Claude 3 Haiku"]
        model_info.is_available_in_region.side_effect = lambda region: region in [
            "us-east-1",
            "eu-west-1",
        ]

        result = unified_manager.get_regions_for_model("Claude 3 Haiku")

        # Should return sorted list of available regions
        assert result == ["eu-west-1", "us-east-1"]

        # Verify all regions were checked
        unified_manager._cached_catalog.get_all_supported_regions.assert_called_once()
        assert model_info.is_available_in_region.call_count == len(all_regions)

        # Verify each region was checked
        for region in all_regions:
            model_info.is_available_in_region.assert_any_call(region=region)

    def test_get_regions_for_model_no_regions_available(self, unified_manager):
        """Test getting regions for model when no regions are available."""
        # Mock all supported regions
        all_regions = ["us-east-1", "us-west-2", "eu-west-1"]
        unified_manager._cached_catalog.get_all_supported_regions.return_value = all_regions

        # Mock model info with no availability in any region
        model_info = unified_manager._cached_catalog.unified_models["Claude 3 Haiku"]
        model_info.is_available_in_region.return_value = False

        result = unified_manager.get_regions_for_model("Claude 3 Haiku")

        assert result == []

        # Verify all regions were checked
        unified_manager._cached_catalog.get_all_supported_regions.assert_called_once()
        assert model_info.is_available_in_region.call_count == len(all_regions)

    def test_get_correlation_stats(self, unified_manager, mock_correlator):
        """Test getting correlation statistics."""
        expected_stats = {"total": 10, "matched": 8, "unmatched": 2}
        mock_correlator.get_correlation_stats.return_value = expected_stats

        result = unified_manager.get_correlation_stats()

        assert result == expected_stats
        mock_correlator.get_correlation_stats.assert_called_once()

    def test_is_fuzzy_matching_enabled(self, unified_manager, mock_correlator):
        """Test checking if fuzzy matching is enabled."""
        mock_correlator.is_fuzzy_matching_enabled.return_value = True

        result = unified_manager.is_fuzzy_matching_enabled()

        assert result is True
        mock_correlator.is_fuzzy_matching_enabled.assert_called_once()

    def test_set_fuzzy_matching_enabled(self, unified_manager, mock_correlator):
        """Test setting fuzzy matching enabled state."""
        unified_manager.set_fuzzy_matching_enabled(False)

        mock_correlator.set_fuzzy_matching_enabled.assert_called_once_with(enabled=False)

    def test_save_unified_catalog(self, unified_manager, mock_serializer):
        """Test saving unified catalog to JSON."""
        # Create mock catalog
        mock_catalog = Mock(spec=UnifiedModelCatalog)
        mock_catalog.to_dict.return_value = {"unified_models": {}}

        unified_manager._save_unified_catalog(mock_catalog)

        mock_catalog.to_dict.assert_called_once()
        mock_serializer.serialize_dict_to_file.assert_called_once_with(
            data={"unified_models": {}}, output_path=unified_manager.json_output_path
        )

    def test_repr(self, unified_manager, mock_correlator):
        """Test string representation of UnifiedModelManager."""
        mock_correlator.is_fuzzy_matching_enabled.return_value = True

        repr_str = repr(unified_manager)

        assert "UnifiedModelManager" in repr_str


class TestUnifiedModelManagerCacheManagement:
    """Test cases for UnifiedModelManager cache management functionality."""

    @pytest.fixture
    def cache_manager(self):
        """Create a UnifiedModelManager for cache testing."""
        return UnifiedModelManager(max_cache_age_hours=24.0)

    @pytest.fixture
    def mock_serializer_with_data(self):
        """Create a mock serializer that returns valid cache data."""
        mock = Mock()
        # Valid cache data with timestamp
        mock.load_from_file.return_value = {
            "retrieval_timestamp": "2023-01-01T12:00:00.000000Z",
            "unified_models": {"Claude 3 Haiku": {"model_name": "Claude 3 Haiku"}},
        }
        return mock

    def test_init_cache_age_validation_valid(self):
        """Test initialization with valid cache age."""
        manager = UnifiedModelManager(max_cache_age_hours=12.0)
        assert manager.max_cache_age_hours == 12.0

    def test_init_cache_age_validation_too_low(self):
        """Test initialization with cache age too low."""
        with pytest.raises(UnifiedModelManagerError, match="max_cache_age_hours must be between"):
            UnifiedModelManager(max_cache_age_hours=0.05)  # Below minimum

    def test_init_cache_age_validation_too_high(self):
        """Test initialization with cache age too high."""
        with pytest.raises(UnifiedModelManagerError, match="max_cache_age_hours must be between"):
            UnifiedModelManager(max_cache_age_hours=200.0)  # Above maximum

    def test_get_cache_age_hours_valid_timestamp(self, cache_manager):
        """Test cache age calculation with valid timestamp."""
        # Use a timestamp that's 2 hours in the past from "now"
        import time
        from datetime import timezone

        # Calculate a timestamp that's 2 hours ago
        two_hours_ago = time.time() - (2 * 3600)  # 2 hours in seconds

        # Convert to ISO format string (the format the method expects)
        from datetime import datetime

        dt = datetime.fromtimestamp(two_hours_ago, tz=timezone.utc)
        timestamp_str = dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        age_hours = cache_manager._get_cache_age_hours(timestamp_str)

        # Should be approximately 2 hours (allow some tolerance for execution time)
        assert 1.9 <= age_hours <= 2.1

    def test_get_cache_age_hours_fallback_format(self, cache_manager):
        """Test cache age calculation with fallback timestamp format."""
        # Use a timestamp that's 3 hours in the past from "now"
        import time
        from datetime import timezone

        # Calculate a timestamp that's 3 hours ago
        three_hours_ago = time.time() - (3 * 3600)  # 3 hours in seconds

        # Convert to ISO format string without microseconds (the fallback format)
        from datetime import datetime

        dt = datetime.fromtimestamp(three_hours_ago, tz=timezone.utc)
        timestamp_str = dt.strftime("%Y-%m-%dT%H:%M:%SZ")  # No microseconds

        age_hours = cache_manager._get_cache_age_hours(timestamp_str)

        # Should be approximately 3 hours (allow some tolerance for execution time)
        assert 2.9 <= age_hours <= 3.1

    def test_get_cache_age_hours_invalid_timestamp(self, cache_manager):
        """Test cache age calculation with invalid timestamp."""
        with pytest.raises(UnifiedModelManagerError, match="Failed to parse cache timestamp"):
            cache_manager._get_cache_age_hours("invalid-timestamp")

    def test_validate_cache_file_missing(self, cache_manager, tmp_path):
        """Test cache validation when file is missing."""
        cache_manager.json_output_path = tmp_path / "nonexistent.json"

        status, reason = cache_manager._validate_cache()

        assert status == CacheManagementConstants.CACHE_MISSING
        assert "does not exist" in reason

    def test_validate_cache_corrupted_json(
        self, cache_manager, tmp_path, mock_serializer_with_data
    ):
        """Test cache validation with corrupted JSON."""
        # Create corrupted JSON file
        json_file = tmp_path / "corrupted.json"
        json_file.write_text('{"invalid": json}')
        cache_manager.json_output_path = json_file

        # Mock serializer to raise exception
        with patch(
            "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer"
        ) as mock_serializer_class:
            mock_serializer = Mock()
            mock_serializer.load_from_file.side_effect = Exception("JSON decode error")
            mock_serializer_class.return_value = mock_serializer
            cache_manager._serializer = mock_serializer

            status, reason = cache_manager._validate_cache()

        assert status == CacheManagementConstants.CACHE_CORRUPTED
        assert "corrupted or unreadable" in reason

    def test_validate_cache_missing_timestamp(self, cache_manager, tmp_path):
        """Test cache validation with missing timestamp field."""
        json_file = tmp_path / "no_timestamp.json"
        json_file.write_text('{"unified_models": {}}')  # Missing timestamp
        cache_manager.json_output_path = json_file

        # Mock serializer to return data without timestamp
        with patch(
            "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer"
        ) as mock_serializer_class:
            mock_serializer = Mock()
            mock_serializer.load_from_file.return_value = {"unified_models": {}}
            mock_serializer_class.return_value = mock_serializer
            cache_manager._serializer = mock_serializer

            status, reason = cache_manager._validate_cache()

        assert status == CacheManagementConstants.CACHE_CORRUPTED
        assert "missing required timestamp field" in reason

    @patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.datetime")
    def test_validate_cache_expired(self, mock_datetime, cache_manager, tmp_path):
        """Test cache validation with expired data."""
        # Mock current time with timezone awareness (25 hours later than cache)
        from datetime import timezone

        current_time = datetime(2023, 1, 2, 13, 0, 0, tzinfo=timezone.utc)  # 25 hours later
        mock_datetime.now.return_value = current_time
        mock_datetime.strptime = datetime.strptime

        json_file = tmp_path / "expired.json"
        json_file.write_text("{}")
        cache_manager.json_output_path = json_file

        # Mock serializer to return expired data
        with patch(
            "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer"
        ) as mock_serializer_class:
            mock_serializer = Mock()
            mock_serializer.load_from_file.return_value = {
                "retrieval_timestamp": "2023-01-01T12:00:00.000000Z",  # 25 hours ago
                "unified_models": {"Test": {}},
            }
            mock_serializer_class.return_value = mock_serializer
            cache_manager._serializer = mock_serializer

            status, reason = cache_manager._validate_cache()

        assert status == CacheManagementConstants.CACHE_EXPIRED
        assert "expired" in reason
        assert "25.0 hours" in reason

    @patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.datetime")
    def test_validate_cache_valid(self, mock_datetime, cache_manager, tmp_path):
        """Test cache validation with valid, current data."""
        # Mock current time with timezone awareness (1 hour later than cache)
        from datetime import timezone

        current_time = datetime(2023, 1, 1, 13, 0, 0, tzinfo=timezone.utc)  # 1 hour later
        mock_datetime.now.return_value = current_time
        mock_datetime.strptime = datetime.strptime

        json_file = tmp_path / "valid.json"
        json_file.write_text("{}")
        cache_manager.json_output_path = json_file

        # Mock serializer and catalog
        mock_catalog = Mock()
        mock_catalog.model_count = 5

        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer"
            ) as mock_serializer_class,
            patch.object(UnifiedModelCatalog, "from_dict", return_value=mock_catalog),
        ):

            mock_serializer = Mock()
            mock_serializer.load_from_file.return_value = {
                "retrieval_timestamp": "2023-01-01T12:00:00.000000Z",  # 1 hour ago
                "unified_models": {"Test": {}},
            }
            mock_serializer_class.return_value = mock_serializer
            cache_manager._serializer = mock_serializer

            status, reason = cache_manager._validate_cache()

        assert status == CacheManagementConstants.CACHE_VALID
        assert "valid" in reason
        assert "1.0 hours" in reason
        assert cache_manager._cached_catalog == mock_catalog

    @patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.datetime")
    def test_validate_cache_empty_catalog(self, mock_datetime, cache_manager, tmp_path):
        """Test cache validation with empty catalog."""
        # Mock current time to make cache appear fresh (1 hour later)
        from datetime import timezone

        current_time = datetime(2023, 1, 1, 13, 0, 0, tzinfo=timezone.utc)  # 1 hour later
        mock_datetime.now.return_value = current_time
        mock_datetime.strptime = datetime.strptime

        json_file = tmp_path / "empty.json"
        json_file.write_text("{}")
        cache_manager.json_output_path = json_file

        # Mock serializer and empty catalog
        mock_catalog = Mock()
        mock_catalog.model_count = 0  # Empty catalog

        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer"
            ) as mock_serializer_class,
            patch.object(UnifiedModelCatalog, "from_dict", return_value=mock_catalog),
        ):

            mock_serializer = Mock()
            mock_serializer.load_from_file.return_value = {
                "retrieval_timestamp": "2023-01-01T12:00:00.000000Z",  # 1 hour ago - fresh enough
                "unified_models": {},
            }
            mock_serializer_class.return_value = mock_serializer
            cache_manager._serializer = mock_serializer

            status, reason = cache_manager._validate_cache()

        assert status == CacheManagementConstants.CACHE_CORRUPTED
        assert "no model data" in reason

    def test_get_cache_status_missing(self, cache_manager, tmp_path):
        """Test getting cache status when file is missing."""
        cache_manager.json_output_path = tmp_path / "missing.json"

        status_info = cache_manager.get_cache_status()

        assert status_info["status"] == CacheManagementConstants.CACHE_MISSING
        assert status_info["exists"] is False
        assert status_info["max_age_hours"] == 24.0
        assert str(tmp_path / "missing.json") in status_info["path"]
        assert "age_hours" not in status_info  # Age not available for missing files

    @patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.datetime")
    def test_get_cache_status_valid_with_age(self, mock_datetime, cache_manager, tmp_path):
        """Test getting cache status with valid cache including age information."""
        # Mock current time with timezone awareness
        from datetime import timezone

        current_time = datetime(2023, 1, 1, 14, 30, 0, tzinfo=timezone.utc)  # 2.5 hours later
        mock_datetime.now.return_value = current_time
        mock_datetime.strptime = datetime.strptime

        json_file = tmp_path / "valid.json"
        json_file.write_text("{}")
        cache_manager.json_output_path = json_file

        # Mock serializer and catalog
        mock_catalog = Mock()
        mock_catalog.model_count = 3

        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer"
            ) as mock_serializer_class,
            patch.object(UnifiedModelCatalog, "from_dict", return_value=mock_catalog),
        ):

            mock_serializer = Mock()
            mock_serializer.load_from_file.return_value = {
                "retrieval_timestamp": "2023-01-01T12:00:00.000000Z",  # 2.5 hours ago
                "unified_models": {"Test": {}},
            }
            mock_serializer_class.return_value = mock_serializer
            cache_manager._serializer = mock_serializer

            status_info = cache_manager.get_cache_status()

        assert status_info["status"] == CacheManagementConstants.CACHE_VALID
        assert status_info["exists"] is True
        assert status_info["age_hours"] == 2.5
        assert status_info["max_age_hours"] == 24.0

    def test_ensure_data_available_cache_valid(self, cache_manager):
        """Test ensure_data_available with valid cache."""
        # Mock valid cache
        mock_catalog = Mock()
        cache_manager._cached_catalog = mock_catalog

        with patch.object(
            cache_manager,
            "_validate_cache",
            return_value=(CacheManagementConstants.CACHE_VALID, "Valid cache"),
        ):
            result = cache_manager.ensure_data_available()

        assert result == mock_catalog

    def test_ensure_data_available_cache_missing_refresh_success(self, cache_manager):
        """Test ensure_data_available with missing cache that refreshes successfully."""
        mock_catalog = Mock()

        with (
            patch.object(
                cache_manager,
                "_validate_cache",
                return_value=(CacheManagementConstants.CACHE_MISSING, "No cache file"),
            ),
            patch.object(
                cache_manager, "refresh_unified_data", return_value=mock_catalog
            ) as mock_refresh,
        ):

            result = cache_manager.ensure_data_available()

        assert result == mock_catalog
        mock_refresh.assert_called_once_with(force_download=True)

    def test_ensure_data_available_cache_expired_refresh_success(self, cache_manager):
        """Test ensure_data_available with expired cache that refreshes successfully."""
        mock_catalog = Mock()

        with (
            patch.object(
                cache_manager,
                "_validate_cache",
                return_value=(CacheManagementConstants.CACHE_EXPIRED, "Cache too old"),
            ),
            patch.object(
                cache_manager, "refresh_unified_data", return_value=mock_catalog
            ) as mock_refresh,
        ):

            result = cache_manager.ensure_data_available()

        assert result == mock_catalog
        mock_refresh.assert_called_once_with(force_download=True)

    def test_ensure_data_available_cache_corrupted_refresh_success(self, cache_manager):
        """Test ensure_data_available with corrupted cache that refreshes successfully."""
        mock_catalog = Mock()

        with (
            patch.object(
                cache_manager,
                "_validate_cache",
                return_value=(CacheManagementConstants.CACHE_CORRUPTED, "Bad JSON"),
            ),
            patch.object(
                cache_manager, "refresh_unified_data", return_value=mock_catalog
            ) as mock_refresh,
        ):

            result = cache_manager.ensure_data_available()

        assert result == mock_catalog
        mock_refresh.assert_called_once_with(force_download=True)

    def test_ensure_data_available_refresh_fails(self, cache_manager):
        """Test ensure_data_available when refresh fails."""
        with (
            patch.object(
                cache_manager,
                "_validate_cache",
                return_value=(CacheManagementConstants.CACHE_MISSING, "No cache"),
            ),
            patch.object(
                cache_manager, "refresh_unified_data", side_effect=Exception("Network error")
            ),
        ):

            with pytest.raises(
                UnifiedModelManagerError, match="Automatic cache refresh failed: Network error"
            ):
                cache_manager.ensure_data_available()

    def test_ensure_data_available_critical_error(self, cache_manager):
        """Test ensure_data_available with critical error during validation."""
        with patch.object(
            cache_manager, "_validate_cache", side_effect=Exception("Critical error")
        ):

            with pytest.raises(
                UnifiedModelManagerError, match="Critical error in data availability check"
            ):
                cache_manager.ensure_data_available()

    def test_ensure_data_available_unified_model_manager_error_propagation(self, cache_manager):
        """Test that UnifiedModelManagerError is propagated correctly."""
        original_error = UnifiedModelManagerError("Original error")

        with (
            patch.object(
                cache_manager,
                "_validate_cache",
                return_value=(CacheManagementConstants.CACHE_MISSING, "No cache"),
            ),
            patch.object(cache_manager, "refresh_unified_data", side_effect=original_error),
        ):

            with pytest.raises(
                UnifiedModelManagerError, match="Automatic cache refresh failed: Original error"
            ):
                cache_manager.ensure_data_available()


class TestUnifiedModelManagerStaleCacheHandling:
    """Test cases for stale cache handling and age control features."""

    @pytest.fixture
    def cache_manager_permissive(self):
        """Create UnifiedModelManager with permissive cache mode (default)."""
        return UnifiedModelManager(
            strict_cache_mode=False,  # Permissive (default)
            ignore_cache_age=False,  # Respect expiration (default)
            max_cache_age_hours=24.0,
        )

    @pytest.fixture
    def cache_manager_strict(self):
        """Create UnifiedModelManager with strict cache mode."""
        return UnifiedModelManager(
            strict_cache_mode=True,  # Strict mode
            ignore_cache_age=False,  # Respect expiration (default)
            max_cache_age_hours=24.0,
        )

    @pytest.fixture
    def cache_manager_ignore_age(self):
        """Create UnifiedModelManager that ignores cache age."""
        return UnifiedModelManager(
            strict_cache_mode=False,  # Permissive (default)
            ignore_cache_age=True,  # Ignore age
            max_cache_age_hours=24.0,
        )

    def test_strict_cache_mode_default_permissive(self, cache_manager_permissive):
        """Test that default strict_cache_mode is permissive (False)."""
        assert cache_manager_permissive.strict_cache_mode is False

    def test_ignore_cache_age_default_respects_expiration(self, cache_manager_permissive):
        """Test that default ignore_cache_age respects expiration (False)."""
        assert cache_manager_permissive.ignore_cache_age is False

    @patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.datetime")
    def test_strict_cache_mode_false_uses_stale_cache(
        self, mock_datetime, cache_manager_permissive, tmp_path
    ):
        """Test permissive mode uses stale cache when refresh fails."""
        from datetime import timezone

        # Mock current time (26 hours later than cache)
        current_time = datetime(2023, 1, 2, 14, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = current_time
        mock_datetime.strptime = datetime.strptime

        # Create expired cache file
        json_file = tmp_path / "expired.json"
        json_file.write_text("{}")
        cache_manager_permissive.json_output_path = json_file

        # Mock serializer and catalog
        mock_catalog = Mock()
        mock_catalog.model_count = 3

        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer"
            ) as mock_serializer_class,
            patch.object(UnifiedModelCatalog, "from_dict", return_value=mock_catalog),
            patch.object(
                cache_manager_permissive,
                "refresh_unified_data",
                side_effect=Exception("Network error"),
            ),
        ):
            mock_serializer = Mock()
            mock_serializer.load_from_file.return_value = {
                "retrieval_timestamp": "2023-01-01T12:00:00.000000Z",  # 26 hours ago
                "unified_models": {"Test": {}},
            }
            mock_serializer_class.return_value = mock_serializer
            cache_manager_permissive._serializer = mock_serializer

            # Should use stale cache with warning (not raise exception)
            result = cache_manager_permissive.ensure_data_available()

        assert result == mock_catalog

    @patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.datetime")
    def test_strict_cache_mode_true_fails_on_expired(
        self, mock_datetime, cache_manager_strict, tmp_path
    ):
        """Test strict mode fails when expired cache cannot be refreshed."""
        from datetime import timezone

        # Mock current time (26 hours later than cache)
        current_time = datetime(2023, 1, 2, 14, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = current_time
        mock_datetime.strptime = datetime.strptime

        # Create expired cache file
        json_file = tmp_path / "expired.json"
        json_file.write_text("{}")
        cache_manager_strict.json_output_path = json_file

        # Mock serializer
        mock_catalog = Mock()
        mock_catalog.model_count = 3

        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer"
            ) as mock_serializer_class,
            patch.object(UnifiedModelCatalog, "from_dict", return_value=mock_catalog),
            patch.object(
                cache_manager_strict, "refresh_unified_data", side_effect=Exception("Network error")
            ),
        ):
            mock_serializer = Mock()
            mock_serializer.load_from_file.return_value = {
                "retrieval_timestamp": "2023-01-01T12:00:00.000000Z",  # 26 hours ago
                "unified_models": {"Test": {}},
            }
            mock_serializer_class.return_value = mock_serializer
            cache_manager_strict._serializer = mock_serializer

            # Should raise error in strict mode
            with pytest.raises(
                UnifiedModelManagerError,
                match="Strict cache mode enabled.*Cannot use expired cache",
            ):
                cache_manager_strict.ensure_data_available()

    @patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.datetime")
    def test_ignore_cache_age_true_skips_validation(
        self, mock_datetime, cache_manager_ignore_age, tmp_path
    ):
        """Test that ignore_cache_age bypasses age validation."""
        from datetime import timezone

        # Mock current time (100 hours later than cache - way past expiration)
        current_time = datetime(2023, 1, 5, 16, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = current_time
        mock_datetime.strptime = datetime.strptime

        # Create very old cache file
        json_file = tmp_path / "old.json"
        json_file.write_text("{}")
        cache_manager_ignore_age.json_output_path = json_file

        # Mock serializer and catalog
        mock_catalog = Mock()
        mock_catalog.model_count = 5

        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer"
            ) as mock_serializer_class,
            patch.object(UnifiedModelCatalog, "from_dict", return_value=mock_catalog),
        ):
            mock_serializer = Mock()
            mock_serializer.load_from_file.return_value = {
                "retrieval_timestamp": "2023-01-01T12:00:00.000000Z",  # 100 hours ago
                "unified_models": {"Test": {}},
            }
            mock_serializer_class.return_value = mock_serializer
            cache_manager_ignore_age._serializer = mock_serializer

            # Should validate as VALID despite being very old
            status, reason = cache_manager_ignore_age._validate_cache()

        assert status == CacheManagementConstants.CACHE_VALID
        assert "valid" in reason.lower()

    @patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.datetime")
    def test_stale_cache_warning_message_content(
        self, mock_datetime, cache_manager_permissive, tmp_path, caplog
    ):
        """Test that stale cache usage emits proper warning message."""
        import logging
        from datetime import timezone

        caplog.set_level(logging.WARNING)

        # Mock current time (48 hours later than cache)
        current_time = datetime(2023, 1, 3, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = current_time
        mock_datetime.strptime = datetime.strptime

        # Create expired cache file
        json_file = tmp_path / "expired.json"
        json_file.write_text("{}")
        cache_manager_permissive.json_output_path = json_file

        # Mock serializer and catalog
        mock_catalog = Mock()
        mock_catalog.model_count = 3

        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer"
            ) as mock_serializer_class,
            patch.object(UnifiedModelCatalog, "from_dict", return_value=mock_catalog),
            patch.object(
                cache_manager_permissive,
                "refresh_unified_data",
                side_effect=Exception("Network error"),
            ),
        ):
            mock_serializer = Mock()
            mock_serializer.load_from_file.return_value = {
                "retrieval_timestamp": "2023-01-01T12:00:00.000000Z",  # 48 hours ago
                "unified_models": {"Test": {}},
            }
            mock_serializer_class.return_value = mock_serializer
            cache_manager_permissive._serializer = mock_serializer

            result = cache_manager_permissive.ensure_data_available()

        # Check warning was logged
        assert any("Using outdated model data cache" in record.message for record in caplog.records)
        assert any("48.0 hours" in record.message for record in caplog.records)
        assert any("24.0 hours" in record.message for record in caplog.records)

        # Verify result is the stale catalog
        assert result == mock_catalog

    @patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.datetime")
    def test_stale_cache_fallback_when_unloadable(
        self, mock_datetime, cache_manager_permissive, tmp_path
    ):
        """Test that we fail if stale cache cannot be loaded."""
        from datetime import timezone

        # Mock current time (26 hours later)
        current_time = datetime(2023, 1, 2, 14, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = current_time
        mock_datetime.strptime = datetime.strptime

        # Create expired cache file
        json_file = tmp_path / "expired.json"
        json_file.write_text("{}")
        cache_manager_permissive.json_output_path = json_file

        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer"
            ) as mock_serializer_class,
            patch.object(
                cache_manager_permissive,
                "refresh_unified_data",
                side_effect=Exception("Network error"),
            ),
            patch.object(cache_manager_permissive, "load_cached_data", return_value=None),
        ):
            mock_serializer = Mock()
            mock_serializer.load_from_file.return_value = {
                "retrieval_timestamp": "2023-01-01T12:00:00.000000Z",
                "unified_models": {"Test": {}},
            }
            mock_serializer_class.return_value = mock_serializer
            cache_manager_permissive._serializer = mock_serializer

            # Should fail because stale cache cannot be loaded
            with pytest.raises(
                UnifiedModelManagerError, match="Cannot load stale cache after refresh failure"
            ):
                cache_manager_permissive.ensure_data_available()

    @patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.datetime")
    def test_force_download_overrides_ignore_cache_age(self, mock_datetime, tmp_path):
        """Test that force_download=True with refresh_unified_data() bypasses cache."""
        from datetime import timezone

        # Create manager with ignore_cache_age and force_download
        manager = UnifiedModelManager(
            force_download=True, ignore_cache_age=True, max_cache_age_hours=24.0
        )

        # Mock current time
        current_time = datetime(2023, 1, 5, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = current_time
        mock_datetime.strptime = datetime.strptime

        # Create very old cache file
        json_file = tmp_path / "old.json"
        json_file.write_text("{}")
        manager.json_output_path = json_file

        mock_catalog = Mock()
        mock_catalog.model_count = 5

        # Create mock managers
        mock_model_manager = Mock()
        mock_cris_manager = Mock()
        mock_model_manager.refresh_model_data = Mock(return_value=Mock())
        mock_cris_manager.refresh_cris_data = Mock(return_value=Mock())

        # Replace managers
        manager._model_manager = mock_model_manager
        manager._cris_manager = mock_cris_manager

        # Mock the underlying managers
        with (
            patch.object(manager._correlator, "correlate_catalogs", return_value=mock_catalog),
            patch.object(manager, "_save_unified_catalog"),
        ):
            # Call refresh_unified_data directly (as LLMManager does with force_download)
            # This should use force_download=True (from __init__)
            result = manager.refresh_unified_data()

        # Verify force_download was used (models are refreshed with force_download)
        mock_model_manager.refresh_model_data.assert_called_once_with(force_download=True)
        assert result == mock_catalog

    @patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.datetime")
    def test_decision_matrix_scenario_workshop(self, mock_datetime, tmp_path):
        """Test workshop scenario: ignore_cache_age=True, use any cache."""
        from datetime import timezone

        # Create manager for workshop scenario
        manager = UnifiedModelManager(
            force_download=False,
            ignore_cache_age=True,  # Use cache regardless of age
            strict_cache_mode=False,  # Permissive (default)
            max_cache_age_hours=24.0,
        )

        # Mock current time (200 hours later - way past expiration)
        current_time = datetime(2023, 1, 10, 8, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = current_time
        mock_datetime.strptime = datetime.strptime

        # Create very old cache file
        json_file = tmp_path / "workshop.json"
        json_file.write_text("{}")
        manager.json_output_path = json_file

        mock_catalog = Mock()
        mock_catalog.model_count = 5

        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer"
            ) as mock_serializer_class,
            patch.object(UnifiedModelCatalog, "from_dict", return_value=mock_catalog),
        ):
            mock_serializer = Mock()
            mock_serializer.load_from_file.return_value = {
                "retrieval_timestamp": "2023-01-01T12:00:00.000000Z",  # 200 hours ago!
                "unified_models": {"Test": {}},
            }
            mock_serializer_class.return_value = mock_serializer
            manager._serializer = mock_serializer

            result = manager.ensure_data_available()

        # Should use old cache without trying to refresh
        assert result == mock_catalog

    @patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.datetime")
    def test_decision_matrix_scenario_production_strict(
        self, mock_datetime, cache_manager_strict, tmp_path
    ):
        """Test production strict scenario: fail if can't refresh expired cache."""
        from datetime import timezone

        # Mock current time (26 hours later)
        current_time = datetime(2023, 1, 2, 14, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = current_time
        mock_datetime.strptime = datetime.strptime

        # Create expired cache file
        json_file = tmp_path / "strict.json"
        json_file.write_text("{}")
        cache_manager_strict.json_output_path = json_file

        mock_catalog = Mock()
        mock_catalog.model_count = 3

        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer"
            ) as mock_serializer_class,
            patch.object(UnifiedModelCatalog, "from_dict", return_value=mock_catalog),
            patch.object(
                cache_manager_strict, "refresh_unified_data", side_effect=Exception("Network error")
            ),
        ):
            mock_serializer = Mock()
            mock_serializer.load_from_file.return_value = {
                "retrieval_timestamp": "2023-01-01T12:00:00.000000Z",  # 26 hours ago
                "unified_models": {"Test": {}},
            }
            mock_serializer_class.return_value = mock_serializer
            cache_manager_strict._serializer = mock_serializer

            # Should fail in strict mode
            with pytest.raises(
                UnifiedModelManagerError,
                match="Strict cache mode enabled.*Cannot use expired cache",
            ):
                cache_manager_strict.ensure_data_available()

    @patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.datetime")
    def test_decision_matrix_scenario_hybrid(
        self, mock_datetime, cache_manager_permissive, tmp_path
    ):
        """Test hybrid scenario: try refresh, fallback to stale on failure."""
        from datetime import timezone

        # Mock current time (26 hours later)
        current_time = datetime(2023, 1, 2, 14, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = current_time
        mock_datetime.strptime = datetime.strptime

        # Create expired cache file
        json_file = tmp_path / "hybrid.json"
        json_file.write_text("{}")
        cache_manager_permissive.json_output_path = json_file

        mock_catalog = Mock()
        mock_catalog.model_count = 3

        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer"
            ) as mock_serializer_class,
            patch.object(UnifiedModelCatalog, "from_dict", return_value=mock_catalog),
            patch.object(
                cache_manager_permissive,
                "refresh_unified_data",
                side_effect=Exception("Network error"),
            ) as mock_refresh,
        ):
            mock_serializer = Mock()
            mock_serializer.load_from_file.return_value = {
                "retrieval_timestamp": "2023-01-01T12:00:00.000000Z",  # 26 hours ago
                "unified_models": {"Test": {}},
            }
            mock_serializer_class.return_value = mock_serializer
            cache_manager_permissive._serializer = mock_serializer

            result = cache_manager_permissive.ensure_data_available()

        # Should try refresh first, then fall back to stale
        mock_refresh.assert_called_once()
        assert result == mock_catalog

    @patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.datetime")
    def test_decision_matrix_cache_valid_and_fresh(
        self, mock_datetime, cache_manager_permissive, tmp_path
    ):
        """Test happy path: cache valid and fresh."""
        from datetime import timezone

        # Mock current time (1 hour later)
        current_time = datetime(2023, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = current_time
        mock_datetime.strptime = datetime.strptime

        # Create fresh cache file
        json_file = tmp_path / "fresh.json"
        json_file.write_text("{}")
        cache_manager_permissive.json_output_path = json_file

        mock_catalog = Mock()
        mock_catalog.model_count = 5

        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer"
            ) as mock_serializer_class,
            patch.object(UnifiedModelCatalog, "from_dict", return_value=mock_catalog),
            patch.object(cache_manager_permissive, "refresh_unified_data") as mock_refresh,
        ):
            mock_serializer = Mock()
            mock_serializer.load_from_file.return_value = {
                "retrieval_timestamp": "2023-01-01T12:00:00.000000Z",  # 1 hour ago
                "unified_models": {"Test": {}},
            }
            mock_serializer_class.return_value = mock_serializer
            cache_manager_permissive._serializer = mock_serializer

            result = cache_manager_permissive.ensure_data_available()

        # Should use cache without refresh
        mock_refresh.assert_not_called()
        assert result == mock_catalog

    @patch("bestehorn_llmmanager.bedrock.UnifiedModelManager.datetime")
    def test_decision_matrix_expired_refresh_succeeds(
        self, mock_datetime, cache_manager_permissive, tmp_path
    ):
        """Test that successful refresh is used when cache is expired."""
        from datetime import timezone

        # Mock current time (26 hours later)
        current_time = datetime(2023, 1, 2, 14, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = current_time
        mock_datetime.strptime = datetime.strptime

        # Create expired cache file
        json_file = tmp_path / "expired.json"
        json_file.write_text("{}")
        cache_manager_permissive.json_output_path = json_file

        old_catalog = Mock()
        old_catalog.model_count = 3
        new_catalog = Mock()
        new_catalog.model_count = 10

        with (
            patch(
                "bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer"
            ) as mock_serializer_class,
            patch.object(UnifiedModelCatalog, "from_dict", return_value=old_catalog),
            patch.object(
                cache_manager_permissive, "refresh_unified_data", return_value=new_catalog
            ) as mock_refresh,
        ):
            mock_serializer = Mock()
            mock_serializer.load_from_file.return_value = {
                "retrieval_timestamp": "2023-01-01T12:00:00.000000Z",  # 26 hours ago
                "unified_models": {"Test": {}},
            }
            mock_serializer_class.return_value = mock_serializer
            cache_manager_permissive._serializer = mock_serializer

            result = cache_manager_permissive.ensure_data_available()

        # Should use fresh data from refresh
        mock_refresh.assert_called_once()
        assert result == new_catalog

    def test_decision_matrix_cache_missing_try_refresh(self, cache_manager_permissive, tmp_path):
        """Test that missing cache tries to refresh."""
        # Point to non-existent file
        cache_manager_permissive.json_output_path = tmp_path / "missing.json"

        mock_catalog = Mock()

        with patch.object(
            cache_manager_permissive, "refresh_unified_data", return_value=mock_catalog
        ) as mock_refresh:
            result = cache_manager_permissive.ensure_data_available()

        # Should try to refresh
        mock_refresh.assert_called_once_with(force_download=True)
        assert result == mock_catalog
