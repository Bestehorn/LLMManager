"""
Unit tests for message builder constants.
Tests all constant classes used in the ConverseMessageBuilder system.
"""

import pytest
from typing import Dict, List

from src.bedrock.models.message_builder_constants import (
    MessageBuilderFields, MessageBuilderConfig, MessageBuilderLogMessages,
    MessageBuilderErrorMessages, SupportedFormats
)


class TestMessageBuilderFields:
    """Test cases for MessageBuilderFields constants."""
    
    def test_field_constants_are_strings(self):
        """Test that all field constants are strings."""
        assert isinstance(MessageBuilderFields.ROLE, str)
        assert isinstance(MessageBuilderFields.CONTENT_BLOCKS, str)
        assert isinstance(MessageBuilderFields.FILENAME, str)
        assert isinstance(MessageBuilderFields.DETECTED_FORMAT, str)
        assert isinstance(MessageBuilderFields.DETECTION_METHOD, str)
        assert isinstance(MessageBuilderFields.CONFIDENCE, str)
    
    def test_field_constant_values(self):
        """Test specific field constant values."""
        assert MessageBuilderFields.ROLE == "role"
        assert MessageBuilderFields.CONTENT_BLOCKS == "content_blocks"
        assert MessageBuilderFields.FILENAME == "filename"
        assert MessageBuilderFields.DETECTED_FORMAT == "detected_format"
        assert MessageBuilderFields.DETECTION_METHOD == "detection_method"
        assert MessageBuilderFields.CONFIDENCE == "confidence"


class TestMessageBuilderConfig:
    """Test cases for MessageBuilderConfig constants."""
    
    def test_config_constants_types(self):
        """Test that config constants have correct types."""
        assert isinstance(MessageBuilderConfig.DEFAULT_DETECTION_CONFIDENCE, float)
        assert isinstance(MessageBuilderConfig.MIN_DETECTION_CONFIDENCE, float)
        assert isinstance(MessageBuilderConfig.MAX_CONTENT_BLOCKS_PER_MESSAGE, int)
        assert isinstance(MessageBuilderConfig.MAX_IMAGE_SIZE_BYTES, int)
        assert isinstance(MessageBuilderConfig.MAX_DOCUMENT_SIZE_BYTES, int)
        assert isinstance(MessageBuilderConfig.MAX_VIDEO_SIZE_BYTES, int)
        assert isinstance(MessageBuilderConfig.MAGIC_BYTES_READ_SIZE, int)
        assert isinstance(MessageBuilderConfig.EXTENSION_DETECTION_ENABLED, bool)
        assert isinstance(MessageBuilderConfig.CONTENT_DETECTION_ENABLED, bool)
    
    def test_confidence_values(self):
        """Test confidence-related constants."""
        assert 0.0 <= MessageBuilderConfig.DEFAULT_DETECTION_CONFIDENCE <= 1.0
        assert 0.0 <= MessageBuilderConfig.MIN_DETECTION_CONFIDENCE <= 1.0
        assert MessageBuilderConfig.MIN_DETECTION_CONFIDENCE <= MessageBuilderConfig.DEFAULT_DETECTION_CONFIDENCE
    
    def test_size_limits(self):
        """Test size limit constants are reasonable."""
        assert MessageBuilderConfig.MAX_IMAGE_SIZE_BYTES > 0
        assert MessageBuilderConfig.MAX_DOCUMENT_SIZE_BYTES > 0
        assert MessageBuilderConfig.MAX_VIDEO_SIZE_BYTES > 0
        
        # Video should typically be larger than image/document limits
        assert MessageBuilderConfig.MAX_VIDEO_SIZE_BYTES > MessageBuilderConfig.MAX_IMAGE_SIZE_BYTES
        assert MessageBuilderConfig.MAX_VIDEO_SIZE_BYTES > MessageBuilderConfig.MAX_DOCUMENT_SIZE_BYTES
    
    def test_content_block_limit(self):
        """Test content block limit is reasonable."""
        assert MessageBuilderConfig.MAX_CONTENT_BLOCKS_PER_MESSAGE > 0
        assert MessageBuilderConfig.MAX_CONTENT_BLOCKS_PER_MESSAGE <= 1000  # Reasonable upper bound
    
    def test_detection_settings(self):
        """Test detection-related settings."""
        assert MessageBuilderConfig.MAGIC_BYTES_READ_SIZE > 0
        assert MessageBuilderConfig.MAGIC_BYTES_READ_SIZE <= 1024  # Reasonable upper bound
        assert MessageBuilderConfig.EXTENSION_DETECTION_ENABLED is True
        assert MessageBuilderConfig.CONTENT_DETECTION_ENABLED is True


