"""
Unit tests for RetryManager class with content filtering capabilities.

Tests the enhanced retry manager that fixes the image analysis issue by properly
managing content filtering and restoration across retry attempts.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any, List

from bestehorn_llmmanager.bedrock.retry.retry_manager import RetryManager
from bestehorn_llmmanager.bedrock.models.llm_manager_structures import (
    RetryConfig, RetryStrategy, RequestAttempt, ContentFilterState
)
from bestehorn_llmmanager.bedrock.models.llm_manager_constants import ConverseAPIFields
from bestehorn_llmmanager.bedrock.models.access_method import ModelAccessMethod, ModelAccessInfo
from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import RetryExhaustedError


class TestRetryManagerContentFiltering:
    """Test cases for RetryManager with content filtering."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.retry_config = RetryConfig(
            max_retries=3,
            retry_delay=0.1,  # Short delay for tests
            enable_feature_fallback=True
        )
        self.retry_manager = RetryManager(retry_config=self.retry_config)
        
        # Sample request with image content (the problematic case)
        self.image_request = {
            ConverseAPIFields.MESSAGES: [
                {
                    ConverseAPIFields.ROLE: ConverseAPIFields.ROLE_USER,
                    ConverseAPIFields.CONTENT: [
                        {
                            ConverseAPIFields.TEXT: "Please analyze this image and describe what you see."
                        },
                        {
                            ConverseAPIFields.IMAGE: {
                                ConverseAPIFields.FORMAT: "jpeg",
                                ConverseAPIFields.SOURCE: {
                                    ConverseAPIFields.BYTES: "base64_encoded_image_data"
                                }
                            }
                        }
                    ]
                }
            ]
        }
        
        # Mock access info objects
        self.text_model_access = ModelAccessInfo(
            model_id="ai21.jamba-text-1",
            inference_profile_id=None, 
            region="us-east-1",
            access_method=ModelAccessMethod.DIRECT
        )
        
        self.multimodal_model_access = ModelAccessInfo(
            model_id="anthropic.claude-3-5-sonnet",
            inference_profile_id=None,
            region="us-east-1", 
            access_method=ModelAccessMethod.DIRECT
        )
    
    def test_content_filter_initialization(self):
        """Test that content filter is properly initialized."""
        assert hasattr(self.retry_manager, '_content_filter')
        assert self.retry_manager._content_filter is not None
    
    def test_execute_with_retry_image_restoration(self):
        """Test the main fix: image content restoration across model attempts."""
        # Mock operation that fails for text model, succeeds for multimodal
        def mock_operation(**kwargs):
            model_id = kwargs.get('model_id')
            messages = kwargs.get(ConverseAPIFields.MESSAGES, [])
            
            # Check if image content is present
            has_image = False
            for msg in messages:
                for block in msg.get(ConverseAPIFields.CONTENT, []):
                    if ConverseAPIFields.IMAGE in block:
                        has_image = True
                        break
            
            if model_id and 'ai21' in model_id and has_image:
                # Text-only model fails with image content
                raise Exception("Model does not support image processing")
            elif model_id and 'claude' in model_id:
                # Multimodal model succeeds
                return {"output": {"message": {"content": [{"text": "I can see an image..."}]}}}
            else:
                raise Exception("Unknown model")
        
        retry_targets = [
            ("AI21 Jamba", "us-east-1", self.text_model_access),
            ("Claude 3.5 Sonnet", "us-east-1", self.multimodal_model_access)
        ]
        
        # Execute with retry
        result, attempts, warnings = self.retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args=self.image_request,
            retry_targets=retry_targets
        )
        
        # Should succeed after 2 attempts
        assert result is not None
        assert len(attempts) == 2
        assert attempts[0].success == False  # First attempt failed
        assert attempts[1].success == True   # Second attempt succeeded
        
        # Should have warnings about feature restoration
        assert any("Restored image_processing" in warning for warning in warnings)
    
    def test_feature_fallback_on_same_model(self):
        """Test feature fallback on the same model."""
        def mock_operation(**kwargs):
            messages = kwargs.get(ConverseAPIFields.MESSAGES, [])
            
            # Check if image content is present
            has_image = False
            for msg in messages:
                for block in msg.get(ConverseAPIFields.CONTENT, []):
                    if ConverseAPIFields.IMAGE in block:
                        has_image = True
                        break
            
            if has_image:
                # Fail with image content
                raise Exception("image processing not supported")
            else:
                # Succeed without image
                return {"output": {"message": {"content": [{"text": "Text only response"}]}}}
        
        retry_targets = [
            ("Test Model", "us-east-1", self.text_model_access)
        ]
        
        result, attempts, warnings = self.retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args=self.image_request,
            retry_targets=retry_targets
        )
        
        # Should succeed after feature fallback
        assert result is not None
        assert len(attempts) == 1
        assert attempts[0].success == True
        
        # Should have warning about disabled feature
        assert any("image_processing" in warning for warning in warnings)
    
    def test_content_restoration_between_models(self):
        """Test that content is properly restored when switching between models."""
        requests_received = []
        
        def mock_operation(**kwargs):
            # Store the request to analyze later
            messages = kwargs.get(ConverseAPIFields.MESSAGES, [])
            requests_received.append(messages)
            
            model_id = kwargs.get('model_id')
            if model_id and 'ai21' in model_id:
                raise Exception("image not supported")
            else:
                return {"output": {"message": {"content": [{"text": "Success"}]}}}
        
        retry_targets = [
            ("AI21 Jamba", "us-east-1", self.text_model_access),
            ("Claude 3.5 Sonnet", "us-east-1", self.multimodal_model_access)
        ]
        
        result, attempts, warnings = self.retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args=self.image_request,
            retry_targets=retry_targets
        )
        
        # Should have received 3 requests (original + fallback + model switch)
        assert len(requests_received) == 3
        
        # First request should have image (original request to AI21)
        first_request = requests_received[0]
        first_content_blocks = first_request[0][ConverseAPIFields.CONTENT]
        has_image_first = any(ConverseAPIFields.IMAGE in block for block in first_content_blocks)
        assert has_image_first, "First request should have image"
        
        # Second request should have image filtered out (fallback on AI21)
        second_request = requests_received[1]
        second_content_blocks = second_request[0][ConverseAPIFields.CONTENT]
        has_image_second = any(ConverseAPIFields.IMAGE in block for block in second_content_blocks)
        assert not has_image_second, "Second request should not have image (filtered for fallback)"
        
        # Third request should have image restored (switch to Claude)
        third_request = requests_received[2]
        third_content_blocks = third_request[0][ConverseAPIFields.CONTENT]
        has_image_third = any(ConverseAPIFields.IMAGE in block for block in third_content_blocks)
        assert has_image_third, "Image content should be restored for multimodal model"
    
    def test_multiple_content_types_restoration(self):
        """Test restoration of multiple content types."""
        multimodal_request = {
            ConverseAPIFields.MESSAGES: [
                {
                    ConverseAPIFields.ROLE: ConverseAPIFields.ROLE_USER,
                    ConverseAPIFields.CONTENT: [
                        {ConverseAPIFields.TEXT: "Process these files."},
                        {ConverseAPIFields.IMAGE: {"format": "png", "source": {"bytes": "img"}}},
                        {ConverseAPIFields.DOCUMENT: {"name": "doc.pdf", "format": "pdf", "source": {"bytes": "doc"}}}
                    ]
                }
            ]
        }
        
        requests_received = []
        
        def mock_operation(**kwargs):
            messages = kwargs.get(ConverseAPIFields.MESSAGES, [])
            requests_received.append(messages)
            
            model_id = kwargs.get('model_id')
            if model_id and 'ai21' in model_id:
                # Text-only model
                content_blocks = messages[0][ConverseAPIFields.CONTENT]
                # Check for specific content types
                has_image = any(ConverseAPIFields.IMAGE in block for block in content_blocks)
                has_document = any(ConverseAPIFields.DOCUMENT in block for block in content_blocks)
                
                # Raise error for the first unsupported content type found
                if has_image:
                    raise Exception("image not supported")
                elif has_document:
                    raise Exception("document not supported")
                return {"output": {"message": {"content": [{"text": "Text only"}]}}}
            else:
                # Multimodal model
                return {"output": {"message": {"content": [{"text": "Multimodal response"}]}}}
        
        retry_targets = [
            ("AI21 Jamba", "us-east-1", self.text_model_access),
            ("Claude 3.5 Sonnet", "us-east-1", self.multimodal_model_access)
        ]
        
        result, attempts, warnings = self.retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args=multimodal_request,
            retry_targets=retry_targets
        )
        
        # Should succeed
        assert result is not None
        assert len(attempts) == 2
        
        # Check restoration warnings
        restoration_warnings = [w for w in warnings if "Restored" in w]
        assert len(restoration_warnings) >= 1  # Should restore at least one feature
        
        # Check that both features were disabled at some point
        disabled_warnings = [w for w in warnings if "Disabled" in w]
        assert any("image_processing" in w for w in disabled_warnings)
        # Document processing might not be explicitly disabled if handled together
    
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_retry_delay_with_content_filtering(self, mock_sleep):
        """Test that retry delays work correctly with content filtering."""
        call_count = 0
        
        def mock_operation(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("temporary failure")
            return {"output": {"message": {"content": [{"text": "Success after retries"}]}}}
        
        retry_targets = [
            ("Model 1", "us-east-1", self.text_model_access),
            ("Model 2", "us-east-1", self.text_model_access),
            ("Model 3", "us-east-1", self.text_model_access)
        ]
        
        result, attempts, warnings = self.retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args=self.image_request,
            retry_targets=retry_targets
        )
        
        assert result is not None
        assert len(attempts) == 3
        assert attempts[2].success == True
        
        # Should have called sleep for delays (not for the final successful attempt)
        assert mock_sleep.call_count >= 1
    
    def test_filter_state_preservation(self):
        """Test that filter state is preserved across retry attempts."""
        filter_states = []
        
        def mock_operation(**kwargs):
            # We can't directly access the filter state, but we can observe
            # the pattern of content filtering
            messages = kwargs.get(ConverseAPIFields.MESSAGES, [])
            content_blocks = messages[0][ConverseAPIFields.CONTENT]
            
            # Count content types to infer filter state
            text_count = sum(1 for block in content_blocks if ConverseAPIFields.TEXT in block)
            image_count = sum(1 for block in content_blocks if ConverseAPIFields.IMAGE in block)
            
            filter_states.append({
                'text_count': text_count,
                'image_count': image_count,
                'total_blocks': len(content_blocks)
            })
            
            # Always succeed for this test
            return {"output": {"message": {"content": [{"text": "Success"}]}}}
        
        retry_targets = [
            ("Claude 3.5 Sonnet", "us-east-1", self.multimodal_model_access)
        ]
        
        result, attempts, warnings = self.retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args=self.image_request,
            retry_targets=retry_targets
        )
        
        # Should have preserved original content since model supports images
        assert len(filter_states) == 1
        state = filter_states[0]
        assert state['text_count'] == 1
        assert state['image_count'] == 1
        assert state['total_blocks'] == 2
    
    def test_all_retries_exhausted_with_filtering(self):
        """Test retry exhaustion with content filtering."""
        def mock_operation(**kwargs):
            raise Exception("persistent failure")
        
        retry_targets = [
            ("Model 1", "us-east-1", self.text_model_access),
            ("Model 2", "us-east-1", self.text_model_access)
        ]
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            self.retry_manager.execute_with_retry(
                operation=mock_operation,
                operation_args=self.image_request,
                retry_targets=retry_targets
            )
        
        # Should have detailed error information
        error = exc_info.value
        assert error.attempts_made == 2
        assert len(error.models_tried) == 2
        assert len(error.regions_tried) == 1


