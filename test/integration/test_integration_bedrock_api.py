"""
Integration tests for AWS Bedrock API functionality.

These tests validate that the Bedrock API calls work correctly with real models
and handle various scenarios including success, failures, and edge cases.
"""

import pytest
from src.bedrock.testing.integration_markers import IntegrationTestMarkers
from src.bedrock.testing.integration_config import IntegrationTestError


@pytest.mark.integration
class TestBedrockAPIIntegration:
    """Integration tests for Bedrock API functionality."""
    
    def test_converse_with_anthropic_model(
        self, 
        aws_test_client, 
        integration_config, 
        sample_test_messages,
        simple_inference_config
    ):
        """
        Test Bedrock converse API with Anthropic model.
        
        Args:
            aws_test_client: Configured AWS test client
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
            simple_inference_config: Simple inference configuration
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")
        
        response = aws_test_client.test_bedrock_converse(
            model_id=anthropic_model,
            messages=sample_test_messages,
            inferenceConfig=simple_inference_config
        )
        
        # Verify response structure
        assert response.success is True
        assert response.model_used == anthropic_model
        assert response.region_used is not None
        
        # Verify response content
        content = response.get_content()
        assert content is not None
        assert len(content) > 0
        assert isinstance(content, str)
        
        # Verify usage information
        usage = response.get_usage()
        assert usage is not None
        assert "input_tokens" in usage
        assert "output_tokens" in usage
        assert usage["input_tokens"] > 0
        assert usage["output_tokens"] > 0
    
    def test_converse_with_amazon_model(
        self, 
        aws_test_client, 
        integration_config, 
        sample_test_messages,
        simple_inference_config
    ):
        """
        Test Bedrock converse API with Amazon model.
        
        Args:
            aws_test_client: Configured AWS test client
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
            simple_inference_config: Simple inference configuration
        """
        amazon_model = integration_config.get_test_model_for_provider("amazon")
        if not amazon_model:
            pytest.skip("Amazon model not configured for testing")
        
        response = aws_test_client.test_bedrock_converse(
            model_id=amazon_model,
            messages=sample_test_messages,
            inferenceConfig=simple_inference_config
        )
        
        # Verify basic response
        assert response.success is True
        assert response.model_used == amazon_model
        
        # Verify content
        content = response.get_content()
        assert content is not None
        assert len(content) > 0
    
    @pytest.mark.parametrize("provider", ["anthropic", "amazon"])
    def test_converse_multiple_providers(
        self, 
        aws_test_client, 
        integration_config, 
        sample_test_messages,
        simple_inference_config,
        provider
    ):
        """
        Test Bedrock converse API with multiple providers.
        
        Args:
            aws_test_client: Configured AWS test client
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
            simple_inference_config: Simple inference configuration
            provider: Model provider to test
        """
        model_id = integration_config.get_test_model_for_provider(provider)
        if not model_id:
            pytest.skip(f"{provider} model not configured for testing")
        
        response = aws_test_client.test_bedrock_converse(
            model_id=model_id,
            messages=sample_test_messages,
            inferenceConfig=simple_inference_config
        )
        
        assert response.success is True
        assert response.model_used == model_id
        
        # Verify metrics
        metrics = response.get_metrics()
        assert metrics is not None
        assert "total_duration_ms" in metrics or "api_latency_ms" in metrics
    
    def test_converse_with_invalid_model(self, aws_test_client, sample_test_messages):
        """
        Test Bedrock converse API with invalid model.
        
        Args:
            aws_test_client: Configured AWS test client
            sample_test_messages: Sample messages for testing
        """
        invalid_model = "invalid.model.id"
        
        with pytest.raises(IntegrationTestError) as exc_info:
            aws_test_client.test_bedrock_converse(
                model_id=invalid_model,
                messages=sample_test_messages
            )
        
        assert "not enabled for testing" in str(exc_info.value)
    
    def test_converse_with_session_tracking(
        self, 
        aws_test_client, 
        integration_config, 
        sample_test_messages,
        integration_test_session
    ):
        """
        Test Bedrock converse API with session tracking.
        
        Args:
            aws_test_client: Configured AWS test client
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
            integration_test_session: Test session for tracking
        """
        model_id = integration_config.get_test_model_for_provider("anthropic")
        if not model_id:
            pytest.skip("Anthropic model not configured for testing")
        
        # Verify session is active
        assert integration_test_session.total_estimated_cost_usd == 0.0
        
        response = aws_test_client.test_bedrock_converse(
            model_id=model_id,
            messages=sample_test_messages,
            inferenceConfig={"maxTokens": 50}
        )
        
        assert response.success is True
        
        # Verify session tracking
        assert len(integration_test_session.requests) == 1
        request_metrics = integration_test_session.requests[0]
        assert request_metrics.success is True
        assert request_metrics.model_id == model_id
        assert request_metrics.duration_seconds is not None
        assert request_metrics.duration_seconds > 0
    
    def test_converse_performance_benchmarks(
        self, 
        aws_test_client, 
        integration_config, 
        sample_test_messages
    ):
        """
        Test Bedrock converse API performance benchmarks.
        
        Args:
            aws_test_client: Configured AWS test client
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
        """
        model_id = integration_config.get_test_model_for_provider("anthropic")
        if not model_id:
            pytest.skip("Anthropic model not configured for testing")
        
        # Run multiple requests to check consistency
        durations = []
        for _ in range(3):
            response = aws_test_client.test_bedrock_converse(
                model_id=model_id,
                messages=sample_test_messages,
                inferenceConfig={"maxTokens": 50}
            )
            
            assert response.success is True
            
            metrics = response.get_metrics()
            if metrics and "api_latency_ms" in metrics:
                durations.append(metrics["api_latency_ms"] / 1000)  # Convert to seconds
        
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            
            # Performance assertions
            assert avg_duration < 30.0, f"Average API latency too slow: {avg_duration}s"
            assert max_duration < 60.0, f"Max API latency too slow: {max_duration}s"


@pytest.mark.integration
class TestBedrockStreamingIntegration:
    """Integration tests for Bedrock streaming API functionality."""
    
    def test_converse_stream_with_anthropic_model(
        self, 
        aws_test_client, 
        integration_config, 
        sample_test_messages
    ):
        """
        Test Bedrock streaming converse API with Anthropic model.
        
        Args:
            aws_test_client: Configured AWS test client
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")
        
        response = aws_test_client.test_bedrock_converse_stream(
            model_id=anthropic_model,
            messages=sample_test_messages,
            inferenceConfig={"maxTokens": 100}
        )
        
        # Verify response structure
        assert response.success is True
        assert response.model_used == anthropic_model
        assert response.region_used is not None
        
        # Verify streaming response data exists
        assert response.response_data is not None
        assert "stream" in response.response_data or "body" in response.response_data
    
    def test_streaming_vs_regular_converse_comparison(
        self, 
        aws_test_client, 
        integration_config, 
        sample_test_messages
    ):
        """
        Compare streaming vs regular converse API responses.
        
        Args:
            aws_test_client: Configured AWS test client
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
        """
        model_id = integration_config.get_test_model_for_provider("anthropic")
        if not model_id:
            pytest.skip("Anthropic model not configured for testing")
        
        inference_config = {"maxTokens": 50, "temperature": 0.1}
        
        # Regular converse
        regular_response = aws_test_client.test_bedrock_converse(
            model_id=model_id,
            messages=sample_test_messages,
            inferenceConfig=inference_config
        )
        
        # Streaming converse
        streaming_response = aws_test_client.test_bedrock_converse_stream(
            model_id=model_id,
            messages=sample_test_messages,
            inferenceConfig=inference_config
        )
        
        # Both should succeed
        assert regular_response.success is True
        assert streaming_response.success is True
        
        # Both should use the same model and region
        assert regular_response.model_used == streaming_response.model_used
        assert regular_response.region_used == streaming_response.region_used


