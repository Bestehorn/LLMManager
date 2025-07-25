"""
Unit tests for ConverseMessageBuilder.
Tests the main message builder class and its functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
    RequestValidationError,
)
from bestehorn_llmmanager.bedrock.models.llm_manager_constants import ConverseAPIFields
from bestehorn_llmmanager.message_builder import (
    ConverseMessageBuilder,
    MessageBuilder,
    create_assistant_message,
    create_message,
    create_user_message,
)
from bestehorn_llmmanager.message_builder_enums import (
    DetectionMethodEnum,
    DocumentFormatEnum,
    ImageFormatEnum,
    RolesEnum,
    VideoFormatEnum,
)
from bestehorn_llmmanager.util.file_type_detector.base_detector import DetectionResult


class TestConverseMessageBuilderInitialization:
    """Test cases for ConverseMessageBuilder initialization."""

    def test_initialization_with_valid_role(self):
        """Test successful initialization with valid role."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        assert builder.role == RolesEnum.USER
        assert builder.content_block_count == 0
        assert hasattr(builder, "_file_detector")
        assert hasattr(builder, "_logger")

    def test_initialization_with_assistant_role(self):
        """Test initialization with assistant role."""
        builder = ConverseMessageBuilder(role=RolesEnum.ASSISTANT)

        assert builder.role == RolesEnum.ASSISTANT
        assert builder.content_block_count == 0

    def test_initialization_with_invalid_role(self):
        """Test initialization fails with invalid role."""
        with pytest.raises(RequestValidationError):
            ConverseMessageBuilder(role="invalid_role")  # type: ignore


class TestAddTextMethod:
    """Test cases for add_text method."""

    def test_add_text_success(self):
        """Test successfully adding text content."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        result = builder.add_text(text="Hello, world!")

        assert result is builder  # Method chaining
        assert builder.content_block_count == 1

    def test_add_text_strips_whitespace(self):
        """Test that text is stripped of surrounding whitespace."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        builder.add_text(text="  Hello, world!  ")
        message = builder.build()

        text_block = message[ConverseAPIFields.CONTENT][0]
        assert text_block[ConverseAPIFields.TEXT] == "Hello, world!"

    def test_add_text_empty_string(self):
        """Test adding empty text raises error."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        with pytest.raises(RequestValidationError):
            builder.add_text(text="")

    def test_add_text_whitespace_only(self):
        """Test adding whitespace-only text raises error."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        with pytest.raises(RequestValidationError):
            builder.add_text(text="   ")

    def test_add_multiple_text_blocks(self):
        """Test adding multiple text blocks."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        builder.add_text(text="First text").add_text(text="Second text")

        assert builder.content_block_count == 2

        message = builder.build()
        content_blocks = message[ConverseAPIFields.CONTENT]

        assert content_blocks[0][ConverseAPIFields.TEXT] == "First text"
        assert content_blocks[1][ConverseAPIFields.TEXT] == "Second text"


class TestAddImageBytesMethod:
    """Test cases for add_image_bytes method."""

    def test_add_image_with_explicit_format(self):
        """Test adding image with explicitly specified format."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        image_data = b"\xff\xd8\xff\xe0"  # JPEG header

        result = builder.add_image_bytes(bytes=image_data, format=ImageFormatEnum.JPEG)

        assert result is builder
        assert builder.content_block_count == 1

        message = builder.build()
        image_block = message[ConverseAPIFields.CONTENT][0]

        assert ConverseAPIFields.IMAGE in image_block
        assert image_block[ConverseAPIFields.IMAGE][ConverseAPIFields.FORMAT] == "jpeg"
        assert (
            image_block[ConverseAPIFields.IMAGE][ConverseAPIFields.SOURCE][ConverseAPIFields.BYTES]
            == image_data
        )

    @patch("bestehorn_llmmanager.message_builder.FileTypeDetector")
    def test_add_image_with_auto_detection(self, mock_detector_class):
        """Test adding image with automatic format detection."""
        # Mock the detector
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector

        # Mock successful detection result
        from bestehorn_llmmanager.message_builder_enums import DetectionMethodEnum
        from bestehorn_llmmanager.util.file_type_detector.base_detector import DetectionResult

        mock_result = DetectionResult(
            detected_format="jpeg",
            confidence=0.95,
            detection_method=DetectionMethodEnum.CONTENT,
            filename="test.jpg",
        )
        mock_detector.detect_image_format.return_value = mock_result

        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        image_data = b"\xff\xd8\xff\xe0"

        result = builder.add_image_bytes(bytes=image_data, filename="test.jpg")

        assert result is builder
        assert builder.content_block_count == 1

        # Verify detector was called
        mock_detector.detect_image_format.assert_called_once_with(
            content=image_data, filename="test.jpg"
        )

    def test_add_image_empty_bytes(self):
        """Test adding empty image bytes raises error."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        with pytest.raises(RequestValidationError):
            builder.add_image_bytes(bytes=b"")

    def test_add_image_unsupported_format(self):
        """Test adding image with unsupported format raises error."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        image_data = b"test data"

        # This should work since JPEG is supported
        with pytest.raises(RequestValidationError):
            # We need to create a scenario where format validation fails
            # This is a bit contrived since our enum only has supported formats
            # Mock the detector to return an unsupported format
            with patch(
                "bestehorn_llmmanager.message_builder.FileTypeDetector"
            ) as mock_detector_class:
                mock_detector = Mock()
                mock_detector_class.return_value = mock_detector

                from bestehorn_llmmanager.message_builder_enums import DetectionMethodEnum
                from bestehorn_llmmanager.util.file_type_detector.base_detector import (
                    DetectionResult,
                )

                # Mock detection result with unsupported format
                mock_result = DetectionResult(
                    detected_format="bmp",  # Unsupported format
                    confidence=0.95,
                    detection_method=DetectionMethodEnum.CONTENT,
                    filename="test.bmp",
                )
                mock_detector.detect_image_format.return_value = mock_result

                # This should raise RequestValidationError due to unsupported format
                builder.add_image_bytes(bytes=image_data, filename="test.bmp")


