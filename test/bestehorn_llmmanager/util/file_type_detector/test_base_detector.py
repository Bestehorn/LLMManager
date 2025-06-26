"""
Unit tests for base detector interface and data structures.
Tests the abstract base class and DetectionResult data class.
"""

from unittest.mock import Mock

import pytest

from src.bestehorn_llmmanager.message_builder_enums import DetectionMethodEnum
from src.bestehorn_llmmanager.util.file_type_detector.base_detector import (
    BaseDetector,
    DetectionResult,
)


class TestDetectionResult:
    """Test cases for DetectionResult data class."""

    def test_detection_result_creation(self):
        """Test creating a DetectionResult instance."""
        result = DetectionResult(
            detected_format="jpeg",
            confidence=0.95,
            detection_method=DetectionMethodEnum.CONTENT,
            filename="test.jpg",
        )

        assert result.detected_format == "jpeg"
        assert result.confidence == 0.95
        assert result.detection_method == DetectionMethodEnum.CONTENT
        assert result.filename == "test.jpg"
        assert result.error_message is None
        assert result.metadata is None

    def test_detection_result_with_error(self):
        """Test creating a DetectionResult with error."""
        result = DetectionResult(
            detected_format="unknown",
            confidence=0.0,
            detection_method=DetectionMethodEnum.CONTENT,
            error_message="Detection failed",
        )

        assert result.detected_format == "unknown"
        assert result.confidence == 0.0
        assert result.error_message == "Detection failed"
        assert not result.is_successful

    def test_detection_result_with_metadata(self):
        """Test creating a DetectionResult with metadata."""
        metadata = {"magic_bytes": "ffd8ffe0", "extension": "jpg"}
        result = DetectionResult(
            detected_format="jpeg",
            confidence=0.95,
            detection_method=DetectionMethodEnum.COMBINED,
            metadata=metadata,
        )

        assert result.metadata == metadata
        assert result.metadata is not None
        assert result.metadata["magic_bytes"] == "ffd8ffe0"

    def test_is_successful_property(self):
        """Test is_successful property logic."""
        # Successful case
        success_result = DetectionResult(
            detected_format="jpeg", confidence=0.8, detection_method=DetectionMethodEnum.CONTENT
        )
        assert success_result.is_successful

        # Failed case - with error message
        error_result = DetectionResult(
            detected_format="unknown",
            confidence=0.5,
            detection_method=DetectionMethodEnum.CONTENT,
            error_message="Failed to detect",
        )
        assert not error_result.is_successful

        # Failed case - zero confidence
        zero_conf_result = DetectionResult(
            detected_format="jpeg", confidence=0.0, detection_method=DetectionMethodEnum.CONTENT
        )
        assert not zero_conf_result.is_successful

    def test_is_high_confidence_property(self):
        """Test is_high_confidence property logic."""
        # High confidence
        high_conf = DetectionResult(
            detected_format="jpeg", confidence=0.9, detection_method=DetectionMethodEnum.CONTENT
        )
        assert high_conf.is_high_confidence

        # Medium confidence
        med_conf = DetectionResult(
            detected_format="jpeg", confidence=0.7, detection_method=DetectionMethodEnum.CONTENT
        )
        assert not med_conf.is_high_confidence

        # Exactly at threshold
        threshold_conf = DetectionResult(
            detected_format="jpeg", confidence=0.8, detection_method=DetectionMethodEnum.CONTENT
        )
        assert threshold_conf.is_high_confidence

    def test_detection_result_string_representation(self):
        """Test string representation of DetectionResult."""
        result = DetectionResult(
            detected_format="jpeg", confidence=0.95, detection_method=DetectionMethodEnum.CONTENT
        )

        str_repr = str(result)
        assert "successful" in str_repr
        assert "jpeg" in str_repr
        assert "0.95" in str_repr
        assert "content" in str_repr

        # Test failed result string representation
        failed_result = DetectionResult(
            detected_format="unknown",
            confidence=0.0,
            detection_method=DetectionMethodEnum.CONTENT,
            error_message="Failed",
        )

        failed_str = str(failed_result)
        assert "failed" in failed_str

    def test_detection_result_immutability(self):
        """Test that DetectionResult is immutable (frozen dataclass)."""
        result = DetectionResult(
            detected_format="jpeg", confidence=0.95, detection_method=DetectionMethodEnum.CONTENT
        )

        # Should not be able to modify attributes (frozen dataclass)
        with pytest.raises((AttributeError, TypeError)):
            result.detected_format = "png"  # type: ignore

        with pytest.raises((AttributeError, TypeError)):
            result.confidence = 0.5  # type: ignore


class ConcreteDetector(BaseDetector):
    """Concrete implementation of BaseDetector for testing."""

    def detect_image_format(self, content: bytes, filename=None):
        return self._create_success_result(
            detected_format="jpeg",
            confidence=0.9,
            detection_method=DetectionMethodEnum.CONTENT,
            filename=filename,
        )

    def detect_document_format(self, content: bytes, filename=None):
        return self._create_success_result(
            detected_format="pdf",
            confidence=0.8,
            detection_method=DetectionMethodEnum.CONTENT,
            filename=filename,
        )

    def detect_video_format(self, content: bytes, filename=None):
        return self._create_success_result(
            detected_format="mp4",
            confidence=0.7,
            detection_method=DetectionMethodEnum.CONTENT,
            filename=filename,
        )


