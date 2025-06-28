"""
Unit tests for LLMManager class.
Tests the main functionality of the LLM Manager system.
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
    AuthenticationError,
    ConfigurationError,
    RequestValidationError,
    RetryExhaustedError,
)
from bestehorn_llmmanager.bedrock.models.bedrock_response import BedrockResponse, StreamingResponse
from bestehorn_llmmanager.bedrock.models.llm_manager_constants import (
    ContentLimits,
    ConverseAPIFields,
)
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    AuthConfig,
    AuthenticationType,
    RetryConfig,
    RetryStrategy,
)
from bestehorn_llmmanager.llm_manager import LLMManager


class TestLLMManager:
    """Test cases for LLMManager class."""

    @pytest.fixture
    def mock_unified_model_manager(self):
        """Create a mock UnifiedModelManager."""
        mock_manager = Mock()
        mock_manager.load_cached_data.return_value = True
        mock_manager.get_model_access_info.return_value = Mock(
            access_method=Mock(value="direct"),
            model_id="test-model-id",
            inference_profile_id="test-profile-id",
            region="us-east-1",
        )
        return mock_manager

    @pytest.fixture
    def basic_llm_manager(self, mock_unified_model_manager):
        """Create a basic LLMManager instance for testing."""
        with patch(
            "bestehorn_llmmanager.llm_manager.UnifiedModelManager",
            return_value=mock_unified_model_manager,
        ):
            return LLMManager(models=["Claude 3 Haiku"], regions=["us-east-1"])

    def test_init_basic_configuration(self, mock_unified_model_manager):
        """Test basic initialization of LLMManager."""
        with patch(
            "bestehorn_llmmanager.llm_manager.UnifiedModelManager",
            return_value=mock_unified_model_manager,
        ):
            manager = LLMManager(
                models=["Claude 3 Haiku", "Claude 3 Sonnet"], regions=["us-east-1", "us-west-2"]
            )

            assert manager.get_available_models() == ["Claude 3 Haiku", "Claude 3 Sonnet"]
            assert manager.get_available_regions() == ["us-east-1", "us-west-2"]

    def test_init_with_auth_config(self, mock_unified_model_manager):
        """Test initialization with authentication configuration."""
        auth_config = AuthConfig(auth_type=AuthenticationType.PROFILE, profile_name="test-profile")

        with patch(
            "bestehorn_llmmanager.llm_manager.UnifiedModelManager",
            return_value=mock_unified_model_manager,
        ):
            manager = LLMManager(
                models=["Claude 3 Haiku"], regions=["us-east-1"], auth_config=auth_config
            )

            assert manager is not None

    def test_init_with_retry_config(self, mock_unified_model_manager):
        """Test initialization with retry configuration."""
        retry_config = RetryConfig(max_retries=5, retry_strategy=RetryStrategy.MODEL_FIRST)

        with patch(
            "bestehorn_llmmanager.llm_manager.UnifiedModelManager",
            return_value=mock_unified_model_manager,
        ):
            manager = LLMManager(
                models=["Claude 3 Haiku"], regions=["us-east-1"], retry_config=retry_config
            )

            stats = manager.get_retry_stats()
            assert stats["max_retries"] == 5
            assert stats["retry_strategy"] == "model_first"

    def test_init_empty_models_raises_error(self):
        """Test that empty models list raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="No models specified for LLM Manager"):
            LLMManager(models=[], regions=["us-east-1"])

    def test_init_empty_regions_raises_error(self):
        """Test that empty regions list raises ConfigurationError."""
        with pytest.raises(ConfigurationError, match="No regions specified for LLM Manager"):
            LLMManager(models=["Claude 3 Haiku"], regions=[])

    def test_init_invalid_model_name_raises_error(self):
        """Test that invalid model names raise ConfigurationError."""
        with pytest.raises(ConfigurationError, match="Invalid model name:"):
            LLMManager(models=["Claude 3 Haiku", ""], regions=["us-east-1"])

    def test_init_invalid_region_name_raises_error(self):
        """Test that invalid region names raise ConfigurationError."""
        with pytest.raises(ConfigurationError, match="Invalid region name:"):
            LLMManager(models=["Claude 3 Haiku"], regions=["us-east-1", ""])

    def test_validate_converse_request_empty_messages(self, basic_llm_manager):
        """Test validation of empty messages."""
        with pytest.raises(RequestValidationError, match="Messages cannot be empty"):
            basic_llm_manager._validate_converse_request([])

    def test_validate_converse_request_invalid_message_type(self, basic_llm_manager):
        """Test validation of invalid message types."""
        with pytest.raises(RequestValidationError, match="Message 0 must be a dictionary"):
            basic_llm_manager._validate_converse_request(["invalid"])

    def test_validate_converse_request_missing_role(self, basic_llm_manager):
        """Test validation of messages missing role field."""
        message = {"content": [{"text": "Hello"}]}

        with pytest.raises(RequestValidationError, match="Message 0 missing required 'role' field"):
            basic_llm_manager._validate_converse_request([message])

    def test_validate_converse_request_invalid_role(self, basic_llm_manager):
        """Test validation of messages with invalid role."""
        message = {"role": "invalid_role", "content": [{"text": "Hello"}]}

        with pytest.raises(RequestValidationError, match="Message 0 has invalid role"):
            basic_llm_manager._validate_converse_request([message])

    def test_validate_converse_request_missing_content(self, basic_llm_manager):
        """Test validation of messages missing content field."""
        message = {"role": "user"}

        with pytest.raises(
            RequestValidationError, match="Message 0 missing required 'content' field"
        ):
            basic_llm_manager._validate_converse_request([message])

    def test_validate_converse_request_invalid_content_type(self, basic_llm_manager):
        """Test validation of messages with invalid content type."""
        message = {"role": "user", "content": "invalid_content"}

        with pytest.raises(RequestValidationError, match="Message 0 content must be a list"):
            basic_llm_manager._validate_converse_request([message])

    def test_validate_converse_request_valid_message(self, basic_llm_manager):
        """Test validation of valid messages."""
        messages = [
            {"role": "user", "content": [{"text": "Hello"}]},
            {"role": "assistant", "content": [{"text": "Hi there!"}]},
        ]

        # Should not raise any exception
        basic_llm_manager._validate_converse_request(messages)

    def test_validate_content_blocks_image_limit_exceeded(self, basic_llm_manager):
        """Test validation of content blocks exceeding image limits."""
        errors = []
        content_blocks = [
            {"image": {"format": "png"}} for _ in range(ContentLimits.MAX_IMAGES_PER_REQUEST + 1)
        ]

        basic_llm_manager._validate_content_blocks(content_blocks, 0, errors)

        assert len(errors) == 1
        assert "exceeds image limit" in errors[0]

    def test_validate_content_blocks_document_limit_exceeded(self, basic_llm_manager):
        """Test validation of content blocks exceeding document limits."""
        errors = []
        content_blocks = [
            {"document": {"name": "test.pd"}}
            for _ in range(ContentLimits.MAX_DOCUMENTS_PER_REQUEST + 1)
        ]

        basic_llm_manager._validate_content_blocks(content_blocks, 0, errors)

        assert len(errors) == 1
        assert "exceeds document limit" in errors[0]

    def test_validate_content_blocks_video_limit_exceeded(self, basic_llm_manager):
        """Test validation of content blocks exceeding video limits."""
        errors = []
        content_blocks = [
            {"video": {"format": "mp4"}} for _ in range(ContentLimits.MAX_VIDEOS_PER_REQUEST + 1)
        ]

        basic_llm_manager._validate_content_blocks(content_blocks, 0, errors)

        assert len(errors) == 1
        assert "exceeds video limit" in errors[0]

    def test_build_converse_request_basic(self, basic_llm_manager):
        """Test building basic converse request."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]

        request_args = basic_llm_manager._build_converse_request(messages=messages)

        assert ConverseAPIFields.MESSAGES in request_args
        assert request_args[ConverseAPIFields.MESSAGES] == messages

    def test_build_converse_request_with_system(self, basic_llm_manager):
        """Test building converse request with system messages."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        system = [{"text": "You are a helpful assistant"}]

        request_args = basic_llm_manager._build_converse_request(messages=messages, system=system)

        assert ConverseAPIFields.SYSTEM in request_args
        assert request_args[ConverseAPIFields.SYSTEM] == system

    def test_build_converse_request_with_inference_config(self, basic_llm_manager):
        """Test building converse request with inference configuration."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        inference_config = {"temperature": 0.7, "maxTokens": 1000}

        request_args = basic_llm_manager._build_converse_request(
            messages=messages, inference_config=inference_config
        )

        assert ConverseAPIFields.INFERENCE_CONFIG in request_args
        assert request_args[ConverseAPIFields.INFERENCE_CONFIG]["temperature"] == 0.7
        assert request_args[ConverseAPIFields.INFERENCE_CONFIG]["maxTokens"] == 1000

    def test_build_converse_request_merges_default_inference_config(
        self, mock_unified_model_manager
    ):
        """Test that default and provided inference configs are merged properly."""
        default_config = {"temperature": 0.5, "maxTokens": 2000}

        with patch(
            "bestehorn_llmmanager.llm_manager.UnifiedModelManager",
            return_value=mock_unified_model_manager,
        ):
            manager = LLMManager(
                models=["Claude 3 Haiku"],
                regions=["us-east-1"],
                default_inference_config=default_config,
            )

        messages = [{"role": "user", "content": [{"text": "Hello"}]}]
        inference_config = {"temperature": 0.7}  # Override temperature, keep maxTokens

        request_args = manager._build_converse_request(
            messages=messages, inference_config=inference_config
        )

        final_config = request_args[ConverseAPIFields.INFERENCE_CONFIG]
        assert final_config["temperature"] == 0.7  # Overridden
        assert final_config["maxTokens"] == 2000  # From default

    def test_build_converse_request_with_all_optional_fields(self, basic_llm_manager):
        """Test building converse request with all optional fields."""
        messages = [{"role": "user", "content": [{"text": "Hello"}]}]

        request_args = basic_llm_manager._build_converse_request(
            messages=messages,
            system=[{"text": "System prompt"}],
            inference_config={"temperature": 0.7},
            additional_model_request_fields={"custom_field": "value"},
            additional_model_response_field_paths=["/custom_path"],
            guardrail_config={"guardrailId": "test-id"},
            tool_config={"tools": []},
            request_metadata={"userId": "test-user"},
            prompt_variables={"var1": "value1"},
        )

        # Check all fields are present
        expected_fields = [
            ConverseAPIFields.MESSAGES,
            ConverseAPIFields.SYSTEM,
            ConverseAPIFields.INFERENCE_CONFIG,
            ConverseAPIFields.ADDITIONAL_MODEL_REQUEST_FIELDS,
            ConverseAPIFields.ADDITIONAL_MODEL_RESPONSE_FIELD_PATHS,
            ConverseAPIFields.GUARDRAIL_CONFIG,
            ConverseAPIFields.TOOL_CONFIG,
            ConverseAPIFields.REQUEST_METADATA,
            ConverseAPIFields.PROMPT_VARIABLES,
        ]

        for field in expected_fields:
            assert field in request_args

    def test_get_model_access_info_success(self, basic_llm_manager):
        """Test successful retrieval of model access information."""
        result = basic_llm_manager.get_model_access_info("Claude 3 Haiku", "us-east-1")

        assert result is not None
        assert "access_method" in result
        assert "model_id" in result
        assert "inference_profile_id" in result
        assert "region" in result

    def test_get_model_access_info_not_found(self, basic_llm_manager):
        """Test retrieval of model access information when not found."""
        # Mock the unified model manager to return None
        basic_llm_manager._unified_model_manager.get_model_access_info.return_value = None

        result = basic_llm_manager.get_model_access_info("NonExistent Model", "us-east-1")

        assert result is None

    def test_validate_configuration_success(self, basic_llm_manager):
        """Test successful configuration validation."""
        result = basic_llm_manager.validate_configuration()

        assert result["valid"] is True
        assert result["model_region_combinations"] > 0
        assert "auth_type" in result["auth_status"] or result["auth_status"] != "unknown"

    def test_validate_configuration_no_valid_combinations(self, basic_llm_manager):
        """Test configuration validation with no valid model/region combinations."""
        # Mock to return None for all access info calls
        basic_llm_manager._unified_model_manager.get_model_access_info.return_value = None

        result = basic_llm_manager.validate_configuration()

        assert result["valid"] is False
        assert result["model_region_combinations"] == 0
        assert "No valid model/region combinations found" in result["errors"]

    def test_refresh_model_data_success(self, basic_llm_manager):
        """Test successful model data refresh."""
        basic_llm_manager._unified_model_manager.refresh_unified_data = Mock()

        # Should not raise any exception
        basic_llm_manager.refresh_model_data()

        basic_llm_manager._unified_model_manager.refresh_unified_data.assert_called_once()

    def test_refresh_model_data_failure(self, basic_llm_manager):
        """Test model data refresh failure."""
        basic_llm_manager._unified_model_manager.refresh_unified_data.side_effect = Exception(
            "Network error"
        )

        with pytest.raises(Exception, match="Failed to refresh model data"):
            basic_llm_manager.refresh_model_data()

    def test_get_retry_stats(self, basic_llm_manager):
        """Test retrieval of retry statistics."""
        stats = basic_llm_manager.get_retry_stats()

        assert isinstance(stats, dict)
        assert "max_retries" in stats
        assert "retry_strategy" in stats

    def test_repr(self, basic_llm_manager):
        """Test string representation of LLMManager."""
        repr_str = repr(basic_llm_manager)

        assert "LLMManager" in repr_str
        assert "models=1" in repr_str
        assert "regions=1" in repr_str
        assert "auth=" in repr_str

    def test_converse_no_retry_targets_raises_error(self, basic_llm_manager):
        """Test converse method when no retry targets are available."""
        # Mock retry manager to return empty targets
        with patch.object(
            basic_llm_manager._retry_manager, "generate_retry_targets", return_value=[]
        ):
            messages = [{"role": "user", "content": [{"text": "Hello"}]}]

            with pytest.raises(
                ConfigurationError, match="No valid model/region combinations available"
            ):
                basic_llm_manager.converse(messages=messages)

    def test_converse_stream_no_retry_targets_raises_error(self, basic_llm_manager):
        """Test converse_stream method when no retry targets are available."""
        # Mock retry manager to return empty targets
        with patch.object(
            basic_llm_manager._retry_manager, "generate_retry_targets", return_value=[]
        ):
            messages = [{"role": "user", "content": [{"text": "Hello"}]}]

            with pytest.raises(
                ConfigurationError,
                match="No valid model/region combinations available for streaming",
            ):
                basic_llm_manager.converse_stream(messages=messages)


class TestLLMManagerIntegration:
    """Integration tests for LLMManager that test component interactions."""

    @pytest.fixture
    def mock_components(self):
        """Create mocked components for integration testing."""
        # Mock successful execution
        mock_result = {
            "output": {"message": {"content": [{"text": "Test response"}]}},
            "usage": {"inputTokens": 10, "outputTokens": 20, "totalTokens": 30},
            "metrics": {"latencyMs": 150},
        }

        mock_attempt = Mock()
        mock_attempt.model_id = "Claude 3 Haiku"
        mock_attempt.region = "us-east-1"
        mock_attempt.access_method = "direct"
        mock_attempt.success = True

        mocks = {
            "unified_model_manager": Mock(),
            "auth_manager": Mock(),
            "retry_manager": Mock(),
            "execute_result": (mock_result, [mock_attempt], []),
        }

        # Configure unified model manager
        mocks["unified_model_manager"].load_cached_data.return_value = True
        mocks["unified_model_manager"].get_model_access_info.return_value = Mock(
            access_method=Mock(value="direct"),
            model_id="test-model-id",
            inference_profile_id="test-profile-id",
            region="us-east-1",
        )

        # Configure retry manager
        retry_targets = [("test-model", "us-east-1", Mock())]
        mocks["retry_manager"].generate_retry_targets.return_value = retry_targets
        mocks["retry_manager"].execute_with_retry.return_value = mocks["execute_result"]

        return mocks

    @patch("bestehorn_llmmanager.llm_manager.datetime")
    def test_converse_success_flow(self, mock_datetime, mock_components):
        """Test successful converse operation end-to-end."""
        # Setup datetime mock
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 1, 12, 0, 1)
        mock_datetime.now.side_effect = [start_time, end_time]

        with patch(
            "bestehorn_llmmanager.llm_manager.UnifiedModelManager",
            return_value=mock_components["unified_model_manager"],
        ), patch(
            "bestehorn_llmmanager.llm_manager.AuthManager",
            return_value=mock_components["auth_manager"],
        ), patch(
            "bestehorn_llmmanager.llm_manager.RetryManager",
            return_value=mock_components["retry_manager"],
        ):

            manager = LLMManager(models=["Claude 3 Haiku"], regions=["us-east-1"])

            messages = [{"role": "user", "content": [{"text": "Hello"}]}]
            response = manager.converse(messages=messages)

            # Verify response
            assert isinstance(response, BedrockResponse)
            assert response.success is True
            assert response.model_used == "Claude 3 Haiku"
            assert response.region_used == "us-east-1"
            assert response.access_method_used in ["direct", "both"]  # Can be either direct or both
            assert response.total_duration_ms == 1000.0  # 1 second difference

    def test_converse_retry_exhausted_flow(self, mock_components):
        """Test converse operation when all retries are exhausted."""
        # Configure retry manager to raise RetryExhaustedError
        mock_components["retry_manager"].execute_with_retry.side_effect = RetryExhaustedError(
            message="All retries failed",
            attempts_made=3,
            models_tried=["model1"],
            regions_tried=["us-east-1"],
        )

        with patch(
            "bestehorn_llmmanager.llm_manager.UnifiedModelManager",
            return_value=mock_components["unified_model_manager"],
        ), patch(
            "bestehorn_llmmanager.llm_manager.AuthManager",
            return_value=mock_components["auth_manager"],
        ), patch(
            "bestehorn_llmmanager.llm_manager.RetryManager",
            return_value=mock_components["retry_manager"],
        ):

            manager = LLMManager(models=["Claude 3 Haiku"], regions=["us-east-1"])

            messages = [{"role": "user", "content": [{"text": "Hello"}]}]

            with pytest.raises(RetryExhaustedError):
                manager.converse(messages=messages)


class TestLLMManagerUncoveredCases:
    """Test cases for uncovered lines in LLMManager."""

    @pytest.fixture
    def mock_unified_model_manager(self):
        """Create a mock UnifiedModelManager."""
        mock_manager = Mock()
        mock_manager.load_cached_data.return_value = True
        mock_manager.get_model_access_info.return_value = Mock(
            access_method=Mock(value="direct"),
            model_id="test-model-id",
            inference_profile_id="test-profile-id",
            region="us-east-1",
        )
        return mock_manager

    @pytest.fixture
    def basic_llm_manager(self, mock_unified_model_manager):
        """Create a basic LLMManager instance for testing."""
        with patch(
            "bestehorn_llmmanager.llm_manager.UnifiedModelManager",
            return_value=mock_unified_model_manager,
        ):
            return LLMManager(models=["Claude 3 Haiku"], regions=["us-east-1"])

    def test_init_unified_model_manager_load_cached_fails(self):
        """Test initialization when UnifiedModelManager fails to load cached data."""
        mock_unified_manager = Mock()
        mock_unified_manager.load_cached_data.return_value = None  # No cached data
        mock_unified_manager.refresh_unified_data.return_value = None
        mock_unified_manager.get_model_access_info.return_value = Mock(
            access_method=Mock(value="direct"),
            model_id="test-model-id",
            inference_profile_id="test-profile-id",
            region="us-east-1",
        )

        with patch(
            "bestehorn_llmmanager.llm_manager.UnifiedModelManager",
            return_value=mock_unified_manager,
        ):
            manager = LLMManager(models=["Claude 3 Haiku"], regions=["us-east-1"])

            # Verify refresh was called when load_cached_data returned None
            mock_unified_manager.refresh_unified_data.assert_called_once()

    def test_init_unified_model_manager_exception(self):
        """Test initialization when UnifiedModelManager raises exception."""
        mock_unified_manager = Mock()
        mock_unified_manager.load_cached_data.side_effect = Exception("Failed to load")
        mock_unified_manager.get_model_access_info.return_value = None

        with patch(
            "bestehorn_llmmanager.llm_manager.UnifiedModelManager",
            return_value=mock_unified_manager,
        ):
            # Should raise ConfigurationError due to no valid model/region combinations
            with pytest.raises(
                ConfigurationError, match="No valid model/region combinations found"
            ):
                LLMManager(models=["Claude 3 Haiku"], regions=["us-east-1"])

    def test_validate_model_region_combinations_no_valid_combinations(self):
        """Test validation when no model/region combinations are available."""
        mock_unified_manager = Mock()
        mock_unified_manager.load_cached_data.return_value = True
        mock_unified_manager.get_model_access_info.side_effect = Exception("Not available")

        with patch(
            "bestehorn_llmmanager.llm_manager.UnifiedModelManager",
            return_value=mock_unified_manager,
        ):
            # Should raise ConfigurationError due to no valid model/region combinations
            with pytest.raises(
                ConfigurationError, match="No valid model/region combinations found"
            ):
                LLMManager(models=["Claude 3 Haiku"], regions=["us-east-1"])

    def test_validate_content_blocks_invalid_block_type(self, basic_llm_manager):
        """Test validation of content blocks with invalid block type."""
        errors = []
        content_blocks = ["invalid_block", {"text": "valid"}]

        basic_llm_manager._validate_content_blocks(content_blocks, 0, errors)

        assert len(errors) == 1
        assert "block 0 must be a dictionary" in errors[0]

    def test_execute_converse_success(self, basic_llm_manager):
        """Test _execute_converse method success."""
        mock_client = Mock()
        mock_client.converse.return_value = {
            "output": {"message": {"content": [{"text": "Response"}]}}
        }

        with patch.object(
            basic_llm_manager._auth_manager, "get_bedrock_client", return_value=mock_client
        ):
            result = basic_llm_manager._execute_converse(
                model_id="test-model", messages=[{"role": "user", "content": [{"text": "Hello"}]}]
            )

            assert result == {"output": {"message": {"content": [{"text": "Response"}]}}}
            mock_client.converse.assert_called_once()

    def test_execute_converse_no_region_available(self, basic_llm_manager):
        """Test _execute_converse when no region is available."""
        with patch.object(
            basic_llm_manager._auth_manager,
            "get_bedrock_client",
            side_effect=Exception("Auth failed"),
        ):
            with pytest.raises(
                AuthenticationError, match="Could not authenticate to any specified region"
            ):
                basic_llm_manager._execute_converse(
                    model_id="test-model",
                    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
                )

    def test_execute_converse_stream_success(self, basic_llm_manager):
        """Test _execute_converse_stream method success."""
        mock_client = Mock()
        mock_stream_response = Mock()
        mock_client.converse_stream.return_value = mock_stream_response

        with patch.object(
            basic_llm_manager._auth_manager, "get_bedrock_client", return_value=mock_client
        ):
            result = basic_llm_manager._execute_converse_stream(
                model_id="test-model", messages=[{"role": "user", "content": [{"text": "Hello"}]}]
            )

            assert result == mock_stream_response
            mock_client.converse_stream.assert_called_once()

    def test_execute_converse_stream_no_region_available(self, basic_llm_manager):
        """Test _execute_converse_stream when no region is available."""
        with patch.object(
            basic_llm_manager._auth_manager,
            "get_bedrock_client",
            side_effect=Exception("Auth failed"),
        ):
            with pytest.raises(
                AuthenticationError, match="Could not authenticate to any specified region"
            ):
                basic_llm_manager._execute_converse_stream(
                    model_id="test-model",
                    messages=[{"role": "user", "content": [{"text": "Hello"}]}],
                )

    def test_get_model_access_info_exception(self, basic_llm_manager):
        """Test get_model_access_info when exception occurs."""
        basic_llm_manager._unified_model_manager.get_model_access_info.side_effect = Exception(
            "Error"
        )

        result = basic_llm_manager.get_model_access_info("Claude 3 Haiku", "us-east-1")

        assert result is None

    def test_validate_configuration_auth_error(self, basic_llm_manager):
        """Test validate_configuration when authentication fails."""
        with patch.object(
            basic_llm_manager._auth_manager, "get_auth_info", side_effect=Exception("Auth error")
        ):
            result = basic_llm_manager.validate_configuration()

            assert result["valid"] is False
            assert "Authentication error" in result["errors"][0]
