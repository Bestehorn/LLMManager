"""
Unit tests for FileTypeDetector.
Tests the main file type detection functionality with comprehensive coverage.
"""

import pytest
from unittest.mock import Mock, patch

from bestehorn_llmmanager.util.file_type_detector.file_type_detector import FileTypeDetector
from bestehorn_llmmanager.util.file_type_detector.base_detector import DetectionResult
from bestehorn_llmmanager.util.file_type_detector.detector_constants import (
    MagicBytesConstants,
    FileExtensionConstants,
    DetectionConstants,
    DetectorErrorMessages,
    DetectorLogMessages,
)
from bestehorn_llmmanager.message_builder_enums import DetectionMethodEnum


class TestFileTypeDetectorInitialization:
    """Test cases for FileTypeDetector initialization."""

    def test_initialization(self):
        """Test successful initialization."""
        detector = FileTypeDetector()
        
        assert hasattr(detector, '_logger')
        assert detector._logger.name == 'bestehorn_llmmanager.util.file_type_detector.file_type_detector'


class TestImageDetection:
    """Test cases for image format detection."""

    def test_detect_jpeg_by_content_jfif(self):
        """Test JPEG JFIF detection by content."""
        detector = FileTypeDetector()
        jpeg_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        
        result = detector.detect_image_format(content=jpeg_content, filename="test.jpg")
        
        assert result.is_successful
        assert result.detected_format == "jpeg"
        assert result.confidence >= DetectionConstants.MEDIUM_CONFIDENCE
        assert result.detection_method == DetectionMethodEnum.COMBINED

    def test_detect_jpeg_by_content_exif(self):
        """Test JPEG EXIF detection by content."""
        detector = FileTypeDetector()
        jpeg_content = b"\xff\xd8\xff\xe1\x00\x16Exif\x00\x00"
        
        result = detector.detect_image_format(content=jpeg_content, filename="test.jpg")
        
        assert result.is_successful
        assert result.detected_format == "jpeg"
        assert result.confidence >= DetectionConstants.HIGH_CONFIDENCE

    def test_detect_jpeg_by_content_raw(self):
        """Test JPEG raw detection by content."""
        detector = FileTypeDetector()
        jpeg_content = b"\xff\xd8\xff\xdb\x00\x43\x00\x01\x02\x03"  # Extended to 10 bytes
        
        result = detector.detect_image_format(content=jpeg_content, filename="test.jpg")
        
        assert result.is_successful
        assert result.detected_format == "jpeg"
        assert result.confidence >= DetectionConstants.HIGH_CONFIDENCE

    def test_detect_png_by_content(self):
        """Test PNG detection by content."""
        detector = FileTypeDetector()
        png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        
        result = detector.detect_image_format(content=png_content, filename="test.png")
        
        assert result.is_successful
        assert result.detected_format == "png"
        assert result.confidence >= DetectionConstants.HIGH_CONFIDENCE

    def test_detect_gif87a_by_content(self):
        """Test GIF87a detection by content."""
        detector = FileTypeDetector()
        gif_content = b"GIF87a\x01\x00\x01\x00"
        
        result = detector.detect_image_format(content=gif_content, filename="test.gif")
        
        assert result.is_successful
        assert result.detected_format == "gif"
        assert result.confidence >= DetectionConstants.HIGH_CONFIDENCE

    def test_detect_gif89a_by_content(self):
        """Test GIF89a detection by content."""
        detector = FileTypeDetector()
        gif_content = b"GIF89a\x01\x00\x01\x00"
        
        result = detector.detect_image_format(content=gif_content, filename="test.gif")
        
        assert result.is_successful
        assert result.detected_format == "gif"

    def test_detect_webp_by_content(self):
        """Test WEBP detection by content."""
        detector = FileTypeDetector()
        webp_content = b"RIFF\x1c\x00\x00\x00WEBP"
        
        result = detector.detect_image_format(content=webp_content, filename="test.webp")
        
        assert result.is_successful
        assert result.detected_format == "webp"
        assert result.confidence >= DetectionConstants.HIGH_CONFIDENCE

    def test_detect_image_by_extension_only(self):
        """Test image detection by extension when content detection fails."""
        detector = FileTypeDetector()
        unknown_content = b"unknown image format"
        
        result = detector.detect_image_format(content=unknown_content, filename="test.jpg")
        
        assert result.is_successful
        assert result.detected_format == "jpeg"
        assert result.confidence == DetectionConstants.MEDIUM_CONFIDENCE
        assert result.detection_method == DetectionMethodEnum.EXTENSION

    def test_detect_image_content_only_no_filename(self):
        """Test image detection by content only when no filename provided."""
        detector = FileTypeDetector()
        jpeg_content = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        
        result = detector.detect_image_format(content=jpeg_content)
        
        assert result.is_successful
        assert result.detected_format == "jpeg"
        assert result.detection_method == DetectionMethodEnum.CONTENT

    def test_detect_image_invalid_content(self):
        """Test image detection with invalid content."""
        detector = FileTypeDetector()
        
        # Test with empty bytes
        result = detector.detect_image_format(content=b"", filename="test.jpg")
        assert not result.is_successful
        
        # Test with non-bytes content
        result = detector.detect_image_format(content="not bytes", filename="test.jpg")  # type: ignore
        assert not result.is_successful

    def test_detect_image_insufficient_content(self):
        """Test image detection with insufficient content."""
        detector = FileTypeDetector()
        small_content = b"123"  # Less than 8 bytes
        
        result = detector.detect_image_format(content=small_content, filename="test.jpg")
        
        # Should fall back to extension detection
        assert result.is_successful
        assert result.detected_format == "jpeg"
        assert result.detection_method == DetectionMethodEnum.EXTENSION

    def test_detect_image_no_detection_possible(self):
        """Test image detection when no method succeeds."""
        detector = FileTypeDetector()
        unknown_content = b"definitely not an image format"
        
        result = detector.detect_image_format(content=unknown_content, filename="test.unknown")
        
        assert not result.is_successful
        assert result.error_message is not None

    def test_detect_image_format_mismatch(self):
        """Test image detection when extension and content disagree."""
        detector = FileTypeDetector()
        png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        
        # PNG content but JPEG extension
        result = detector.detect_image_format(content=png_content, filename="test.jpg")
        
        assert result.is_successful
        assert result.detected_format == "png"  # Content wins
        assert result.detection_method == DetectionMethodEnum.COMBINED
        assert result.confidence < DetectionConstants.HIGH_CONFIDENCE  # Penalty for disagreement


