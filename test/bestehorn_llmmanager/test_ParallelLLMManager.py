"""
Tests for ParallelLLMManager class.
"""

from unittest.mock import Mock, patch

import pytest

from bestehorn_llmmanager.bedrock.exceptions.parallel_exceptions import (
    ParallelConfigurationError,
    ParallelProcessingError,
)
from bestehorn_llmmanager.bedrock.models.bedrock_response import BedrockResponse
from bestehorn_llmmanager.bedrock.models.parallel_structures import (
    BedrockConverseRequest,
    FailureHandlingStrategy,
    LoadBalancingStrategy,
    ParallelProcessingConfig,
)
from bestehorn_llmmanager.parallel_llm_manager import ParallelLLMManager


class TestParallelLLMManager:
    """Test cases for ParallelLLMManager."""

    def test_initialization_success(self) -> None:
        """Test successful initialization of ParallelLLMManager."""
        models = ["Claude 3 Haiku", "Claude 3 Sonnet"]
        regions = ["us-east-1", "us-west-2"]

        with patch("bestehorn_llmmanager.parallel_llm_manager.LLMManager") as mock_llm_manager:
            parallel_manager = ParallelLLMManager(models=models, regions=regions)

            assert parallel_manager.get_available_models() == models
            assert parallel_manager.get_available_regions() == regions
            config = parallel_manager.get_parallel_config()
            assert config is not None
            assert hasattr(config, "max_concurrent_requests")
            mock_llm_manager.assert_called_once()

    def test_initialization_with_custom_config(self) -> None:
        """Test initialization with custom parallel configuration."""
        models = ["Claude 3 Haiku"]
        regions = ["us-east-1", "us-west-2"]

        custom_config = ParallelProcessingConfig(
            max_concurrent_requests=10,
            request_timeout_seconds=120,
            failure_handling_strategy=FailureHandlingStrategy.STOP_ON_THRESHOLD,
            load_balancing_strategy=LoadBalancingStrategy.RANDOM,
        )

        with patch("bestehorn_llmmanager.parallel_llm_manager.LLMManager"):
            parallel_manager = ParallelLLMManager(
                models=models, regions=regions, parallel_config=custom_config
            )

            config = parallel_manager.get_parallel_config()
            assert config.max_concurrent_requests == 10
            assert config.request_timeout_seconds == 120
            assert config.failure_handling_strategy == FailureHandlingStrategy.STOP_ON_THRESHOLD
            assert config.load_balancing_strategy == LoadBalancingStrategy.RANDOM

    def test_initialization_no_models_raises_error(self) -> None:
        """Test that initialization without models raises ParallelConfigurationError."""
        try:
            ParallelLLMManager(models=[], regions=["us-east-1"])
            assert False, "Should have raised ParallelConfigurationError"
        except ParallelConfigurationError as e:
            assert "No models specified" in str(e)

    def test_initialization_no_regions_raises_error(self) -> None:
        """Test that initialization without regions raises ParallelConfigurationError."""
        try:
            ParallelLLMManager(models=["claude-3-haiku"], regions=[])
            assert False, "Should have raised ParallelConfigurationError"
        except ParallelConfigurationError as e:
            assert "No regions specified" in str(e)

    def test_converse_with_request_success(self) -> None:
        """Test successful single request execution."""
        models = ["claude-3-haiku"]
        regions = ["us-east-1"]

        # Create mock response
        mock_response = BedrockResponse(success=True)

        with patch(
            "bestehorn_llmmanager.parallel_llm_manager.LLMManager"
        ) as mock_llm_manager_class:
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

    def test_converse_parallel_basic_success(self) -> None:
        """Test basic parallel processing success."""
        models = ["claude-3-haiku"]
        regions = ["us-east-1", "us-west-2"]

        # Mock successful responses
        mock_responses = {
            "req_test1_123456": BedrockResponse(success=True),
            "req_test2_123457": BedrockResponse(success=True),
        }

        with patch("bestehorn_llmmanager.parallel_llm_manager.LLMManager"):
            parallel_manager = ParallelLLMManager(models=models, regions=regions)

            # Create test requests
            requests = [
                BedrockConverseRequest(
                    messages=[{"role": "user", "content": [{"text": "Hello 1"}]}],
                    request_id="req_test1_123456",
                ),
                BedrockConverseRequest(
                    messages=[{"role": "user", "content": [{"text": "Hello 2"}]}],
                    request_id="req_test2_123457",
                ),
            ]

            with patch.object(parallel_manager._request_validator, "validate_batch_requests"):
                with patch.object(
                    parallel_manager._region_distributor, "distribute_requests"
                ) as mock_distribute:
                    with patch.object(
                        parallel_manager._parallel_executor, "execute_requests_parallel"
                    ) as mock_execute:
                        mock_distribute.return_value = [
                            Mock(request_id="req_test1_123456", assigned_regions=["us-east-1"]),
                            Mock(request_id="req_test2_123457", assigned_regions=["us-west-2"]),
                        ]
                        mock_execute.return_value = mock_responses

                        result = parallel_manager.converse_parallel(requests)

                        assert result is not None
                        assert hasattr(result, "success")
                        assert result.success
                        assert hasattr(result, "request_responses")
                        assert len(result.request_responses) == 2

    def test_get_underlying_llm_manager(self) -> None:
        """Test getting the underlying LLMManager instance."""
        with patch(
            "bestehorn_llmmanager.parallel_llm_manager.LLMManager"
        ) as mock_llm_manager_class:
            mock_llm_manager = Mock()
            mock_llm_manager_class.return_value = mock_llm_manager

            parallel_manager = ParallelLLMManager(models=["claude-3-haiku"], regions=["us-east-1"])

            assert parallel_manager.get_underlying_llm_manager() == mock_llm_manager

    def test_validate_configuration(self) -> None:
        """Test configuration validation."""
        with patch(
            "bestehorn_llmmanager.parallel_llm_manager.LLMManager"
        ) as mock_llm_manager_class:
            mock_llm_manager = Mock()
            mock_llm_manager.validate_configuration.return_value = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "model_region_combinations": 2,
                "auth_status": "profile",
            }
            mock_llm_manager_class.return_value = mock_llm_manager

            parallel_manager = ParallelLLMManager(
                models=["claude-3-haiku"], regions=["us-east-1", "us-west-2"]
            )

            validation_result = parallel_manager.validate_configuration()

            assert validation_result["valid"]
            assert "parallel_config_valid" in validation_result
            assert "max_concurrent_requests" in validation_result
            assert "load_balancing_strategy" in validation_result

    def test_refresh_model_data_success(self) -> None:
        """Test successful model data refresh."""
        with patch(
            "bestehorn_llmmanager.parallel_llm_manager.LLMManager"
        ) as mock_llm_manager_class:
            mock_llm_manager = Mock()
            mock_llm_manager_class.return_value = mock_llm_manager

            parallel_manager = ParallelLLMManager(models=["claude-3-haiku"], regions=["us-east-1"])

            parallel_manager.refresh_model_data()

            mock_llm_manager.refresh_model_data.assert_called_once()

    def test_refresh_model_data_failure(self) -> None:
        """Test model data refresh failure."""
        with patch(
            "bestehorn_llmmanager.parallel_llm_manager.LLMManager"
        ) as mock_llm_manager_class:
            mock_llm_manager = Mock()
            mock_llm_manager.refresh_model_data.side_effect = Exception("Refresh failed")
            mock_llm_manager_class.return_value = mock_llm_manager

            parallel_manager = ParallelLLMManager(models=["claude-3-haiku"], regions=["us-east-1"])

            with pytest.raises(ParallelProcessingError, match="Failed to refresh model data"):
                parallel_manager.refresh_model_data()

    def test_repr(self) -> None:
        """Test string representation of ParallelLLMManager."""
        models = ["claude-3-haiku", "claude-3-sonnet"]
        regions = ["us-east-1", "us-west-2", "eu-west-1"]

        with patch("bestehorn_llmmanager.parallel_llm_manager.LLMManager"):
            parallel_manager = ParallelLLMManager(models=models, regions=regions)

            repr_str = repr(parallel_manager)

            assert "ParallelLLMManager" in repr_str
            assert "models=2" in repr_str
            assert "regions=3" in repr_str
            assert "max_concurrent=5" in repr_str  # default value
            assert "strategy=round_robin" in repr_str  # default value

    def test_auto_calculate_target_regions_with_more_regions_than_concurrent(self) -> None:
        """Test auto-calculation when available regions > max_concurrent_requests."""
        models = ["claude-3-haiku"]
        regions = [
            "us-east-1",
            "us-west-2",
            "eu-west-1",
            "ap-southeast-1",
            "ca-central-1",
        ]  # 5 regions

        custom_config = ParallelProcessingConfig(max_concurrent_requests=2)  # 2 < 5 regions

        with patch("bestehorn_llmmanager.parallel_llm_manager.LLMManager"):
            parallel_manager = ParallelLLMManager(
                models=models, regions=regions, parallel_config=custom_config
            )

            # Test the private method directly
            optimal_target = parallel_manager._calculate_optimal_target_regions()

            # Should use max_concurrent_requests (2) since it's smaller than available regions (5)
            assert optimal_target == 2

    def test_auto_calculate_target_regions_with_fewer_regions_than_concurrent(self) -> None:
        """Test auto-calculation when available regions < max_concurrent_requests."""
        models = ["claude-3-haiku"]
        regions = ["us-east-1", "us-west-2"]  # 2 regions

        custom_config = ParallelProcessingConfig(max_concurrent_requests=5)  # 5 > 2 regions

        with patch("bestehorn_llmmanager.parallel_llm_manager.LLMManager"):
            parallel_manager = ParallelLLMManager(
                models=models, regions=regions, parallel_config=custom_config
            )

            # Test the private method directly
            optimal_target = parallel_manager._calculate_optimal_target_regions()

            # Should use available regions (2) since it's smaller than max_concurrent_requests (5)
            assert optimal_target == 2

    def test_auto_calculate_target_regions_equal_values(self) -> None:
        """Test auto-calculation when available regions == max_concurrent_requests."""
        models = ["claude-3-haiku"]
        regions = ["us-east-1", "us-west-2", "eu-west-1"]  # 3 regions

        custom_config = ParallelProcessingConfig(max_concurrent_requests=3)  # 3 == 3 regions

        with patch("bestehorn_llmmanager.parallel_llm_manager.LLMManager"):
            parallel_manager = ParallelLLMManager(
                models=models, regions=regions, parallel_config=custom_config
            )

            # Test the private method directly
            optimal_target = parallel_manager._calculate_optimal_target_regions()

            # Should use either value (both are 3)
            assert optimal_target == 3

    def test_converse_parallel_auto_calculation_triggers_warning(self) -> None:
        """Test that auto-calculation triggers appropriate warning messages."""
        models = ["claude-3-haiku"]
        regions = ["us-east-1", "us-west-2"]  # 2 regions

        custom_config = ParallelProcessingConfig(max_concurrent_requests=5)  # 5 > 2 regions

        with patch("bestehorn_llmmanager.parallel_llm_manager.LLMManager"):
            parallel_manager = ParallelLLMManager(
                models=models, regions=regions, parallel_config=custom_config
            )

            # Mock successful responses
            mock_responses = {
                "req_test1_123456": BedrockResponse(success=True),
            }

            # Create test request
            requests = [
                BedrockConverseRequest(
                    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
                    request_id="req_test1_123456",
                ),
            ]

            with patch.object(parallel_manager._request_validator, "validate_batch_requests"):
                with patch.object(
                    parallel_manager._region_distributor, "distribute_requests"
                ) as mock_distribute:
                    with patch.object(
                        parallel_manager._parallel_executor, "execute_requests_parallel"
                    ) as mock_execute:
                        with patch.object(parallel_manager._logger, "warning") as mock_warning:
                            mock_distribute.return_value = [
                                Mock(request_id="req_test1_123456", assigned_regions=["us-east-1"]),
                            ]
                            mock_execute.return_value = mock_responses

                            # Call without target_regions_per_request (should trigger auto-calculation)
                            parallel_manager.converse_parallel(requests)

                            # Verify warning was logged
                            mock_warning.assert_called_once()
                            warning_message = mock_warning.call_args[0][0]
                            assert "auto-adjusted to 2" in warning_message
                            assert "available_regions=2" in warning_message

                            # Verify distribute_requests was called with auto-calculated value (2)
                            mock_distribute.assert_called_once()
                            call_args = mock_distribute.call_args
                            assert call_args[1]["target_regions_per_request"] == 2

    def test_converse_parallel_explicit_target_regions_no_warning(self) -> None:
        """Test that explicitly providing target_regions_per_request doesn't trigger auto-calculation."""
        models = ["claude-3-haiku"]
        regions = ["us-east-1", "us-west-2"]  # 2 regions

        with patch("bestehorn_llmmanager.parallel_llm_manager.LLMManager"):
            parallel_manager = ParallelLLMManager(models=models, regions=regions)

            # Mock successful responses
            mock_responses = {
                "req_test1_123456": BedrockResponse(success=True),
            }

            # Create test request
            requests = [
                BedrockConverseRequest(
                    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
                    request_id="req_test1_123456",
                ),
            ]

            with patch.object(parallel_manager._request_validator, "validate_batch_requests"):
                with patch.object(
                    parallel_manager._region_distributor, "distribute_requests"
                ) as mock_distribute:
                    with patch.object(
                        parallel_manager._parallel_executor, "execute_requests_parallel"
                    ) as mock_execute:
                        with patch.object(parallel_manager._logger, "warning") as mock_warning:
                            mock_distribute.return_value = [
                                Mock(request_id="req_test1_123456", assigned_regions=["us-east-1"]),
                            ]
                            mock_execute.return_value = mock_responses

                            # Call WITH explicit target_regions_per_request (should NOT trigger auto-calculation)
                            parallel_manager.converse_parallel(
                                requests, target_regions_per_request=1
                            )

                            # Verify NO warning was logged
                            mock_warning.assert_not_called()

                            # Verify distribute_requests was called with explicit value (1)
                            mock_distribute.assert_called_once()
                            call_args = mock_distribute.call_args
                            assert call_args[1]["target_regions_per_request"] == 1

    def test_log_target_regions_adjustment_messages(self) -> None:
        """Test different warning messages for different adjustment scenarios."""
        models = ["claude-3-haiku"]

        # Test case 1: Adjustment capped by region availability
        regions_limited = ["us-east-1", "us-west-2"]  # 2 regions
        config_high_concurrent = ParallelProcessingConfig(max_concurrent_requests=5)  # 5 > 2

        with patch("bestehorn_llmmanager.parallel_llm_manager.LLMManager"):
            parallel_manager = ParallelLLMManager(
                models=models, regions=regions_limited, parallel_config=config_high_concurrent
            )

            with patch.object(parallel_manager._logger, "warning") as mock_warning:
                parallel_manager._log_target_regions_adjustment(2)

                warning_message = mock_warning.call_args[0][0]
                assert "due to limited region availability" in warning_message
                assert "available_regions=2" in warning_message

        # Test case 2: Adjustment capped by concurrency limit
        regions_many = [
            "us-east-1",
            "us-west-2",
            "eu-west-1",
            "ap-southeast-1",
            "ca-central-1",
        ]  # 5 regions
        config_low_concurrent = ParallelProcessingConfig(max_concurrent_requests=2)  # 2 < 5

        with patch("bestehorn_llmmanager.parallel_llm_manager.LLMManager"):
            parallel_manager = ParallelLLMManager(
                models=models, regions=regions_many, parallel_config=config_low_concurrent
            )

            with patch.object(parallel_manager._logger, "warning") as mock_warning:
                parallel_manager._log_target_regions_adjustment(2)

                warning_message = mock_warning.call_args[0][0]
                assert "based on concurrency limit" in warning_message
                assert "max_concurrent_requests=2" in warning_message

        # Test case 3: General auto-adjustment message (equal values)
        regions_equal = ["us-east-1", "us-west-2", "eu-west-1"]  # 3 regions
        config_equal = ParallelProcessingConfig(max_concurrent_requests=3)  # 3 == 3

        with patch("bestehorn_llmmanager.parallel_llm_manager.LLMManager"):
            parallel_manager = ParallelLLMManager(
                models=models, regions=regions_equal, parallel_config=config_equal
            )

            with patch.object(parallel_manager._logger, "warning") as mock_warning:
                parallel_manager._log_target_regions_adjustment(3)

                warning_message = mock_warning.call_args[0][0]
                assert "not specified, auto-adjusted to 3" in warning_message
                assert "max_concurrent_requests=3" in warning_message
                assert "available_regions=3" in warning_message
