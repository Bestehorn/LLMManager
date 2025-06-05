"""
Tests for ParallelLLMManager class.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import List

from bedrock.ParallelLLMManager import ParallelLLMManager
from bedrock.models.parallel_structures import (
    BedrockConverseRequest, ParallelResponse, ParallelProcessingConfig,
    FailureHandlingStrategy, LoadBalancingStrategy
)
from bedrock.models.llm_manager_structures import AuthConfig, RetryConfig
from bedrock.models.bedrock_response import BedrockResponse
from bedrock.exceptions.parallel_exceptions import (
    ParallelConfigurationError, ParallelProcessingError
)


class TestParallelLLMManager:
    """Test cases for ParallelLLMManager."""
    
    def test_initialization_success(self):
        """Test successful initialization of ParallelLLMManager."""
        models = ["claude-3-haiku", "claude-3-sonnet"]
        regions = ["us-east-1", "us-west-2"]
        
        with patch('bedrock.ParallelLLMManager.LLMManager') as mock_llm_manager:
            parallel_manager = ParallelLLMManager(
                models=models,
                regions=regions
            )
            
            assert parallel_manager.get_available_models() == models
            assert parallel_manager.get_available_regions() == regions
            assert isinstance(parallel_manager.get_parallel_config(), ParallelProcessingConfig)
            mock_llm_manager.assert_called_once()
    
    def test_initialization_with_custom_config(self):
        """Test initialization with custom parallel configuration."""
        models = ["claude-3-haiku"]
        regions = ["us-east-1", "us-west-2"]
        
        custom_config = ParallelProcessingConfig(
            max_concurrent_requests=10,
            request_timeout_seconds=120,
            failure_handling_strategy=FailureHandlingStrategy.STOP_ON_THRESHOLD,
            load_balancing_strategy=LoadBalancingStrategy.RANDOM
        )
        
        with patch('bedrock.ParallelLLMManager.LLMManager'):
            parallel_manager = ParallelLLMManager(
                models=models,
                regions=regions,
                parallel_config=custom_config
            )
            
            config = parallel_manager.get_parallel_config()
            assert config.max_concurrent_requests == 10
            assert config.request_timeout_seconds == 120
            assert config.failure_handling_strategy == FailureHandlingStrategy.STOP_ON_THRESHOLD
            assert config.load_balancing_strategy == LoadBalancingStrategy.RANDOM
    
    def test_initialization_no_models_raises_error(self):
        """Test that initialization without models raises ParallelConfigurationError."""
        with pytest.raises(ParallelConfigurationError) as exc_info:
            ParallelLLMManager(models=[], regions=["us-east-1"])
        
        assert "No models specified" in str(exc_info.value)
    
    def test_initialization_no_regions_raises_error(self):
        """Test that initialization without regions raises ParallelConfigurationError."""
        with pytest.raises(ParallelConfigurationError) as exc_info:
            ParallelLLMManager(models=["claude-3-haiku"], regions=[])
        
        assert "No regions specified" in str(exc_info.value)
    
    def test_converse_with_request_success(self):
        """Test successful single request execution."""
        models = ["claude-3-haiku"]
        regions = ["us-east-1"]
        
        # Create mock response
        mock_response = BedrockResponse(success=True)
        
        with patch('bedrock.ParallelLLMManager.LLMManager') as mock_llm_manager_class:
            mock_llm_manager = Mock()
            mock_llm_manager.converse.return_value = mock_response
            mock_llm_manager_class.return_value = mock_llm_manager
            
            parallel_manager = ParallelLLMManager(models=models, regions=regions)
            
            # Create test request
            request = BedrockConverseRequest(
                messages=[{"role": "user", "content": [{"text": "Hello"}]}]
            )
            
            result = parallel_manager.converse_with_request(request)
            
            assert result == mock_response
            mock_llm_manager.converse.assert_called_once()
    
    @patch('bedrock.ParallelLLMManager.asyncio.run')
    def test_converse_parallel_basic_success(self, mock_asyncio_run):
        """Test basic parallel processing success."""
        models = ["claude-3-haiku"]
        regions = ["us-east-1", "us-west-2"]
        
        # Mock successful responses
        mock_responses = {
            "req_test1_123456": BedrockResponse(success=True),
            "req_test2_123457": BedrockResponse(success=True)
        }
        mock_asyncio_run.return_value = mock_responses
        
        with patch('bedrock.ParallelLLMManager.LLMManager'):
            parallel_manager = ParallelLLMManager(models=models, regions=regions)
            
            # Create test requests
            requests = [
                BedrockConverseRequest(
                    messages=[{"role": "user", "content": [{"text": "Hello 1"}]}],
                    request_id="req_test1_123456"
                ),
                BedrockConverseRequest(
                    messages=[{"role": "user", "content": [{"text": "Hello 2"}]}],
                    request_id="req_test2_123457"
                )
            ]
            
            with patch.object(parallel_manager._request_validator, 'validate_batch_requests'):
                with patch.object(parallel_manager._region_distributor, 'distribute_requests') as mock_distribute:
                    mock_distribute.return_value = [
                        Mock(request_id="req_test1_123456", assigned_regions=["us-east-1"]),
                        Mock(request_id="req_test2_123457", assigned_regions=["us-west-2"])
                    ]
                    
                    result = parallel_manager.converse_parallel(requests)
                    
                    assert isinstance(result, ParallelResponse)
                    assert result.success
                    assert len(result.request_responses) == 2
    
    def test_get_underlying_llm_manager(self):
        """Test getting the underlying LLMManager instance."""
        with patch('bedrock.ParallelLLMManager.LLMManager') as mock_llm_manager_class:
            mock_llm_manager = Mock()
            mock_llm_manager_class.return_value = mock_llm_manager
            
            parallel_manager = ParallelLLMManager(
                models=["claude-3-haiku"],
                regions=["us-east-1"]
            )
            
            assert parallel_manager.get_underlying_llm_manager() == mock_llm_manager
    
    def test_validate_configuration(self):
        """Test configuration validation."""
        with patch('bedrock.ParallelLLMManager.LLMManager') as mock_llm_manager_class:
            mock_llm_manager = Mock()
            mock_llm_manager.validate_configuration.return_value = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "model_region_combinations": 2,
                "auth_status": "profile"
            }
            mock_llm_manager_class.return_value = mock_llm_manager
            
            parallel_manager = ParallelLLMManager(
                models=["claude-3-haiku"],
                regions=["us-east-1", "us-west-2"]
            )
            
            validation_result = parallel_manager.validate_configuration()
            
            assert validation_result["valid"]
            assert "parallel_config_valid" in validation_result
            assert "max_concurrent_requests" in validation_result
            assert "load_balancing_strategy" in validation_result
    
    def test_refresh_model_data_success(self):
        """Test successful model data refresh."""
        with patch('bedrock.ParallelLLMManager.LLMManager') as mock_llm_manager_class:
            mock_llm_manager = Mock()
            mock_llm_manager_class.return_value = mock_llm_manager
            
            parallel_manager = ParallelLLMManager(
                models=["claude-3-haiku"],
                regions=["us-east-1"]
            )
            
            parallel_manager.refresh_model_data()
            
            mock_llm_manager.refresh_model_data.assert_called_once()
    
    def test_refresh_model_data_failure(self):
        """Test model data refresh failure."""
        with patch('bedrock.ParallelLLMManager.LLMManager') as mock_llm_manager_class:
            mock_llm_manager = Mock()
            mock_llm_manager.refresh_model_data.side_effect = Exception("Refresh failed")
            mock_llm_manager_class.return_value = mock_llm_manager
            
            parallel_manager = ParallelLLMManager(
                models=["claude-3-haiku"],
                regions=["us-east-1"]
            )
            
            with pytest.raises(ParallelProcessingError) as exc_info:
                parallel_manager.refresh_model_data()
            
            assert "Failed to refresh model data" in str(exc_info.value)
    
    def test_repr(self):
        """Test string representation of ParallelLLMManager."""
        models = ["claude-3-haiku", "claude-3-sonnet"]
        regions = ["us-east-1", "us-west-2", "eu-west-1"]
        
        with patch('bedrock.ParallelLLMManager.LLMManager'):
            parallel_manager = ParallelLLMManager(models=models, regions=regions)
            
            repr_str = repr(parallel_manager)
            
            assert "ParallelLLMManager" in repr_str
            assert "models=2" in repr_str
            assert "regions=3" in repr_str
            assert "max_concurrent=5" in repr_str  # default value
            assert "strategy=round_robin" in repr_str  # default value