class TestAddDocumentBytesMethod:
    """Test cases for add_document_bytes method."""

    def test_add_document_with_explicit_format(self):
        """Test adding document with explicitly specified format."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        pdf_data = b"%PDF-1.4"  # PDF header

        result = builder.add_document_bytes(
            bytes=pdf_data, format=DocumentFormatEnum.PDF, name="test_document.pd"
        )

        assert result is builder
        assert builder.content_block_count == 1

        message = builder.build()
        doc_block = message[ConverseAPIFields.CONTENT][0]

        assert ConverseAPIFields.DOCUMENT in doc_block
        assert doc_block[ConverseAPIFields.DOCUMENT][ConverseAPIFields.FORMAT] == "pdf"
        assert (
            doc_block[ConverseAPIFields.DOCUMENT][ConverseAPIFields.SOURCE][ConverseAPIFields.BYTES]
            == pdf_data
        )
        assert doc_block[ConverseAPIFields.DOCUMENT][ConverseAPIFields.NAME] == "test_document.pd"

    def test_add_document_with_filename_as_name(self):
        """Test adding document uses filename as name when no explicit name."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        pdf_data = b"%PDF-1.4"

        builder.add_document_bytes(
            bytes=pdf_data, format=DocumentFormatEnum.PDF, filename="report.pd"
        )

        message = builder.build()
        doc_block = message[ConverseAPIFields.CONTENT][0]

        assert doc_block[ConverseAPIFields.DOCUMENT][ConverseAPIFields.NAME] == "report.pd"


