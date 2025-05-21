"""
Content type definitions for multimodal content in Bedrock Converse API.
"""
from enum import Enum

class ContentType(Enum):
    """Enum representing the different content types supported by the Converse API."""
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    VIDEO = "video"

class SourceType(Enum):
    """Enum representing the different source types for content."""
    BYTES = "bytes"
    S3 = "s3"
    URI = "uri"
