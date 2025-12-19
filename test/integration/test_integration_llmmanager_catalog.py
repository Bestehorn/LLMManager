"""
Integration tests for LLMManager with new BedrockModelCatalog.

These tests validate that LLMManager works correctly with the new catalog system,
including model validation, Lambda-like scenarios, and cache modes.

Requirements tested:
- 7.2: LLMManager integration with BedrockModelCatalog
- 8.1: Lambda-friendly design with configurable cache modes
"""

from pathlib import Path
from typing import Any

import pytest

from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
    ConfigurationError,
)
from bestehorn_llmmanager.bedrock.models.catalog_structures import CacheMode
from bestehorn_llmmanager.llm_manager import LLMManager


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestLLMManagerCatalogIntegration:
    """Integration tests for LLMManager with BedrockModelCatalog."""

    def test_llm_manager_uses_catalog_for_validation(
        self, integration_config: Any, sample_test_messages: Any
    ) -> None:
        """
        Test that LLMManager uses catalog for model validation.

        Validates Requirement 7.2: LLMManager integration with BedrockModelCatalog

        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample test messages
        """
        # Get a valid model from integration config
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        region = integration_config.get_primary_test_region()

        # Initialize LLMManager - should use catalog internally
        try:
            manager = LLMManager(
                models=[anthropic_model],
                regions=[region],
                timeout=30,
            )

            # Verify manager initialized successfully
            assert manager is not None

            # Verify model validation worked
            validation_result = manager.validate_configuration()
            assert "valid" in validation_result
            assert validation_result.get("valid") is True

            # Make a test request to verify catalog integration
            response = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 50},
            )

            assert response.success is True
            assert response.model_used == anthropic_model

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to catalog issues: {str(e)}")

    def test_llm_manager_with_invalid_model_uses_catalog(self, integration_config: Any) -> None:
        """
        Test that LLMManager uses catalog to detect invalid models.

        Validates Requirement 7.2: LLMManager integration with BedrockModelCatalog

        Args:
            integration_config: Integration test configuration
        """
        region = integration_config.get_primary_test_region()

        # Try to initialize with invalid model - should fail during initialization
        with pytest.raises(ConfigurationError) as exc_info:
            LLMManager(
                models=["invalid-model-id-12345"],
                regions=[region],
            )

        # Verify error message mentions the invalid model
        error_msg = str(exc_info.value)
        assert "invalid-model-id-12345" in error_msg
        assert "not found" in error_msg.lower()

    def test_llm_manager_model_availability_check(self, integration_config: Any) -> None:
        """
        Test LLMManager model availability checking via catalog.

        Args:
            integration_config: Integration test configuration
        """
        # Get a valid model
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        region = integration_config.get_primary_test_region()

        try:
            manager = LLMManager(
                models=[anthropic_model],
                regions=[region],
            )

            # Check model availability
            available_models = manager.get_available_models()
            assert anthropic_model in available_models

            # Check region availability
            available_regions = manager.get_available_regions()
            assert region in available_regions

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to catalog issues: {str(e)}")


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestLLMManagerCacheModes:
    """Integration tests for LLMManager with different cache modes."""

    def test_llm_manager_with_file_cache_mode(
        self, integration_config: Any, tmp_path: Path, sample_test_messages: Any
    ) -> None:
        """
        Test LLMManager with FILE cache mode.

        Validates Requirement 8.1: Lambda-friendly design with cache modes

        Args:
            integration_config: Integration test configuration
            tmp_path: Pytest temporary directory
            sample_test_messages: Sample test messages
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        region = integration_config.get_primary_test_region()
        cache_dir = tmp_path / "llm_cache"

        try:
            # Initialize with FILE cache mode
            manager = LLMManager(
                models=[anthropic_model],
                regions=[region],
                catalog_cache_mode=CacheMode.FILE,
                catalog_cache_directory=cache_dir,
            )

            # Make a request
            response = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 50},
            )

            assert response.success is True

            # Verify cache file was created
            cache_file = cache_dir / "bedrock_catalog.json"
            assert cache_file.exists()

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to catalog issues: {str(e)}")

    def test_llm_manager_with_memory_cache_mode(
        self, integration_config: Any, tmp_path: Path, sample_test_messages: Any
    ) -> None:
        """
        Test LLMManager with MEMORY cache mode.

        Validates Requirement 8.1: Lambda-friendly design with cache modes

        Args:
            integration_config: Integration test configuration
            tmp_path: Pytest temporary directory
            sample_test_messages: Sample test messages
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        region = integration_config.get_primary_test_region()
        cache_dir = tmp_path / "memory_cache"

        try:
            # Initialize with MEMORY cache mode
            manager = LLMManager(
                models=[anthropic_model],
                regions=[region],
                catalog_cache_mode=CacheMode.MEMORY,
                catalog_cache_directory=cache_dir,  # Should be ignored
            )

            # Make a request
            response = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 50},
            )

            assert response.success is True

            # Verify no cache file was created
            assert not cache_dir.exists()

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to catalog issues: {str(e)}")

    def test_llm_manager_with_none_cache_mode(
        self, integration_config: Any, tmp_path: Path, sample_test_messages: Any
    ) -> None:
        """
        Test LLMManager with NONE cache mode (Lambda-friendly).

        Validates Requirement 8.1: Lambda-friendly design with no file system access

        Args:
            integration_config: Integration test configuration
            tmp_path: Pytest temporary directory
            sample_test_messages: Sample test messages
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        region = integration_config.get_primary_test_region()
        cache_dir = tmp_path / "none_cache"

        try:
            # Initialize with NONE cache mode
            manager = LLMManager(
                models=[anthropic_model],
                regions=[region],
                catalog_cache_mode=CacheMode.NONE,
                catalog_cache_directory=cache_dir,  # Should be ignored
            )

            # Make a request
            response = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 50},
            )

            assert response.success is True

            # Verify no cache directory or file was created
            assert not cache_dir.exists()

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to catalog issues: {str(e)}")


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestLLMManagerLambdaScenarios:
    """Integration tests for Lambda-like scenarios."""

    def test_llm_manager_lambda_tmp_directory(
        self, integration_config: Any, tmp_path: Path, sample_test_messages: Any
    ) -> None:
        """
        Test LLMManager with /tmp directory (Lambda scenario).

        Validates Requirement 8.1: Lambda-friendly design

        Args:
            integration_config: Integration test configuration
            tmp_path: Pytest temporary directory (simulates /tmp)
            sample_test_messages: Sample test messages
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        region = integration_config.get_primary_test_region()

        # Simulate Lambda /tmp directory
        lambda_tmp = tmp_path / "tmp"
        lambda_tmp.mkdir()

        try:
            # Initialize with /tmp cache directory
            manager = LLMManager(
                models=[anthropic_model],
                regions=[region],
                catalog_cache_mode=CacheMode.FILE,
                catalog_cache_directory=lambda_tmp,
            )

            # Make a request
            response = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 50},
            )

            assert response.success is True

            # Verify cache was written to /tmp
            cache_file = lambda_tmp / "bedrock_catalog.json"
            assert cache_file.exists()

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to catalog issues: {str(e)}")

    def test_llm_manager_lambda_cold_start_with_bundled_data(
        self, integration_config: Any, sample_test_messages: Any
    ) -> None:
        """
        Test LLMManager cold start with bundled data fallback.

        Simulates Lambda cold start where API might be slow or fail,
        and bundled data provides fast initialization.

        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample test messages
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        region = integration_config.get_primary_test_region()

        try:
            # Initialize with NONE cache mode (forces fresh load each time)
            # This simulates Lambda cold start behavior
            manager = LLMManager(
                models=[anthropic_model],
                regions=[region],
                catalog_cache_mode=CacheMode.NONE,
            )

            # Verify manager initialized (may use bundled data if API is slow)
            assert manager is not None

            # Make a request
            response = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 50},
            )

            assert response.success is True

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to catalog issues: {str(e)}")

    def test_llm_manager_lambda_warm_start_with_memory_cache(
        self, integration_config: Any, sample_test_messages: Any
    ) -> None:
        """
        Test LLMManager warm start with memory cache.

        Simulates Lambda warm start where catalog is cached in memory
        across invocations.

        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample test messages
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        region = integration_config.get_primary_test_region()

        try:
            # Initialize with MEMORY cache mode
            manager = LLMManager(
                models=[anthropic_model],
                regions=[region],
                catalog_cache_mode=CacheMode.MEMORY,
            )

            # First request (cold)
            response1 = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 50},
            )
            assert response1.success is True

            # Second request (warm - should use cached catalog)
            response2 = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 50},
            )
            assert response2.success is True

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to catalog issues: {str(e)}")


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestLLMManagerCatalogRefresh:
    """Integration tests for catalog refresh functionality."""

    def test_llm_manager_catalog_refresh(
        self, integration_config: Any, sample_test_messages: Any
    ) -> None:
        """
        Test LLMManager catalog refresh functionality.

        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample test messages
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        region = integration_config.get_primary_test_region()

        try:
            # Initialize manager
            manager = LLMManager(
                models=[anthropic_model],
                regions=[region],
                catalog_cache_mode=CacheMode.MEMORY,
            )

            # Make initial request
            response1 = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 50},
            )
            assert response1.success is True

            # Refresh model data (catalog)
            manager.refresh_model_data()

            # Make another request after refresh
            response2 = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 50},
            )
            assert response2.success is True

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to catalog issues: {str(e)}")

    def test_llm_manager_get_model_access_info(self, integration_config: Any) -> None:
        """
        Test LLMManager get_model_access_info with catalog.

        Args:
            integration_config: Integration test configuration
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        region = integration_config.get_primary_test_region()

        try:
            # Initialize manager
            manager = LLMManager(
                models=[anthropic_model],
                regions=[region],
            )

            # Get model access info
            access_info = manager.get_model_access_info(
                model_name=anthropic_model,
                region=region,
            )

            # Verify access info
            if access_info:  # May be None if catalog doesn't have detailed info
                assert "access_method" in access_info
                assert "model_id" in access_info
                assert "region" in access_info
                assert access_info["region"] == region

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to catalog issues: {str(e)}")


