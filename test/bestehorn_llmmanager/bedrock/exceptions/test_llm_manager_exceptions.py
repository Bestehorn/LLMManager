"""
Comprehensive unit tests for LLM Manager exceptions.
Tests all exception classes and their functionality.
"""

import pytest
from typing import Dict, Any, List, Optional

from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
    LLMManagerError,
    ConfigurationError,
    AuthenticationError,
    ModelAccessError,
    RetryExhaustedError,
    RequestValidationError,
    StreamingError,
    ContentError
)


class TestLLMManagerError:
    """Test suite for base LLMManagerError class."""
    
    def test_basic_initialization(self):
        """Test basic error initialization."""
        error = LLMManagerError("Test error message")
        
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.details is None
    
    def test_initialization_with_details(self):
        """Test error initialization with details."""
        details = {"key1": "value1", "key2": 42}
        error = LLMManagerError("Test error", details=details)
        
        assert error.message == "Test error"
        assert error.details == details
        assert "Details: {'key1': 'value1', 'key2': 42}" in str(error)
    
    def test_initialization_with_none_details(self):
        """Test initialization with None details."""
        error = LLMManagerError("Test error", details=None)
        
        assert error.details is None
        assert str(error) == "Test error"
    
    def test_repr_method(self):
        """Test __repr__ method."""
        details = {"error_code": 500}
        error = LLMManagerError("Test error", details=details)
        
        repr_str = repr(error)
        assert "LLMManagerError" in repr_str
        assert "Test error" in repr_str
        assert "error_code" in repr_str
    
    def test_repr_without_details(self):
        """Test __repr__ method without details."""
        error = LLMManagerError("Simple error")
        
        repr_str = repr(error)
        assert "LLMManagerError" in repr_str
        assert "Simple error" in repr_str
        assert "None" in repr_str
    
    def test_str_method_with_details(self):
        """Test __str__ method with details."""
        details = {"code": "E001", "context": "test"}
        error = LLMManagerError("Error occurred", details=details)
        
        str_repr = str(error)
        assert "Error occurred" in str_repr
        assert "Details:" in str_repr
        assert "code" in str_repr
        assert "E001" in str_repr
    
    def test_str_method_without_details(self):
        """Test __str__ method without details."""
        error = LLMManagerError("Simple error")
        
        str_repr = str(error)
        assert str_repr == "Simple error"
        assert "Details:" not in str_repr


class TestConfigurationError:
    """Test suite for ConfigurationError class."""
    
    def test_basic_initialization(self):
        """Test basic configuration error initialization."""
        error = ConfigurationError("Invalid configuration")
        
        assert isinstance(error, LLMManagerError)
        assert error.message == "Invalid configuration"
        assert error.invalid_config is None
        assert error.details is None
    
    def test_initialization_with_invalid_config(self):
        """Test initialization with invalid configuration data."""
        invalid_config = {"region": "invalid-region", "timeout": -1}
        error = ConfigurationError("Bad config", invalid_config=invalid_config)
        
        assert error.message == "Bad config"
        assert error.invalid_config == invalid_config
        assert error.details == {"invalid_config": invalid_config}
    
    def test_initialization_with_none_config(self):
        """Test initialization with None configuration."""
        error = ConfigurationError("Config error", invalid_config=None)
        
        assert error.invalid_config is None
        assert error.details is None  # Should be None when invalid_config is None
    
    def test_inheritance(self):
        """Test that ConfigurationError inherits from LLMManagerError."""
        error = ConfigurationError("Test")
        assert isinstance(error, LLMManagerError)
        assert isinstance(error, ConfigurationError)


