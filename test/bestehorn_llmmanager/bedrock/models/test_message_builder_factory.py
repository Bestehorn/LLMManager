"""
Unit tests for message builder factory functions.
Tests the factory functions for creating ConverseMessageBuilder instances.
"""

import pytest

from src.bedrock.models.message_builder_factory import (
    create_message, create_user_message, create_assistant_message
)
from src.bedrock.models.converse_message_builder import ConverseMessageBuilder
from src.bedrock.models.message_builder_enums import RolesEnum
from src.bedrock.exceptions.llm_manager_exceptions import RequestValidationError


class TestCreateMessage:
    """Test cases for create_message factory function."""
    
    def test_create_message_with_user_role(self):
        """Test creating message with USER role."""
        builder = create_message(role=RolesEnum.USER)
        
        assert isinstance(builder, ConverseMessageBuilder)
        assert builder.role == RolesEnum.USER
        assert builder.content_block_count == 0
    
    def test_create_message_with_assistant_role(self):
        """Test creating message with ASSISTANT role."""
        builder = create_message(role=RolesEnum.ASSISTANT)
        
        assert isinstance(builder, ConverseMessageBuilder)
        assert builder.role == RolesEnum.ASSISTANT
        assert builder.content_block_count == 0
    
    def test_create_message_with_invalid_role(self):
        """Test creating message with invalid role raises error."""
        with pytest.raises(RequestValidationError):
            create_message(role="invalid_role")  # type: ignore
    
    def test_create_message_returns_fluent_interface(self):
        """Test that created message supports fluent interface."""
        builder = create_message(role=RolesEnum.USER)
        
        result = builder.add_text(text="Hello world!")
        
        assert result is builder
        assert builder.content_block_count == 1
    
    def test_create_message_can_build_complete_message(self):
        """Test that created message can build complete message."""
        message = create_message(role=RolesEnum.USER)\
            .add_text(text="Test message")\
            .build()
        
        assert isinstance(message, dict)
        assert message["role"] == "user"
        assert len(message["content"]) == 1
        assert message["content"][0]["text"] == "Test message"


class TestCreateUserMessage:
    """Test cases for create_user_message convenience function."""
    
    def test_create_user_message(self):
        """Test creating user message."""
        builder = create_user_message()
        
        assert isinstance(builder, ConverseMessageBuilder)
        assert builder.role == RolesEnum.USER
        assert builder.content_block_count == 0
    
    def test_create_user_message_equivalence(self):
        """Test that create_user_message is equivalent to create_message with USER role."""
        user_builder1 = create_user_message()
        user_builder2 = create_message(role=RolesEnum.USER)
        
        assert user_builder1.role == user_builder2.role
        assert type(user_builder1) == type(user_builder2)
    
    def test_create_user_message_fluent_interface(self):
        """Test fluent interface with create_user_message."""
        message = create_user_message()\
            .add_text(text="Hello from user!")\
            .build()
        
        assert message["role"] == "user"
        assert message["content"][0]["text"] == "Hello from user!"


class TestCreateAssistantMessage:
    """Test cases for create_assistant_message convenience function."""
    
    def test_create_assistant_message(self):
        """Test creating assistant message."""
        builder = create_assistant_message()
        
        assert isinstance(builder, ConverseMessageBuilder)
        assert builder.role == RolesEnum.ASSISTANT
        assert builder.content_block_count == 0
    
    def test_create_assistant_message_equivalence(self):
        """Test that create_assistant_message is equivalent to create_message with ASSISTANT role."""
        assistant_builder1 = create_assistant_message()
        assistant_builder2 = create_message(role=RolesEnum.ASSISTANT)
        
        assert assistant_builder1.role == assistant_builder2.role
        assert type(assistant_builder1) == type(assistant_builder2)
    
    def test_create_assistant_message_fluent_interface(self):
        """Test fluent interface with create_assistant_message."""
        message = create_assistant_message()\
            .add_text(text="Hello from assistant!")\
            .build()
        
        assert message["role"] == "assistant"
        assert message["content"][0]["text"] == "Hello from assistant!"


class TestFactoryFunctionIntegration:
    """Test integration between factory functions and message building."""
    
    def test_multiple_messages_creation(self):
        """Test creating multiple messages with different factory functions."""
        user_message = create_user_message()\
            .add_text(text="What's the weather like?")\
            .build()
        
        assistant_message = create_assistant_message()\
            .add_text(text="The weather is sunny and warm.")\
            .build()
        
        # Verify both messages are correctly formatted
        assert user_message["role"] == "user"
        assert assistant_message["role"] == "assistant"
        
        assert user_message["content"][0]["text"] == "What's the weather like?"
        assert assistant_message["content"][0]["text"] == "The weather is sunny and warm."
    
    def test_complex_message_with_factory(self):
        """Test creating complex multi-modal message using factory."""
        image_data = b'\xFF\xD8\xFF\xE0'  # JPEG header
        
        message = create_user_message()\
            .add_text(text="Please analyze this image:")\
            .add_image_bytes(bytes=image_data, format=None, filename="photo.jpg")\
            .add_text(text="What do you see?")\
            .build()
        
        assert len(message["content"]) == 3
        assert message["content"][0]["text"] == "Please analyze this image:"
        assert message["content"][2]["text"] == "What do you see?"
        assert "image" in message["content"][1]
    
    def test_factory_functions_return_independent_builders(self):
        """Test that factory functions return independent builder instances."""
        builder1 = create_user_message()
        builder2 = create_user_message()
        
        # Should be different instances
        assert builder1 is not builder2
        
        # Modifications to one shouldn't affect the other
        builder1.add_text(text="Message 1")
        builder2.add_text(text="Message 2")
        
        assert builder1.content_block_count == 1
        assert builder2.content_block_count == 1
        
        message1 = builder1.build()
        message2 = builder2.build()
        
        assert message1["content"][0]["text"] == "Message 1"
        assert message2["content"][0]["text"] == "Message 2"


class TestFactoryDocumentation:
    """Test that factory functions work as documented in docstrings."""
    
    def test_docstring_examples_work(self):
        """Test that examples from docstrings actually work."""
        # Example from create_message docstring
        message = create_message(role=RolesEnum.USER)\
            .add_text(text="Hello, how are you?")\
            .build()
        
        assert message["role"] == "user"
        assert message["content"][0]["text"] == "Hello, how are you?"
        
        # Example from create_user_message docstring  
        message = create_user_message()\
            .add_text(text="What's the weather like?")\
            .build()
        
        assert message["role"] == "user"
        assert message["content"][0]["text"] == "What's the weather like?"
        
        # Example from create_assistant_message docstring
        message = create_assistant_message()\
            .add_text(text="The weather is sunny and warm.")\
            .build()
        
        assert message["role"] == "assistant"
        assert message["content"][0]["text"] == "The weather is sunny and warm."


class TestFactoryErrorHandling:
    """Test error handling in factory functions."""
    
    def test_factory_preserves_validation_errors(self):
        """Test that factory functions preserve validation errors from builder."""
        # Test that validation errors are still raised properly
        builder = create_user_message()
        
        with pytest.raises(RequestValidationError):
            builder.add_text(text="")  # Empty text should raise error
        
        with pytest.raises(RequestValidationError):
            builder.build()  # Building without content should raise error
    
    def test_factory_with_chained_operations_error(self):
        """Test error handling in chained operations from factory."""
        with pytest.raises(RequestValidationError):
            create_user_message()\
                .add_text(text="Valid text")\
                .add_image_bytes(bytes=b"")\
                .build()  # Empty image bytes should raise error