class TestDocumentDetection:
    """Test cases for document format detection."""

    def test_detect_pdf_by_content(self):
        """Test PDF detection by content."""
        detector = FileTypeDetector()
        pdf_content = b"%PDF-1.4\x01\x00\x00\x00"
        
        result = detector.detect_document_format(content=pdf_content, filename="test.pdf")
        
        assert result.is_successful
        assert result.detected_format == "pdf"
        assert result.confidence >= DetectionConstants.HIGH_CONFIDENCE

    def test_detect_docx_by_content(self):
        """Test DOCX detection by content."""
        detector = FileTypeDetector()
        # ZIP signature + DOCX content indicator
        docx_content = b"PK\x03\x04" + b"\x00" * 100 + b"[Content_Types].xml" + b"\x00" * 100
        
        result = detector.detect_document_format(content=docx_content, filename="test.docx")
        
        assert result.is_successful
        assert result.detected_format == "docx"
        assert result.confidence >= DetectionConstants.MEDIUM_CONFIDENCE

    def test_detect_xlsx_by_content(self):
        """Test XLSX detection by content."""
        detector = FileTypeDetector()
        # ZIP signature + XLSX content indicator
        xlsx_content = b"PK\x03\x04" + b"\x00" * 100 + b"xl/" + b"\x00" * 100
        
        result = detector.detect_document_format(content=xlsx_content, filename="test.xlsx")
        
        assert result.is_successful
        assert result.detected_format == "xlsx"

    def test_detect_doc_by_content_with_extension(self):
        """Test DOC detection by content with .doc extension."""
        detector = FileTypeDetector()
        doc_content = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100
        
        result = detector.detect_document_format(content=doc_content, filename="test.doc")
        
        assert result.is_successful
        assert result.detected_format == "doc"

    def test_detect_xls_by_content_with_extension(self):
        """Test XLS detection by content with .xls extension."""
        detector = FileTypeDetector()
        xls_content = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100
        
        result = detector.detect_document_format(content=xls_content, filename="test.xls")
        
        assert result.is_successful
        assert result.detected_format == "xls"

    def test_detect_doc_by_content_no_extension(self):
        """Test DOC detection by content without extension (defaults to doc)."""
        detector = FileTypeDetector()
        doc_content = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100
        
        result = detector.detect_document_format(content=doc_content)
        
        assert result.is_successful
        assert result.detected_format == "doc"  # Default when no extension

    def test_detect_html_by_content_doctype(self):
        """Test HTML detection by content with DOCTYPE."""
        detector = FileTypeDetector()
        html_content = b"<!DOCTYPE html><html><head></head><body></body></html>"
        
        result = detector.detect_document_format(content=html_content, filename="test.html")
        
        assert result.is_successful
        assert result.detected_format == "html"

    def test_detect_html_by_content_html_tag(self):
        """Test HTML detection by content with <html> tag."""
        detector = FileTypeDetector()
        html_content = b"<html><head></head><body></body></html>"
        
        result = detector.detect_document_format(content=html_content, filename="test.html")
        
        assert result.is_successful
        assert result.detected_format == "html"

    def test_detect_document_by_extension_only(self):
        """Test document detection by extension when content detection fails."""
        detector = FileTypeDetector()
        unknown_content = b"unknown document format"
        
        result = detector.detect_document_format(content=unknown_content, filename="test.csv")
        
        assert result.is_successful
        assert result.detected_format == "csv"
        assert result.detection_method == DetectionMethodEnum.EXTENSION

    def test_detect_document_insufficient_content(self):
        """Test document detection with insufficient content."""
        detector = FileTypeDetector()
        small_content = b"12"  # Less than 4 bytes
        
        result = detector.detect_document_format(content=small_content, filename="test.pdf")
        
        # Should fall back to extension detection
        assert result.is_successful
        assert result.detected_format == "pdf"
        assert result.detection_method == DetectionMethodEnum.EXTENSION