@pytest.mark.integration
class TestBedrockErrorHandling:
    """Integration tests for Bedrock API error handling."""
    
    def test_converse_with_malformed_messages(self, aws_test_client, integration_config):
        """
        Test Bedrock converse API with malformed messages.
        
        Args:
            aws_test_client: Configured AWS test client
            integration_config: Integration test configuration
        """
        model_id = integration_config.get_test_model_for_provider("anthropic")
        if not model_id:
            pytest.skip("Anthropic model not configured for testing")
        
        # Test with empty messages
        with pytest.raises(IntegrationTestError):
            aws_test_client.test_bedrock_converse(
                model_id=model_id,
                messages=[]
            )
        
        # Test with malformed message structure
        with pytest.raises(IntegrationTestError):
            aws_test_client.test_bedrock_converse(
                model_id=model_id,
                messages=[{"invalid": "structure"}]
            )
    
    def test_converse_with_excessive_token_limit(
        self, 
        aws_test_client, 
        integration_config, 
        sample_test_messages
    ):
        """
        Test Bedrock converse API with excessive token limits.
        
        Args:
            aws_test_client: Configured AWS test client
            integration_config: Integration test configuration
            sample_test_messages: Sample messages for testing
        """
        model_id = integration_config.get_test_model_for_provider("anthropic")
        if not model_id:
            pytest.skip("Anthropic model not configured for testing")
        
        # Test with unreasonably high token limit
        with pytest.raises(IntegrationTestError):
            aws_test_client.test_bedrock_converse(
                model_id=model_id,
                messages=sample_test_messages,
                inferenceConfig={"maxTokens": 1000000}  # Unreasonably high
            )
