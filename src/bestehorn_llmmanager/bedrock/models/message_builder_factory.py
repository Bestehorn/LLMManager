"""
Factory functions for creating ConverseMessageBuilder instances.
Provides convenient factory methods for message creation.
"""

from .converse_message_builder import ConverseMessageBuilder
from .message_builder_enums import RolesEnum


def create_message(role: RolesEnum) -> ConverseMessageBuilder:
    """
    Factory function to create a new ConverseMessageBuilder instance.
    
    This is the main entry point for building Converse API messages using
    the fluent interface pattern.
    
    Args:
        role: The role for the message (RolesEnum.USER or RolesEnum.ASSISTANT)
        
    Returns:
        ConverseMessageBuilder instance ready for method chaining
        
    Raises:
        RequestValidationError: If role is invalid
        
    Example:
        Basic text message:
        >>> message = create_message(role=RolesEnum.USER)\\
        ...     .add_text(text="Hello, how are you?")\\
        ...     .build()
        
        Multi-modal message with auto-detection:
        >>> message = create_message(role=RolesEnum.USER)\\
        ...     .add_text(text="Please analyze this image")\\
        ...     .add_image_bytes(bytes=image_data, filename="photo.jpg")\\
        ...     .add_document_bytes(bytes=pdf_data, filename="report.pdf")\\
        ...     .build()
        
        Message with explicit formats:
        >>> from .message_builder_enums import ImageFormatEnum, DocumentFormatEnum
        >>> message = create_message(role=RolesEnum.USER)\\
        ...     .add_text(text="Analyze these files")\\
        ...     .add_image_bytes(bytes=image_data, format=ImageFormatEnum.JPEG)\\
        ...     .add_document_bytes(bytes=pdf_data, format=DocumentFormatEnum.PDF)\\
        ...     .build()
    """
    return ConverseMessageBuilder(role=role)


def create_user_message() -> ConverseMessageBuilder:
    """
    Convenience factory function to create a user message builder.
    
    Equivalent to create_message(role=RolesEnum.USER).
    
    Returns:
        ConverseMessageBuilder instance with USER role
        
    Example:
        >>> message = create_user_message()\\
        ...     .add_text(text="What's the weather like?")\\
        ...     .build()
    """
    return create_message(role=RolesEnum.USER)


def create_assistant_message() -> ConverseMessageBuilder:
    """
    Convenience factory function to create an assistant message builder.
    
    Equivalent to create_message(role=RolesEnum.ASSISTANT).
    
    Returns:
        ConverseMessageBuilder instance with ASSISTANT role
        
    Example:
        >>> message = create_assistant_message()\\
        ...     .add_text(text="The weather is sunny and warm.")\\
        ...     .build()
    """
    return create_message(role=RolesEnum.ASSISTANT)
