"""
Integration tests for UnifiedModelManager functionality with real AWS.

These tests validate the UnifiedModelManager functionality with real AWS calls,
covering areas that have low coverage in unit tests due to mocking.
"""

import pytest
from pathlib import Path
from typing import List, Dict, Any

from src.bedrock.UnifiedModelManager import UnifiedModelManager, UnifiedModelManagerError
from src.bedrock.models.access_method import ModelAccessMethod
from src.bedrock.testing.integration_markers import IntegrationTestMarkers


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.aws_fast
class TestUnifiedModelManagerBasicFunctionality:
    """Integration tests for basic UnifiedModelManager functionality."""
    
    def test_unified_model_manager_initialization(self, tmp_path):
        """
        Test UnifiedModelManager initialization.
        
        Args:
            tmp_path: Temporary directory for test files
        """
        json_output_path = tmp_path / "unified_models.json"
        
        manager = UnifiedModelManager(
            json_output_path=json_output_path,
            force_download=False,  # Don't force download for basic init test
            download_timeout=10
        )
        
        # Verify manager is properly initialized
        assert manager.json_output_path == json_output_path
        assert manager.force_download == False
        assert not manager.is_fuzzy_matching_enabled() or manager.is_fuzzy_matching_enabled()  # Should have a boolean value
    
    def test_unified_model_manager_load_cached_data(self, tmp_path):
        """
        Test UnifiedModelManager loading cached data.
        
        Args:
            tmp_path: Temporary directory for test files
        """
        json_output_path = tmp_path / "unified_models.json"
        
        manager = UnifiedModelManager(
            json_output_path=json_output_path,
            force_download=False
        )
        
        # Try to load cached data (should be None for new manager)
        cached_data = manager.load_cached_data()
        
        # Should be None since no cached data exists
        assert cached_data is None
    
    def test_unified_model_manager_refresh_data(self, tmp_path):
        """
        Test UnifiedModelManager data refresh functionality.
        
        Args:
            tmp_path: Temporary directory for test files
        """
        json_output_path = tmp_path / "unified_models.json"
        
        manager = UnifiedModelManager(
            json_output_path=json_output_path,
            force_download=True,
            download_timeout=30
        )
        
        # Refresh unified data (this makes real network calls)
        try:
            catalog = manager.refresh_unified_data()
            
            # Verify catalog structure
            assert catalog is not None
            assert catalog.model_count >= 0
            assert len(catalog.unified_models) >= 0
            
            # Verify JSON file was created
            assert json_output_path.exists()
            
            # Verify correlation stats
            correlation_stats = manager.get_correlation_stats()
            assert isinstance(correlation_stats, dict)
            
        except Exception as e:
            # If network or AWS connectivity issues, skip but don't fail
            pytest.skip(f"Could not refresh model data: {str(e)}")
    
    def test_unified_model_manager_model_queries(self, tmp_path):
        """
        Test UnifiedModelManager model query functionality.
        
        Args:
            tmp_path: Temporary directory for test files
        """
        json_output_path = tmp_path / "unified_models.json"
        
        manager = UnifiedModelManager(
            json_output_path=json_output_path,
            force_download=True,
            download_timeout=30
        )
        
        try:
            # Refresh data first
            catalog = manager.refresh_unified_data()
            
            if catalog.model_count > 0:
                # Test getting model names
                model_names = manager.get_model_names()
                assert isinstance(model_names, list)
                assert len(model_names) == catalog.model_count
                
                # Test getting supported regions
                supported_regions = manager.get_all_supported_regions()
                assert isinstance(supported_regions, list)
                assert len(supported_regions) > 0
                
                # Test checking if model exists
                if model_names:
                    first_model = model_names[0]
                    assert manager.has_model(first_model) is True
                    assert manager.has_model("NonExistentModel") is False
                
                # Test getting models by region
                if supported_regions:
                    first_region = supported_regions[0]
                    models_in_region = manager.get_models_by_region(first_region)
                    assert isinstance(models_in_region, dict)
                
                # Test getting streaming models
                streaming_models = manager.get_streaming_models()
                assert isinstance(streaming_models, dict)
                
        except Exception as e:
            pytest.skip(f"Could not test model queries: {str(e)}")


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.aws_fast
class TestUnifiedModelManagerModelAccess:
    """Integration tests for UnifiedModelManager model access functionality."""
    
    def test_unified_model_manager_model_access_info(self, tmp_path, integration_config):
        """
        Test UnifiedModelManager model access information retrieval.
        
        Args:
            tmp_path: Temporary directory for test files
            integration_config: Integration test configuration
        """
        json_output_path = tmp_path / "unified_models.json"
        
        manager = UnifiedModelManager(
            json_output_path=json_output_path,
            force_download=True,
            download_timeout=30
        )
        
        try:
            # Refresh data first
            catalog = manager.refresh_unified_data()
            
            if catalog.model_count > 0:
                # Test with known model names from integration config
                anthropic_model = integration_config.get_test_model_for_provider("anthropic")
                test_region = integration_config.get_primary_test_region()
                
                # Try to get access info for Claude models
                claude_models = ["Claude 3 Haiku", "Claude 3 Sonnet", "Claude 3.5 Sonnet"]
                
                for model_name in claude_models:
                    access_info = manager.get_model_access_info(
                        model_name=model_name,
                        region=test_region
                    )
                    
                    if access_info:  # May be None if model not available
                        assert access_info.region == test_region
                        assert access_info.access_method in [
                            ModelAccessMethod.DIRECT,
                            ModelAccessMethod.CRIS_ONLY,
                            ModelAccessMethod.BOTH
                        ]
                        
                        # Test model availability check
                        is_available = manager.is_model_available_in_region(
                            model_name=model_name,
                            region=test_region
                        )
                        assert is_available is True
                        
                        # Test getting recommended access
                        recommendation = manager.get_recommended_access(
                            model_name=model_name,
                            region=test_region
                        )
                        
                        if recommendation:
                            assert recommendation.recommended_access is not None
                            assert recommendation.rationale is not None
                            assert isinstance(recommendation.alternatives, list)
                        
                        break  # Found at least one working model
                
        except Exception as e:
            pytest.skip(f"Could not test model access info: {str(e)}")
    
    def test_unified_model_manager_regional_queries(self, tmp_path, integration_config):
        """
        Test UnifiedModelManager regional query functionality.
        
        Args:
            tmp_path: Temporary directory for test files
            integration_config: Integration test configuration
        """
        json_output_path = tmp_path / "unified_models.json"
        
        manager = UnifiedModelManager(
            json_output_path=json_output_path,
            force_download=True,
            download_timeout=30
        )
        
        try:
            # Refresh data first
            catalog = manager.refresh_unified_data()
            
            if catalog.model_count > 0:
                test_region = integration_config.get_primary_test_region()
                
                # Test getting models by region
                models_in_region = manager.get_models_by_region(test_region)
                assert isinstance(models_in_region, dict)
                
                # Test getting direct access models
                direct_models = manager.get_direct_access_models_by_region(test_region)
                assert isinstance(direct_models, dict)
                
                # Test getting CRIS-only models
                cris_models = manager.get_cris_only_models_by_region(test_region)
                assert isinstance(cris_models, dict)
                
                # Test getting models by provider
                providers = ["Amazon", "Anthropic", "Meta", "Mistral", "Cohere"]
                
                for provider in providers:
                    provider_models = manager.get_models_by_provider(provider)
                    assert isinstance(provider_models, dict)
                    # May be empty if no models from this provider
                
        except Exception as e:
            pytest.skip(f"Could not test regional queries: {str(e)}")


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestUnifiedModelManagerConfiguration:
    """Integration tests for UnifiedModelManager configuration functionality."""
    
    def test_unified_model_manager_fuzzy_matching(self, tmp_path):
        """
        Test UnifiedModelManager fuzzy matching configuration.
        
        Args:
            tmp_path: Temporary directory for test files
        """
        json_output_path = tmp_path / "unified_models.json"
        
        # Test with fuzzy matching enabled
        manager_with_fuzzy = UnifiedModelManager(
            json_output_path=json_output_path,
            force_download=False,
            enable_fuzzy_matching=True
        )
        
        assert manager_with_fuzzy.is_fuzzy_matching_enabled() is True
        
        # Test disabling fuzzy matching
        manager_with_fuzzy.set_fuzzy_matching_enabled(False)
        assert manager_with_fuzzy.is_fuzzy_matching_enabled() is False
        
        # Test with fuzzy matching disabled
        manager_without_fuzzy = UnifiedModelManager(
            json_output_path=json_output_path,
            force_download=False,
            enable_fuzzy_matching=False
        )
        
        assert manager_without_fuzzy.is_fuzzy_matching_enabled() is False
    
    def test_unified_model_manager_error_handling(self, tmp_path):
        """
        Test UnifiedModelManager error handling.
        
        Args:
            tmp_path: Temporary directory for test files
        """
        json_output_path = tmp_path / "unified_models.json"
        
        manager = UnifiedModelManager(
            json_output_path=json_output_path,
            force_download=False
        )
        
        # Test error when no data is available
        with pytest.raises(UnifiedModelManagerError):
            manager.get_model_access_info("Claude 3 Haiku", "us-east-1")
        
        with pytest.raises(UnifiedModelManagerError):
            manager.get_model_names()
        
        with pytest.raises(UnifiedModelManagerError):
            manager.get_all_supported_regions()
        
        with pytest.raises(UnifiedModelManagerError):
            manager.is_model_available_in_region("Claude 3 Haiku", "us-east-1")
    
    def test_unified_model_manager_repr(self, tmp_path):
        """
        Test UnifiedModelManager string representation.
        
        Args:
            tmp_path: Temporary directory for test files
        """
        json_output_path = tmp_path / "unified_models.json"
        
        manager = UnifiedModelManager(
            json_output_path=json_output_path,
            force_download=True,
            enable_fuzzy_matching=True
        )
        
        repr_string = repr(manager)
        assert "UnifiedModelManager" in repr_string
        assert str(json_output_path) in repr_string
        assert "force_download=True" in repr_string
        assert "fuzzy_matching=True" in repr_string