class TestBuildMethod:
    """Test cases for build method."""

    def test_build_with_content(self):
        """Test building message with content."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        builder.add_text(text="Hello!")

        message = builder.build()

        assert isinstance(message, dict)
        assert message[ConverseAPIFields.ROLE] == "user"
        assert ConverseAPIFields.CONTENT in message
        assert len(message[ConverseAPIFields.CONTENT]) == 1
        assert message[ConverseAPIFields.CONTENT][0][ConverseAPIFields.TEXT] == "Hello!"

    def test_build_without_content(self):
        """Test building message without content raises error."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        with pytest.raises(RequestValidationError):
            builder.build()

    def test_build_complex_message(self):
        """Test building complex message with multiple content types."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        image_data = b"\xff\xd8\xff\xe0"
        pdf_data = b"%PDF-1.4"

        builder.add_text(text="Please analyze these files:").add_image_bytes(
            bytes=image_data, format=ImageFormatEnum.JPEG
        ).add_document_bytes(bytes=pdf_data, format=DocumentFormatEnum.PDF).add_text(
            text="What do you think?"
        )

        message = builder.build()

        assert len(message[ConverseAPIFields.CONTENT]) == 4

        # Check text blocks
        assert (
            message[ConverseAPIFields.CONTENT][0][ConverseAPIFields.TEXT]
            == "Please analyze these files:"
        )
        assert message[ConverseAPIFields.CONTENT][3][ConverseAPIFields.TEXT] == "What do you think?"

        # Check image block
        assert ConverseAPIFields.IMAGE in message[ConverseAPIFields.CONTENT][1]

        # Check document block
        assert ConverseAPIFields.DOCUMENT in message[ConverseAPIFields.CONTENT][2]


class TestMethodChaining:
    """Test cases for method chaining functionality."""

    def test_method_chaining(self):
        """Test that all methods support chaining."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        image_data = b"\xff\xd8\xff\xe0"

        result = (
            builder.add_text(text="First text")
            .add_image_bytes(bytes=image_data, format=ImageFormatEnum.JPEG)
            .add_text(text="Second text")
        )

        assert result is builder
        assert builder.content_block_count == 3

    def test_chaining_returns_same_instance(self):
        """Test that chaining methods return the same instance."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        text_result = builder.add_text(text="Test")
        assert text_result is builder

        # Can continue chaining from returned instance
        image_data = b"\xff\xd8\xff\xe0"
        image_result = text_result.add_image_bytes(bytes=image_data, format=ImageFormatEnum.JPEG)
        assert image_result is builder


class TestValidationAndLimits:
    """Test cases for validation and content limits."""

    def test_content_block_limit_warning(self):
        """Test that approaching content block limit generates warning."""
        # This test would require mocking the logger to capture warnings
        # For now, just test that we can add a reasonable number of blocks
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        # Add several text blocks
        for i in range(10):
            builder.add_text(text=f"Text block {i}")

        assert builder.content_block_count == 10

        # Should still be able to build
        message = builder.build()
        assert len(message[ConverseAPIFields.CONTENT]) == 10


class TestStringRepresentation:
    """Test cases for string representation methods."""

    def test_str_representation(self):
        """Test string representation of builder."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        builder.add_text(text="Test")

        str_repr = str(builder)
        assert "ConverseMessageBuilder" in str_repr
        assert "user" in str_repr
        assert "1" in str_repr  # content block count

    def test_repr_representation(self):
        """Test detailed string representation of builder."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        repr_str = repr(builder)
        assert "ConverseMessageBuilder" in repr_str
        assert "user" in repr_str
        assert "FileTypeDetector" in repr_str


class TestPropertyAccess:
    """Test cases for property access."""

    def test_role_property(self):
        """Test role property access."""
        user_builder = ConverseMessageBuilder(role=RolesEnum.USER)
        assert user_builder.role == RolesEnum.USER

        assistant_builder = ConverseMessageBuilder(role=RolesEnum.ASSISTANT)
        assert assistant_builder.role == RolesEnum.ASSISTANT

    def test_content_block_count_property(self):
        """Test content_block_count property."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        assert builder.content_block_count == 0

        builder.add_text(text="Test 1")
        assert builder.content_block_count == 1

        builder.add_text(text="Test 2")
        assert builder.content_block_count == 2


