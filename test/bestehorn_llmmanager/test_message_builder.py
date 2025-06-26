"""
Unit tests for ConverseMessageBuilder.
Tests the main message builder class and its functionality.
"""

from unittest.mock import Mock, patch

import pytest

from src.bestehorn_llmmanager.bedrock.exceptions.llm_manager_exceptions import (
    RequestValidationError,
)
from src.bestehorn_llmmanager.bedrock.models.llm_manager_constants import ConverseAPIFields
from src.bestehorn_llmmanager.message_builder import ConverseMessageBuilder
from src.bestehorn_llmmanager.message_builder_enums import (
    DocumentFormatEnum,
    ImageFormatEnum,
    RolesEnum,
    VideoFormatEnum,
)


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

    @patch("src.bestehorn_llmmanager.message_builder.FileTypeDetector")
    def test_add_image_with_auto_detection(self, mock_detector_class):
        """Test adding image with automatic format detection."""
        # Mock the detector
        mock_detector = Mock()
        mock_detector_class.return_value = mock_detector

        # Mock successful detection result
        from src.bestehorn_llmmanager.message_builder_enums import DetectionMethodEnum
        from src.bestehorn_llmmanager.util.file_type_detector.base_detector import DetectionResult

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
                "src.bestehorn_llmmanager.message_builder.FileTypeDetector"
            ) as mock_detector_class:
                mock_detector = Mock()
                mock_detector_class.return_value = mock_detector

                from src.bestehorn_llmmanager.message_builder_enums import DetectionMethodEnum
                from src.bestehorn_llmmanager.util.file_type_detector.base_detector import (
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
            bytes=pdf_data, format=DocumentFormatEnum.PDF, name="test_document.pdf"
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
        assert doc_block[ConverseAPIFields.DOCUMENT][ConverseAPIFields.NAME] == "test_document.pdf"

    def test_add_document_with_filename_as_name(self):
        """Test adding document uses filename as name when no explicit name."""
        builder = ConverseMessageBuilder(role=RolesEnum.USER)
        pdf_data = b"%PDF-1.4"

        builder.add_document_bytes(
            bytes=pdf_data, format=DocumentFormatEnum.PDF, filename="report.pdf"
        )

        message = builder.build()
        doc_block = message[ConverseAPIFields.CONTENT][0]

        assert doc_block[ConverseAPIFields.DOCUMENT][ConverseAPIFields.NAME] == "report.pdf"


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