class TestMessageBuilderLogMessages:
    """Test cases for MessageBuilderLogMessages constants."""
    
    def test_log_messages_are_strings(self):
        """Test that all log message constants are strings."""
        assert isinstance(MessageBuilderLogMessages.AUTO_DETECTION_SUCCESS, str)
        assert isinstance(MessageBuilderLogMessages.AUTO_DETECTION_FALLBACK, str)
        assert isinstance(MessageBuilderLogMessages.DETECTION_MISMATCH, str)
        assert isinstance(MessageBuilderLogMessages.DETECTION_LOW_CONFIDENCE, str)
        assert isinstance(MessageBuilderLogMessages.MESSAGE_BUILD_STARTED, str)
        assert isinstance(MessageBuilderLogMessages.MESSAGE_BUILD_COMPLETED, str)
        assert isinstance(MessageBuilderLogMessages.CONTENT_BLOCK_ADDED, str)
        assert isinstance(MessageBuilderLogMessages.CONTENT_SIZE_WARNING, str)
        assert isinstance(MessageBuilderLogMessages.CONTENT_BLOCK_LIMIT_WARNING, str)
    
    def test_log_messages_contain_placeholders(self):
        """Test that log messages contain expected format placeholders."""
        # Auto-detection messages should have filename and type placeholders
        assert "{filename}" in MessageBuilderLogMessages.AUTO_DETECTION_SUCCESS
        assert "{detected_type}" in MessageBuilderLogMessages.AUTO_DETECTION_SUCCESS
        assert "{method}" in MessageBuilderLogMessages.AUTO_DETECTION_SUCCESS
        assert "{confidence" in MessageBuilderLogMessages.AUTO_DETECTION_SUCCESS
        
        # Build messages should have count placeholders
        assert "{role}" in MessageBuilderLogMessages.MESSAGE_BUILD_STARTED
        assert "{block_count}" in MessageBuilderLogMessages.MESSAGE_BUILD_STARTED
        assert "{block_count}" in MessageBuilderLogMessages.MESSAGE_BUILD_COMPLETED
        
        # Content messages should have type and size placeholders
        assert "{content_type}" in MessageBuilderLogMessages.CONTENT_BLOCK_ADDED
        assert "{size}" in MessageBuilderLogMessages.CONTENT_BLOCK_ADDED
    
    def test_log_message_formatting(self):
        """Test that log messages can be formatted with sample data."""
        # Test auto-detection success message
        formatted = MessageBuilderLogMessages.AUTO_DETECTION_SUCCESS.format(
            filename="test.jpg",
            detected_type="jpeg",
            method="content",
            confidence=0.95
        )
        assert "test.jpg" in formatted
        assert "jpeg" in formatted
        assert "content" in formatted
        assert "0.95" in formatted
        
        # Test message build completed
        formatted = MessageBuilderLogMessages.MESSAGE_BUILD_COMPLETED.format(
            block_count=3
        )
        assert "3" in formatted