class TestAddLocalImageMethod:
    """Test cases for add_local_image method."""

    def test_add_local_image_success(self):
        """Test successfully adding local image file."""
        # Write some JPEG-like data
        jpeg_data = b"\xff\xd8\xff\xe0\x00\x10JFIF"

        # Create temp file, write data, and close it properly for Windows compatibility
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            tmp_file.write(jpeg_data)
            tmp_file.flush()
            tmp_file_path = tmp_file.name

        try:
            builder = ConverseMessageBuilder(role=RolesEnum.USER)

            with patch.object(builder, "add_image_bytes") as mock_add_image:
                mock_add_image.return_value = builder

                result = builder.add_local_image(path_to_local_file=tmp_file_path)

                assert result is builder
                mock_add_image.assert_called_once_with(
                    bytes=jpeg_data, format=None, filename=Path(tmp_file_path).name
                )
        finally:
            Path(tmp_file_path).unlink(missing_ok=True)

    def test_add_local_image_file_not_found(self):
        """Test adding non-existent local image raises FileNotFoundError."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        with pytest.raises(FileNotFoundError):
            builder.add_local_image(path_to_local_file="nonexistent.jpg")

    def test_add_local_image_not_a_file(self):
        """Test adding directory path raises RequestValidationError."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        with tempfile.TemporaryDirectory() as tmp_dir:
            with pytest.raises(RequestValidationError, match="Path is not a file"):
                builder.add_local_image(path_to_local_file=tmp_dir)

    def test_add_local_image_size_exceeded(self):
        """Test adding oversized image raises RequestValidationError."""
        # Write data larger than limit
        large_data = b"x" * (5 * 1024 * 1024)  # 5MB

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            tmp_file.write(large_data)
            tmp_file.flush()
            tmp_file_path = tmp_file.name

        try:
            builder = ConverseMessageBuilder(role=RolesEnum.USER)

            with pytest.raises(RequestValidationError, match="size limit exceeded"):
                builder.add_local_image(path_to_local_file=tmp_file_path, max_size_mb=3.75)
        finally:
            Path(tmp_file_path).unlink(missing_ok=True)

    def test_add_local_image_read_error(self):
        """Test file read error raises RequestValidationError."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        # Create temp file, write data, and get the path
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
            tmp_file.write(b"test")
            tmp_file.flush()
            tmp_file_path = tmp_file.name

        # Now the file is closed and we can use it
        try:
            # Mock open to raise an exception
            with patch("builtins.open", side_effect=PermissionError("Access denied")):
                with pytest.raises(RequestValidationError, match="Failed to read image file"):
                    builder.add_local_image(path_to_local_file=tmp_file_path)
        finally:
            Path(tmp_file_path).unlink(missing_ok=True)


class TestAddVideoBytesMethod:
    """Test cases for add_video_bytes method."""

    def test_add_video_with_explicit_format(self):
        """Test adding video with explicitly specified format."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        video_data = b"\x00\x00\x00\x18ftypmp4"  # MP4 header

        result = builder.add_video_bytes(bytes=video_data, format=VideoFormatEnum.MP4)

        assert result is builder
        assert builder.content_block_count == 1

        message = builder.build()
        video_block = message[ConverseAPIFields.CONTENT][0]

        assert ConverseAPIFields.VIDEO in video_block
        assert video_block[ConverseAPIFields.VIDEO][ConverseAPIFields.FORMAT] == "mp4"
        assert (
            video_block[ConverseAPIFields.VIDEO][ConverseAPIFields.SOURCE][ConverseAPIFields.BYTES]
            == video_data
        )

    @patch("bestehorn_llmmanager.message_builder.FileTypeDetector")
    def test_add_video_with_auto_detection(self, mock_detector_class):
        """Test adding video with automatic format detection."""
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector

        mock_result = DetectionResult(
            detected_format="mp4",
            confidence=0.95,
            detection_method=DetectionMethodEnum.CONTENT,
            filename="test.mp4",
        )
        mock_detector.detect_video_format.return_value = mock_result

        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        video_data = b"\x00\x00\x00\x18ftypmp4"

        result = builder.add_video_bytes(bytes=video_data, filename="test.mp4")

        assert result is builder
        assert builder.content_block_count == 1
        mock_detector.detect_video_format.assert_called_once_with(
            content=video_data, filename="test.mp4"
        )

    def test_add_video_empty_bytes(self):
        """Test adding empty video bytes raises error."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        with pytest.raises(RequestValidationError, match="empty"):
            builder.add_video_bytes(bytes=b"")

    @patch("bestehorn_llmmanager.message_builder.FileTypeDetector")
    def test_add_video_detection_failure(self, mock_detector_class):
        """Test video detection failure raises error."""
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector

        # Mock failed detection
        failed_result = DetectionResult(
            detected_format="unknown",
            confidence=0.0,
            detection_method=DetectionMethodEnum.CONTENT,
            filename="test.mp4",
            error_message="Unknown format",
        )
        mock_detector.detect_video_format.return_value = failed_result

        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        video_data = b"unknown format"

        with pytest.raises(RequestValidationError, match="Detection failed"):
            builder.add_video_bytes(bytes=video_data, filename="test.mp4")

    @patch("bestehorn_llmmanager.message_builder.FileTypeDetector")
    def test_add_video_unsupported_format(self, mock_detector_class):
        """Test unsupported video format raises error."""
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector

        mock_result = DetectionResult(
            detected_format="flv",  # Unsupported format
            confidence=0.95,
            detection_method=DetectionMethodEnum.CONTENT,
            filename="test.flv",
        )
        mock_detector.detect_video_format.return_value = mock_result

        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        video_data = b"flv data"

        with pytest.raises(RequestValidationError, match="Unsupported format"):
            builder.add_video_bytes(bytes=video_data, filename="test.flv")


class TestAddLocalVideoMethod:
    """Test cases for add_local_video method."""

    def test_add_local_video_success(self):
        """Test successfully adding local video file."""
        video_data = b"\x00\x00\x00\x18ftypmp4"

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_file.write(video_data)
            tmp_file.flush()
            tmp_file_path = tmp_file.name

        try:
            builder = ConverseMessageBuilder(role=RolesEnum.USER)

            with patch.object(builder, "add_video_bytes") as mock_add_video:
                mock_add_video.return_value = builder

                result = builder.add_local_video(path_to_local_file=tmp_file_path)

                assert result is builder
                mock_add_video.assert_called_once_with(
                    bytes=video_data, format=None, filename=Path(tmp_file_path).name
                )
        finally:
            Path(tmp_file_path).unlink(missing_ok=True)

    def test_add_local_video_file_not_found(self):
        """Test adding non-existent local video raises FileNotFoundError."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        with pytest.raises(FileNotFoundError):
            builder.add_local_video(path_to_local_file="nonexistent.mp4")

    def test_add_local_video_size_exceeded(self):
        """Test adding oversized video raises RequestValidationError."""
        # Write data larger than limit
        large_data = b"x" * (150 * 1024 * 1024)  # 150MB

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
            tmp_file.write(large_data)
            tmp_file.flush()
            tmp_file_path = tmp_file.name

        try:
            builder = ConverseMessageBuilder(role=RolesEnum.USER)

            with pytest.raises(RequestValidationError, match="size limit exceeded"):
                builder.add_local_video(path_to_local_file=tmp_file_path, max_size_mb=100.0)
        finally:
            Path(tmp_file_path).unlink(missing_ok=True)