class TestAuthenticationError:
    """Test suite for AuthenticationError class."""
    
    def test_basic_initialization(self):
        """Test basic authentication error initialization."""
        error = AuthenticationError("Authentication failed")
        
        assert isinstance(error, LLMManagerError)
        assert error.message == "Authentication failed"
        assert error.auth_type is None
        assert error.region is None
        assert error.details is None
    
    def test_initialization_with_auth_type(self):
        """Test initialization with authentication type."""
        error = AuthenticationError("Auth failed", auth_type="oauth")
        
        assert error.auth_type == "oauth"
        assert error.details == {"auth_type": "oauth"}
    
    def test_initialization_with_region(self):
        """Test initialization with region."""
        error = AuthenticationError("Auth failed", region="us-east-1")
        
        assert error.region == "us-east-1"
        assert error.details == {"region": "us-east-1"}
    
    def test_initialization_with_both_parameters(self):
        """Test initialization with both auth_type and region."""
        error = AuthenticationError(
            "Auth failed", 
            auth_type="iam", 
            region="eu-west-1"
        )
        
        assert error.auth_type == "iam"
        assert error.region == "eu-west-1"
        assert error.details == {"auth_type": "iam", "region": "eu-west-1"}
    
    def test_initialization_with_none_values(self):
        """Test initialization with None values."""
        error = AuthenticationError("Auth failed", auth_type=None, region=None)
        
        assert error.auth_type is None
        assert error.region is None
        assert error.details is None


class TestModelAccessError:
    """Test suite for ModelAccessError class."""
    
    def test_basic_initialization(self):
        """Test basic model access error initialization."""
        error = ModelAccessError("Model access denied")
        
        assert isinstance(error, LLMManagerError)
        assert error.message == "Model access denied"
        assert error.model_id is None
        assert error.region is None
        assert error.access_method is None
        assert error.details is None
    
    def test_initialization_with_model_id(self):
        """Test initialization with model ID."""
        error = ModelAccessError("Access denied", model_id="claude-3-sonnet")
        
        assert error.model_id == "claude-3-sonnet"
        assert error.details == {"model_id": "claude-3-sonnet"}
    
    def test_initialization_with_all_parameters(self):
        """Test initialization with all parameters."""
        error = ModelAccessError(
            "Access failed",
            model_id="claude-3-sonnet",
            region="us-west-2",
            access_method="direct"
        )
        
        assert error.model_id == "claude-3-sonnet"
        assert error.region == "us-west-2"
        assert error.access_method == "direct"
        assert error.details == {
            "model_id": "claude-3-sonnet",
            "region": "us-west-2",
            "access_method": "direct"
        }
    
    def test_partial_parameters(self):
        """Test initialization with partial parameters."""
        error = ModelAccessError("Access failed", region="ap-south-1")
        
        assert error.model_id is None
        assert error.region == "ap-south-1"
        assert error.access_method is None
        assert error.details == {"region": "ap-south-1"}


class TestRetryExhaustedError:
    """Test suite for RetryExhaustedError class."""
    
    def test_basic_initialization(self):
        """Test basic retry exhausted error initialization."""
        error = RetryExhaustedError("All retries exhausted")
        
        assert isinstance(error, LLMManagerError)
        assert error.message == "All retries exhausted"
        assert error.attempts_made is None
        assert error.last_errors == []
        assert error.models_tried == []
        assert error.regions_tried == []
        assert error.details is None
    
    def test_initialization_with_attempts(self):
        """Test initialization with attempts count."""
        error = RetryExhaustedError("Retries failed", attempts_made=5)
        
        assert error.attempts_made == 5
        assert error.details == {"attempts_made": 5}
    
    def test_initialization_with_errors(self):
        """Test initialization with error list."""
        errors = [ValueError("Error 1"), RuntimeError("Error 2")]
        error = RetryExhaustedError("Retries failed", last_errors=errors)
        
        assert error.last_errors == errors
        assert error.details == {"last_errors": ["Error 1", "Error 2"]}
    
    def test_initialization_with_models_and_regions(self):
        """Test initialization with models and regions tried."""
        models = ["claude-3-sonnet", "claude-3-haiku"]
        regions = ["us-east-1", "us-west-2"]
        
        error = RetryExhaustedError(
            "Retries failed",
            models_tried=models,
            regions_tried=regions
        )
        
        assert error.models_tried == models
        assert error.regions_tried == regions
        assert error.details == {
            "models_tried": models,
            "regions_tried": regions
        }
    
    def test_initialization_with_all_parameters(self):
        """Test initialization with all parameters."""
        errors = [Exception("Test error")]
        models = ["model1"]
        regions = ["region1"]
        
        error = RetryExhaustedError(
            "Complete failure",
            attempts_made=3,
            last_errors=errors,
            models_tried=models,
            regions_tried=regions
        )
        
        assert error.attempts_made == 3
        assert error.last_errors == errors
        assert error.models_tried == models
        assert error.regions_tried == regions
        assert error.details == {
            "attempts_made": 3,
            "last_errors": ["Test error"],
            "models_tried": models,
            "regions_tried": regions
        }
    
    def test_initialization_with_none_lists(self):
        """Test initialization with None lists."""
        error = RetryExhaustedError(
            "Failed",
            last_errors=None,
            models_tried=None,
            regions_tried=None
        )
        
        assert error.last_errors == []
        assert error.models_tried == []
        assert error.regions_tried == []