class TestVideoDetection:
    """Test cases for video format detection."""

    def test_detect_mp4_by_content(self):
        """Test MP4 detection by content."""
        detector = FileTypeDetector()
        mp4_content = b"\x00\x00\x00\x18ftypmp4\x00\x00\x00\x00"
        
        result = detector.detect_video_format(content=mp4_content, filename="test.mp4")
        
        assert result.is_successful
        assert result.detected_format == "mp4"
        assert result.confidence >= DetectionConstants.HIGH_CONFIDENCE

    def test_detect_mov_by_content(self):
        """Test MOV detection by content."""
        detector = FileTypeDetector()
        mov_content = b"\x00\x00\x00\x14ftypqt\x00\x00\x00\x00" + b"\x00" * 20
        
        result = detector.detect_video_format(content=mov_content, filename="test.mov")
        
        assert result.is_successful
        assert result.detected_format == "mov"

    def test_detect_avi_by_content(self):
        """Test AVI detection by content."""
        detector = FileTypeDetector()
        avi_content = b"RIFF\x1c\x00\x00\x00AVI "
        
        result = detector.detect_video_format(content=avi_content, filename="test.avi")
        
        assert result.is_successful
        assert result.detected_format == "avi"

    def test_detect_webm_by_content(self):
        """Test WEBM detection by content."""
        detector = FileTypeDetector()
        webm_content = b"\x1a\x45\xdf\xa3\x00\x00\x00\x00"
        
        result = detector.detect_video_format(content=webm_content, filename="test.webm")
        
        assert result.is_successful
        assert result.detected_format == "webm"

    def test_detect_mkv_by_content_with_extension(self):
        """Test MKV detection by content with .mkv extension."""
        detector = FileTypeDetector()
        mkv_content = b"\x1a\x45\xdf\xa3\x00\x00\x00\x00"
        
        result = detector.detect_video_format(content=mkv_content, filename="test.mkv")
        
        assert result.is_successful
        assert result.detected_format == "mkv"

    def test_detect_webm_by_content_no_extension(self):
        """Test WEBM detection by content without extension (defaults to webm)."""
        detector = FileTypeDetector()
        webm_content = b"\x1a\x45\xdf\xa3\x00\x00\x00\x00\x00\x00\x00\x00"  # 12 bytes minimum
        
        result = detector.detect_video_format(content=webm_content)
        
        assert result.is_successful
        assert result.detected_format == "webm"  # Default when no extension

    def test_detect_video_insufficient_content(self):
        """Test video detection with insufficient content."""
        detector = FileTypeDetector()
        small_content = b"123456789"  # Less than 12 bytes
        
        result = detector.detect_video_format(content=small_content, filename="test.mp4")
        
        # Should fall back to extension detection
        assert result.is_successful
        assert result.detected_format == "mp4"
        assert result.detection_method == DetectionMethodEnum.EXTENSION