class TestAddLocalDocumentMethod:
    """Test cases for add_local_document method."""

    def test_add_local_document_success(self):
        """Test successfully adding local document file."""
        pdf_data = b"%PDF-1.4"

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(pdf_data)
            tmp_file.flush()
            tmp_file_path = tmp_file.name

        try:
            builder = ConverseMessageBuilder(role=RolesEnum.USER)

            with patch.object(builder, "add_document_bytes") as mock_add_doc:
                mock_add_doc.return_value = builder

                result = builder.add_local_document(
                    path_to_local_file=tmp_file_path, name="Test Document"
                )

                assert result is builder
                mock_add_doc.assert_called_once_with(
                    bytes=pdf_data,
                    format=None,
                    filename=Path(tmp_file_path).name,
                    name="Test Document",
                )
        finally:
            Path(tmp_file_path).unlink(missing_ok=True)

    def test_add_local_document_file_not_found(self):
        """Test adding non-existent local document raises FileNotFoundError."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        with pytest.raises(FileNotFoundError):
            builder.add_local_document(path_to_local_file="nonexistent.pdf")

    def test_add_local_document_size_exceeded(self):
        """Test adding oversized document raises RequestValidationError."""
        # Write data larger than limit
        large_data = b"x" * (6 * 1024 * 1024)  # 6MB

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_file.write(large_data)
            tmp_file.flush()
            tmp_file_path = tmp_file.name

        try:
            builder = ConverseMessageBuilder(role=RolesEnum.USER)

            with pytest.raises(RequestValidationError, match="size limit exceeded"):
                builder.add_local_document(path_to_local_file=tmp_file_path, max_size_mb=4.5)
        finally:
            Path(tmp_file_path).unlink(missing_ok=True)


class TestContentSizeValidation:
    """Test cases for content size validation."""

    def test_image_size_validation(self):
        """Test image size validation."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        # Create data that exceeds the image size limit
        large_image_data = b"x" * (4 * 1024 * 1024)  # 4MB > 3.75MB limit

        with pytest.raises(RequestValidationError, match="size limit exceeded"):
            builder.add_image_bytes(bytes=large_image_data, format=ImageFormatEnum.JPEG)

    def test_document_size_validation(self):
        """Test document size validation."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        # Create data that exceeds the document size limit
        large_doc_data = b"x" * (5 * 1024 * 1024)  # 5MB > 4.5MB limit

        with pytest.raises(RequestValidationError, match="size limit exceeded"):
            builder.add_document_bytes(bytes=large_doc_data, format=DocumentFormatEnum.PDF)

    def test_video_size_validation(self):
        """Test video size validation."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        # Create data that exceeds the video size limit
        large_video_data = b"x" * (101 * 1024 * 1024)  # 101MB > 100MB limit

        with pytest.raises(RequestValidationError, match="size limit exceeded"):
            builder.add_video_bytes(bytes=large_video_data, format=VideoFormatEnum.MP4)


