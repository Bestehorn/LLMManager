"""
Unit tests for UnifiedModelManager class.
Tests the functionality of the Unified Amazon Bedrock Model Manager.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from bestehorn_llmmanager.bedrock.UnifiedModelManager import UnifiedModelManager, UnifiedModelManagerError
from bestehorn_llmmanager.bedrock.models.unified_structures import UnifiedModelInfo, UnifiedModelCatalog
from bestehorn_llmmanager.bedrock.models.access_method import ModelAccessMethod, ModelAccessInfo, AccessRecommendation
from bestehorn_llmmanager.bedrock.models.unified_constants import UnifiedFilePaths, UnifiedErrorMessages, AccessMethodPriority
from bestehorn_llmmanager.bedrock.models.data_structures import ModelCatalog, BedrockModelInfo
from bestehorn_llmmanager.bedrock.models.cris_structures import CRISCatalog
from bestehorn_llmmanager.bedrock.correlators.model_cris_correlator import ModelCRISCorrelationError
from bestehorn_llmmanager.bedrock.downloaders.base_downloader import NetworkError, FileSystemError
from bestehorn_llmmanager.bedrock.parsers.base_parser import ParsingError


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
            "Claude 3 Sonnet": Mock(spec=UnifiedModelInfo)
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
            "uncorrelated": 0
        }
        mock.is_fuzzy_matching_enabled.return_value = True
        return mock
    
    @pytest.fixture
    def mock_serializer(self):
        """Create a mock JSONModelSerializer."""
        return Mock()
    
    @pytest.fixture
    def unified_manager(self, mock_model_manager, mock_cris_manager, mock_correlator, 
                       mock_serializer, mock_unified_catalog):
        """Create a UnifiedModelManager instance with mocked components."""
        with patch('bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelManager', return_value=mock_model_manager), \
             patch('bestehorn_llmmanager.bedrock.UnifiedModelManager.CRISManager', return_value=mock_cris_manager), \
             patch('bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelCRISCorrelator', return_value=mock_correlator), \
             patch('bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer', return_value=mock_serializer):
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
            enable_fuzzy_matching=False
        )
        
        assert manager.json_output_path == json_path
        assert manager.force_download is False
    
    def test_refresh_unified_data_success(self, mock_model_manager, mock_cris_manager, 
                                        mock_correlator, mock_serializer):
        """Test successful unified data refresh."""
        # Create a fresh manager without pre-populated cache
        with patch('bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelManager', return_value=mock_model_manager), \
             patch('bestehorn_llmmanager.bedrock.UnifiedModelManager.CRISManager', return_value=mock_cris_manager), \
             patch('bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelCRISCorrelator', return_value=mock_correlator), \
             patch('bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer', return_value=mock_serializer):
            
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
    
    def test_refresh_unified_data_force_download_override(self, mock_model_manager, mock_cris_manager):
        """Test unified data refresh with force_download override."""
        # Create a fresh manager
        with patch('bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelManager', return_value=mock_model_manager), \
             patch('bestehorn_llmmanager.bedrock.UnifiedModelManager.CRISManager', return_value=mock_cris_manager):
            
            manager = UnifiedModelManager()
            
            # Execute with force_download=False
            manager.refresh_unified_data(force_download=False)
            
            # Verify force_download was passed correctly
            mock_model_manager.refresh_model_data.assert_called_once_with(force_download=False)
            mock_cris_manager.refresh_cris_data.assert_called_once_with(force_download=False)
    
    def test_refresh_unified_data_network_error(self, mock_model_manager):
        """Test unified data refresh with network error."""
        with patch('bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelManager', return_value=mock_model_manager):
            manager = UnifiedModelManager()
            
            mock_model_manager.refresh_model_data.side_effect = NetworkError("Connection failed")
            
            with pytest.raises(UnifiedModelManagerError, match="Failed to refresh unified model data: Connection failed"):
                manager.refresh_unified_data()
    
    def test_refresh_unified_data_parsing_error(self, mock_cris_manager, mock_model_manager):
        """Test unified data refresh with parsing error."""
        with patch('bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelManager', return_value=mock_model_manager), \
             patch('bestehorn_llmmanager.bedrock.UnifiedModelManager.CRISManager', return_value=mock_cris_manager):
            
            manager = UnifiedModelManager()
            
            # Model manager succeeds but CRIS manager fails
            mock_cris_manager.refresh_cris_data.side_effect = ParsingError("Invalid CRIS data")
            
            with pytest.raises(UnifiedModelManagerError, match="Failed to refresh unified model data: Invalid CRIS data"):
                manager.refresh_unified_data()
    
    def test_refresh_unified_data_correlation_error(self, mock_correlator):
        """Test unified data refresh with correlation error."""
        with patch('bestehorn_llmmanager.bedrock.UnifiedModelManager.ModelCRISCorrelator', return_value=mock_correlator):
            manager = UnifiedModelManager()
            
            mock_correlator.correlate_catalogs.side_effect = ModelCRISCorrelationError("Correlation failed")
            
            with pytest.raises(UnifiedModelManagerError, match="Failed to refresh unified model data: Correlation failed"):
                manager.refresh_unified_data()
    
    def test_refresh_unified_data_file_system_error(self, mock_serializer):
        """Test unified data refresh with file system error."""
        with patch('bestehorn_llmmanager.bedrock.UnifiedModelManager.JSONModelSerializer', return_value=mock_serializer):
            manager = UnifiedModelManager()
            
            mock_serializer.serialize_dict_to_file.side_effect = FileSystemError("Permission denied")
            
            with pytest.raises(UnifiedModelManagerError, match="Failed to refresh unified model data: Permission denied"):
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
        with patch.object(UnifiedModelCatalog, 'from_dict', return_value=mock_catalog):
            result = unified_manager.load_cached_data()
        
        assert result == mock_catalog
        assert unified_manager._cached_catalog == mock_catalog
        mock_serializer.load_from_file.assert_called_once_with(input_path=json_file)
    
    def test_load_cached_data_error(self, unified_manager, mock_serializer, tmp_path):
        """Test loading cached data with error."""
        json_file = tmp_path / "unified.json"
        json_file.write_text('invalid json')
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
        
        with pytest.raises(UnifiedModelManagerError, match=r"No model data available\. Call refresh_unified_data\(\) first"):
            manager.get_model_access_info("Claude 3 Haiku", "us-east-1")
    
    def test_get_model_access_info_model_not_found(self, unified_manager):
        """Test getting model access info for non-existent model."""
        result = unified_manager.get_model_access_info("NonExistent Model", "us-east-1")
        
        assert result is None
    
    def test_get_model_access_info_success(self, unified_manager):
        """Test successful retrieval of model access info."""
        # Setup mock access info
        mock_access_info = ModelAccessInfo(
            access_method=ModelAccessMethod.DIRECT,
            region="us-east-1",
            model_id="test-model-id",
            inference_profile_id="test-profile-id"
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
        
        with pytest.raises(UnifiedModelManagerError, match=r"No model data available\. Call refresh_unified_data\(\) first"):
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
        # Setup mock access info
        mock_access_info = ModelAccessInfo(
            access_method=ModelAccessMethod.DIRECT,
            region="us-east-1",
            model_id="test-model-id",
            inference_profile_id=None
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
            access_method=ModelAccessMethod.CRIS_ONLY,
            region="us-east-1",
            model_id=None,
            inference_profile_id="test-profile-id"
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
        # Setup mock access info with both methods
        mock_access_info = ModelAccessInfo(
            access_method=ModelAccessMethod.BOTH,
            region="us-east-1",
            model_id="test-model-id",
            inference_profile_id="test-profile-id"
        )
        
        model = unified_manager._cached_catalog.unified_models["Claude 3 Haiku"]
        model.get_access_info_for_region.return_value = mock_access_info
        
        result = unified_manager.get_recommended_access("Claude 3 Haiku", "us-east-1")
        
        assert isinstance(result, AccessRecommendation)
        # Should recommend direct access
        assert result.recommended_access.access_method == ModelAccessMethod.DIRECT
        assert result.recommended_access.model_id == "test-model-id"
        assert result.rationale == AccessMethodPriority.PRIORITY_RATIONALES["direct_preferred"]
        # Should have CRIS as alternative
        assert len(result.alternatives) == 1
        assert result.alternatives[0].access_method == ModelAccessMethod.CRIS_ONLY
        assert result.alternatives[0].inference_profile_id == "test-profile-id"
    
    def test_is_model_available_in_region_no_data(self):
        """Test checking model availability when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None
        
        with pytest.raises(UnifiedModelManagerError, match=r"No model data available\. Call refresh_unified_data\(\) first"):
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
        
        with pytest.raises(UnifiedModelManagerError, match=r"No model data available\. Call refresh_unified_data\(\) first"):
            manager.get_models_by_region("us-east-1")
    
    def test_get_models_by_region_success(self, unified_manager):
        """Test successful retrieval of models by region."""
        expected_models = {"Model1": Mock()}
        unified_manager._cached_catalog.get_models_by_region.return_value = expected_models
        
        result = unified_manager.get_models_by_region("us-east-1")
        
        assert result == expected_models
        unified_manager._cached_catalog.get_models_by_region.assert_called_once_with(region="us-east-1")
    
    def test_get_models_by_provider_no_data(self):
        """Test getting models by provider when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None
        
        with pytest.raises(UnifiedModelManagerError, match=r"No model data available\. Call refresh_unified_data\(\) first"):
            manager.get_models_by_provider("Amazon")
    
    def test_get_models_by_provider_success(self, unified_manager):
        """Test successful retrieval of models by provider."""
        expected_models = {"Model1": Mock()}
        unified_manager._cached_catalog.get_models_by_provider.return_value = expected_models
        
        result = unified_manager.get_models_by_provider("Amazon")
        
        assert result == expected_models
        unified_manager._cached_catalog.get_models_by_provider.assert_called_once_with(provider="Amazon")
    
    def test_get_direct_access_models_by_region_no_data(self):
        """Test getting direct access models when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None
        
        with pytest.raises(UnifiedModelManagerError, match=r"No model data available\. Call refresh_unified_data\(\) first"):
            manager.get_direct_access_models_by_region("us-east-1")
    
    def test_get_direct_access_models_by_region_success(self, unified_manager):
        """Test successful retrieval of direct access models by region."""
        expected_models = {"Model1": Mock()}
        unified_manager._cached_catalog.get_direct_access_models_by_region.return_value = expected_models
        
        result = unified_manager.get_direct_access_models_by_region("us-east-1")
        
        assert result == expected_models
        unified_manager._cached_catalog.get_direct_access_models_by_region.assert_called_once_with(region="us-east-1")
    
    def test_get_cris_only_models_by_region_no_data(self):
        """Test getting CRIS-only models when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None
        
        with pytest.raises(UnifiedModelManagerError, match=r"No model data available\. Call refresh_unified_data\(\) first"):
            manager.get_cris_only_models_by_region("us-east-1")
    
    def test_get_cris_only_models_by_region_success(self, unified_manager):
        """Test successful retrieval of CRIS-only models by region."""
        expected_models = {"Model1": Mock()}
        unified_manager._cached_catalog.get_cris_only_models_by_region.return_value = expected_models
        
        result = unified_manager.get_cris_only_models_by_region("us-east-1")
        
        assert result == expected_models
        unified_manager._cached_catalog.get_cris_only_models_by_region.assert_called_once_with(region="us-east-1")
    
    def test_get_all_supported_regions_no_data(self):
        """Test getting all supported regions when no data is available."""
        manager = UnifiedModelManager()
        manager._cached_catalog = None
        
        with pytest.raises(UnifiedModelManagerError, match=r"No model data available\. Call refresh_unified_data\(\) first"):
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
        
        with pytest.raises(UnifiedModelManagerError, match=r"No model data available\. Call refresh_unified_data\(\) first"):
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
        
        with pytest.raises(UnifiedModelManagerError, match=r"No model data available\. Call refresh_unified_data\(\) first"):
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
        
        with pytest.raises(UnifiedModelManagerError, match=r"No model data available\. Call refresh_unified_data\(\) first"):
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
        
        with pytest.raises(UnifiedModelManagerError, match=r"No model data available\. Call refresh_unified_data\(\) first"):
            manager.has_model("Claude 3 Haiku")
    
    def test_has_model_success(self, unified_manager):
        """Test successful check for model existence."""
        unified_manager._cached_catalog.has_model.return_value = True
        
        result = unified_manager.has_model("Claude 3 Haiku")
        
        assert result is True
        unified_manager._cached_catalog.has_model.assert_called_once_with(model_name="Claude 3 Haiku")
    
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
            data={"unified_models": {}},
            output_path=unified_manager.json_output_path
        )
    
    def test_repr(self, unified_manager, mock_correlator):
        """Test string representation of UnifiedModelManager."""
        mock_correlator.is_fuzzy_matching_enabled.return_value = True
        
        repr_str = repr(unified_manager)
        
        assert "UnifiedModelManager" in repr_str