class TestMessageBuilderErrorMessages:
    """Test cases for MessageBuilderErrorMessages constants."""
    
    def test_error_messages_are_strings(self):
        """Test that all error message constants are strings."""
        assert isinstance(MessageBuilderErrorMessages.INVALID_ROLE, str)
        assert isinstance(MessageBuilderErrorMessages.EMPTY_CONTENT, str)
        assert isinstance(MessageBuilderErrorMessages.INVALID_FORMAT, str)
        assert isinstance(MessageBuilderErrorMessages.CONTENT_SIZE_EXCEEDED, str)
        assert isinstance(MessageBuilderErrorMessages.CONTENT_BLOCK_LIMIT_EXCEEDED, str)
        assert isinstance(MessageBuilderErrorMessages.DETECTION_FAILED, str)
        assert isinstance(MessageBuilderErrorMessages.UNSUPPORTED_FORMAT, str)
        assert isinstance(MessageBuilderErrorMessages.DETECTION_CONFIDENCE_LOW, str)
        assert isinstance(MessageBuilderErrorMessages.BUILD_VALIDATION_FAILED, str)
        assert isinstance(MessageBuilderErrorMessages.NO_CONTENT_BLOCKS, str)
    
    def test_error_messages_contain_placeholders(self):
        """Test that error messages contain expected format placeholders."""
        # Role error should have role and valid_roles placeholders
        assert "{role}" in MessageBuilderErrorMessages.INVALID_ROLE
        assert "{valid_roles}" in MessageBuilderErrorMessages.INVALID_ROLE
        
        # Content type errors should have content_type placeholder
        assert "{content_type}" in MessageBuilderErrorMessages.EMPTY_CONTENT
        assert "{content_type}" in MessageBuilderErrorMessages.INVALID_FORMAT
        
        # Size errors should have size and limit placeholders
        assert "{size}" in MessageBuilderErrorMessages.CONTENT_SIZE_EXCEEDED
        assert "{limit}" in MessageBuilderErrorMessages.CONTENT_SIZE_EXCEEDED
        
        # Detection errors should have filename placeholder
        assert "{filename}" in MessageBuilderErrorMessages.DETECTION_FAILED
        assert "{error}" in MessageBuilderErrorMessages.DETECTION_FAILED
    
    def test_error_message_formatting(self):
        """Test that error messages can be formatted with sample data."""
        # Test invalid role message
        formatted = MessageBuilderErrorMessages.INVALID_ROLE.format(
            role="invalid",
            valid_roles=["user", "assistant"]
        )
        assert "invalid" in formatted
        assert "user" in formatted
        assert "assistant" in formatted
        
        # Test content size exceeded
        formatted = MessageBuilderErrorMessages.CONTENT_SIZE_EXCEEDED.format(
            size=5000000,
            limit=4000000,
            content_type="image"
        )
        assert "5000000" in formatted
        assert "4000000" in formatted
        assert "image" in formatted