class TestContentBlockLimits:
    """Test cases for content block limits."""

    @patch(
        "bestehorn_llmmanager.message_builder_constants.MessageBuilderConfig.MAX_CONTENT_BLOCKS_PER_MESSAGE",
        3,
    )
    def test_content_block_limit_exceeded(self):
        """Test that exceeding content block limit raises error."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        # Add blocks up to the limit
        builder.add_text("Text 1")
        builder.add_text("Text 2")
        builder.add_text("Text 3")

        # This should exceed the limit
        with pytest.raises(RequestValidationError, match="Content block limit exceeded"):
            builder.add_text("Text 4")

    @patch(
        "bestehorn_llmmanager.message_builder_constants.MessageBuilderConfig.MAX_CONTENT_BLOCKS_PER_MESSAGE",
        5,
    )
    def test_content_block_warning_threshold(self):
        """Test warning at 80% of content block limit."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        with patch.object(builder._logger, "warning") as mock_warning:
            # Add blocks to reach 80% threshold (4 out of 5)
            builder.add_text("Text 1")
            builder.add_text("Text 2")
            builder.add_text("Text 3")
            builder.add_text("Text 4")  # This should trigger warning

            # Verify warning was logged
            mock_warning.assert_called()
            args = mock_warning.call_args[0][0]
            assert "Content block limit warning" in args or "approaching" in args.lower()