class TestExtensionDetection:
    """Test cases for extension-based detection."""

    def test_detect_by_extension_success(self):
        """Test successful extension detection."""
        detector = FileTypeDetector()
        
        # Test various image extensions
        result = detector._detect_by_extension(
            filename="test.jpg",
            supported_formats=["jpeg", "png", "gif"],
            extension_map=FileExtensionConstants.IMAGE_EXTENSIONS
        )
        
        assert result is not None
        assert result.detected_format == "jpeg"
        assert result.confidence == DetectionConstants.MEDIUM_CONFIDENCE
        assert result.detection_method == DetectionMethodEnum.EXTENSION

    def test_detect_by_extension_no_filename(self):
        """Test extension detection with no filename."""
        detector = FileTypeDetector()
        
        result = detector._detect_by_extension(
            filename=None,
            supported_formats=["jpeg"],
            extension_map=FileExtensionConstants.IMAGE_EXTENSIONS
        )
        
        assert result is None

    def test_detect_by_extension_no_extension(self):
        """Test extension detection with filename but no extension."""
        detector = FileTypeDetector()
        
        result = detector._detect_by_extension(
            filename="testfile",
            supported_formats=["jpeg"],
            extension_map=FileExtensionConstants.IMAGE_EXTENSIONS
        )
        
        assert result is None

    def test_detect_by_extension_unsupported_extension(self):
        """Test extension detection with unsupported extension."""
        detector = FileTypeDetector()
        
        result = detector._detect_by_extension(
            filename="test.unknown",
            supported_formats=["jpeg"],
            extension_map=FileExtensionConstants.IMAGE_EXTENSIONS
        )
        
        assert result is None

    def test_detect_by_extension_unsupported_format(self):
        """Test extension detection with unsupported format."""
        detector = FileTypeDetector()
        
        # Extension maps to a format but it's not in supported_formats
        with patch.object(detector._logger, 'warning') as mock_warning:
            result = detector._detect_by_extension(
                filename="test.jpg",
                supported_formats=["png"],  # jpeg not supported
                extension_map=FileExtensionConstants.IMAGE_EXTENSIONS
            )
            
            assert result is None
            mock_warning.assert_called()


