"""
Integration tests for AWS authentication functionality.

These tests validate that the authentication system works correctly with real
AWS credentials and can establish connections to Bedrock services.
"""

import pytest
from bestehorn_llmmanager.bedrock.testing.integration_markers import IntegrationTestMarkers
from bestehorn_llmmanager.bedrock.testing.integration_config import IntegrationTestError


@pytest.mark.integration
@pytest.mark.aws_integration
class TestAuthenticationIntegration:
    """Integration tests for AWS authentication functionality."""
    
    def test_authentication_with_primary_region(self, aws_test_client, integration_config):
        """
        Test authentication with the primary configured region.
        
        Args:
            aws_test_client: Configured AWS test client
            integration_config: Integration test configuration
        """
        primary_region = integration_config.get_primary_test_region()
        
        result = aws_test_client.test_authentication(region=primary_region)
        
        assert result["success"] is True
        assert result["region"] == primary_region
        assert "duration_seconds" in result
        assert result["duration_seconds"] > 0
        assert "client_type" in result
        assert "auth_method" in result
    
    @pytest.mark.parametrize("region", ["us-east-1", "us-west-2"])
    def test_authentication_multiple_regions(self, aws_test_client, integration_config, region):
        """
        Test authentication across multiple regions.
        
        Args:
            aws_test_client: Configured AWS test client
            integration_config: Integration test configuration
            region: AWS region to test
        """
        if not integration_config.is_region_enabled(region):
            pytest.skip(f"Region {region} not enabled for testing")
        
        result = aws_test_client.test_authentication(region=region)
        
        assert result["success"] is True
        assert result["region"] == region
        assert result["duration_seconds"] > 0
        assert result["duration_seconds"] < integration_config.timeout_seconds
    
    def test_authentication_all_configured_regions(self, aws_test_client, integration_config):
        """
        Test authentication for all configured regions.
        
        Args:
            aws_test_client: Configured AWS test client
            integration_config: Integration test configuration
        """
        results = {}
        
        for region in integration_config.test_regions:
            result = aws_test_client.test_authentication(region=region)
            results[region] = result
            
            assert result["success"] is True
            assert result["region"] == region
        
        # Verify all regions were tested
        assert len(results) == len(integration_config.test_regions)
        
        # Verify no region took too long
        for region, result in results.items():
            assert result["duration_seconds"] < integration_config.timeout_seconds
    
    def test_authentication_with_invalid_region(self, aws_test_client):
        """
        Test authentication with an invalid/disabled region.
        
        Args:
            aws_test_client: Configured AWS test client
        """
        invalid_region = "invalid-region-1"
        
        with pytest.raises(IntegrationTestError) as exc_info:
            aws_test_client.test_authentication(region=invalid_region)
        
        assert "not enabled for testing" in str(exc_info.value)
    
    def test_authentication_performance_benchmarks(self, aws_test_client, integration_config):
        """
        Test authentication performance benchmarks.
        
        Args:
            aws_test_client: Configured AWS test client
            integration_config: Integration test configuration
        """
        primary_region = integration_config.get_primary_test_region()
        
        # Run multiple authentication tests to check consistency
        durations = []
        for _ in range(3):
            result = aws_test_client.test_authentication(region=primary_region)
            durations.append(result["duration_seconds"])
            assert result["success"] is True
        
        # Check performance consistency
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)
        
        # Performance assertions
        assert avg_duration < 5.0, f"Average authentication time too slow: {avg_duration}s"
        assert max_duration < 10.0, f"Max authentication time too slow: {max_duration}s"
        assert max_duration - min_duration < 5.0, "Authentication times too inconsistent"


@pytest.mark.integration
@pytest.mark.aws_integration
class TestEnvironmentValidation:
    """Integration tests for test environment validation."""
    
    def test_validate_complete_test_environment(self, aws_test_client):
        """
        Test complete test environment validation.
        
        Args:
            aws_test_client: Configured AWS test client
        """
        validation_results = aws_test_client.validate_test_environment()
        
        # Check overall validation success
        assert "overall_success" in validation_results
        assert "config_valid" in validation_results
        assert "auth_results" in validation_results
        assert "errors" in validation_results
        
        # If there are errors, they should be informative
        if not validation_results["overall_success"]:
            assert len(validation_results["errors"]) > 0
            for error in validation_results["errors"]:
                assert isinstance(error, str)
                assert len(error) > 0
        
        # Check authentication results for all regions
        auth_results = validation_results["auth_results"]
        assert len(auth_results) > 0
        
        for region, auth_result in auth_results.items():
            assert "success" in auth_result
            if auth_result["success"]:
                assert "region" in auth_result
                assert "duration_seconds" in auth_result
                assert auth_result["region"] == region
            else:
                assert "error" in auth_result
                assert isinstance(auth_result["error"], str)
    
    def test_test_client_configuration(self, aws_test_client, integration_config):
        """
        Test AWS test client configuration.
        
        Args:
            aws_test_client: Configured AWS test client
            integration_config: Integration test configuration
        """
        # Test available models
        available_models = aws_test_client.get_available_test_models()
        assert isinstance(available_models, dict)
        assert len(available_models) > 0
        
        # Verify models match configuration
        for provider, model_id in available_models.items():
            assert integration_config.is_model_enabled(model_id)
        
        # Test available regions
        available_regions = aws_test_client.get_available_test_regions()
        assert isinstance(available_regions, list)
        assert len(available_regions) > 0
        
        # Verify regions match configuration
        for region in available_regions:
            assert integration_config.is_region_enabled(region)
    
    def test_cost_limit_enforcement(self, aws_test_client, integration_config):
        """
        Test that cost limits are properly enforced.
        
        Args:
            aws_test_client: Configured AWS test client
            integration_config: Integration test configuration
        """
        # Verify cost limit is set
        assert integration_config.cost_limit_usd > 0
        
        # Start a test session to verify tracking
        session_id = "cost_limit_test"
        session = aws_test_client.start_test_session(session_id=session_id)
        
        assert session.config.cost_limit_usd == integration_config.cost_limit_usd
        assert session.total_estimated_cost_usd == 0.0
        
        # Clean up
        summary = aws_test_client.end_test_session()
        assert summary is not None
        assert summary["session_id"] == session_id