class TestAutoDetectionScenarios:
    """Test cases for auto-detection scenarios."""

    @patch("bestehorn_llmmanager.message_builder.FileTypeDetector")
    def test_document_auto_detection_success(self, mock_detector_class):
        """Test successful document auto-detection."""
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector

        mock_result = DetectionResult(
            detected_format="pdf",
            confidence=0.95,
            detection_method=DetectionMethodEnum.CONTENT,
            filename="test.pdf",
        )
        mock_detector.detect_document_format.return_value = mock_result

        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        pdf_data = b"%PDF-1.4"

        result = builder.add_document_bytes(bytes=pdf_data, filename="test.pdf")

        assert result is builder
        mock_detector.detect_document_format.assert_called_once_with(
            content=pdf_data, filename="test.pdf"
        )

    @patch("bestehorn_llmmanager.message_builder.FileTypeDetector")
    def test_document_detection_failure(self, mock_detector_class):
        """Test document detection failure."""
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector

        failed_result = DetectionResult(
            detected_format="unknown",
            confidence=0.0,
            detection_method=DetectionMethodEnum.CONTENT,
            filename="test.doc",
            error_message="Unsupported format",
        )
        mock_detector.detect_document_format.return_value = failed_result

        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        doc_data = b"unknown format"

        with pytest.raises(RequestValidationError, match="Detection failed"):
            builder.add_document_bytes(bytes=doc_data, filename="test.doc")

    @patch("bestehorn_llmmanager.message_builder.FileTypeDetector")
    def test_image_detection_failure(self, mock_detector_class):
        """Test image detection failure."""
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector

        failed_result = DetectionResult(
            detected_format="unknown",
            confidence=0.0,
            detection_method=DetectionMethodEnum.CONTENT,
            filename="test.img",
            error_message="Unknown image format",
        )
        mock_detector.detect_image_format.return_value = failed_result

        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        image_data = b"unknown format"

        with pytest.raises(RequestValidationError, match="Detection failed"):
            builder.add_image_bytes(bytes=image_data, filename="test.img")


class TestFactoryFunctions:
    """Test cases for factory functions."""

    def test_create_message_function(self):
        """Test create_message factory function."""
        builder = create_message(role=RolesEnum.USER)

        assert isinstance(builder, ConverseMessageBuilder)
        assert builder.role == RolesEnum.USER
        assert builder.content_block_count == 0

    def test_create_user_message_function(self):
        """Test create_user_message factory function."""
        builder = create_user_message()

        assert isinstance(builder, ConverseMessageBuilder)
        assert builder.role == RolesEnum.USER
        assert builder.content_block_count == 0

    def test_create_assistant_message_function(self):
        """Test create_assistant_message factory function."""
        builder = create_assistant_message()

        assert isinstance(builder, ConverseMessageBuilder)
        assert builder.role == RolesEnum.ASSISTANT
        assert builder.content_block_count == 0

    def test_message_builder_alias(self):
        """Test MessageBuilder alias."""
        assert MessageBuilder is ConverseMessageBuilder

        # Can use alias to create instance
        builder = MessageBuilder(role=RolesEnum.USER)
        assert isinstance(builder, ConverseMessageBuilder)

    def test_factory_function_chaining(self):
        """Test factory functions support method chaining."""
        message = create_user_message().add_text("Hello world").build()

        assert message[ConverseAPIFields.ROLE] == "user"
        assert len(message[ConverseAPIFields.CONTENT]) == 1
        assert message[ConverseAPIFields.CONTENT][0][ConverseAPIFields.TEXT] == "Hello world"