class TestSupportedFormats:
    """Test cases for SupportedFormats constants."""
    
    def test_supported_formats_are_lists(self):
        """Test that format constants are lists."""
        assert isinstance(SupportedFormats.IMAGE_FORMATS, list)
        assert isinstance(SupportedFormats.DOCUMENT_FORMATS, list)
        assert isinstance(SupportedFormats.VIDEO_FORMATS, list)
    
    def test_image_formats(self):
        """Test image format support."""
        expected_formats = ["jpeg", "png", "gif", "webp"]
        assert all(fmt in SupportedFormats.IMAGE_FORMATS for fmt in expected_formats)
        assert len(SupportedFormats.IMAGE_FORMATS) >= len(expected_formats)
    
    def test_document_formats(self):
        """Test document format support."""
        expected_formats = ["pdf", "csv", "doc", "docx", "xls", "xlsx", "html", "txt", "md"]
        assert all(fmt in SupportedFormats.DOCUMENT_FORMATS for fmt in expected_formats)
        assert len(SupportedFormats.DOCUMENT_FORMATS) >= len(expected_formats)
    
    def test_video_formats(self):
        """Test video format support."""
        expected_formats = ["mp4", "mov", "avi", "webm", "mkv"]
        assert all(fmt in SupportedFormats.VIDEO_FORMATS for fmt in expected_formats)
        assert len(SupportedFormats.VIDEO_FORMATS) >= len(expected_formats)
    
    def test_get_all_supported_formats(self):
        """Test get_all_supported_formats class method."""
        all_formats = SupportedFormats.get_all_supported_formats()
        
        assert isinstance(all_formats, dict)
        assert "image" in all_formats
        assert "document" in all_formats
        assert "video" in all_formats
        
        assert all_formats["image"] == SupportedFormats.IMAGE_FORMATS
        assert all_formats["document"] == SupportedFormats.DOCUMENT_FORMATS
        assert all_formats["video"] == SupportedFormats.VIDEO_FORMATS
    
    def test_format_uniqueness(self):
        """Test that formats don't overlap between categories."""
        image_set = set(SupportedFormats.IMAGE_FORMATS)
        document_set = set(SupportedFormats.DOCUMENT_FORMATS)
        video_set = set(SupportedFormats.VIDEO_FORMATS)
        
        # No overlap between image and document formats
        assert len(image_set.intersection(document_set)) == 0
        
        # No overlap between image and video formats
        assert len(image_set.intersection(video_set)) == 0
        
        # No overlap between document and video formats
        assert len(document_set.intersection(video_set)) == 0
    
    def test_format_strings_are_lowercase(self):
        """Test that all format strings are lowercase."""
        all_formats = (
            SupportedFormats.IMAGE_FORMATS +
            SupportedFormats.DOCUMENT_FORMATS +
            SupportedFormats.VIDEO_FORMATS
        )
        
        for format_str in all_formats:
            assert format_str == format_str.lower(), f"Format '{format_str}' should be lowercase"
            assert format_str.isalnum() or format_str.isalpha(), f"Format '{format_str}' should be alphanumeric"


class TestConstantIntegrity:
    """Test overall constant integrity and consistency."""
    
    def test_no_empty_constants(self):
        """Test that no constants are empty."""
        # Test string constants are not empty
        assert MessageBuilderFields.ROLE != ""
        assert MessageBuilderLogMessages.AUTO_DETECTION_SUCCESS != ""
        assert MessageBuilderErrorMessages.INVALID_ROLE != ""
        
        # Test list constants are not empty
        assert len(SupportedFormats.IMAGE_FORMATS) > 0
        assert len(SupportedFormats.DOCUMENT_FORMATS) > 0
        assert len(SupportedFormats.VIDEO_FORMATS) > 0
    
    def test_constant_types_consistency(self):
        """Test that constants have consistent types within their groups."""
        # All field constants should be strings
        field_attrs = [attr for attr in dir(MessageBuilderFields) if not attr.startswith('_')]
        for attr_name in field_attrs:
            attr_value = getattr(MessageBuilderFields, attr_name)
            assert isinstance(attr_value, str), f"{attr_name} should be a string"
        
        # All log message constants should be strings
        log_attrs = [attr for attr in dir(MessageBuilderLogMessages) if not attr.startswith('_')]
        for attr_name in log_attrs:
            attr_value = getattr(MessageBuilderLogMessages, attr_name)
            assert isinstance(attr_value, str), f"{attr_name} should be a string"
    
    def test_format_placeholder_consistency(self):
        """Test that format placeholders are consistent across messages."""
        # Common placeholders that should appear in multiple messages
        filename_messages = [
            MessageBuilderLogMessages.AUTO_DETECTION_SUCCESS,
            MessageBuilderLogMessages.DETECTION_MISMATCH,
            MessageBuilderErrorMessages.DETECTION_FAILED
        ]
        
        for message in filename_messages:
            assert "{filename}" in message, f"Message should contain filename placeholder: {message}"
        
        # Content type messages
        content_type_messages = [
            MessageBuilderErrorMessages.EMPTY_CONTENT,
            MessageBuilderErrorMessages.INVALID_FORMAT,
            MessageBuilderErrorMessages.CONTENT_SIZE_EXCEEDED
        ]
        
        for message in content_type_messages:
            assert "{content_type}" in message, f"Message should contain content_type placeholder: {message}"
