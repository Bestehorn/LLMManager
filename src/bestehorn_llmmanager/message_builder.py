"""
MessageBuilder - Fluent interface for building Converse API messages.

Provides a convenient way to construct messages with automatic format detection,
validation, and multi-modal support.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from .bedrock.exceptions.llm_manager_exceptions import RequestValidationError
from .bedrock.models.llm_manager_constants import ConverseAPIFields
from .message_builder_constants import (
    MessageBuilderConfig,
    MessageBuilderErrorMessages,
    MessageBuilderLogMessages,
    SupportedFormats,
)
from .message_builder_enums import DocumentFormatEnum, ImageFormatEnum, RolesEnum, VideoFormatEnum
from .util.file_type_detector import FileTypeDetector


class ConverseMessageBuilder:
    """
    Fluent interface for building Converse API messages.

    Provides methods to add different types of content (text, images, documents, videos)
    with automatic format detection and validation.

    Example:
        message = ConverseMessageBuilder(role=RolesEnum.USER)
            .add_text(text="Analyze this image")
            .add_image_bytes(bytes=image_data, filename="photo.jpg")
            .build()
    """

    def __init__(self, role: RolesEnum) -> None:
        """
        Initialize the message builder with a role.

        Args:
            role: The role for this message (USER or ASSISTANT)
        """
        self._logger = logging.getLogger(__name__)

        # Validate role parameter before using it
        self._validate_role(role=role)

        self._role = role
        self._content_blocks: List[Dict[str, Any]] = []
        self._file_detector = FileTypeDetector()

        self._logger.debug(f"Initialized ConverseMessageBuilder with role: {role.value}")

    def add_text(self, text: str) -> "ConverseMessageBuilder":
        """
        Add a text content block to the message.

        Args:
            text: Text content to add

        Returns:
            Self for method chaining

        Raises:
            RequestValidationError: If text is empty or invalid
        """
        if not text or not text.strip():
            raise RequestValidationError(
                MessageBuilderErrorMessages.EMPTY_CONTENT.format(content_type="text")
            )

        self._validate_content_block_limit()

        text_block = {ConverseAPIFields.TEXT: text.strip()}

        self._content_blocks.append(text_block)

        self._logger.debug(
            MessageBuilderLogMessages.CONTENT_BLOCK_ADDED.format(
                content_type="text", size=len(text.encode("utf-8"))
            )
        )

        return self

    def add_image_bytes(
        self, bytes: bytes, format: Optional[ImageFormatEnum] = None, filename: Optional[str] = None
    ) -> "ConverseMessageBuilder":
        """
        Add an image content block to the message.

        Args:
            bytes: Raw image bytes
            format: Optional image format (auto-detected if not provided)
            filename: Optional filename for format detection and logging

        Returns:
            Self for method chaining

        Raises:
            RequestValidationError: If image data is invalid or format unsupported
        """
        if not bytes:
            raise RequestValidationError(
                MessageBuilderErrorMessages.EMPTY_CONTENT.format(content_type="image")
            )

        self._validate_content_block_limit()
        self._validate_content_size(
            content_size=len(bytes),
            max_size=MessageBuilderConfig.MAX_IMAGE_SIZE_BYTES,
            content_type="image",
        )

        # Auto-detect format if not provided
        if format is None:
            detection_result = self._file_detector.detect_image_format(
                content=bytes, filename=filename
            )

            if not detection_result.is_successful:
                raise RequestValidationError(
                    MessageBuilderErrorMessages.DETECTION_FAILED.format(
                        filename=filename or "unnamed_file", error=detection_result.error_message
                    )
                )

            detected_format = detection_result.detected_format

            # Log the auto-detection
            self._logger.info(
                MessageBuilderLogMessages.AUTO_DETECTION_SUCCESS.format(
                    filename=filename or "unnamed_file",
                    detected_type=detected_format,
                    method=detection_result.detection_method.value,
                    confidence=detection_result.confidence,
                )
            )

            # Convert string format to enum
            try:
                format = ImageFormatEnum(detected_format)
            except ValueError:
                raise RequestValidationError(
                    MessageBuilderErrorMessages.UNSUPPORTED_FORMAT.format(
                        content_type="image", format=detected_format
                    )
                )

        # Validate format is supported
        if format.value not in SupportedFormats.IMAGE_FORMATS:
            raise RequestValidationError(
                MessageBuilderErrorMessages.INVALID_FORMAT.format(
                    content_type="image",
                    format=format.value,
                    supported_formats=SupportedFormats.IMAGE_FORMATS,
                )
            )

        # Build image content block
        image_block = {
            ConverseAPIFields.IMAGE: {
                ConverseAPIFields.FORMAT: format.value,
                ConverseAPIFields.SOURCE: {ConverseAPIFields.BYTES: bytes},
            }
        }

        self._content_blocks.append(image_block)

        self._logger.debug(
            MessageBuilderLogMessages.CONTENT_BLOCK_ADDED.format(
                content_type=f"image ({format.value})", size=len(bytes)
            )
        )

        return self

    def add_local_image(
        self,
        path_to_local_file: str,
        format: Optional[ImageFormatEnum] = None,
        max_size_mb: float = 3.75,
    ) -> "ConverseMessageBuilder":
        """
        Add an image content block from a local file path.

        Args:
            path_to_local_file: Path to the local image file
            format: Optional image format (auto-detected if not provided)
            max_size_mb: Maximum allowed size in MB

        Returns:
            Self for method chaining

        Raises:
            RequestValidationError: If file cannot be read or is invalid
            FileNotFoundError: If the file does not exist
            ValueError: If image is too large and cannot be resized
        """
        file_path = Path(path_to_local_file)

        # Validate file exists
        if not file_path.exists():
            raise FileNotFoundError(f"Image file not found: {path_to_local_file}")

        if not file_path.is_file():
            raise RequestValidationError(f"Path is not a file: {path_to_local_file}")

        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        max_size_bytes = int(max_size_mb * 1024 * 1024)

        if file_size_mb > max_size_mb:
            self._logger.warning(
                f"Image {file_path.name} is {file_size_mb:.2f}MB, exceeds limit of {max_size_mb}MB"
            )
            raise RequestValidationError(
                MessageBuilderErrorMessages.CONTENT_SIZE_EXCEEDED.format(
                    size=file_path.stat().st_size, limit=max_size_bytes, content_type="image"
                )
            )

        # Read the file
        try:
            with open(file_path, "rb") as image_file:
                image_bytes = image_file.read()
        except Exception as e:
            raise RequestValidationError(f"Failed to read image file {path_to_local_file}: {e}")

        # Use the existing add_image_bytes method
        return self.add_image_bytes(bytes=image_bytes, format=format, filename=file_path.name)

    def add_document_bytes(
        self,
        bytes: bytes,
        format: Optional[DocumentFormatEnum] = None,
        filename: Optional[str] = None,
        name: Optional[str] = None,
    ) -> "ConverseMessageBuilder":
        """
        Add a document content block to the message.

        Args:
            bytes: Raw document bytes
            format: Optional document format (auto-detected if not provided)
            filename: Optional filename for format detection and logging
            name: Optional document name for the API

        Returns:
            Self for method chaining

        Raises:
            RequestValidationError: If document data is invalid or format unsupported
        """
        if not bytes:
            raise RequestValidationError(
                MessageBuilderErrorMessages.EMPTY_CONTENT.format(content_type="document")
            )

        self._validate_content_block_limit()
        self._validate_content_size(
            content_size=len(bytes),
            max_size=MessageBuilderConfig.MAX_DOCUMENT_SIZE_BYTES,
            content_type="document",
        )

        # Auto-detect format if not provided
        if format is None:
            detection_result = self._file_detector.detect_document_format(
                content=bytes, filename=filename
            )

            if not detection_result.is_successful:
                raise RequestValidationError(
                    MessageBuilderErrorMessages.DETECTION_FAILED.format(
                        filename=filename or "unnamed_file", error=detection_result.error_message
                    )
                )

            detected_format = detection_result.detected_format

            # Log the auto-detection
            self._logger.info(
                MessageBuilderLogMessages.AUTO_DETECTION_SUCCESS.format(
                    filename=filename or "unnamed_file",
                    detected_type=detected_format,
                    method=detection_result.detection_method.value,
                    confidence=detection_result.confidence,
                )
            )

            # Convert string format to enum
            try:
                format = DocumentFormatEnum(detected_format)
            except ValueError:
                raise RequestValidationError(
                    MessageBuilderErrorMessages.UNSUPPORTED_FORMAT.format(
                        content_type="document", format=detected_format
                    )
                )

        # Validate format is supported
        if format.value not in SupportedFormats.DOCUMENT_FORMATS:
            raise RequestValidationError(
                MessageBuilderErrorMessages.INVALID_FORMAT.format(
                    content_type="document",
                    format=format.value,
                    supported_formats=SupportedFormats.DOCUMENT_FORMATS,
                )
            )

        # Build document content block
        document_block = {
            ConverseAPIFields.DOCUMENT: {
                ConverseAPIFields.FORMAT: format.value,
                ConverseAPIFields.SOURCE: {ConverseAPIFields.BYTES: bytes},
            }
        }

        # Add document name if provided
        if name:
            document_block[ConverseAPIFields.DOCUMENT][ConverseAPIFields.NAME] = name
        elif filename:
            # Use filename as document name if no explicit name provided
            document_block[ConverseAPIFields.DOCUMENT][ConverseAPIFields.NAME] = filename

        self._content_blocks.append(document_block)

        self._logger.debug(
            MessageBuilderLogMessages.CONTENT_BLOCK_ADDED.format(
                content_type=f"document ({format.value})", size=len(bytes)
            )
        )

        return self

    def add_local_document(
        self,
        path_to_local_file: str,
        format: Optional[DocumentFormatEnum] = None,
        name: Optional[str] = None,
        max_size_mb: float = 4.5,
    ) -> "ConverseMessageBuilder":
        """
        Add a document content block from a local file path.

        Args:
            path_to_local_file: Path to the local document file
            format: Optional document format (auto-detected if not provided)
            name: Optional document name for the API
            max_size_mb: Maximum allowed size in MB

        Returns:
            Self for method chaining

        Raises:
            RequestValidationError: If file cannot be read or is invalid
            FileNotFoundError: If the file does not exist
        """
        file_path = Path(path_to_local_file)

        # Validate file exists
        if not file_path.exists():
            raise FileNotFoundError(f"Document file not found: {path_to_local_file}")

        if not file_path.is_file():
            raise RequestValidationError(f"Path is not a file: {path_to_local_file}")

        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        max_size_bytes = int(max_size_mb * 1024 * 1024)

        if file_size_mb > max_size_mb:
            self._logger.warning(
                f"Document {file_path.name} is {file_size_mb:.2f}MB, exceeds limit of {max_size_mb}MB"
            )
            raise RequestValidationError(
                MessageBuilderErrorMessages.CONTENT_SIZE_EXCEEDED.format(
                    size=file_path.stat().st_size, limit=max_size_bytes, content_type="document"
                )
            )

        # Read the file
        try:
            with open(file_path, "rb") as document_file:
                document_bytes = document_file.read()
        except Exception as e:
            raise RequestValidationError(f"Failed to read document file {path_to_local_file}: {e}")

        # Use the existing add_document_bytes method
        return self.add_document_bytes(
            bytes=document_bytes, format=format, filename=file_path.name, name=name
        )

    def add_video_bytes(
        self, bytes: bytes, format: Optional[VideoFormatEnum] = None, filename: Optional[str] = None
    ) -> "ConverseMessageBuilder":
        """
        Add a video content block to the message.

        Args:
            bytes: Raw video bytes
            format: Optional video format (auto-detected if not provided)
            filename: Optional filename for format detection and logging

        Returns:
            Self for method chaining

        Raises:
            RequestValidationError: If video data is invalid or format unsupported
        """
        if not bytes:
            raise RequestValidationError(
                MessageBuilderErrorMessages.EMPTY_CONTENT.format(content_type="video")
            )

        self._validate_content_block_limit()
        self._validate_content_size(
            content_size=len(bytes),
            max_size=MessageBuilderConfig.MAX_VIDEO_SIZE_BYTES,
            content_type="video",
        )

        # Auto-detect format if not provided
        if format is None:
            detection_result = self._file_detector.detect_video_format(
                content=bytes, filename=filename
            )

            if not detection_result.is_successful:
                raise RequestValidationError(
                    MessageBuilderErrorMessages.DETECTION_FAILED.format(
                        filename=filename or "unnamed_file", error=detection_result.error_message
                    )
                )

            detected_format = detection_result.detected_format

            # Log the auto-detection
            self._logger.info(
                MessageBuilderLogMessages.AUTO_DETECTION_SUCCESS.format(
                    filename=filename or "unnamed_file",
                    detected_type=detected_format,
                    method=detection_result.detection_method.value,
                    confidence=detection_result.confidence,
                )
            )

            # Convert string format to enum
            try:
                format = VideoFormatEnum(detected_format)
            except ValueError:
                raise RequestValidationError(
                    MessageBuilderErrorMessages.UNSUPPORTED_FORMAT.format(
                        content_type="video", format=detected_format
                    )
                )

        # Validate format is supported
        if format.value not in SupportedFormats.VIDEO_FORMATS:
            raise RequestValidationError(
                MessageBuilderErrorMessages.INVALID_FORMAT.format(
                    content_type="video",
                    format=format.value,
                    supported_formats=SupportedFormats.VIDEO_FORMATS,
                )
            )

        # Build video content block
        video_block = {
            ConverseAPIFields.VIDEO: {
                ConverseAPIFields.FORMAT: format.value,
                ConverseAPIFields.SOURCE: {ConverseAPIFields.BYTES: bytes},
            }
        }

        self._content_blocks.append(video_block)

        self._logger.debug(
            MessageBuilderLogMessages.CONTENT_BLOCK_ADDED.format(
                content_type=f"video ({format.value})", size=len(bytes)
            )
        )

        return self

    def add_local_video(
        self,
        path_to_local_file: str,
        format: Optional[VideoFormatEnum] = None,
        max_size_mb: float = 100.0,
    ) -> "ConverseMessageBuilder":
        """
        Add a video content block from a local file path.

        Args:
            path_to_local_file: Path to the local video file
            format: Optional video format (auto-detected if not provided)
            max_size_mb: Maximum allowed size in MB

        Returns:
            Self for method chaining

        Raises:
            RequestValidationError: If file cannot be read or is invalid
            FileNotFoundError: If the file does not exist
        """
        file_path = Path(path_to_local_file)

        # Validate file exists
        if not file_path.exists():
            raise FileNotFoundError(f"Video file not found: {path_to_local_file}")

        if not file_path.is_file():
            raise RequestValidationError(f"Path is not a file: {path_to_local_file}")

        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        max_size_bytes = int(max_size_mb * 1024 * 1024)

        if file_size_mb > max_size_mb:
            self._logger.warning(
                f"Video {file_path.name} is {file_size_mb:.2f}MB, exceeds limit of {max_size_mb}MB"
            )
            raise RequestValidationError(
                MessageBuilderErrorMessages.CONTENT_SIZE_EXCEEDED.format(
                    size=file_path.stat().st_size, limit=max_size_bytes, content_type="video"
                )
            )

        # Read the file
        try:
            with open(file_path, "rb") as video_file:
                video_bytes = video_file.read()
        except Exception as e:
            raise RequestValidationError(f"Failed to read video file {path_to_local_file}: {e}")

        # Use the existing add_video_bytes method
        return self.add_video_bytes(bytes=video_bytes, format=format, filename=file_path.name)

    def build(self) -> Dict[str, Any]:
        """
        Build and return the complete message dictionary.

        Returns:
            Dictionary compatible with LLMManager.converse() messages parameter

        Raises:
            RequestValidationError: If message validation fails
        """
        # Validate we have content blocks
        if not self._content_blocks:
            raise RequestValidationError(MessageBuilderErrorMessages.NO_CONTENT_BLOCKS)

        self._logger.debug(
            MessageBuilderLogMessages.MESSAGE_BUILD_STARTED.format(
                role=self._role.value, block_count=len(self._content_blocks)
            )
        )

        # Build the message dictionary
        message = {
            ConverseAPIFields.ROLE: self._role.value,
            ConverseAPIFields.CONTENT: self._content_blocks.copy(),
        }

        self._logger.info(
            MessageBuilderLogMessages.MESSAGE_BUILD_COMPLETED.format(
                block_count=len(self._content_blocks)
            )
        )

        return message

    def _validate_content_block_limit(self) -> None:
        """
        Validate that we haven't exceeded the content block limit.

        Raises:
            RequestValidationError: If limit is exceeded
        """
        current_count = len(self._content_blocks)
        max_count = MessageBuilderConfig.MAX_CONTENT_BLOCKS_PER_MESSAGE

        if current_count >= max_count:
            raise RequestValidationError(
                MessageBuilderErrorMessages.CONTENT_BLOCK_LIMIT_EXCEEDED.format(limit=max_count)
            )

        # Warning at 80% of limit
        warning_threshold = int(max_count * 0.8)
        if current_count >= warning_threshold:
            self._logger.warning(
                MessageBuilderLogMessages.CONTENT_BLOCK_LIMIT_WARNING.format(
                    count=current_count, limit=max_count
                )
            )

    def _validate_content_size(self, content_size: int, max_size: int, content_type: str) -> None:
        """
        Validate content size against limits.

        Args:
            content_size: Size of content in bytes
            max_size: Maximum allowed size in bytes
            content_type: Type of content for error messages

        Raises:
            RequestValidationError: If size limit is exceeded
        """
        if content_size > max_size:
            raise RequestValidationError(
                MessageBuilderErrorMessages.CONTENT_SIZE_EXCEEDED.format(
                    size=content_size, limit=max_size, content_type=content_type
                )
            )

        # Warning at 80% of limit
        warning_threshold = int(max_size * 0.8)
        if content_size >= warning_threshold:
            self._logger.warning(
                MessageBuilderLogMessages.CONTENT_SIZE_WARNING.format(
                    size=content_size, limit=max_size, content_type=content_type
                )
            )

    def _validate_role(self, role: RolesEnum) -> None:
        """
        Validate role parameter is a valid RolesEnum instance.

        Args:
            role: The role to validate

        Raises:
            RequestValidationError: If role is invalid
        """
        if not isinstance(role, RolesEnum):
            raise RequestValidationError(
                f"Invalid role type. Expected RolesEnum, got {type(role).__name__}. "
                f"Valid roles are: {', '.join([r.value for r in RolesEnum])}"
            )

    @property
    def role(self) -> RolesEnum:
        """Get the role for this message."""
        return self._role

    @property
    def content_block_count(self) -> int:
        """Get the current number of content blocks."""
        return len(self._content_blocks)

    def __str__(self) -> str:
        """String representation of the builder."""
        return (
            f"ConverseMessageBuilder(role={self._role.value}, "
            f"content_blocks={len(self._content_blocks)})"
        )

    def __repr__(self) -> str:
        """Detailed string representation of the builder."""
        return (
            f"ConverseMessageBuilder(role={self._role.value}, "
            f"content_blocks={len(self._content_blocks)}, "
            f"detector={self._file_detector.__class__.__name__})"
        )


# Factory Functions
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
        ...     .add_document_bytes(bytes=pdf_data, filename="report.pd")\\
        ...     .build()

        Message with explicit formats:
        >>> from bestehorn_llmmanager.message_builder_enums import ImageFormatEnum, DocumentFormatEnum
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


# Alias for backwards compatibility and naming consistency
MessageBuilder = ConverseMessageBuilder