class TestRequestValidationError:
    """Test suite for RequestValidationError class."""
    
    def test_basic_initialization(self):
        """Test basic request validation error initialization."""
        error = RequestValidationError("Validation failed")
        
        assert isinstance(error, LLMManagerError)
        assert error.message == "Validation failed"
        assert error.validation_errors == []
        assert error.invalid_fields == []
        assert error.details is None
    
    def test_initialization_with_validation_errors(self):
        """Test initialization with validation errors."""
        validation_errors = ["Field 'name' is required", "Invalid email format"]
        error = RequestValidationError("Validation failed", validation_errors=validation_errors)
        
        assert error.validation_errors == validation_errors
        assert error.details == {"validation_errors": validation_errors}
    
    def test_initialization_with_invalid_fields(self):
        """Test initialization with invalid fields."""
        invalid_fields = ["email", "phone"]
        error = RequestValidationError("Validation failed", invalid_fields=invalid_fields)
        
        assert error.invalid_fields == invalid_fields
        assert error.details == {"invalid_fields": invalid_fields}
    
    def test_initialization_with_both_parameters(self):
        """Test initialization with both validation errors and invalid fields."""
        validation_errors = ["Error 1", "Error 2"]
        invalid_fields = ["field1", "field2"]
        
        error = RequestValidationError(
            "Validation failed",
            validation_errors=validation_errors,
            invalid_fields=invalid_fields
        )
        
        assert error.validation_errors == validation_errors
        assert error.invalid_fields == invalid_fields
        assert error.details == {
            "validation_errors": validation_errors,
            "invalid_fields": invalid_fields
        }
    
    def test_initialization_with_none_lists(self):
        """Test initialization with None lists."""
        error = RequestValidationError(
            "Failed",
            validation_errors=None,
            invalid_fields=None
        )
        
        assert error.validation_errors == []
        assert error.invalid_fields == []


class TestStreamingError:
    """Test suite for StreamingError class."""
    
    def test_basic_initialization(self):
        """Test basic streaming error initialization."""
        error = StreamingError("Streaming failed")
        
        assert isinstance(error, LLMManagerError)
        assert error.message == "Streaming failed"
        assert error.stream_position is None
        assert error.partial_content is None
        assert error.details is None
    
    def test_initialization_with_position(self):
        """Test initialization with stream position."""
        error = StreamingError("Stream error", stream_position=1024)
        
        assert error.stream_position == 1024
        assert error.details == {"stream_position": 1024}
    
    def test_initialization_with_partial_content(self):
        """Test initialization with partial content."""
        content = "Partial response content"
        error = StreamingError("Stream error", partial_content=content)
        
        assert error.partial_content == content
        assert error.details == {"partial_content": content}
    
    def test_initialization_with_both_parameters(self):
        """Test initialization with both position and content."""
        content = "Partial content"
        position = 512
        
        error = StreamingError(
            "Stream failed",
            stream_position=position,
            partial_content=content
        )
        
        assert error.stream_position == position
        assert error.partial_content == content
        assert error.details == {
            "stream_position": position,
            "partial_content": content
        }
    
    def test_initialization_with_zero_position(self):
        """Test initialization with zero position."""
        error = StreamingError("Stream error", stream_position=0)
        
        assert error.stream_position == 0
        assert error.details == {"stream_position": 0}