class TestDocumentNameHandling:
    """Test cases for document name handling."""

    def test_document_no_name_or_filename(self):
        """Test document without name or filename."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        pdf_data = b"%PDF-1.4"

        builder.add_document_bytes(bytes=pdf_data, format=DocumentFormatEnum.PDF)
        message = builder.build()

        doc_block = message[ConverseAPIFields.CONTENT][0]
        # Should not have a name field
        assert ConverseAPIFields.NAME not in doc_block[ConverseAPIFields.DOCUMENT]

    def test_document_with_both_name_and_filename(self):
        """Test document with both explicit name and filename (name takes precedence)."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        pdf_data = b"%PDF-1.4"

        builder.add_document_bytes(
            bytes=pdf_data, format=DocumentFormatEnum.PDF, filename="file.pdf", name="Custom Name"
        )
        message = builder.build()

        doc_block = message[ConverseAPIFields.CONTENT][0]
        assert doc_block[ConverseAPIFields.DOCUMENT][ConverseAPIFields.NAME] == "Custom Name"

    def test_document_empty_bytes(self):
        """Test adding empty document bytes raises error."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        with pytest.raises(RequestValidationError, match="empty"):
            builder.add_document_bytes(bytes=b"")


class TestComplexScenarios:
    """Test cases for complex usage scenarios."""

    def test_mixed_content_types(self):
        """Test building message with all content types."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)

        image_data = b"\xff\xd8\xff\xe0"
        doc_data = b"%PDF-1.4"
        video_data = b"\x00\x00\x00\x18ftypmp4"

        builder.add_text("Please analyze these files:").add_image_bytes(
            bytes=image_data, format=ImageFormatEnum.JPEG
        ).add_document_bytes(bytes=doc_data, format=DocumentFormatEnum.PDF).add_video_bytes(
            bytes=video_data, format=VideoFormatEnum.MP4
        ).add_text(
            "What insights can you provide?"
        )

        message = builder.build()

        assert len(message[ConverseAPIFields.CONTENT]) == 5
        assert (
            message[ConverseAPIFields.CONTENT][0][ConverseAPIFields.TEXT]
            == "Please analyze these files:"
        )
        assert ConverseAPIFields.IMAGE in message[ConverseAPIFields.CONTENT][1]
        assert ConverseAPIFields.DOCUMENT in message[ConverseAPIFields.CONTENT][2]
        assert ConverseAPIFields.VIDEO in message[ConverseAPIFields.CONTENT][3]
        assert (
            message[ConverseAPIFields.CONTENT][4][ConverseAPIFields.TEXT]
            == "What insights can you provide?"
        )

    def test_build_creates_copy_of_content_blocks(self):
        """Test that build() creates a copy of content blocks."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        builder.add_text("Original text")

        message1 = builder.build()

        # Modify the builder
        builder.add_text("Additional text")
        message2 = builder.build()

        # First message should not be affected
        assert len(message1[ConverseAPIFields.CONTENT]) == 1
        assert len(message2[ConverseAPIFields.CONTENT]) == 2

    @patch("bestehorn_llmmanager.message_builder.FileTypeDetector")
    def test_format_conversion_error(self, mock_detector_class):
        """Test error when detected format cannot be converted to enum."""
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector

        # Mock detection with format that doesn't exist in enum
        mock_result = DetectionResult(
            detected_format="unknown_format",
            confidence=0.95,
            detection_method=DetectionMethodEnum.CONTENT,
            filename="test.unk",
        )
        mock_detector.detect_image_format.return_value = mock_result

        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        image_data = b"test data"

        with pytest.raises(RequestValidationError, match="Unsupported format"):
            builder.add_image_bytes(bytes=image_data, filename="test.unk")
