"""
Tests for content compatibility error handling in retry manager.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.bedrock.retry.retry_manager import RetryManager
from src.bedrock.models.llm_manager_structures import RetryConfig, RetryStrategy, RequestAttempt
from src.bedrock.models.access_method import ModelAccessMethod, ModelAccessInfo
from src.bedrock.exceptions.llm_manager_exceptions import RetryExhaustedError

from botocore.exceptions import ClientError


class TestContentCompatibilityErrorHandling:
    """Test content compatibility error detection and handling."""
    
    @pytest.fixture
    def retry_config(self):
        """Create retry configuration for testing."""
        return RetryConfig(
            max_retries=3,
            retry_strategy=RetryStrategy.MODEL_FIRST,
            enable_feature_fallback=True
        )
    
    @pytest.fixture
    def retry_manager(self, retry_config):
        """Create retry manager for testing."""
        return RetryManager(retry_config=retry_config)
    
    @pytest.fixture
    def mock_access_info(self):
        """Create mock access info."""
        return ModelAccessInfo(
            model_id="claude-3-sonnet",
            region="us-east-1",
            access_method=ModelAccessMethod.DIRECT,
            inference_profile_id=None
        )
    
    def test_is_content_compatibility_error_video(self, retry_manager):
        """Test detection of video compatibility error."""
        # Create mock error with video incompatibility message
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'ValidationException',
                    'Message': "This model doesn't support the video content block that you provided."
                }
            },
            operation_name='Converse'
        )
        
        is_content_error, content_type = retry_manager.is_content_compatibility_error(error)
        
        assert is_content_error is True
        assert content_type == 'video_processing'
    
    def test_is_content_compatibility_error_image(self, retry_manager):
        """Test detection of image compatibility error."""
        # Create mock error with image incompatibility message
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'ValidationException',
                    'Message': "This model doesn't support the image content block that you provided."
                }
            },
            operation_name='Converse'
        )
        
        is_content_error, content_type = retry_manager.is_content_compatibility_error(error)
        
        assert is_content_error is True
        assert content_type == 'image_processing'
    
    def test_is_content_compatibility_error_document(self, retry_manager):
        """Test detection of document compatibility error."""
        # Create mock error with document incompatibility message
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'ValidationException',
                    'Message': "This model doesn't support the document content block that you provided."
                }
            },
            operation_name='Converse'
        )
        
        is_content_error, content_type = retry_manager.is_content_compatibility_error(error)
        
        assert is_content_error is True
        assert content_type == 'document_processing'
    
    def test_is_content_compatibility_error_non_content_error(self, retry_manager):
        """Test that non-content errors are not detected as content compatibility errors."""
        # Create mock error that's not a content compatibility error
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'ValidationException',
                    'Message': "Invalid request parameters."
                }
            },
            operation_name='Converse'
        )
        
        is_content_error, content_type = retry_manager.is_content_compatibility_error(error)
        
        assert is_content_error is False
        assert content_type is None
    
    def test_should_disable_feature_and_retry_excludes_content_errors(self, retry_manager):
        """Test that content compatibility errors do not trigger feature disabling."""
        # Create mock error with video incompatibility message
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'ValidationException',
                    'Message': "This model doesn't support the video content block that you provided."
                }
            },
            operation_name='Converse'
        )
        
        should_disable, feature = retry_manager.should_disable_feature_and_retry(error)
        
        assert should_disable is False
        assert feature is None
    
    def test_should_disable_feature_and_retry_api_level_errors(self, retry_manager):
        """Test that API-level errors still trigger feature disabling."""
        # Create mock error with guardrail incompatibility message
        error = ClientError(
            error_response={
                'Error': {
                    'Code': 'ValidationException',
                    'Message': "Guardrail configuration is not supported for this model."
                }
            },
            operation_name='Converse'
        )
        
        should_disable, feature = retry_manager.should_disable_feature_and_retry(error)
        
        assert should_disable is True
        assert feature == 'guardrails'
    
    @patch('src.bedrock.retry.retry_manager.time.sleep')
    def test_execute_with_retry_content_compatibility_skips_feature_fallback(
        self, mock_sleep, retry_manager, mock_access_info
    ):
        """Test that content compatibility errors skip feature fallback and try next model."""
        # Mock operation that fails with video compatibility error on first model
        # but succeeds on second model
        mock_operation = Mock()
        
        # First call fails with video compatibility error
        video_error = ClientError(
            error_response={
                'Error': {
                    'Code': 'ValidationException',
                    'Message': "This model doesn't support the video content block that you provided."
                }
            },
            operation_name='Converse'
        )
        
        # Second call succeeds
        success_response = {'output': {'message': {'content': [{'text': 'Success'}]}}}
        
        mock_operation.side_effect = [video_error, success_response]
        
        # Create retry targets with two different models
        retry_targets = [
            ("Claude 3.5 Sonnet v2", "us-east-1", mock_access_info),
            ("Nova Pro", "us-east-1", mock_access_info)
        ]
        
        operation_args = {
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {'text': 'Analyze this video'},
                        {'video': {'format': 'mp4', 'source': {'bytes': b'video_data'}}}
                    ]
                }
            ]
        }
        
        # Execute with retry
        result, attempts, warnings = retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args=operation_args,
            retry_targets=retry_targets
        )
        
        # Verify behavior
        assert result == success_response
        assert len(attempts) == 2
        assert attempts[0].success is False
        assert attempts[1].success is True
        assert mock_operation.call_count == 2
        
        # Verify that no feature fallback was attempted (would have been a third call)
        assert mock_operation.call_count == 2
    
    @patch('src.bedrock.retry.retry_manager.time.sleep')
    def test_execute_with_retry_api_error_uses_feature_fallback(
        self, mock_sleep, retry_manager, mock_access_info
    ):
        """Test that API-level errors still use feature fallback."""
        # Mock operation that fails with guardrail error, then succeeds with fallback
        mock_operation = Mock()
        
        # First call fails with guardrail error
        guardrail_error = ClientError(
            error_response={
                'Error': {
                    'Code': 'ValidationException',
                    'Message': "Guardrail configuration is not supported for this model."
                }
            },
            operation_name='Converse'
        )
        
        # Second call (feature fallback) succeeds
        success_response = {'output': {'message': {'content': [{'text': 'Success'}]}}}
        
        mock_operation.side_effect = [guardrail_error, success_response]
        
        # Create retry targets with one model
        retry_targets = [
            ("Claude 3.5 Sonnet v2", "us-east-1", mock_access_info)
        ]
        
        operation_args = {
            'messages': [{'role': 'user', 'content': [{'text': 'Hello'}]}],
            'guardrailConfig': {'guardrailId': 'test-guardrail'}
        }
        
        # Execute with retry
        result, attempts, warnings = retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args=operation_args,
            retry_targets=retry_targets
        )
        
        # Verify behavior
        assert result == success_response
        assert len(attempts) == 1  # Only one attempt record, but feature fallback happened
        assert attempts[0].success is True  # Final success after fallback
        assert mock_operation.call_count == 2  # Original call + fallback call
        assert 'Disabled guardrails due to compatibility issues' in warnings
