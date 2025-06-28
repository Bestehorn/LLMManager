"""
Constants for the ConverseMessageBuilder system.
Contains string constants and configuration values for message building operations.
"""

from typing import Dict, Final, List


class MessageBuilderFields:
    """JSON field constants for message builder operations."""

    # Internal builder fields
    ROLE: Final[str] = "role"
    CONTENT_BLOCKS: Final[str] = "content_blocks"
    FILENAME: Final[str] = "filename"
    DETECTED_FORMAT: Final[str] = "detected_format"
    DETECTION_METHOD: Final[str] = "detection_method"
    CONFIDENCE: Final[str] = "confidence"


class MessageBuilderConfig:
    """Configuration constants for message builder operations."""

    # Default values
    DEFAULT_DETECTION_CONFIDENCE: Final[float] = 0.95
    MIN_DETECTION_CONFIDENCE: Final[float] = 0.5
    MAX_CONTENT_BLOCKS_PER_MESSAGE: Final[int] = 100

    # File size limits (in bytes)
    MAX_IMAGE_SIZE_BYTES: Final[int] = 3_750_000  # 3.75 MB
    MAX_DOCUMENT_SIZE_BYTES: Final[int] = 4_500_000  # 4.5 MB
    MAX_VIDEO_SIZE_BYTES: Final[int] = 100_000_000  # 100 MB

    # Detection settings
    MAGIC_BYTES_READ_SIZE: Final[int] = 32  # Bytes to read for magic byte detection
    EXTENSION_DETECTION_ENABLED: Final[bool] = True
    CONTENT_DETECTION_ENABLED: Final[bool] = True


class MessageBuilderLogMessages:
    """Logging message constants for message builder operations."""

    # Auto-detection messages
    AUTO_DETECTION_SUCCESS: Final[str] = (
        "Auto-detected file type for '{filename}': {detected_type} (method: {method}, confidence: {confidence:.2f})"
    )
    AUTO_DETECTION_FALLBACK: Final[str] = (
        "Using fallback detection for '{filename}': {detected_type} (confidence: {confidence:.2f})"
    )
    DETECTION_MISMATCH: Final[str] = (
        "Format mismatch for '{filename}': extension suggests {ext_type}, content suggests {content_type}, using {final_type}"
    )
    DETECTION_LOW_CONFIDENCE: Final[str] = (
        "Low confidence detection for '{filename}': {detected_type} (confidence: {confidence:.2f})"
    )

    # Builder messages
    MESSAGE_BUILD_STARTED: Final[str] = (
        "Building message with role '{role}' and {block_count} content blocks"
    )
    MESSAGE_BUILD_COMPLETED: Final[str] = (
        "Message built successfully with {block_count} content blocks"
    )
    CONTENT_BLOCK_ADDED: Final[str] = "Added {content_type} content block (size: {size} bytes)"

    # Validation messages
    CONTENT_SIZE_WARNING: Final[str] = (
        "Content size ({size} bytes) approaching limit ({limit} bytes) for {content_type}"
    )
    CONTENT_BLOCK_LIMIT_WARNING: Final[str] = (
        "Content block count ({count}) approaching limit ({limit})"
    )


class MessageBuilderErrorMessages:
    """Error message constants for message builder operations."""

    # Configuration errors
    INVALID_ROLE: Final[str] = "Invalid role specified: {role}. Must be one of: {valid_roles}"
    EMPTY_CONTENT: Final[str] = "Content cannot be empty for {content_type}"
    INVALID_FORMAT: Final[str] = (
        "Invalid {content_type} format: {format}. Supported formats: {supported_formats}"
    )

    # Size limit errors
    CONTENT_SIZE_EXCEEDED: Final[str] = (
        "Content size ({size} bytes) exceeds limit ({limit} bytes) for {content_type}"
    )
    CONTENT_BLOCK_LIMIT_EXCEEDED: Final[str] = (
        "Cannot add more content blocks. Maximum allowed: {limit}"
    )

    # Detection errors
    DETECTION_FAILED: Final[str] = "Failed to detect file type for {filename}: {error}"
    UNSUPPORTED_FORMAT: Final[str] = "Unsupported {content_type} format detected: {format}"
    DETECTION_CONFIDENCE_LOW: Final[str] = (
        "Detection confidence too low ({confidence:.2f}) for {filename}. Minimum required: {min_confidence:.2f}"
    )

    # Build errors
    BUILD_VALIDATION_FAILED: Final[str] = "Message build validation failed: {errors}"
    NO_CONTENT_BLOCKS: Final[str] = "Cannot build message without content blocks"


class SupportedFormats:
    """Lists of supported formats for validation purposes."""

    IMAGE_FORMATS: Final[List[str]] = ["jpeg", "png", "gi", "webp"]
    DOCUMENT_FORMATS: Final[List[str]] = [
        "pd",
        "csv",
        "doc",
        "docx",
        "xls",
        "xlsx",
        "html",
        "txt",
        "md",
    ]
    VIDEO_FORMATS: Final[List[str]] = ["mp4", "mov", "avi", "webm", "mkv"]

    @classmethod
    def get_all_supported_formats(cls) -> Dict[str, List[str]]:
        """Get all supported formats organized by content type."""
        return {
            "image": cls.IMAGE_FORMATS,
            "document": cls.DOCUMENT_FORMATS,
            "video": cls.VIDEO_FORMATS,
        }
