"""
Main file type detector implementation.
Provides comprehensive file type detection using multiple strategies.
"""

import logging
from pathlib import Path
from typing import Optional

from ...message_builder_constants import SupportedFormats
from ...message_builder_enums import DetectionMethodEnum
from .base_detector import BaseDetector, DetectionResult
from .detector_constants import (
    DetectionConstants,
    DetectorErrorMessages,
    DetectorLogMessages,
    FileExtensionConstants,
    MagicBytesConstants,
)


class FileTypeDetector(BaseDetector):
    """
    Main file type detector implementation.

    Uses a combination of extension-based and content-based detection
    to provide accurate file type identification with confidence scoring.
    """

    def __init__(self) -> None:
        """Initialize the file type detector."""
        super().__init__()
        self._logger = logging.getLogger(__name__)

    def detect_image_format(
        self, content: bytes, filename: Optional[str] = None
    ) -> DetectionResult:
        """
        Detect image format using combined detection strategies.

        Args:
            content: Raw image content bytes
            filename: Optional filename for extension-based detection

        Returns:
            DetectionResult with detected format and confidence
        """
        safe_filename = self._get_safe_filename(filename=filename)

        if not self._validate_content(content=content):
            return self._create_error_result(
                error_message=DetectorErrorMessages.CONTENT_READ_ERROR.format(
                    error="Invalid content"
                ),
                filename=filename,
                detection_method=DetectionMethodEnum.CONTENT,
            )

        self._logger.debug(DetectorLogMessages.DETECTION_STARTED.format(filename=safe_filename))

        # Try extension detection first (fast)
        extension_result = self._detect_by_extension(
            filename=filename,
            supported_formats=SupportedFormats.IMAGE_FORMATS,
            extension_map=FileExtensionConstants.IMAGE_EXTENSIONS,
        )

        # Try content detection (accurate)
        content_result = self._detect_image_by_content(content=content, filename=filename)

        # Combine results
        final_result = self._combine_detection_results(
            extension_result=extension_result, content_result=content_result, filename=filename
        )

        self._logger.info(
            DetectorLogMessages.DETECTION_COMPLETED.format(
                filename=safe_filename,
                format=final_result.detected_format,
                method=final_result.detection_method.value,
                confidence=final_result.confidence,
            )
        )

        return final_result

    def detect_document_format(
        self, content: bytes, filename: Optional[str] = None
    ) -> DetectionResult:
        """
        Detect document format using combined detection strategies.

        Args:
            content: Raw document content bytes
            filename: Optional filename for extension-based detection

        Returns:
            DetectionResult with detected format and confidence
        """
        safe_filename = self._get_safe_filename(filename=filename)

        if not self._validate_content(content=content):
            return self._create_error_result(
                error_message=DetectorErrorMessages.CONTENT_READ_ERROR.format(
                    error="Invalid content"
                ),
                filename=filename,
                detection_method=DetectionMethodEnum.CONTENT,
            )

        self._logger.debug(DetectorLogMessages.DETECTION_STARTED.format(filename=safe_filename))

        # Try extension detection first
        extension_result = self._detect_by_extension(
            filename=filename,
            supported_formats=SupportedFormats.DOCUMENT_FORMATS,
            extension_map=FileExtensionConstants.DOCUMENT_EXTENSIONS,
        )

        # Try content detection
        content_result = self._detect_document_by_content(content=content, filename=filename)

        # Combine results
        final_result = self._combine_detection_results(
            extension_result=extension_result, content_result=content_result, filename=filename
        )

        self._logger.info(
            DetectorLogMessages.DETECTION_COMPLETED.format(
                filename=safe_filename,
                format=final_result.detected_format,
                method=final_result.detection_method.value,
                confidence=final_result.confidence,
            )
        )

        return final_result

    def detect_video_format(
        self, content: bytes, filename: Optional[str] = None
    ) -> DetectionResult:
        """
        Detect video format using combined detection strategies.

        Args:
            content: Raw video content bytes
            filename: Optional filename for extension-based detection

        Returns:
            DetectionResult with detected format and confidence
        """
        safe_filename = self._get_safe_filename(filename=filename)

        if not self._validate_content(content=content):
            return self._create_error_result(
                error_message=DetectorErrorMessages.CONTENT_READ_ERROR.format(
                    error="Invalid content"
                ),
                filename=filename,
                detection_method=DetectionMethodEnum.CONTENT,
            )

        self._logger.debug(DetectorLogMessages.DETECTION_STARTED.format(filename=safe_filename))

        # Try extension detection first
        extension_result = self._detect_by_extension(
            filename=filename,
            supported_formats=SupportedFormats.VIDEO_FORMATS,
            extension_map=FileExtensionConstants.VIDEO_EXTENSIONS,
        )

        # Try content detection
        content_result = self._detect_video_by_content(content=content, filename=filename)

        # Combine results
        final_result = self._combine_detection_results(
            extension_result=extension_result, content_result=content_result, filename=filename
        )

        self._logger.info(
            DetectorLogMessages.DETECTION_COMPLETED.format(
                filename=safe_filename,
                format=final_result.detected_format,
                method=final_result.detection_method.value,
                confidence=final_result.confidence,
            )
        )

        return final_result

    def _detect_by_extension(
        self, filename: Optional[str], supported_formats: list, extension_map: dict
    ) -> Optional[DetectionResult]:
        """
        Detect format based on file extension.

        Args:
            filename: Optional filename
            supported_formats: List of supported formats
            extension_map: Dictionary mapping extensions to formats

        Returns:
            DetectionResult if extension is recognized, None otherwise
        """
        if not filename:
            return None

        file_path = Path(filename)
        extension = file_path.suffix.lower()

        if not extension:
            return None

        safe_filename = self._get_safe_filename(filename=filename)

        if extension in extension_map:
            detected_format = extension_map[extension]

            if detected_format in supported_formats:
                self._logger.debug(
                    DetectorLogMessages.EXTENSION_DETECTION.format(
                        filename=safe_filename, extension=extension, format=detected_format
                    )
                )

                return self._create_success_result(
                    detected_format=detected_format,
                    confidence=DetectionConstants.MEDIUM_CONFIDENCE,
                    detection_method=DetectionMethodEnum.EXTENSION,
                    filename=filename,
                    metadata={"extension": extension},
                )
            else:
                self._logger.warning(
                    DetectorErrorMessages.UNSUPPORTED_FORMAT.format(
                        format=detected_format, content_type="extension"
                    )
                )
        else:
            self._logger.debug(
                DetectorLogMessages.UNSUPPORTED_EXTENSION.format(
                    extension=extension, filename=safe_filename
                )
            )

        return None

    def _detect_image_by_content(
        self, content: bytes, filename: Optional[str] = None
    ) -> Optional[DetectionResult]:
        """
        Detect image format by analyzing content magic bytes.

        Args:
            content: Raw image content bytes
            filename: Optional filename for logging

        Returns:
            DetectionResult if format is detected, None otherwise
        """
        if len(content) < 8:  # Minimum bytes needed for image detection
            return None

        safe_filename = self._get_safe_filename(filename=filename)
        header = content[: DetectionConstants.MAGIC_BYTES_READ_SIZE]

        # Check JPEG signatures
        for jpeg_sig in MagicBytesConstants.JPEG_SIGNATURES:
            if header.startswith(jpeg_sig):
                self._logger.debug(
                    DetectorLogMessages.CONTENT_DETECTION.format(
                        filename=safe_filename, format="jpeg"
                    )
                )
                return self._create_success_result(
                    detected_format="jpeg",
                    confidence=DetectionConstants.HIGH_CONFIDENCE,
                    detection_method=DetectionMethodEnum.CONTENT,
                    filename=filename,
                    metadata={"magic_bytes": jpeg_sig.hex()},
                )

        # Check PNG signature
        if header.startswith(MagicBytesConstants.PNG_SIGNATURE):
            self._logger.debug(
                DetectorLogMessages.CONTENT_DETECTION.format(filename=safe_filename, format="png")
            )
            return self._create_success_result(
                detected_format="png",
                confidence=DetectionConstants.HIGH_CONFIDENCE,
                detection_method=DetectionMethodEnum.CONTENT,
                filename=filename,
                metadata={"magic_bytes": MagicBytesConstants.PNG_SIGNATURE.hex()},
            )

        # Check GIF signatures
        for gif_sig in MagicBytesConstants.GIF_SIGNATURES:
            if header.startswith(gif_sig):
                self._logger.debug(
                    DetectorLogMessages.CONTENT_DETECTION.format(
                        filename=safe_filename, format="gif"
                    )
                )
                return self._create_success_result(
                    detected_format="gif",
                    confidence=DetectionConstants.HIGH_CONFIDENCE,
                    detection_method=DetectionMethodEnum.CONTENT,
                    filename=filename,
                    metadata={"magic_bytes": gif_sig.hex()},
                )

        # Check WEBP signature (RIFF + WEBP)
        if (
            header.startswith(MagicBytesConstants.WEBP_SIGNATURE)
            and len(content) >= 12
            and MagicBytesConstants.WEBP_FORMAT_SIGNATURE in content[:12]
        ):
            self._logger.debug(
                DetectorLogMessages.CONTENT_DETECTION.format(filename=safe_filename, format="webp")
            )
            return self._create_success_result(
                detected_format="webp",
                confidence=DetectionConstants.HIGH_CONFIDENCE,
                detection_method=DetectionMethodEnum.CONTENT,
                filename=filename,
                metadata={"magic_bytes": header[:12].hex()},
            )

        return None

    def _detect_document_by_content(
        self, content: bytes, filename: Optional[str] = None
    ) -> Optional[DetectionResult]:
        """
        Detect document format by analyzing content magic bytes.

        Args:
            content: Raw document content bytes
            filename: Optional filename for logging

        Returns:
            DetectionResult if format is detected, None otherwise
        """
        if len(content) < 4:
            return None

        safe_filename = self._get_safe_filename(filename=filename)
        header = content[: DetectionConstants.MAGIC_BYTES_READ_SIZE]

        # Check PDF signature
        if header.startswith(MagicBytesConstants.PDF_SIGNATURE):
            self._logger.debug(
                DetectorLogMessages.CONTENT_DETECTION.format(filename=safe_filename, format="pdf")
            )
            return self._create_success_result(
                detected_format="pdf",
                confidence=DetectionConstants.HIGH_CONFIDENCE,
                detection_method=DetectionMethodEnum.CONTENT,
                filename=filename,
                metadata={"magic_bytes": MagicBytesConstants.PDF_SIGNATURE.hex()},
            )

        # Check ZIP-based Office formats
        if header.startswith(MagicBytesConstants.ZIP_SIGNATURE):
            if len(content) >= DetectionConstants.ZIP_HEADER_READ_SIZE:
                zip_content = content[: DetectionConstants.ZIP_HEADER_READ_SIZE]

                # Check for DOCX
                if MagicBytesConstants.DOCX_CONTENT_TYPES in zip_content:
                    return self._create_success_result(
                        detected_format="docx",
                        confidence=DetectionConstants.HIGH_CONFIDENCE,
                        detection_method=DetectionMethodEnum.CONTENT,
                        filename=filename,
                        metadata={"magic_bytes": MagicBytesConstants.ZIP_SIGNATURE.hex()},
                    )

                # Check for XLSX
                if MagicBytesConstants.XLSX_CONTENT_TYPES in zip_content:
                    return self._create_success_result(
                        detected_format="xlsx",
                        confidence=DetectionConstants.HIGH_CONFIDENCE,
                        detection_method=DetectionMethodEnum.CONTENT,
                        filename=filename,
                        metadata={"magic_bytes": MagicBytesConstants.ZIP_SIGNATURE.hex()},
                    )

        # Check legacy Office formats
        if header.startswith(MagicBytesConstants.DOC_SIGNATURE):
            # This signature is shared by DOC and XLS - use extension if available
            if filename:
                file_path = Path(filename)
                extension = file_path.suffix.lower()
                if extension == ".doc":
                    detected_format = "doc"
                elif extension == ".xls":
                    detected_format = "xls"
                else:
                    detected_format = "doc"  # Default to DOC
            else:
                detected_format = "doc"

            return self._create_success_result(
                detected_format=detected_format,
                confidence=DetectionConstants.MEDIUM_CONFIDENCE,
                detection_method=DetectionMethodEnum.CONTENT,
                filename=filename,
                metadata={"magic_bytes": MagicBytesConstants.DOC_SIGNATURE.hex()},
            )

        # Check HTML signatures
        for html_sig in MagicBytesConstants.HTML_SIGNATURES:
            if html_sig in header:
                return self._create_success_result(
                    detected_format="html",
                    confidence=DetectionConstants.HIGH_CONFIDENCE,
                    detection_method=DetectionMethodEnum.CONTENT,
                    filename=filename,
                    metadata={"magic_bytes": html_sig.hex()},
                )

        return None

    def _detect_video_by_content(
        self, content: bytes, filename: Optional[str] = None
    ) -> Optional[DetectionResult]:
        """
        Detect video format by analyzing content magic bytes.

        Args:
            content: Raw video content bytes
            filename: Optional filename for logging

        Returns:
            DetectionResult if format is detected, None otherwise
        """
        if len(content) < 12:
            return None

        safe_filename = self._get_safe_filename(filename=filename)
        header = content[: DetectionConstants.MAGIC_BYTES_READ_SIZE]

        # Check MP4 signatures
        for mp4_sig in MagicBytesConstants.MP4_SIGNATURES:
            if mp4_sig in content[:32]:  # Check first 32 bytes for MP4 signature
                self._logger.debug(
                    DetectorLogMessages.CONTENT_DETECTION.format(
                        filename=safe_filename, format="mp4"
                    )
                )
                return self._create_success_result(
                    detected_format="mp4",
                    confidence=DetectionConstants.HIGH_CONFIDENCE,
                    detection_method=DetectionMethodEnum.CONTENT,
                    filename=filename,
                    metadata={"magic_bytes": mp4_sig.hex()},
                )

        # Check MOV signature
        if MagicBytesConstants.MOV_SIGNATURE in content[:32]:
            return self._create_success_result(
                detected_format="mov",
                confidence=DetectionConstants.HIGH_CONFIDENCE,
                detection_method=DetectionMethodEnum.CONTENT,
                filename=filename,
                metadata={"magic_bytes": MagicBytesConstants.MOV_SIGNATURE.hex()},
            )

        # Check AVI signature (RIFF + AVI)
        if (
            header.startswith(MagicBytesConstants.AVI_SIGNATURE)
            and len(content) >= 12
            and MagicBytesConstants.AVI_FORMAT_SIGNATURE in content[:12]
        ):
            return self._create_success_result(
                detected_format="avi",
                confidence=DetectionConstants.HIGH_CONFIDENCE,
                detection_method=DetectionMethodEnum.CONTENT,
                filename=filename,
                metadata={"magic_bytes": header[:12].hex()},
            )

        # Check WEBM/MKV signature (same signature, differentiate by extension if available)
        if header.startswith(MagicBytesConstants.WEBM_SIGNATURE):
            detected_format = "webm"  # Default to WEBM

            if filename:
                file_path = Path(filename)
                extension = file_path.suffix.lower()
                if extension == ".mkv":
                    detected_format = "mkv"

            return self._create_success_result(
                detected_format=detected_format,
                confidence=DetectionConstants.MEDIUM_CONFIDENCE,
                detection_method=DetectionMethodEnum.CONTENT,
                filename=filename,
                metadata={"magic_bytes": MagicBytesConstants.WEBM_SIGNATURE.hex()},
            )

        return None

    def _combine_detection_results(
        self,
        extension_result: Optional[DetectionResult],
        content_result: Optional[DetectionResult],
        filename: Optional[str] = None,
    ) -> DetectionResult:
        """
        Combine extension and content detection results intelligently.

        Args:
            extension_result: Result from extension-based detection
            content_result: Result from content-based detection
            filename: Optional filename for logging

        Returns:
            Combined DetectionResult with highest confidence
        """
        safe_filename = self._get_safe_filename(filename=filename)

        # If both methods agree, high confidence
        if (
            extension_result
            and content_result
            and extension_result.detected_format == content_result.detected_format
        ):
            return self._create_success_result(
                detected_format=content_result.detected_format,
                confidence=DetectionConstants.HIGH_CONFIDENCE,
                detection_method=DetectionMethodEnum.COMBINED,
                filename=filename,
                metadata={
                    "extension_confidence": extension_result.confidence,
                    "content_confidence": content_result.confidence,
                    "agreement": True,
                },
            )

        # If methods disagree, prefer content detection (more reliable)
        if extension_result and content_result:
            self._logger.warning(
                DetectorLogMessages.FORMAT_MISMATCH.format(
                    filename=safe_filename,
                    ext_format=extension_result.detected_format,
                    content_format=content_result.detected_format,
                )
            )

            return self._create_success_result(
                detected_format=content_result.detected_format,
                confidence=content_result.confidence * 0.9,  # Slight penalty for disagreement
                detection_method=DetectionMethodEnum.COMBINED,
                filename=filename,
                metadata={
                    "extension_format": extension_result.detected_format,
                    "content_format": content_result.detected_format,
                    "agreement": False,
                    "chosen_method": "content",
                },
            )

        # Use content result if available (higher confidence)
        if content_result:
            return content_result

        # Fall back to extension result
        if extension_result:
            return extension_result

        # No detection succeeded
        return self._create_error_result(
            error_message=DetectorErrorMessages.DETECTION_FAILED.format(filename=safe_filename),
            filename=filename,
            detection_method=DetectionMethodEnum.COMBINED,
        )