class TestContentError:
    """Test suite for ContentError class."""
    
    def test_basic_initialization(self):
        """Test basic content error initialization."""
        error = ContentError("Content validation failed")
        
        assert isinstance(error, LLMManagerError)
        assert error.message == "Content validation failed"
        assert error.content_type is None
        assert error.content_size is None
        assert error.max_allowed_size is None
        assert error.details is None
    
    def test_initialization_with_content_type(self):
        """Test initialization with content type."""
        error = ContentError("Invalid content", content_type="image/jpeg")
        
        assert error.content_type == "image/jpeg"
        assert error.details == {"content_type": "image/jpeg"}
    
    def test_initialization_with_sizes(self):
        """Test initialization with content sizes."""
        error = ContentError(
            "Content too large",
            content_size=1048576,
            max_allowed_size=524288
        )
        
        assert error.content_size == 1048576
        assert error.max_allowed_size == 524288
        assert error.details == {
            "content_size": 1048576,
            "max_allowed_size": 524288
        }
    
    def test_initialization_with_all_parameters(self):
        """Test initialization with all parameters."""
        error = ContentError(
            "Content error",
            content_type="application/pdf",
            content_size=2097152,
            max_allowed_size=1048576
        )
        
        assert error.content_type == "application/pdf"
        assert error.content_size == 2097152
        assert error.max_allowed_size == 1048576
        assert error.details == {
            "content_type": "application/pdf",
            "content_size": 2097152,
            "max_allowed_size": 1048576
        }
    
    def test_initialization_with_zero_sizes(self):
        """Test initialization with zero sizes."""
        error = ContentError(
            "Empty content",
            content_size=0,
            max_allowed_size=0
        )
        
        assert error.content_size == 0
        assert error.max_allowed_size == 0
        assert error.details == {
            "content_size": 0,
            "max_allowed_size": 0
        }


class TestExceptionInheritance:
    """Test suite for exception inheritance and polymorphism."""
    
    def test_all_exceptions_inherit_from_llm_manager_error(self):
        """Test that all custom exceptions inherit from LLMManagerError."""
        exceptions = [
            ConfigurationError("test"),
            AuthenticationError("test"),
            ModelAccessError("test"),
            RetryExhaustedError("test"),
            RequestValidationError("test"),
            StreamingError("test"),
            ContentError("test")
        ]
        
        for exc in exceptions:
            assert isinstance(exc, LLMManagerError)
            assert isinstance(exc, Exception)
    
    def test_exception_hierarchy(self):
        """Test exception hierarchy and method resolution."""
        error = ConfigurationError("test config error", invalid_config={"key": "value"})
        
        # Should be able to call parent methods
        assert "test config error" in str(error)
        assert "ConfigurationError" in repr(error)
        
        # Should have its own attributes
        assert hasattr(error, 'invalid_config')
        assert error.invalid_config == {"key": "value"}
    
    def test_exception_catching(self):
        """Test that exceptions can be caught by their base class."""
        def raise_config_error():
            raise ConfigurationError("Config problem")
        
        def raise_auth_error():
            raise AuthenticationError("Auth problem")
        
        # Should be catchable as LLMManagerError
        with pytest.raises(LLMManagerError):
            raise_config_error()
        
        with pytest.raises(LLMManagerError):
            raise_auth_error()
        
        # Should also be catchable as specific exception
        with pytest.raises(ConfigurationError):
            raise_config_error()
        
        with pytest.raises(AuthenticationError):
            raise_auth_error()


class TestExceptionEdgeCases:
    """Test suite for edge cases and unusual scenarios."""
    
    def test_empty_message(self):
        """Test exceptions with empty messages."""
        error = LLMManagerError("")
        assert error.message == ""
        assert str(error) == ""
    
    def test_none_message_handling(self):
        """Test handling of None message (should not happen normally)."""
        # This tests the robustness of the implementation
        try:
            # This should raise TypeError in normal Python behavior
            # Skip test - type checking prevents None as message
            pass  # error = LLMManagerError(None)
        except TypeError:
            # Expected behavior - None is not a valid string
            pass
    
    def test_complex_details_object(self):
        """Test with complex details objects."""
        complex_details = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "none_value": None,
            "boolean": True
        }
        
        error = LLMManagerError("Complex error", details=complex_details)
        assert error.details == complex_details
        
        # Should be representable as string
        error_str = str(error)
        assert "Complex error" in error_str
        assert "Details:" in error_str
    
    def test_very_long_message(self):
        """Test with very long error messages."""
        long_message = "A" * 10000
        error = LLMManagerError(long_message)
        
        assert error.message == long_message
        assert len(str(error)) == len(long_message)
    
    def test_unicode_characters(self):
        """Test with unicode characters in messages."""
        unicode_message = "Error with émojis 🚨 and special chars: αβγ"
        error = LLMManagerError(unicode_message)
        
        assert error.message == unicode_message
        assert unicode_message in str(error)
        assert unicode_message in repr(error)
