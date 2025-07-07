"""
Bestehorn LLMManager - AWS Bedrock Converse API Management Library

This package provides a comprehensive interface for managing AWS Bedrock LLM interactions
with support for multiple models, regions, authentication methods, parallel processing,
and fluent message building with automatic format detection.

Main Components:
    LLMManager: Primary interface for single AWS Bedrock requests
    ParallelLLMManager: Interface for parallel processing of multiple requests
    MessageBuilder: Fluent interface for building multi-modal messages

Example Usage:
    Basic LLM usage:
    >>> from bestehorn_llmmanager import LLMManager
    >>>
    >>> manager = LLMManager(
    ...     models=["Claude 3 Haiku", "Claude 3 Sonnet"],
    ...     regions=["us-east-1", "us-west-2"]
    ... )
    >>> response = manager.converse(
    ...     messages=[{"role": "user", "content": [{"text": "Hello!"}]}]
    ... )
    >>> print(response.get_content())

    MessageBuilder usage:
    >>> from bestehorn_llmmanager import MessageBuilder, create_user_message
    >>>
    >>> message = create_user_message()
    ...     .add_text("Analyze this image:")
    ...     .add_local_image("photo.jpg")
    ...     .build()
    >>> response = manager.converse(messages=[message])

For detailed documentation, see the documentation in the docs/ directory.
"""

# Package metadata
from .llm_manager import LLMManager

# MessageBuilder - Direct imports for easy access
from .message_builder import ConverseMessageBuilder as MessageBuilder
from .message_builder import (
    create_assistant_message,
    create_message,
    create_user_message,
)
from .message_builder_enums import (
    DetectionMethodEnum,
    DocumentFormatEnum,
    ImageFormatEnum,
    RolesEnum,
    VideoFormatEnum,
)
from .parallel_llm_manager import ParallelLLMManager

__author__ = "LLMManager Development Team"
__description__ = "AWS Bedrock Converse API Management Library with MessageBuilder"
__license__ = "MIT"

# Version management with setuptools-scm
try:
    from ._version import __version__
except ImportError:
    # Fallback for development/editable installs
    try:
        from importlib.metadata import version
        __version__ = version("bestehorn-llmmanager")
    except Exception:
        __version__ = "dev"

# Public API
__all__ = [
    # Core classes
    "LLMManager",
    "ParallelLLMManager",
    # MessageBuilder components
    "MessageBuilder",
    "create_message",
    "create_user_message",
    "create_assistant_message",
    # Enums
    "RolesEnum",
    "ImageFormatEnum",
    "DocumentFormatEnum",
    "VideoFormatEnum",
    "DetectionMethodEnum",
]
