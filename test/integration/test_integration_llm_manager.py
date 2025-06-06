"""
Integration tests for LLMManager functionality with real AWS Bedrock.

These tests validate the main LLMManager class functionality with real AWS calls,
covering areas that have low coverage in unit tests due to mocking.
"""

import pytest
from typing import List, Dict, Any

from src.LLMManager import LLMManager
from src.bedrock.models.llm_manager_structures import AuthConfig, RetryConfig, AuthenticationType, ResponseValidationConfig
from bedrock.exceptions.llm_manager_exceptions import (
    ConfigurationError, RequestValidationError, RetryExhaustedError
)
from src.bedrock.testing.integration_markers import IntegrationTestMarkers


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.aws_fast
class TestLLMManagerBasicFunctionality:
    """Integration tests for basic LLMManager functionality."""
    
    def test_llm_manager_initialization_with_real_models(self, integration_config):
        """
        Test LLMManager initialization with real model data.
        
        Args:
            integration_config: Integration test configuration
        """
        # Get available test models - use actual model IDs instead of friendly names
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        amazon_model = integration_config.get_test_model_for_provider("amazon")
        
        models = []
        if anthropic_model:
            models.append(anthropic_model)  # Use actual model ID
        if amazon_model:
            models.append(amazon_model)  # Use actual model ID
        
        if not models:
            pytest.skip("No test models configured")
        
        # Initialize with real models and regions - may fail if model data unavailable
        try:
            manager = LLMManager(
                models=models,
                regions=integration_config.test_regions[:2],  # Use first 2 regions
                timeout=30
            )
            
            # Verify manager is properly initialized
            assert len(manager.get_available_models()) == len(models)
            assert len(manager.get_available_regions()) >= 1
            
            # Validate configuration
            validation_result = manager.validate_configuration()
            assert "valid" in validation_result
            assert "auth_status" in validation_result
            assert validation_result["auth_status"] != "unknown"
            
        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to model data issues: {str(e)}")
    
    def test_llm_manager_converse_with_real_model(
        self, 
        integration_config, 
        sample_test_messages, 
        simple_inference_config
    ):
        """
        Test LLMManager converse method with real AWS model.
        
        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
            simple_inference_config: Simple inference configuration
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")
        
        # Initialize manager with real model ID - may fail if model data unavailable
        try:
            manager = LLMManager(
                models=[anthropic_model],  # Use actual model ID
                regions=[integration_config.get_primary_test_region()],
                default_inference_config=simple_inference_config
            )
            
            # Make real converse call
            response = manager.converse(messages=sample_test_messages)
            
            # Verify response structure
            assert response.success is True
            assert response.model_used is not None
            assert response.region_used is not None
            assert response.total_duration_ms is not None and response.total_duration_ms > 0
            
            # Verify content
            content = response.get_content()
            assert content is not None
            assert len(content) > 0
            assert isinstance(content, str)
            
            # Verify usage information
            usage = response.get_usage()
            assert usage is not None
            assert usage.get("input_tokens", 0) > 0
            assert usage.get("output_tokens", 0) > 0
            
            # Verify attempt information
            assert len(response.attempts) >= 1
            successful_attempt = next((a for a in response.attempts if a.success), None)
            assert successful_attempt is not None
            assert successful_attempt.model_id == anthropic_model
            
        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to model data issues: {str(e)}")
    
    def test_llm_manager_converse_with_system_message(
        self, 
        integration_config, 
        sample_test_messages
    ):
        """
        Test LLMManager converse with system message.
        
        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")
        
        try:
            manager = LLMManager(
                models=[anthropic_model],  # Use actual model ID
                regions=[integration_config.get_primary_test_region()]
            )
            
            system_messages = [
                {
                    "text": "You are a helpful assistant. Please respond briefly and clearly."
                }
            ]
            
            response = manager.converse(
                messages=sample_test_messages,
                system=system_messages,
                inference_config={"maxTokens": 50}
            )
            
            assert response.success is True
            assert response.get_content() is not None
            
        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to model data issues: {str(e)}")
    
    def test_llm_manager_converse_with_multiple_regions(self, integration_config, sample_test_messages):
        """
        Test LLMManager with multiple regions for failover.
        
        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")
        
        # Use multiple regions
        test_regions = integration_config.test_regions[:3] if len(integration_config.test_regions) >= 3 else integration_config.test_regions
        
        try:
            manager = LLMManager(
                models=[anthropic_model],  # Use actual model ID
                regions=test_regions
            )
            
            response = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 30}
            )
            
            assert response.success is True
            assert response.region_used in test_regions
            
            # Verify that the manager tried regions in order if needed
            # (This would be more apparent in failure scenarios)
            assert len(response.attempts) >= 1
            
        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to model data issues: {str(e)}")
    
    def test_llm_manager_with_retry_config(self, integration_config, sample_test_messages):
        """
        Test LLMManager with custom retry configuration.
        
        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")
        
        # Configure custom retry behavior
        retry_config = RetryConfig(
            max_retries=2,
            retry_delay=1.0,
            max_retry_delay=5.0,
            backoff_multiplier=2.0
        )
        
        try:
            manager = LLMManager(
                models=[anthropic_model],  # Use actual model ID
                regions=[integration_config.get_primary_test_region()],
                retry_config=retry_config
            )
        except ConfigurationError as e:
            # Skip if model data is not available or model/region combination is invalid
            pytest.skip(f"Could not initialize LLMManager due to model data issues: {str(e)}")
        
        try:
            response = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 30}
            )
            
            assert response.success is True
            
            # Verify retry stats
            retry_stats = manager.get_retry_stats()
            assert isinstance(retry_stats, dict)
            assert "max_retries" in retry_stats
            assert retry_stats["max_retries"] == 2
            
        except ConfigurationError as e:
            # This can happen if model data isn't properly loaded in test environment
            # or if there's a timing/context difference between initialization and runtime
            pytest.skip(f"Model/region data unavailable in test environment: {str(e)}")


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.aws_fast
class TestLLMManagerErrorHandling:
    """Integration tests for LLMManager error handling with real AWS."""
    
    def test_llm_manager_with_invalid_model_name(self, integration_config, sample_test_messages):
        """
        Test LLMManager behavior with invalid model name.
        
        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
        """
        # With fail-fast initialization, LLMManager should raise ConfigurationError
        # during initialization when no valid model/region combinations are available
        with pytest.raises(ConfigurationError) as exc_info:
            manager = LLMManager(
                models=["NonExistentModel"],
                regions=[integration_config.get_primary_test_region()]
            )
        
        # Verify the error message contains expected information
        error_message = str(exc_info.value)
        assert "NonExistentModel" in error_message
        assert "not found" in error_message
        assert "Models specified: ['NonExistentModel']" in error_message
    
    def test_llm_manager_request_validation(self, integration_config):
        """
        Test LLMManager request validation.
        
        Args:
            integration_config: Integration test configuration
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")
        
        try:
            manager = LLMManager(
                models=[anthropic_model],  # Use actual model ID
                regions=[integration_config.get_primary_test_region()]
            )
        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to model data issues: {str(e)}")
        
        # Test empty messages - should raise RequestValidationError
        with pytest.raises(RequestValidationError) as exc_info:
            manager.converse(messages=[])
        
        # Verify the error message
        assert "Messages cannot be empty" in str(exc_info.value)
        
        # Test malformed messages - should raise RequestValidationError
        with pytest.raises(RequestValidationError):
            manager.converse(messages=[{"invalid": "structure"}])
        
        # Test missing required fields - should raise RequestValidationError
        with pytest.raises(RequestValidationError):
            manager.converse(messages=[{"role": "user"}])  # Missing content
    
    def test_llm_manager_with_invalid_region(self, integration_config, sample_test_messages):
        """
        Test LLMManager with invalid AWS region.
        
        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")
        
        # With fail-fast initialization, this should raise ConfigurationError during initialization
        with pytest.raises(ConfigurationError) as exc_info:
            manager = LLMManager(
                models=[anthropic_model],  # Use actual model ID
                regions=["invalid-region-name"]
            )
        
        # Verify the error message contains expected information
        error_message = str(exc_info.value)
        assert "invalid-region-name" in error_message
        assert "not found" in error_message
        assert "Regions specified: ['invalid-region-name']" in error_message


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
@pytest.mark.aws_fast
class TestLLMManagerAdvancedFeatures:
    """Integration tests for advanced LLMManager features."""
    
    def test_llm_manager_converse_stream(self, integration_config, sample_test_messages):
        """
        Test LLMManager streaming converse functionality.
        
        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")
        
        try:
            manager = LLMManager(
                models=[anthropic_model],  # Use actual model ID
                regions=[integration_config.get_primary_test_region()]
            )
            
            # Test streaming converse
            streaming_response = manager.converse_stream(
                messages=sample_test_messages,
                inference_config={"maxTokens": 50}
            )
            
            assert streaming_response.success is True
            # Additional streaming-specific assertions would depend on 
            # the actual implementation of StreamingResponse
            
        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to model data issues: {str(e)}")
    
    def test_llm_manager_model_access_info(self, integration_config):
        """
        Test LLMManager model access information retrieval.
        
        Args:
            integration_config: Integration test configuration
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")
        
        try:
            manager = LLMManager(
                models=[anthropic_model],  # Use actual model ID
                regions=[integration_config.get_primary_test_region()]
            )
            
            # Test model access info - use the actual model ID
            access_info = manager.get_model_access_info(
                model_name=anthropic_model,
                region=integration_config.get_primary_test_region()
            )
            
            if access_info:  # May be None if model data not available
                assert "access_method" in access_info
                assert "model_id" in access_info
                assert "region" in access_info
                assert access_info["region"] == integration_config.get_primary_test_region()
                
        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to model data issues: {str(e)}")
    
    def test_llm_manager_refresh_model_data(self, integration_config):
        """
        Test LLMManager model data refresh functionality.
        
        Args:
            integration_config: Integration test configuration
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")
        
        try:
            manager = LLMManager(
                models=[anthropic_model],  # Use actual model ID
                regions=[integration_config.get_primary_test_region()]
            )
            
            # Test model data refresh
            # This should not raise an exception
            manager.refresh_model_data()
            
            # After refresh, validation should be better
            validation_result = manager.validate_configuration()
            assert "valid" in validation_result
            assert "auth_status" in validation_result
            
        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to model data issues: {str(e)}")


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestLLMManagerResponseValidation:
    """Integration tests for LLMManager response validation features."""
    
    def test_llm_manager_basic_response_handling(self, integration_config, sample_test_messages):
        """
        Test basic LLMManager response handling and content extraction.
        
        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")
        
        try:
            manager = LLMManager(
                models=[anthropic_model],  # Use actual model ID
                regions=[integration_config.get_primary_test_region()]
            )
            
            response = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 100}
            )
            
            assert response.success is True
            content = response.get_content()
            assert content is not None
            assert len(content) > 0  # Should have some content
            
            # Test additional response methods
            usage = response.get_usage()
            assert usage is not None
            assert usage.get("input_tokens", 0) > 0
            
            metrics = response.get_metrics()
            assert metrics is not None
            assert "total_duration_ms" in metrics
            
        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to model data issues: {str(e)}")