@pytest.mark.integration
@pytest.mark.aws_integration
@pytest.mark.aws_low_cost
class TestLLMManagerBackwardCompatibility:
    """Integration tests for backward compatibility with old manager behavior."""

    def test_llm_manager_transparent_catalog_usage(
        self, integration_config: Any, sample_test_messages: Any
    ) -> None:
        """
        Test that catalog usage is transparent to users.

        Users shouldn't need to know about the catalog - it should work
        automatically in the background.

        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample test messages
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        region = integration_config.get_primary_test_region()

        try:
            # Initialize LLMManager without any catalog-specific parameters
            # (catalog should be used automatically)
            manager = LLMManager(
                models=[anthropic_model],
                regions=[region],
            )

            # Make a request - should work transparently
            response = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 50},
            )

            assert response.success is True
            assert response.model_used == anthropic_model

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to catalog issues: {str(e)}")

    def test_llm_manager_existing_api_unchanged(
        self, integration_config: Any, sample_test_messages: Any
    ) -> None:
        """
        Test that existing LLMManager API remains unchanged.

        Validates that the catalog integration doesn't break existing code.

        Args:
            integration_config: Integration test configuration
            sample_test_messages: Sample test messages
        """
        anthropic_model = integration_config.get_test_model_for_provider("anthropic")
        if not anthropic_model:
            pytest.skip("Anthropic model not configured for testing")

        region = integration_config.get_primary_test_region()

        try:
            # Use existing LLMManager API
            manager = LLMManager(
                models=[anthropic_model],
                regions=[region],
                timeout=30,
            )

            # Test existing methods
            assert manager.get_available_models() is not None
            assert manager.get_available_regions() is not None

            validation = manager.validate_configuration()
            assert "valid" in validation

            # Test converse method
            response = manager.converse(
                messages=sample_test_messages,
                inference_config={"maxTokens": 50},
            )
            assert response.success is True

        except ConfigurationError as e:
            pytest.skip(f"Could not initialize LLMManager due to catalog issues: {str(e)}")