class TestCombineDetectionResults:
    """Test cases for combining detection results."""

    def test_combine_results_agreement(self):
        """Test combining results when extension and content agree."""
        detector = FileTypeDetector()
        
        extension_result = DetectionResult(
            detected_format="jpeg",
            confidence=DetectionConstants.MEDIUM_CONFIDENCE,
            detection_method=DetectionMethodEnum.EXTENSION,
            filename="test.jpg"
        )
        
        content_result = DetectionResult(
            detected_format="jpeg",
            confidence=DetectionConstants.HIGH_CONFIDENCE,
            detection_method=DetectionMethodEnum.CONTENT,
            filename="test.jpg"
        )
        
        combined = detector._combine_detection_results(
            extension_result=extension_result,
            content_result=content_result,
            filename="test.jpg"
        )
        
        assert combined.detected_format == "jpeg"
        assert combined.confidence == DetectionConstants.HIGH_CONFIDENCE
        assert combined.detection_method == DetectionMethodEnum.COMBINED
        assert combined.metadata is not None
        assert combined.metadata["agreement"] is True

    def test_combine_results_disagreement(self):
        """Test combining results when extension and content disagree."""
        detector = FileTypeDetector()
        
        extension_result = DetectionResult(
            detected_format="jpeg",
            confidence=DetectionConstants.MEDIUM_CONFIDENCE,
            detection_method=DetectionMethodEnum.EXTENSION,
            filename="test.jpg"
        )
        
        content_result = DetectionResult(
            detected_format="png",
            confidence=DetectionConstants.HIGH_CONFIDENCE,
            detection_method=DetectionMethodEnum.CONTENT,
            filename="test.jpg"
        )
        
        with patch.object(detector._logger, 'warning') as mock_warning:
            combined = detector._combine_detection_results(
                extension_result=extension_result,
                content_result=content_result,
                filename="test.jpg"
            )
            
            assert combined.detected_format == "png"  # Content wins
            assert combined.confidence < content_result.confidence  # Penalty applied
            assert combined.detection_method == DetectionMethodEnum.COMBINED
            assert combined.metadata is not None
            assert combined.metadata["agreement"] is False
            mock_warning.assert_called()

    def test_combine_results_content_only(self):
        """Test combining results with only content detection."""
        detector = FileTypeDetector()
        
        content_result = DetectionResult(
            detected_format="png",
            confidence=DetectionConstants.HIGH_CONFIDENCE,
            detection_method=DetectionMethodEnum.CONTENT,
            filename="test"
        )
        
        combined = detector._combine_detection_results(
            extension_result=None,
            content_result=content_result,
            filename="test"
        )
        
        assert combined == content_result

    def test_combine_results_extension_only(self):
        """Test combining results with only extension detection."""
        detector = FileTypeDetector()
        
        extension_result = DetectionResult(
            detected_format="jpeg",
            confidence=DetectionConstants.MEDIUM_CONFIDENCE,
            detection_method=DetectionMethodEnum.EXTENSION,
            filename="test.jpg"
        )
        
        combined = detector._combine_detection_results(
            extension_result=extension_result,
            content_result=None,
            filename="test.jpg"
        )
        
        assert combined == extension_result

    def test_combine_results_no_detection(self):
        """Test combining results when no detection succeeded."""
        detector = FileTypeDetector()
        
        combined = detector._combine_detection_results(
            extension_result=None,
            content_result=None,
            filename="test.unknown"
        )
        
        assert not combined.is_successful
        assert combined.error_message is not None
        assert combined.detection_method == DetectionMethodEnum.COMBINED


class TestContentDetectionPrivateMethods:
    """Test cases for private content detection methods."""

    def test_detect_image_by_content_webp_insufficient_content(self):
        """Test WEBP detection with insufficient content."""
        detector = FileTypeDetector()
        # RIFF signature but not enough content for WEBP check
        webp_content = b"RIFF\x08\x00\x00\x00"  # Only 8 bytes
        
        result = detector._detect_image_by_content(content=webp_content)
        
        assert result is None  # Should not detect as WEBP

    def test_detect_document_by_content_zip_insufficient_content(self):
        """Test ZIP-based document detection with insufficient content."""
        detector = FileTypeDetector()
        zip_content = b"PK\x03\x04\x00\x00\x00\x00"  # ZIP signature but not enough content
        
        result = detector._detect_document_by_content(content=zip_content)
        
        # Should not detect DOCX/XLSX without sufficient content
        assert result is None

    def test_detect_video_by_content_avi_insufficient_content(self):
        """Test AVI detection with insufficient content."""
        detector = FileTypeDetector()
        avi_content = b"RIFF\x08\x00\x00\x00"  # RIFF but not enough for AVI check
        
        result = detector._detect_video_by_content(content=avi_content)
        
        assert result is None  # Should not detect as AVI


