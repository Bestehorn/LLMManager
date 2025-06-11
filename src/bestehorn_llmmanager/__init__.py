"""
Bestehorn LLMManager - AWS Bedrock Converse API Management Library

This package provides a comprehensive interface for managing AWS Bedrock LLM interactions
with support for multiple models, regions, authentication methods, and parallel processing.

Main Components:
    LLMManager: Primary interface for single AWS Bedrock requests
    ParallelLLMManager: Interface for parallel processing of multiple requests

Example Usage:
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

For detailed documentation, see the documentation in the docs/ directory.
"""

from .llm_manager import LLMManager
from .parallel_llm_manager import ParallelLLMManager

# Package metadata
__version__ = "1.0.0"
__author__ = "LLMManager Development Team"
__description__ = "AWS Bedrock Converse API Management Library"
__license__ = "MIT"

# Public API
__all__ = [
    "LLMManager",
    "ParallelLLMManager",
]