class TestRetryManagerBackwardCompatibility:
    """Test that retry manager maintains backward compatibility."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.retry_config = RetryConfig(max_retries=2)
        self.retry_manager = RetryManager(retry_config=self.retry_config)
    
    def test_text_only_requests_unchanged(self):
        """Test that text-only requests work exactly as before."""
        text_request = {
            ConverseAPIFields.MESSAGES: [
                {
                    ConverseAPIFields.ROLE: ConverseAPIFields.ROLE_USER,
                    ConverseAPIFields.CONTENT: [
                        {ConverseAPIFields.TEXT: "Hello, how are you?"}
                    ]
                }
            ]
        }
        
        def mock_operation(**kwargs):
            return {"output": {"message": {"content": [{"text": "I'm doing well!"}]}}}
        
        access_info = ModelAccessInfo(
            model_id="test-model",
            inference_profile_id=None,
            region="us-east-1",
            access_method=ModelAccessMethod.DIRECT
        )
        
        retry_targets = [("Test Model", "us-east-1", access_info)]
        
        result, attempts, warnings = self.retry_manager.execute_with_retry(
            operation=mock_operation,
            operation_args=text_request,
            retry_targets=retry_targets
        )
        
        assert result is not None
        assert len(attempts) == 1
        assert attempts[0].success == True
        assert len(warnings) == 0  # No filtering warnings for text-only
    
    def test_existing_retry_logic_preserved(self):
        """Test that existing retry logic (delays, error classification) is preserved."""
        call_count = 0
        
        def mock_operation(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                from botocore.exceptions import ClientError
                raise ClientError(
                    error_response={'Error': {'Code': 'ThrottlingException'}},
                    operation_name='Converse'
                )
            return {"success": True}
        
        access_info = ModelAccessInfo(
            model_id="test-model",
            inference_profile_id=None,
            region="us-east-1",
            access_method=ModelAccessMethod.DIRECT
        )
        
        retry_targets = [
            ("Model 1", "us-east-1", access_info),
            ("Model 2", "us-east-1", access_info)
        ]
        
        text_request = {
            ConverseAPIFields.MESSAGES: [
                {
                    ConverseAPIFields.ROLE: ConverseAPIFields.ROLE_USER,
                    ConverseAPIFields.CONTENT: [
                        {ConverseAPIFields.TEXT: "Test message"}
                    ]
                }
            ]
        }
        
        with patch('time.sleep'):  # Mock sleep for faster tests
            result, attempts, warnings = self.retry_manager.execute_with_retry(
                operation=mock_operation,
                operation_args=text_request,
                retry_targets=retry_targets
            )
        
        assert result is not None
        assert len(attempts) == 2
        assert attempts[0].success == False  # First failed due to throttling
        assert attempts[1].success == True   # Second succeeded


if __name__ == "__main__":
    pytest.main([__file__])