class TestLoggingAndMetadata:
    """Test cases for logging and metadata."""

    def test_logging_during_detection(self):
        """Test that appropriate logging occurs during detection."""
        detector = FileTypeDetector()
        
        with patch.object(detector._logger, 'debug') as mock_debug, \
             patch.object(detector._logger, 'info') as mock_info:
            
            jpeg_content = b"\xff\xd8\xff\xe0\x00\x10JFIF"
            result = detector.detect_image_format(content=jpeg_content, filename="test.jpg")
            
            # Verify logging calls were made
            mock_debug.assert_called()
            mock_info.assert_called()

    def test_metadata_in_results(self):
        """Test that detection results contain appropriate metadata."""
        detector = FileTypeDetector()
        jpeg_content = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        
        result = detector.detect_image_format(content=jpeg_content, filename="test.jpg")
        
        assert result.is_successful
        assert result.metadata is not None
        assert "extension_confidence" in result.metadata
        assert "content_confidence" in result.metadata
        assert "agreement" in result.metadata

    def test_safe_filename_handling(self):
        """Test safe filename handling in logging."""
        detector = FileTypeDetector()
        
        # Test with None filename
        safe_name = detector._get_safe_filename(filename=None)
        assert safe_name == "unnamed_file"
        
        # Test with actual filename
        safe_name = detector._get_safe_filename(filename="test.jpg")
        assert safe_name == "test.jpg"


class TestEdgeCases:
    """Test cases for edge cases and error conditions."""

    def test_all_mp4_signatures(self):
        """Test detection of all MP4 signature variants."""
        detector = FileTypeDetector()
        
        for signature in MagicBytesConstants.MP4_SIGNATURES:
            mp4_content = signature + b"\x00" * 20
            result = detector.detect_video_format(content=mp4_content, filename="test.mp4")
            assert result.is_successful
            assert result.detected_format == "mp4"

    def test_all_jpeg_signatures(self):
        """Test detection of all JPEG signature variants."""
        detector = FileTypeDetector()
        
        for signature in MagicBytesConstants.JPEG_SIGNATURES:
            jpeg_content = signature + b"\x00" * 20
            result = detector.detect_image_format(content=jpeg_content, filename="test.jpg")
            assert result.is_successful
            assert result.detected_format == "jpeg"

    def test_all_gif_signatures(self):
        """Test detection of all GIF signature variants."""
        detector = FileTypeDetector()
        
        for signature in MagicBytesConstants.GIF_SIGNATURES:
            gif_content = signature + b"\x00" * 20
            result = detector.detect_image_format(content=gif_content, filename="test.gif")
            assert result.is_successful
            assert result.detected_format == "gif"

    def test_all_html_signatures(self):
        """Test detection of all HTML signature variants."""
        detector = FileTypeDetector()
        
        for signature in MagicBytesConstants.HTML_SIGNATURES:
            html_content = signature + b"<head></head><body></body></html>"
            result = detector.detect_document_format(content=html_content, filename="test.html")
            assert result.is_successful
            assert result.detected_format == "html"

    def test_case_insensitive_extensions(self):
        """Test that extensions are handled case-insensitively."""
        detector = FileTypeDetector()
        
        # Test uppercase extension
        result = detector.detect_image_format(content=b"unknown", filename="test.JPG")
        assert result.is_successful
        assert result.detected_format == "jpeg"
        
        # Test mixed case extension
        result = detector.detect_image_format(content=b"unknown", filename="test.Png")
        assert result.is_successful
        assert result.detected_format == "png"

    def test_htm_extension_maps_to_html(self):
        """Test that .htm extension maps to html format."""
        detector = FileTypeDetector()
        
        result = detector.detect_document_format(content=b"unknown", filename="test.htm")
        assert result.is_successful
        assert result.detected_format == "html"

    def test_markdown_extensions(self):
        """Test that both .md and .markdown extensions work."""
        detector = FileTypeDetector()
        
        result = detector.detect_document_format(content=b"unknown", filename="README.md")
        assert result.is_successful
        assert result.detected_format == "md"
        
        result = detector.detect_document_format(content=b"unknown", filename="README.markdown")
        assert result.is_successful
        assert result.detected_format == "md"
