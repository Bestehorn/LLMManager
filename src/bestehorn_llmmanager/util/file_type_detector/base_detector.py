"""
Base detector interface and data structures for file type detection.
Provides abstract interface and common data structures for detection implementations.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from ...message_builder_enums import DetectionMethodEnum


@dataclass(frozen=True)
class DetectionResult:
    """
    Immutable data class representing the result of file type detection.

    Attributes:
        detected_format: The detected file format (e.g., 'jpeg', 'pdf')
        confidence: Confidence level of the detection (0.0 to 1.0)
        detection_method: Method used for detection
        filename: Original filename (if provided)
        error_message: Error message if detection failed
        metadata: Additional metadata about the detection process
    """

    detected_format: str
    confidence: float
    detection_method: DetectionMethodEnum
    filename: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[dict] = None

    @property
    def is_successful(self) -> bool:
        """Check if detection was successful."""
        return self.error_message is None and self.confidence > 0.0

    @property
    def is_high_confidence(self) -> bool:
        """Check if detection has high confidence (>= 0.8)."""
        return self.confidence >= 0.8

    def __str__(self) -> str:
        """String representation of detection result."""
        status = "successful" if self.is_successful else "failed"
        return (
            f"DetectionResult({status}: {self.detected_format}, "
            f"confidence={self.confidence:.2f}, method={self.detection_method.value})"
        )


class BaseDetector(ABC):
    """
    Abstract base class for file type detectors.

    Defines the interface that all detector implementations must follow.
    Provides common logging and validation functionality.
    """

    def __init__(self) -> None:
        """Initialize the base detector with logging."""
        self._logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def detect_image_format(
        self, content: bytes, filename: Optional[str] = None
    ) -> DetectionResult:
        """
        Detect image format from content and/or filename.

        Args:
            content: Raw file content bytes
            filename: Optional filename for extension-based detection

        Returns:
            DetectionResult with format and confidence information
        """
        ...

    @abstractmethod
    def detect_document_format(
        self, content: bytes, filename: Optional[str] = None
    ) -> DetectionResult:
        """
        Detect document format from content and/or filename.

        Args:
            content: Raw file content bytes
            filename: Optional filename for extension-based detection

        Returns:
            DetectionResult with format and confidence information
        """
        ...

    @abstractmethod
    def detect_video_format(
        self, content: bytes, filename: Optional[str] = None
    ) -> DetectionResult:
        """
        Detect video format from content and/or filename.

        Args:
            content: Raw file content bytes
            filename: Optional filename for extension-based detection

        Returns:
            DetectionResult with format and confidence information
        """
        ...

    def _validate_content(self, content: object) -> bool:
        """
        Validate that content is suitable for detection.

        Args:
            content: Raw file content bytes

        Returns:
            True if content is valid for detection
        """
        if not isinstance(content, bytes):
            self._logger.error("Content must be bytes, got %s", type(content).__name__)
            return False

        if len(content) == 0:
            self._logger.error("Content cannot be empty")
            return False

        return True

    def _get_safe_filename(self, filename: Optional[str]) -> str:
        """
        Get a safe filename for logging purposes.

        Args:
            filename: Optional filename

        Returns:
            Safe filename string for logging
        """
        return filename if filename else "unnamed_file"

    def _create_error_result(
        self,
        error_message: str,
        filename: Optional[str] = None,
        detection_method: DetectionMethodEnum = DetectionMethodEnum.MANUAL,
    ) -> DetectionResult:
        """
        Create a DetectionResult for error cases.

        Args:
            error_message: Error description
            filename: Optional filename
            detection_method: Detection method that failed

        Returns:
            DetectionResult indicating failure
        """
        return DetectionResult(
            detected_format="unknown",
            confidence=0.0,
            detection_method=detection_method,
            filename=filename,
            error_message=error_message,
        )

    def _create_success_result(
        self,
        detected_format: str,
        confidence: float,
        detection_method: DetectionMethodEnum,
        filename: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> DetectionResult:
        """
        Create a DetectionResult for successful detection.

        Args:
            detected_format: The detected format
            confidence: Confidence level (0.0 to 1.0)
            detection_method: Method used for detection
            filename: Optional filename
            metadata: Optional metadata dictionary

        Returns:
            DetectionResult indicating success
        """
        return DetectionResult(
            detected_format=detected_format,
            confidence=confidence,
            detection_method=detection_method,
            filename=filename,
            metadata=metadata,
        )
