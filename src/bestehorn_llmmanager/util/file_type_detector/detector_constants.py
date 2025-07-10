"""
Constants for file type detection operations.
Contains magic bytes, file extensions, and other detection-related constants.
"""

from typing import Dict, Final, List, Set


class MagicBytesConstants:
    """Magic byte signatures for different file formats."""

    # Image format magic bytes
    JPEG_SIGNATURES: Final[List[bytes]] = [
        b"\xff\xd8\xff\xe0",  # JPEG/JFIF
        b"\xff\xd8\xff\xe1",  # JPEG/EXIF
        b"\xff\xd8\xff\xdb",  # JPEG raw
    ]

    PNG_SIGNATURE: Final[bytes] = b"\x89PNG\r\n\x1a\n"

    GIF_SIGNATURES: Final[List[bytes]] = [b"GIF87a", b"GIF89a"]

    WEBP_SIGNATURE: Final[bytes] = b"RIFF"
    WEBP_FORMAT_SIGNATURE: Final[bytes] = b"WEBP"

    # Document format magic bytes
    PDF_SIGNATURE: Final[bytes] = b"%PDF-"

    # Microsoft Office formats (ZIP-based)
    ZIP_SIGNATURE: Final[bytes] = b"PK\x03\x04"
    DOCX_CONTENT_TYPES: Final[bytes] = b"[Content_Types].xml"
    XLSX_CONTENT_TYPES: Final[bytes] = b"xl/"

    # Legacy Microsoft Office formats
    DOC_SIGNATURE: Final[bytes] = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    XLS_SIGNATURE: Final[bytes] = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

    # Text formats
    HTML_SIGNATURES: Final[List[bytes]] = [b"<!DOCTYPE html", b"<!doctype html", b"<html", b"<HTML"]

    # Video format magic bytes
    MP4_SIGNATURES: Final[List[bytes]] = [
        b"\x00\x00\x00\x18ftypmp4",
        b"\x00\x00\x00\x20ftypmp4",
        b"\x00\x00\x00\x1cftypmp4",
    ]

    MOV_SIGNATURE: Final[bytes] = b"\x00\x00\x00\x14ftypqt"
    AVI_SIGNATURE: Final[bytes] = b"RIFF"
    AVI_FORMAT_SIGNATURE: Final[bytes] = b"AVI "
    WEBM_SIGNATURE: Final[bytes] = b"\x1a\x45\xdf\xa3"
    MKV_SIGNATURE: Final[bytes] = b"\x1a\x45\xdf\xa3"


class FileExtensionConstants:
    """File extension mappings for different content types."""

    IMAGE_EXTENSIONS: Final[Dict[str, str]] = {
        ".jpg": "jpeg",
        ".jpeg": "jpeg",
        ".png": "png",
        ".gif": "gif",
        ".webp": "webp",
    }

    DOCUMENT_EXTENSIONS: Final[Dict[str, str]] = {
        ".pdf": "pdf",
        ".doc": "doc",
        ".docx": "docx",
        ".xls": "xls",
        ".xlsx": "xlsx",
        ".csv": "csv",
        ".txt": "txt",
        ".html": "html",
        ".htm": "html",
        ".md": "md",
        ".markdown": "md",
    }

    VIDEO_EXTENSIONS: Final[Dict[str, str]] = {
        ".mp4": "mp4",
        ".mov": "mov",
        ".avi": "avi",
        ".webm": "webm",
        ".mkv": "mkv",
    }

    @classmethod
    def get_all_extensions(cls) -> Set[str]:
        """Get all supported file extensions."""
        all_extensions: Set[str] = set()
        all_extensions.update(cls.IMAGE_EXTENSIONS.keys())
        all_extensions.update(cls.DOCUMENT_EXTENSIONS.keys())
        all_extensions.update(cls.VIDEO_EXTENSIONS.keys())
        return all_extensions


class DetectionConstants:
    """Constants for detection operations and thresholds."""

    # Detection confidence levels
    HIGH_CONFIDENCE: Final[float] = 0.95
    MEDIUM_CONFIDENCE: Final[float] = 0.75
    LOW_CONFIDENCE: Final[float] = 0.50
    MIN_ACCEPTABLE_CONFIDENCE: Final[float] = 0.30

    # Magic bytes reading configuration
    MAGIC_BYTES_READ_SIZE: Final[int] = 64
    ZIP_HEADER_READ_SIZE: Final[int] = 1024  # For Office format detection

    # Content type priorities (higher = more reliable)
    CONTENT_TYPE_PRIORITIES: Final[Dict[str, int]] = {
        "content": 10,  # Magic bytes detection
        "extension": 5,  # File extension detection
        "fallback": 1,  # Default/fallback detection
    }


class DetectorLogMessages:
    """Logging message constants for detector operations."""

    # Detection process messages
    DETECTION_STARTED: Final[str] = "Starting file type detection for '{filename}'"
    DETECTION_COMPLETED: Final[str] = (
        "Detection completed for '{filename}': {format} (method: {method}, confidence: {confidence:.2f})"
    )

    # Method-specific messages
    EXTENSION_DETECTION: Final[str] = (
        "Extension detection for '{filename}': {extension} -> {format}"
    )
    CONTENT_DETECTION: Final[str] = "Content detection for '{filename}': found {format} signature"
    MAGIC_BYTES_READ: Final[str] = "Read {bytes_count} magic bytes for '{filename}'"

    # Validation messages
    FORMAT_MISMATCH: Final[str] = (
        "Format mismatch for '{filename}': extension={ext_format}, content={content_format}"
    )
    CONFIDENCE_ADJUSTMENT: Final[str] = (
        "Confidence adjusted for '{filename}': {old_confidence:.2f} -> {new_confidence:.2f} (reason: {reason})"
    )

    # Fallback messages
    FALLBACK_DETECTION: Final[str] = "Using fallback detection for '{filename}': {reason}"
    UNSUPPORTED_EXTENSION: Final[str] = "Unsupported extension '{extension}' for '{filename}'"


class DetectorErrorMessages:
    """Error message constants for detector operations."""

    # Content reading errors
    CONTENT_READ_ERROR: Final[str] = "Failed to read content for detection: {error}"
    INSUFFICIENT_CONTENT: Final[str] = (
        "Insufficient content for magic byte detection (got {size} bytes, need {required})"
    )

    # Detection failures
    NO_SIGNATURE_MATCH: Final[str] = "No magic byte signature matched for content"
    UNSUPPORTED_FORMAT: Final[str] = (
        "Detected format '{format}' is not supported for {content_type}"
    )
    DETECTION_FAILED: Final[str] = "All detection methods failed for '{filename}'"

    # Validation errors
    INVALID_CONTENT_TYPE: Final[str] = "Invalid content type specified: {content_type}"
    CONFIDENCE_TOO_LOW: Final[str] = (
        "Detection confidence ({confidence:.2f}) below minimum threshold ({min_threshold:.2f})"
    )