class TestBaseDetector:
    """Test cases for BaseDetector abstract base class."""

    def test_base_detector_instantiation(self):
        """Test that BaseDetector cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseDetector()  # type: ignore

    def test_concrete_detector_instantiation(self):
        """Test that concrete detector can be instantiated."""
        detector = ConcreteDetector()
        assert detector is not None
        assert hasattr(detector, "_logger")

    def test_validate_content_valid_bytes(self):
        """Test _validate_content with valid bytes."""
        detector = ConcreteDetector()

        valid_content = b"test content"
        assert detector._validate_content(content=valid_content) is True

    def test_validate_content_empty_bytes(self):
        """Test _validate_content with empty bytes."""
        detector = ConcreteDetector()

        empty_content = b""
        assert detector._validate_content(content=empty_content) is False

    def test_validate_content_invalid_type(self):
        """Test _validate_content with invalid type."""
        detector = ConcreteDetector()

        invalid_content = "not bytes"
        assert detector._validate_content(content=invalid_content) is False  # type: ignore

    def test_get_safe_filename_with_filename(self):
        """Test _get_safe_filename with provided filename."""
        detector = ConcreteDetector()

        filename = "test.jpg"
        safe_name = detector._get_safe_filename(filename=filename)
        assert safe_name == "test.jpg"

    def test_get_safe_filename_without_filename(self):
        """Test _get_safe_filename without filename."""
        detector = ConcreteDetector()

        safe_name = detector._get_safe_filename(filename=None)
        assert safe_name == "unnamed_file"

    def test_create_error_result(self):
        """Test _create_error_result method."""
        detector = ConcreteDetector()

        error_result = detector._create_error_result(
            error_message="Test error",
            filename="test.jpg",
            detection_method=DetectionMethodEnum.CONTENT,
        )

        assert isinstance(error_result, DetectionResult)
        assert error_result.detected_format == "unknown"
        assert error_result.confidence == 0.0
        assert error_result.detection_method == DetectionMethodEnum.CONTENT
        assert error_result.filename == "test.jpg"
        assert error_result.error_message == "Test error"
        assert not error_result.is_successful

    def test_create_success_result(self):
        """Test _create_success_result method."""
        detector = ConcreteDetector()

        success_result = detector._create_success_result(
            detected_format="jpeg",
            confidence=0.95,
            detection_method=DetectionMethodEnum.CONTENT,
            filename="test.jpg",
            metadata={"test": "data"},
        )

        assert isinstance(success_result, DetectionResult)
        assert success_result.detected_format == "jpeg"
        assert success_result.confidence == 0.95
        assert success_result.detection_method == DetectionMethodEnum.CONTENT
        assert success_result.filename == "test.jpg"
        assert success_result.metadata == {"test": "data"}
        assert success_result.error_message is None
        assert success_result.is_successful

    def test_concrete_detector_methods(self):
        """Test that concrete detector implements abstract methods."""
        detector = ConcreteDetector()
        test_content = b"test content"

        # Test image detection
        image_result = detector.detect_image_format(content=test_content, filename="test.jpg")
        assert image_result.detected_format == "jpeg"
        assert image_result.is_successful

        # Test document detection
        doc_result = detector.detect_document_format(content=test_content, filename="test.pdf")
        assert doc_result.detected_format == "pdf"
        assert doc_result.is_successful

        # Test video detection
        video_result = detector.detect_video_format(content=test_content, filename="test.mp4")
        assert video_result.detected_format == "mp4"
        assert video_result.is_successful


class TestDetectorIntegration:
    """Test integration aspects of detector components."""

    def test_detection_result_with_all_enum_values(self):
        """Test DetectionResult with all DetectionMethodEnum values."""
        methods = [
            DetectionMethodEnum.EXTENSION,
            DetectionMethodEnum.CONTENT,
            DetectionMethodEnum.COMBINED,
            DetectionMethodEnum.MANUAL,
        ]

        for method in methods:
            result = DetectionResult(
                detected_format="test", confidence=0.8, detection_method=method
            )
            assert result.detection_method == method
            assert result.is_successful

    def test_confidence_edge_cases(self):
        """Test DetectionResult with edge case confidence values."""
        # Test minimum confidence
        min_result = DetectionResult(
            detected_format="test", confidence=0.0, detection_method=DetectionMethodEnum.CONTENT
        )
        assert not min_result.is_successful
        assert not min_result.is_high_confidence

        # Test maximum confidence
        max_result = DetectionResult(
            detected_format="test", confidence=1.0, detection_method=DetectionMethodEnum.CONTENT
        )
        assert max_result.is_successful
        assert max_result.is_high_confidence

        # Test just below high confidence threshold
        below_threshold = DetectionResult(
            detected_format="test", confidence=0.79, detection_method=DetectionMethodEnum.CONTENT
        )
        assert below_threshold.is_successful
        assert not below_threshold.is_high_confidence

    def test_detector_logging_setup(self):
        """Test that detector sets up logging correctly."""
        detector = ConcreteDetector()

        # Check that logger is set up
        assert hasattr(detector, "_logger")
        assert detector._logger is not None
        assert detector._logger.name == "ConcreteDetector"
